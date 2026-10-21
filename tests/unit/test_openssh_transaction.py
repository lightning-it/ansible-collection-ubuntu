"""Deterministic safety regressions; real systemd acceptance is separate."""

import base64
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[2] / 'roles/openssh_server/files/transaction.py'
SPEC = importlib.util.spec_from_file_location('ssh_transaction', SOURCE)
TX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TX)


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.target = self.root / 'hardening.conf'
        self.target.write_text('Port 22\nPort 1905\n')
        self.snapshot = {str(self.target): dict(
            content=base64.b64encode(self.target.read_bytes()).decode(), mode=0o600, uid=0, gid=0)}
        self.request = dict(machine_id='a' * 32, connection='192.0.2.1 40000 192.0.2.2 1905',
                            approved_sources=['192.0.2.1/32'], source_revision='b' * 40,
                            ee_digest='sha256:' + 'c' * 64, ports=[1905], retired_ports=[22],
                            recovery=dict(reference='protected-receipt', machine_id='a' * 32,
                                          verified_at=time.time()), transaction_id='test-transaction',
                            expected_fingerprint=TX.fingerprint(self.snapshot))
        self.units = {name: dict(enabled='enabled', active=True) for name in ('ssh.socket', 'ssh.service')}
        self.state = dict(status='pending', token='test-transaction', before=TX.fingerprint(self.snapshot),
                          after=TX.fingerprint(self.snapshot), snapshot=self.snapshot, request=dict(self.request),
                          deadline=time.time() + 300, units=self.units, listeners=[22, 1905])

    def guard_context(self):
        return patch.multiple(TX, files=lambda: self.snapshot, run=lambda *a, **kw: 'active')

    def test_wrong_machine_fails_before_snapshot(self):
        with patch.object(Path, 'read_text', return_value='d' * 32), patch.object(TX, 'files') as snapshot:
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                TX.guard(self.request, True)
            snapshot.assert_not_called()

    def test_unapproved_source_fails_before_snapshot(self):
        self.request['approved_sources'] = ['198.51.100.0/24']
        with patch.object(Path, 'read_text', return_value='a' * 32), patch.object(TX, 'files') as snapshot:
            with self.assertRaisesRegex(ValueError, 'Unapproved'):
                TX.guard(self.request, True)
            snapshot.assert_not_called()

    def test_retired_transport_is_rejected(self):
        self.request['connection'] = '192.0.2.1 40000 192.0.2.2 22'
        with patch.object(Path, 'read_text', return_value='a' * 32), patch.object(TX, 'files') as snapshot:
            with self.assertRaisesRegex(ValueError, 'retained port'):
                TX.guard(self.request, True)
            snapshot.assert_not_called()

    def test_missing_or_expired_recovery_is_rejected(self):
        for age in (-1, 86401):
            self.request['recovery']['verified_at'] = time.time() - age
            with self.subTest(age=age), patch.object(Path, 'read_text', return_value='a' * 32):
                with self.assertRaisesRegex(ValueError, 'recovery receipt'):
                    TX.guard(self.request, True)

    def test_source_and_environment_are_exact(self):
        for key in ('source_revision', 'ee_digest'):
            with self.subTest(key=key), patch.object(Path, 'read_text', return_value='a' * 32):
                original = self.request[key]
                self.request[key] = 'latest'
                with self.assertRaises(ValueError):
                    TX.guard(self.request, True)
                self.request[key] = original

    def test_drift_fails_before_systemd(self):
        self.request['expected_fingerprint'] = 'd' * 64
        with patch.object(Path, 'read_text', return_value='a' * 32), \
                patch.object(TX, 'files', return_value=self.snapshot), patch.object(TX, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'drift'):
                TX.guard(self.request, True)
            run.assert_not_called()

    def test_plan_does_not_create_transaction_directory(self):
        with patch.object(TX, 'ROOT', self.root / 'absent'), patch.object(os_module(), 'geteuid', return_value=0), \
                patch.object(TX, 'guard', return_value=(self.snapshot, 'digest')), \
                patch.object(TX, 'ports', return_value={22, 1905}):
            result = TX.execute('plan', self.request)
            self.assertFalse(result['changed'])
            self.assertFalse((self.root / 'absent').exists())

    def test_retired_listener_in_any_family_blocks_acceptance(self):
        with patch.object(TX, 'run', return_value='port 1905'), patch.object(TX, 'ports', return_value={22, 1905}):
            with self.assertRaisesRegex(ValueError, 'listeners'):
                TX.check_ports(self.request)

    def test_extra_effective_port_blocks_acceptance(self):
        with patch.object(TX, 'run', return_value='port 1905\nport 2222'), \
                patch.object(TX, 'ports', return_value={1905}):
            with self.assertRaises(ValueError):
                TX.check_ports(self.request)

    def test_reconcile_stops_inherited_socket_before_reload(self):
        with patch.object(TX, 'run') as run:
            TX.reconcile(self.units)
            self.assertEqual([tuple(c.args) for c in run.call_args_list][:3], [
                ('/usr/bin/systemctl', 'stop', 'ssh.service'),
                ('/usr/bin/systemctl', 'stop', 'ssh.socket'),
                ('/usr/bin/systemctl', 'daemon-reload')])

    def test_confirm_cannot_reuse_old_transport(self):
        self.write_state()
        with self.execution_context(), patch.object(TX, 'guard'), \
                patch.object(TX, 'files', return_value=self.snapshot), patch.object(TX, 'cancel_timer') as cancel:
            with self.assertRaisesRegex(ValueError, 'new authenticated'):
                TX.execute('confirm', self.request)
            cancel.assert_not_called()

    def test_confirm_cannot_change_retirement_contract(self):
        self.write_state()
        self.request['retired_ports'] = [23]
        with self.execution_context(), patch.object(TX, 'guard'), \
                patch.object(TX, 'files', return_value=self.snapshot), patch.object(TX, 'cancel_timer') as cancel:
            with self.assertRaisesRegex(ValueError, 'drift'):
                TX.execute('confirm', self.request)
            cancel.assert_not_called()

    def test_expired_confirmation_rolls_back_and_never_confirms(self):
        self.state['deadline'] = time.time() - 1
        self.write_state()
        with self.execution_context(), patch.object(TX, 'rollback') as rollback:
            with self.assertRaisesRegex(ValueError, 'deadline'):
                TX.execute('confirm', self.request)
            rollback.assert_called_once()

    def test_correct_confirmation_persists_before_timer_cancel(self):
        self.write_state()
        self.request['connection'] = '192.0.2.1 40001 192.0.2.2 1905'
        events = []
        with self.execution_context(), patch.object(TX, 'guard'), \
                patch.object(TX, 'files', return_value=self.snapshot), patch.object(TX, 'check_ports'), \
                patch.object(TX, 'save', side_effect=lambda s: events.append(s['status'])), \
                patch.object(TX, 'cancel_timer', side_effect=lambda: events.append('cancel')):
            self.assertEqual(TX.execute('confirm', self.request)['status'], 'confirmed')
            self.assertEqual(events, ['confirmed', 'cancel'])

    def test_confirmed_transaction_is_never_rolled_back(self):
        self.state['status'] = 'confirmed'
        with patch.object(TX, 'atomic') as write:
            self.assertFalse(TX.rollback(self.state))
            write.assert_not_called()

    def test_pending_transaction_blocks_new_apply(self):
        self.write_state()
        with patch.object(TX, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'pending'):
                TX.apply(self.request, self.snapshot, self.state['before'])

    def test_identical_candidate_checks_listener_state_without_timer(self):
        (self.root / 'staging').mkdir()
        (self.root / 'staging' / 'candidate.conf').write_bytes(self.target.read_bytes())
        with self.execution_context(), patch.object(TX, 'TARGET', self.target), \
                patch.object(TX, 'run'), patch.object(TX, 'check_ports') as ports, patch.object(TX, 'save') as save:
            result = TX.apply(self.request, self.snapshot, self.state['before'])
            self.assertFalse(result['changed'])
            ports.assert_called_once()
            save.assert_not_called()

    def write_state(self):
        (self.root / 'state.json').write_text(json.dumps(self.state))

    @contextmanager
    def execution_context(self):
        original = Path.stat

        def root_owned(path, **kwargs):
            values = list(original(path, **kwargs))
            values[4] = 0
            values[5] = 0
            return os.stat_result(values)

        with patch.object(TX, 'ROOT', self.root), patch.object(TX.os, 'geteuid', return_value=0), \
                patch.object(Path, 'stat', root_owned):
            yield


def os_module():
    return TX.os


if __name__ == '__main__':
    unittest.main()
