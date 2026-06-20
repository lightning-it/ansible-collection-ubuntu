# lit.ubuntu.incus_instance

Manage Incus instance lifecycle on Ubuntu Incus hosts.

The role creates, starts, stops, or deletes Incus instances, injects cloud-init
user-data, waits for IP/SSH readiness, and can write a small generated inventory
file for follow-up plays.

It also supports empty VMs and arbitrary disk devices, which makes it suitable
for ISO-driven installers such as OpenShift Agent-based lab installs without
putting product-specific logic into the Incus role.

## Requirements

- Ubuntu Incus host.
- `incus` CLI installed and usable by the Ansible connection user, or set
  `incus_instance_command_user` to run Incus commands as another local user.
- Required Incus image aliases already imported, for example with
  `lit.ubuntu.incus_image`.

## Variables

See `defaults/main.yml` for the full interface. Key variables:

- `incus_instance_items` (list, default: `[]`): Instance definitions.
- `incus_instance_binary` (string, default: `incus`): Incus CLI path or command.
- `incus_instance_command_user` (string, default: `""`): Optional local user for Incus commands.
- `incus_instance_default_type` (string, default: `vm`): Default instance type, `vm` or `container`.
- `incus_instance_default_state` (string, default: `running`): Default target state.
- `incus_instance_default_empty` (boolean, default: `false`): Create instances with `incus init --empty`.
- `incus_instance_default_reconfigure` (boolean, default: `false`): Reapply config, limits, and devices to
  existing instances.
- `incus_instance_default_ssh_user` (string, default: `cloud-user`): Cloud-init login user.
- `incus_instance_default_ssh_public_keys` (list, default: `[]`): Public SSH keys injected with cloud-init.
- `incus_instance_inventory_path` (string, default: `""`): Optional controller-side inventory output file.

Each `incus_instance_items` entry supports:

- `name`: Incus instance name.
- `image`: Incus image reference.
- `image_candidates`: Optional fallback image references. The first existing image is used.
- `state`: `running`, `present`, `stopped`, or `absent`.
- `type`: `vm` or `container`.
- `empty`: Create an empty instance instead of using an image.
- `reconfigure`: Reapply config, limits, and devices when the instance already exists.
- `project`, `profiles`, `config`, `devices`, `limits`.
- `hostname`, `fqdn`, `ssh_user`, `ssh_public_keys`.
- `cloud_init_enabled`, `cloud_init_user_data`, `cloud_init_network_config`.
- `wait_for_ip`, `wait_for_ssh`, `wait_timeout`, `wait_delay`.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Create RHEL AAP test VM in Incus
  hosts: incus_hosts
  become: true
  roles:
    - role: lit.ubuntu.incus_instance
      vars:
        incus_instance_command_user: github-runner
        incus_instance_default_ssh_public_keys:
          - "{{ lookup('ansible.builtin.file', '~/.ssh/id_ed25519.pub') }}"
        incus_instance_inventory_path: /tmp/aap-test-inventory.yml
        incus_instance_items:
          - name: aap-ci-rhel10
            image_candidates:
              - local:rhel10-ci
              - local:rhel10
            type: vm
            state: running
            fqdn: aap-ci-rhel10.example.com
```

```yaml
---
- name: Create empty ISO-booted VMs
  hosts: incus_hosts
  become: true
  roles:
    - role: lit.ubuntu.incus_instance
      vars:
        incus_instance_items:
          - name: ocp-agent-master-0
            empty: true
            type: vm
            state: running
            cloud_init_enabled: false
            wait_for_ip: false
            wait_for_ssh: false
            reconfigure: true
            limits:
              cpu: "4"
              memory: 16GiB
            devices:
              root:
                type: disk
                path: /
                pool: default
                size: 120GiB
              agent-iso:
                type: disk
                source: /runner/project/agent-example.x86_64.iso
                boot.priority: "10"
              eth0:
                type: nic
                network: incusbr0
                hwaddr: "00:16:3e:10:20:30"
```

## License

MIT

## Author

Lightning IT
