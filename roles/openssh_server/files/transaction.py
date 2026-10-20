#!/usr/bin/python3
"""Root-only, host-local SSH port transaction; Ansible owns orchestration.

No credentials are captured. Timer and snapshot survive controller loss and boot.
The existing openssh_server role renders a candidate, never the live file during
this transaction. All live writes, confirmation and rollback share one lock.
"""

import base64
import datetime
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time


ROOT = Path('/var/lib/lit-openssh-finalize')
UNITS = Path('/etc/systemd/system')
UNIT = 'lit-openssh-rollback'
TARGET = Path('/etc/ssh/sshd_config.d/60-lit-hardening.conf')
HELPER = ROOT / 'transaction.py'


def run(*args, allowed=(0,)):
    result = subprocess.run(args, text=True, capture_output=True, check=False, timeout=30)
    if result.returncode not in allowed:
        raise RuntimeError('Command failed: ' + args[0] + ': ' + result.stderr.strip())
    return result.stdout.strip()


def files(require_target=True):
    paths = [Path('/etc/ssh/sshd_config'), Path('/etc/default/ssh'),
             Path('/etc/systemd/system/ssh.socket'), Path('/etc/systemd/system/ssh.service')]
    for directory in ('/etc/ssh/sshd_config.d', '/etc/systemd/system/ssh.socket.d',
                      '/etc/systemd/system/ssh.service.d'):
        root = Path(directory)
        if root.is_symlink():
            raise ValueError('Configuration directory must not be a symlink')
        if root.exists() and (root.stat().st_uid != 0 or root.stat().st_mode & 0o022):
            raise ValueError('Configuration directories must be protected and root-owned')
        paths.extend(sorted(root.glob('*.conf')))
    result = {}
    for path in sorted(set(paths)):
        if path.is_symlink():
            raise ValueError('Configuration symlinks require explicit assessment')
        if path.exists():
            info = path.stat()
            if not path.is_file():
                raise ValueError('Configuration must be a regular file')
            if info.st_uid != 0 or info.st_mode & 0o022:
                raise ValueError('Configuration must be protected and root-owned')
            if str(path).startswith('/etc/ssh/'):
                for line in path.read_text().splitlines():
                    words = shlex.split(line, comments=True)
                    if words and words[0].lower() == 'include' and words[1:] != ['/etc/ssh/sshd_config.d/*.conf']:
                        raise ValueError('External SSH Includes require explicit snapshot assessment')
            result[str(path)] = dict(content=base64.b64encode(path.read_bytes()).decode(),
                                     mode=info.st_mode & 0o777, uid=info.st_uid, gid=info.st_gid)
    if require_target and str(TARGET) not in result:
        raise ValueError('Existing managed SSH drop-in required')
    return result


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def ports():
    result = set()
    for line in run('/usr/bin/ss', '-H', '-ltn').splitlines():
        result.add(int(line.split()[3].rsplit(':', 1)[1]))
    return result


def check_ports(request):
    effective = {int(line.split()[1]) for line in run('/usr/sbin/sshd', '-T').splitlines()
                 if line.startswith('port ')}
    desired, retired = set(request['ports']), set(request['retired_ports'])
    actual = ports()
    if effective != desired or not desired <= actual or retired & actual:
        raise ValueError('Effective configuration or live listeners violate the port contract')


