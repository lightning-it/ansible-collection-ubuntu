# Podman Role

Installs Podman tooling and prepares the container configuration directory.

## Requirements

None.

## Variables

- `podman_packages`: package list installed via `ansible.builtin.package`
  (default: `["podman", "buildah"]`)
- `podman_registries_conf_dir`: directory ensured present for registry
  configuration files (default: `/etc/containers`)

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.podman
  hosts: all
  become: true
  roles:
    - role: lit.ubuntu.podman
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Usage

```yaml
- hosts: all
  become: true
  roles:
    - role: lit.ubuntu.podman
      vars:
        podman_packages:
          - podman
          - buildah
        podman_registries_conf_dir: /etc/containers
```
