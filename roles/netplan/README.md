# lit.ubuntu.netplan

Render and optionally apply Ubuntu netplan configuration.

## Requirements

- Ubuntu host with netplan installed.
- Existing interface names in `net_ifaces`, or provide `netplan_ethernets` directly.

## Variables

See `defaults/main.yml` for the full interface. Key variables:

- `netplan_config_path`: target netplan YAML file.
- `netplan_renderer`: netplan renderer, defaulting to `networkd`.
- `netplan_net_ifaces`: list of inventory network interfaces. Defaults to `net_ifaces`.
- `netplan_dns_servers`: DNS resolver list. Defaults to `dns_servers`.
- `netplan_ethernets`: explicit netplan `ethernets` mapping. When set, it bypasses `net_ifaces`.
- `netplan_config_files_absent`: stale persistent netplan files to remove before applying netplan.
- `netplan_runtime_networkd_files_absent`: runtime systemd-networkd files to remove before applying netplan.
- `netplan_validate`: run `netplan generate` after rendering.
- `netplan_apply`: run `netplan apply` after rendering.
- `netplan_apply_always`: apply even when the rendered file did not change.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Configure Ubuntu networking
  hosts: ubuntu_hosts
  become: true
  roles:
    - role: lit.ubuntu.netplan
      vars:
        net_ifaces:
          - iface: ens33
            role: uplink
            ipv4: 10.34.71.99/24
            gw4: 10.34.71.1
          - iface: ens34
            role: mgmt
            ipv4: 10.10.30.99/24
        dns_servers:
          - 1.1.1.1
```

## License

MIT

## Author

Lightning IT
