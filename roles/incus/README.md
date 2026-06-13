# lit.ubuntu.incus

Configure an Ubuntu host as an Incus host for system containers and virtual
machines. For VM workloads, Incus manages the instance lifecycle while QEMU/KVM
provides hardware virtualization.

## Requirements

- Ubuntu target with systemd.
- Root privileges on the target host.

## Variables

See `defaults/main.yml` for the full interface. Key variables:

- `incus_packages` (list): Packages installed for Incus and QEMU support.
- `incus_initialize` (bool, default: `true`): Run `incus admin init --minimal` when Incus is not initialized.
- `incus_services` (list): Systemd units to enable and start.
- `incus_users` (list, default: `[]`): Users to add to `incus_user_groups`.
- `incus_user_groups` (list, default: `["incus-admin", "kvm"]`): Runtime groups for Incus users.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Configure Incus hosts
  hosts: incus_hosts
  become: true
  roles:
    - role: lit.ubuntu.incus
      vars:
        incus_users:
          - litadm
          - github-runner
```

## License

GPL-3.0-only

## Author

Lightning IT
