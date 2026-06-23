# Podman Role

Installs Podman tooling, prepares the container configuration directory, and
can enable Podman API sockets for workbench container workflows.

## Requirements

None.

## Variables

- `podman_packages`: package list installed via `ansible.builtin.package`
  (default: `["podman", "buildah"]`)
- `podman_registries_conf_dir`: directory ensured present for registry
  configuration files (default: `/etc/containers`)
- `podman_system_socket_enabled`: enable the root `podman.socket`
  (default: `false`)
- `podman_user_socket_enabled`: enable rootless user `podman.socket`
  instances (default: `false`)
- `podman_user_socket_users`: users that should get a rootless Podman API
  socket
- `podman_user_socket_manage_linger`: enable linger so user sockets can stay
  available without an interactive login (default: `true`)
- `podman_user_socket_manage_shell_init`: export `DOCKER_HOST` and
  `CONTAINER_HOST` for selected users (default: `true`)

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
        podman_user_socket_enabled: true
        podman_user_socket_users:
          - ops-admin
```
