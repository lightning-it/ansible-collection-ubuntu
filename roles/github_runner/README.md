# lit.ubuntu.github_runner

Install and register a GitHub Actions self-hosted runner on Ubuntu.

## Requirements

- Ubuntu target with systemd when `github_runner_manage_service` is enabled.
- Root privileges on the target host.
- A short-lived GitHub runner registration token when registering a new runner
  or replacing an existing registration.

## Variables

See `defaults/main.yml` for the full interface. Key variables:

- `github_runner_version` (string, default: `"2.335.1"`): Pinned GitHub runner version.
- `github_runner_url` (string, default: `""`): Repository or organization URL for runner registration.
- `github_runner_registration_token` (string, default: `""`): Short-lived registration token.
- `github_runner_name` (string, default: inventory host short name): Runner name in GitHub.
- `github_runner_labels` (list): Labels passed to `config.sh`.
- `github_runner_user_groups_extra` (list, default: `[]`): Extra groups for the runner user.
- `github_runner_replace` (bool, default: `false`): Remove and recreate an existing runner registration.
- `github_runner_manage_service` (bool, default: `true`): Install and manage the systemd service.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Configure GitHub Actions runner
  hosts: github_runners
  become: true
  vars:
    incus_enabled: true
    github_runner_user_groups_extra: "{{ incus_user_groups | default(['incus-admin', 'kvm']) }}"
  roles:
    - role: lit.ubuntu.incus
    - role: lit.ubuntu.github_runner
      vars:
        github_runner_url: "https://github.com/example-org/example-repo"
        github_runner_registration_token: "{{ lookup('ansible.builtin.env', 'GITHUB_RUNNER_TOKEN') }}"
        github_runner_labels:
          - self-hosted
          - linux
          - x64
```

## License

MIT

## Author

Lightning IT
