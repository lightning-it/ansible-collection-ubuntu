# Baseline Role

Installs a minimal set of operational packages and configures timezone and locale.

## Requirements

None.

## Variables

- `baseline_packages_present`: list of packages to ensure are installed (default: `["vim", "jq", "tar", "bash-completion"]`)
- `baseline_timezone`: IANA timezone string configured via `community.general.timezone` (default: `Etc/UTC`, set empty to skip)
- `baseline_locale`: locale string written to `/etc/default/locale` (default: `en_US.UTF-8`, set empty to skip)

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.baseline
  hosts: all
  become: true
  roles:
    - role: lit.ubuntu.baseline
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Usage

```yaml
- hosts: all
  roles:
    - role: lit.ubuntu.baseline
      vars:
        baseline_packages_present:
          - vim
        baseline_timezone: Europe/Berlin
        baseline_locale: en_US.UTF-8
```
