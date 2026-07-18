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
- `incus_preseed` (mapping, default: `{}`): Optional preseed passed to `incus admin init --preseed` instead of the
  minimal initializer. It is used only when storage discovery succeeds and no storage pool exists.
- `incus_projects` (list, default: `[]`): Projects to create and project configuration keys to reconcile.
- `incus_profiles` (list, default: `[]`): Project-scoped profiles whose description, configuration, and devices are
  reconciled exactly.
- `incus_services` (list): Systemd units to enable and start.
- `incus_users` (list, default: `[]`): Users to add to `incus_user_groups`.
- `incus_user_groups` (list, default: `["incus-admin", "kvm"]`): Runtime groups for Incus users.

Storage, project, and profile discovery failures stop the role before any related mutation. The default minimal
initializer does not expose the Incus API remotely. A remote listener is configured only when the caller explicitly
supplies the relevant server configuration in `incus_preseed`.

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
        incus_preseed:
          storage_pools:
            - name: default
              driver: dir
        incus_projects:
          - name: development
            config:
              features.images: "false"
        incus_profiles:
          - name: workbench
            project: development
            description: Workbench VM defaults
            config:
              limits.cpu: "4"
            devices:
              root:
                type: disk
                path: /
                pool: default
```

## License

MIT

## Author

Lightning IT
