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
- `openssh_server_config_owner` and `openssh_server_config_group`: ownership for
  the managed directory and drop-in; both default to `root`. Setting either to
  `null` preserves the current ownership, which is useful for isolated,
  unprivileged validation paths.
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

## License

MIT

## Author

Lightning IT
