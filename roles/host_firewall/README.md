# lit.ubuntu.host_firewall

Build and operate a fail-closed nftables policy for an Ubuntu 24.04 host. The role owns one dedicated `inet` table,
replaces that table atomically, and deliberately leaves Podman/Netavark-owned tables intact. A later-priority forward
guard still enforces default deny after container-managed chains have run, because an nftables accept verdict in an
earlier base chain is not final while a later drop is final.

The lifecycle is explicit: `plan` renders a policy fingerprint without changing the host; `check` asks nftables to
validate the complete candidate without applying it; `apply` captures before-state, arms a persistent systemd rollback
timer, applies the candidate, and records after-state; `confirm` requires independent positive and negative test
evidence before a crash-safe systemd one-shot persists the candidate and disarms the timer; `rollback` restores both
the prior runtime ruleset and prior persistent configuration; `readback` records and validates the owned table.
`apply`, `confirm`, and `rollback` are separately authorized and fail closed by default.

## Requirements

- Ubuntu 24.04 LTS with `nftables`, systemd, Bash, and an enabled `nftables.service`.
- Root privileges for `apply`, `confirm`, and `rollback`.
- Network facts or an equally trusted observed-address list containing both expected host addresses.
- Exact `/32` controller, recovery, and Tang consumer sources. Broad source ranges are intentionally rejected.
- An SSH control connection whose actual source, destination address, and destination port match the protected tuple.
- A test runner outside the target for the positive and negative connectivity checks required by `confirm`.

The role does not install packages, open provider-firewall rules, create DNS, or create application forwarding rules.
New container forwarding is denied. Application exposure requires a separate reviewed extension instead of relying on
Podman to bypass this host policy.

## Variables

See `defaults/main.yml` for the complete interface. Important inputs are:

- `host_firewall_action`: one of `plan`, `check`, `apply`, `confirm`, `rollback`, or `readback`.
- `host_firewall_mode`: `bootstrap` allows TCP 22, 1905, and 2222; `hardened` allows only TCP 1905 and 2222.
- `host_firewall_expected_inventory_hostname`, `host_firewall_expected_public_ipv4`, and
  `host_firewall_expected_management_ipv4`: strict target identity.
- `host_firewall_controller_source_cidrs` and `host_firewall_recovery_source_cidrs`: exact management `/32` sources.
- `host_firewall_tang_consumer_cidrs`: exactly three consumer `/32` sources allowed to public TCP 80.
- `host_firewall_control_source_ipv4` and `host_firewall_control_destination_port`: active connection guard.
- `host_firewall_container_interfaces`: every current Podman or container bridge interface; new forwarding is denied.
- `host_firewall_change_id`: immutable transaction identifier shared by `apply` and `confirm`.
- `host_firewall_apply_authorized`, `host_firewall_confirm_authorized`, and
  `host_firewall_rollback_authorized`: explicit mutation gates, all `false` by default.
- `host_firewall_positive_tests_passed`, `host_firewall_negative_tests_passed`, and
  `host_firewall_test_evidence_reference`: required confirmation evidence.

The production caller must not override `host_firewall_observed_ipv4_addresses` with untrusted inventory data. It is
exposed only to make the read-only identity contract testable; the normal value comes from gathered host facts.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Check a bootstrap firewall candidate
  hosts: root_of_trust
  become: true
  gather_facts: true
  roles:
    - role: lit.ubuntu.host_firewall
      vars:
        host_firewall_enabled: true
        host_firewall_action: check
        host_firewall_mode: bootstrap
        host_firewall_expected_inventory_hostname: root01.example.net
        host_firewall_expected_public_ipv4: 192.0.2.10
        host_firewall_expected_management_ipv4: 10.0.30.10
        host_firewall_public_interface: enp1s0
        host_firewall_management_interface: enp1s0.4091
        host_firewall_controller_source_cidrs:
          - 198.51.100.20/32
        host_firewall_recovery_source_cidrs:
          - 198.51.100.21/32
        host_firewall_tang_consumer_cidrs:
          - 192.0.2.21/32
          - 192.0.2.22/32
          - 192.0.2.23/32
```

## License

MIT

## Author

Lightning IT
