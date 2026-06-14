# Podman Role

Installs Podman tooling and prepares the container configuration directory.

## Usage

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

## Variables

- `podman_packages`: package list installed via `ansible.builtin.package`
  (default: `["podman", "buildah"]`)
- `podman_registries_conf_dir`: directory ensured present for registry
  configuration files (default: `/etc/containers`)