def guard(request, require_hash):
    machine = Path('/etc/machine-id').read_text().strip()
    if machine != request['machine_id'] or not re.fullmatch(r'[0-9a-f]{32}', machine):
        raise ValueError('Target machine identity mismatch')
    connection = request['connection'].split()
    if len(connection) != 4 or int(connection[3]) not in request['ports']:
        raise ValueError('A fresh connection through a retained port is required')
    if not any(ipaddress.ip_address(connection[0]) in ipaddress.ip_network(net)
               for net in request['approved_sources']):
        raise ValueError('Unapproved controller source')
    if not re.fullmatch(r'[0-9a-f]{40}', request['source_revision']):
        raise ValueError('An exact approved source revision is required')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', request['ee_digest']):
        raise ValueError('An exact execution-environment digest is required')
    recovery = request['recovery']
    if (not recovery['reference'].strip() or recovery['machine_id'] != machine
            or not 0 <= time.time() - recovery['verified_at'] <= 86400):
        raise ValueError('A current independent administration/recovery receipt is required')
    desired, retired = request['ports'], request['retired_ports']
    if (not desired or not retired or set(desired) & set(retired)
            or any(type(port) is not int or not 1 <= port <= 65535 for port in desired + retired)):
        raise ValueError('Invalid desired or retired port list')
    snapshot = files()
    digest = fingerprint(snapshot)
    if require_hash and digest != request['expected_fingerprint']:
        raise ValueError('Configuration drift since the approved plan')
    run('/usr/sbin/sshd', '-t')
    if run('/usr/bin/systemctl', 'is-active', 'ssh.socket') != 'active':
        raise ValueError('This transaction requires active Ubuntu socket activation')
    return snapshot, digest


def save(state):
    atomic(ROOT / 'state.json', json.dumps(state).encode(), 0o600, 0, 0)


def atomic(path, content, mode, uid, gid):
    temporary = path.with_name(path.name + '.lit-new')
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
            os.fchown(stream.fileno(), uid, gid)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def reconcile(state):
    # Stop the daemon before the socket: an active daemon retains inherited FDs.
    run('/usr/bin/systemctl', 'stop', 'ssh.service')
    run('/usr/bin/systemctl', 'stop', 'ssh.socket')
    run('/usr/bin/systemctl', 'daemon-reload')
    for unit in ('ssh.socket', 'ssh.service'):
        if state[unit]['enabled'] in ('enabled', 'disabled'):
            run('/usr/bin/systemctl', state[unit]['enabled'][:-1], unit)
        if state[unit]['active']:
            run('/usr/bin/systemctl', 'start', unit)


def cancel_timer():
    run('/usr/bin/systemctl', 'disable', '--now', UNIT + '.timer')


def rollback(state):
    if state['status'] == 'confirmed':
        return False
    if state['status'] == 'rolled_back':
        if fingerprint(files()) != state['before']:
            raise ValueError('Configuration drift after completed rollback; refusing overwrite')
        return False
    # Retry even after a partial rollback. Never hide a failed reconciliation.
    for name in set(files(require_target=False)) - set(state['snapshot']):
        Path(name).unlink()
    for name, entry in state['snapshot'].items():
        atomic(Path(name), base64.b64decode(entry['content']), entry['mode'], entry['uid'], entry['gid'])
    run('/usr/sbin/sshd', '-t')
    reconcile(state['units'])
    if fingerprint(files()) != state['before']:
        raise ValueError('Rollback configuration verification failed')
    if not set(state['listeners']) <= ports():
        raise ValueError('Rollback listener verification failed')
    state['status'] = 'rolled_back'
    save(state)
    cancel_timer()
    return True


