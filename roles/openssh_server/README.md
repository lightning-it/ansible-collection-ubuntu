# lit.ubuntu.openssh_server

Render and validate an Ubuntu OpenSSH server drop-in, manage the daemon, and verify every declared local listener.
When Ubuntu socket activation is already active, the role reloads systemd and restarts `ssh.socket` before restarting
the daemon so the generated socket listeners follow the validated port list.

The secure defaults disable root, password, keyboard-interactive, empty-password, and X11 authentication while
retaining public-key authentication and PAM account/session handling. The role manages configuration only; it never
creates accounts, installs authorized keys, or changes firewall policy.

## Requirements

- Ubuntu 22.04 or 24.04 and an Ansible version supported by this collection's `meta/runtime.yml`.
- Privilege escalation when package, `/etc/ssh`, systemd service, or systemd socket state is managed.
- A working public-key account and an independently managed firewall rule before password authentication is disabled.
- An existing control session or out-of-band access during listener transitions. Keep both old and new ports declared
  until controller reachability on the new port has been proven.

OpenSSH must include the configured drop-in directory from its primary `sshd_config`. The Ubuntu package does this by
default. A drop-in loaded earlier than `openssh_server_config_path` can take precedence for single-value directives;
remove conflicting unmanaged configuration before relying on this role.

## Variables

See `defaults/main.yml` for the complete interface. Important inputs are:

- `openssh_server_enabled`: apply the role; defaults to `true`.
- `openssh_server_ports`: nonempty list of unique integer TCP ports; defaults to `[22]`.
- `openssh_server_listen_addresses`: optional addresses on which `sshd` listens. When set, align
  `openssh_server_listener_verify_host` with one of those addresses.
- `openssh_server_allow_users`: optional exact local-account allowlist. Entries are validated before templating.
- `openssh_server_config_path`: managed drop-in path; defaults to
  `/etc/ssh/sshd_config.d/60-lit-hardening.conf`.
- `openssh_server_manage_packages` and `openssh_server_manage_service`: independently control package and service
  lifecycle management.
- `openssh_server_validate_config`: validate the candidate drop-in and the effective server configuration with
  `sshd -t` before handlers run. During a fresh check-mode run, validation is skipped if the binary is not installed.
- `openssh_server_manage_socket_activation`: reconcile an already active `ssh.socket` with the requested service state
  and restart it after configuration changes. The role does not opt an inactive host into socket activation.
- `openssh_server_verify_listeners`: wait for every declared port locally after pending handlers have completed.
- `openssh_server_permit_root_login`, `openssh_server_password_authentication`,
  `openssh_server_kbd_interactive_authentication`, `openssh_server_pubkey_authentication`,
  `openssh_server_permit_empty_passwords`, `openssh_server_x11_forwarding`, and `openssh_server_use_pam`: explicit
  OpenSSH security controls.

### Guarded port retirement

Use `tasks_from: finalize` explicitly for Ubuntu 24 socket-activated port retirement.
Normal role execution and bootstrap transitions retain their existing behavior.
This entrypoint supports `openssh_server_finalize_action: plan | apply | confirm | rollback`.
It uses the existing role to render a protected candidate before touching live SSH.
The live managed path is deliberately fixed to `/etc/ssh/sshd_config.d/60-lit-hardening.conf`.
Packages, accounts, keys, sudo, firewall policy and initramfs recovery are outside this transaction.

Required inputs from approved inventory and the current execution receipt:

| Variable | Contract |
| --- | --- |
| `openssh_server_ports` | Retained ports, also used by the ordinary role |
| `openssh_server_finalize_retired_ports` | Explicit ports that must be absent; default `[22]` |
| `openssh_server_finalize_machine_id` | Independently verified `/etc/machine-id`, 32 hex characters |
| `openssh_server_finalize_approved_sources` | Nonempty management-source CIDRs, checked against actual SSH transport |
| `openssh_server_finalize_source_revision` | Approved immutable 40-character source commit |
| `openssh_server_finalize_ee_digest` | Actual controller EE `sha256:` digest |
| `openssh_server_finalize_recovery` | Independent receipt with `reference`, `machine_id`, Unix `verified_at`; at most 24 hours old |
| `openssh_server_finalize_expected_fingerprint` | Exact configuration fingerprint returned by the reviewed plan; apply only |
| `openssh_server_finalize_transaction_id` | Unique 8–64 character alphanumeric/underscore/hyphen identifier; apply and confirm |

Obtain the recovery receipt through an independently tested administration or recovery
path. A saved SSH session, a configured recovery port or an invented receipt is insufficient.
The role validates the receipt binding and age; the operator remains responsible for
the referenced evidence and protected publication approval. No secrets belong in this input.

`plan` authenticates a new retained-port transport and reports the observed fingerprint
without creating transaction files. Wrong identity, source, stale recovery evidence or
configuration drift fails before a live configuration write. Check mode is rejected;
use `plan` instead.

`apply` stages a candidate through `openssh_server`, then rechecks the fingerprint under
a host-local lock. Before its atomic live write, it records the configuration and unit
state in root-only `/var/lib/lit-openssh-finalize`, enables a persistent host-side timer
with a **300-second** deadline, and verifies that timer is active. The transaction validates
the complete configuration, stops daemon then socket to release inherited descriptors,
reloads the systemd generator and restores the prior enabled/active unit states.
It never edits generated systemd files. A local apply error immediately restores the
snapshot. Controller loss or missing confirmation triggers the timer independently.

Run `confirm` separately within the deadline using the same transaction identity and
immutable contract. It resets SSH transport, authenticates anew through a retained port,
and checks syntax, effective ports, unchanged configuration and absent retired listeners
across both address families before canceling rollback. Reusing the apply transport or
confirming after the deadline is rejected. A confirmed transaction is never rolled back
by a stale timer. Preserve timer failure evidence; its service retries failed rollback.

An identical later `apply`, using a new reviewed plan fingerprint, checks effective
configuration/listeners and reports `already_finalized` without arming another timer.
Keep snapshot/state for audit; do not publish their contents. Reboot, external service
access, permitted forwarding and negative-access acceptance remain separate mandatory
operator checks. No production acceptance is implied by this interface or unit tests.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Configure OpenSSH with a safe transition listener
  hosts: ubuntu_hosts
  become: true
  roles:
    - role: lit.ubuntu.openssh_server
      vars:
        openssh_server_ports:
          - 22
          - 2222
```

For port retirement, supply the mandatory verified evidence through inventory or a
protected execution input file, then select the action explicitly:

```yaml
---
- name: Inspect an approved single-host SSH finalization plan
  hosts: exact_ubuntu_target
  become: true
  gather_facts: false
  tasks:
    - name: Plan the bounded transaction
      ansible.builtin.include_role:
        name: lit.ubuntu.openssh_server
        tasks_from: finalize
      vars:
        openssh_server_finalize_action: plan
```

## License

MIT

## Author

Lightning IT
