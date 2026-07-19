# lit.ubuntu.github_runner

Install and register one or more isolated GitHub Actions self-hosted runners on Ubuntu.

## Requirements

- Ubuntu target with systemd when `github_runner_manage_service` is enabled.
- Root privileges on the target host.
- A short-lived GitHub runner registration token when registering a new runner
  or replacing an existing registration.

## Variables

See `defaults/main.yml` for the full interface. Key variables:

- `github_runner_version` (string, default: `"2.335.1"`): Pinned GitHub runner version.
- `github_runner_url` (string, default: `""`): Repository or organization URL for runner registration.
- `github_runner_runner_group` (string, default: `""`): Optional organization runner group.
- `github_runner_registration_token` (string, default: `""`): Short-lived registration token.
- `github_runner_remove_token` (string, default: `""`): Short-lived runner removal token.
- `github_runner_name` (string, default: inventory host short name): Runner name in GitHub.
- `github_runner_labels` (list): Labels passed to `config.sh`.
- `github_runner_user_groups_extra` (list, default: `[]`): Extra groups for the runner user.
- `github_runner_replace` (bool, default: `false`): Remove and recreate an existing runner registration.
- `github_runner_manage_service` (bool, default: `true`): Install and manage the systemd service.
- `github_runner_instances` (list): Runner instances. Each mapping requires unique `name`, `dir`, and relative
  `work_dir` values, plus `labels`; optional per-instance keys are `runner_group`, `registration_token`, `remove_token`,
  `replace`, `state`, `service_state`, `external_service_name`, and `external_service_unit_path`. The external service
  keys allow an absent-state migration to stop, disable, and remove a pre-existing systemd unit before deleting its
  registration and installation tree. Its default maps the legacy single-runner variables, preserving backward
  compatibility.

Set an instance to `state: absent` with a fresh remove token to unregister it, uninstall its service, and remove its
installation directory. Set `replace: true` only for the instance that must be re-registered and provide both fresh
token types. Runner services are
installed from each instance directory, enabled when `service_state: started`, and therefore survive reboots.

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
    github_runner_instances:
      - name: incus-runner-01
        dir: /opt/actions-runner-01
        work_dir: _work-01
        labels: [self-hosted, linux, x64, incus, nested-virt]
        registration_token: "{{ lookup('ansible.builtin.env', 'GITHUB_RUNNER_TOKEN') }}"
        state: present
        service_state: started
      - name: incus-runner-02
        dir: /opt/actions-runner-02
        work_dir: _work-02
        labels: [self-hosted, linux, x64, incus, nested-virt]
        registration_token: "{{ lookup('ansible.builtin.env', 'GITHUB_RUNNER_TOKEN') }}"
        state: present
        service_state: started
  roles:
    - role: lit.ubuntu.incus
    - role: lit.ubuntu.github_runner
      vars:
        github_runner_url: "https://github.com/example-org/example-repo"
```

## License

MIT

## Author

Lightning IT