def apply(request, snapshot, digest):
    old = ROOT / 'state.json'
    if old.exists() and json.loads(old.read_text())['status'] == 'pending':
        raise ValueError('Another SSH transaction is pending')
    candidate = ROOT / 'staging' / 'candidate.conf'
    if candidate.is_symlink() or candidate.stat().st_uid != 0 or candidate.stat().st_mode & 0o022:
        raise ValueError('Candidate must be root-owned and protected')
    content = candidate.read_bytes()
    run('/usr/sbin/sshd', '-t', '-f', str(candidate))
    if content == base64.b64decode(snapshot[str(TARGET)]['content']):
        check_ports(request)
        return dict(changed=False, status='already_finalized', fingerprint=digest)
    state = dict(status='pending', token=request['transaction_id'], before=digest,
                 snapshot=snapshot, request=request, listeners=sorted(set(request['ports'] + request['retired_ports']) & ports()),
                 deadline=time.time() + 300, units={})
    for unit in ('ssh.socket', 'ssh.service'):
        state['units'][unit] = dict(
            active=run('/usr/bin/systemctl', 'is-active', unit, allowed=(0, 3)) == 'active',
            enabled=run('/usr/bin/systemctl', 'is-enabled', unit, allowed=(0, 1)))
    save(state)
    deadline = datetime.datetime.fromtimestamp(state['deadline'], datetime.timezone.utc)
    service = ('[Unit]\nDescription=Restore unconfirmed SSH configuration\n'
               '[Service]\nType=oneshot\nExecStart=/usr/bin/python3 ' + str(HELPER) + ' rollback\n'
               'Restart=on-failure\nRestartSec=5s\n')
    timer = ('[Unit]\nDescription=Bounded SSH confirmation deadline\n[Timer]\nOnCalendar='
             + deadline.strftime('%Y-%m-%d %H:%M:%S UTC')
             + '\nPersistent=true\nAccuracySec=1s\n[Install]\nWantedBy=timers.target\n')
    try:
        atomic(UNITS / (UNIT + '.service'), service.encode(), 0o644, 0, 0)
        atomic(UNITS / (UNIT + '.timer'), timer.encode(), 0o644, 0, 0)
        run('/usr/bin/systemctl', 'daemon-reload')
        run('/usr/bin/systemctl', 'enable', '--now', UNIT + '.timer')
        run('/usr/bin/systemctl', 'is-active', UNIT + '.timer')
        entry = snapshot[str(TARGET)]
        atomic(TARGET, content, entry['mode'], entry['uid'], entry['gid'])
        run('/usr/sbin/sshd', '-t')
        reconcile(state['units'])
        check_ports(request)
        state['after'] = fingerprint(files())
        if time.time() >= state['deadline']:
            raise ValueError('Confirmation deadline elapsed during apply')
        save(state)
    except Exception:
        rollback(state)
        raise
    return dict(changed=True, status='pending', transaction_id=state['token'],
                deadline=state['deadline'], fingerprint=state['after'])


def execute(action, request):
    if os.geteuid() != 0:
        raise PermissionError('Root required')
    if action == 'plan':
        _, digest = guard(request, False)
        status = 'none'
        if (ROOT / 'state.json').exists():
            status = json.loads((ROOT / 'state.json').read_text())['status']
        return dict(changed=False, fingerprint=digest, listeners=sorted(ports()), transaction_status=status)
    ROOT.mkdir(mode=0o700, exist_ok=True)
    if ROOT.is_symlink() or ROOT.stat().st_uid != 0 or ROOT.stat().st_mode & 0o077:
        raise PermissionError('Transaction directory must be root-only')
    with (ROOT / 'lock').open('a') as lock:
        os.chmod(ROOT / 'lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        if action == 'apply':
            snapshot, digest = guard(request, True)
            return apply(request, snapshot, digest)
        state = json.loads((ROOT / 'state.json').read_text())
        if action == 'rollback':
            return dict(changed=rollback(state), status=state['status'])
        if action != 'confirm' or request['transaction_id'] != state['token']:
            raise ValueError('Unknown action or transaction identity mismatch')
        if state['status'] == 'confirmed':
            return dict(changed=False, status='confirmed')
        if state['status'] != 'pending' or time.time() >= state['deadline']:
            if state['status'] == 'pending':
                rollback(state)
            raise ValueError('Transaction is not pending within its deadline')
        guard(request, False)
        immutable = ('machine_id', 'ports', 'retired_ports', 'source_revision', 'ee_digest', 'approved_sources')
        if (fingerprint(files()) != state['after']
                or any(request[key] != state['request'][key] for key in immutable)):
            raise ValueError('Configuration or desired-state drift before confirmation')
        if request['connection'] == state['request']['connection']:
            raise ValueError('Confirmation must use a new authenticated SSH transport')
        check_ports(request)
        state['status'] = 'confirmed'
        save(state)
        cancel_timer()
        return dict(changed=True, status='confirmed', fingerprint=state['after'])


if __name__ == '__main__':
    try:
        print(json.dumps(execute(sys.argv[1], json.load(sys.stdin) if sys.argv[1] != 'rollback' else {})))
    except Exception as error:
        print(json.dumps(dict(failed=True, error=str(error))))
        sys.exit(1)
