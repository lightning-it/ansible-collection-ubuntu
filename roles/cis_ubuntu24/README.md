# CIS Ubuntu 24 Role

Thin wrapper around `ansible-lockdown.ubuntu24_cis`.

## Requirements

The execution environment must install `ansible-lockdown.ubuntu24_cis` as a Galaxy role.

## Variables

Configure the upstream role through inventory variables such as `ubtu24cis_level_1`,
`ubtu24cis_level_2`, `ubtu24cis_disruption_high`, `run_audit`, and `audit_only`.

## Dependencies

External Galaxy role: `ansible-lockdown.ubuntu24_cis`.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.cis_ubuntu24
  hosts: ubuntu24_cis_targets
  become: true
  roles:
    - role: lit.ubuntu.cis_ubuntu24
```

## License

MIT

## Author

Lightning IT
