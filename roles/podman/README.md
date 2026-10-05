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
- `podman_apparmor_profile_reload`: restore Ubuntu's package-compatible
  unconfined Podman attachment declaration and reload only that profile
  (default: `false`)
- `podman_apparmor_profile_path`: Podman AppArmor profile path (default:
  `/etc/apparmor.d/podman`)
- `podman_buildah_apparmor_profile_reload`: restore and reload the
  package-compatible unconfined Buildah attachment profile (default: `false`)
- `podman_buildah_apparmor_profile_path`: Buildah AppArmor profile path
  (default: `/etc/apparmor.d/buildah`)
- `podman_helper_apparmor_profiles`: optional package-compatible helper
  attachment profiles to restore and reload as unconfined (default: `[]`)
- `podman_apparmor_parser_path`: AppArmor parser path used for a targeted
  `--replace` reload (default: `/usr/sbin/apparmor_parser`)
- `podman_executable_path`: Podman executable used by validation (default:
  `/usr/bin/podman`)
- `podman_validate_executable`: validate a direct `podman --version` invocation
  after optional profile repair (default: `false`)
- `podman_dns_authoritative_only`: opt-in no-forwarding startup policy for the
  shared Aardvark resolver (default: `false`, existing policy untouched).
  Requires `podman_dns_resolver_executable` and `podman_dns_resolver_sha256`
  to identify a reviewed build supporting `AARDVARK_NO_PROXY`. The effective
  Netavark DNS helper path reported by `podman info` must match that input;
  every helper ancestor must be a real root-owned non-writable directory.
  Dangling links at managed configuration paths are rejected before creation.
  If check mode predicts package installation, the DNS taskset is deferred:
  no executable inspection or startup-file write is attempted. A real apply
  must still pass every helper and checksum check before writing the policy.
  Requires Podman
  4.9.3 or later with append-capable `containers.conf`. The role writes one
  root-owned drop-in and appends the engine variable without replacing other
  engine environment entries. It does not restart a running resolver, alter
  network DNS settings or add firewall permissions. A separate controlled
  transition must inventory every shared resolver consumer (including secrets
  services), verify actual daemon policy after lifecycle changes, and prove
  expected internal resolution, external NXDOMAIN/no-forwarding and restart
  persistence. Config overrides can supersede the drop-in; its presence alone
  is not runtime acceptance. HTTP proxy egress remains independent.
- `podman_system_socket_enabled`: desired root `podman.socket` state when
  management is active; `true` also activates management for backward
  compatibility (default: `false`)
- `podman_system_socket_manage`: set to `true` to reconcile the root
  `podman.socket`; leave `false` to preserve its existing state (default:
  `false`). Setting `podman_system_socket_enabled: true` also implies
  management for backward compatibility.
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
