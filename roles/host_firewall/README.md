# lit.ubuntu.host_firewall

Build and inspect a fail-closed nftables host policy for Ubuntu 24.04. The role owns exactly one `inet` table and one
dedicated persistence include. It never captures, flushes, restores, or persists the complete host ruleset, and it
never overwrites the administrator-owned root nftables configuration. Foreign tables and Podman/Netavark tables stay
outside the role boundary.

Management access is modeled per function. `bootstrap_ssh` uses TCP 22 only in bootstrap mode, `openssh` uses TCP
1905, and `dropbear` uses TCP 2222. Each function has independent IPv4 `/32` and IPv6 `/128` source lists. The same
source may be approved for more than one function without granting access to any other port.

`plan` renders the candidate and its closed authorization contract. `check` executes `nft --check` even when Ansible
runs in global check mode. Structured readback uses `nft --json`, removes only documented runtime fields, and compares
the resulting canonical SHA-256 with an independently approved policy artifact. Text comments are not acceptance
evidence.

Productive `apply`, `confirm`, and `rollback` remain deliberately fail-closed in this revision. The contract binds the
target, action, candidate, approved readback, policy fingerprint, and change ID, but a trusted external signature
verifier with expiry validation and an atomic one-time claim is not yet integrated. In addition, egress is explicitly
`unresolved-permissive`; confirmation is prohibited until an approved least-privilege IPv4/IPv6 egress policy exists.

The prepared transaction implementation uses one exclusive lock for apply, confirm, timer rollback, and explicit
rollback. Rollback replays only the previous role-owned table and restores only the role-owned persistence include.
The scripts and systemd units are locally testable implementation material, not evidence of a live nftables or systemd
acceptance.

## Requirements

- Ubuntu 24.04 LTS with `nftables`, systemd, Bash, Python 3, `flock`, and an enabled `nftables.service`.
- Root privileges for any future productive lifecycle after the signed-approval blocker is resolved.
- Trusted host facts containing every expected IPv4 and IPv6 address.
- Exact per-function IPv4 `/32` and lowercase, zero-padded, uncompressed IPv6 `/128` source entries.
- An administrator-owned, root-owned, non-symlink root configuration containing exactly one literal include for the
  role-owned persistence file. The role will not add, edit, or remove that root include.
- Preprovisioned root-owned, non-symlink program and systemd unit directories. The role installs only its named files
  and never creates or changes permissions on these shared directories.
- An independently reviewed canonical nftables JSON digest for structured readback.
- External positive and negative connectivity tests for confirmation.

The role does not install packages, change provider firewalls, create DNS, or create application forwarding rules.
New container forwarding remains denied.

## Variables

See `defaults/main.yml` for the complete interface. Important inputs are:

- `host_firewall_action`: `plan`, `check`, `apply`, `confirm`, `rollback`, or `readback`.
- `host_firewall_mode`: `bootstrap` or `hardened`.
- `host_firewall_management_access`: exact mapping for `bootstrap_ssh`, `openssh`, and `dropbear`; every entry has a
  fixed port/mode contract plus independent `sources_ipv4` and `sources_ipv6` lists.
- `host_firewall_tang_access`: fixed TCP 80 with explicit IPv4 and IPv6 consumer host lists.
- `host_firewall_expected_*` and `host_firewall_observed_*`: target identity and observed-address binding.
- `host_firewall_control_source_address` and `host_firewall_control_destination_port`: protected live SSH tuple.
- `host_firewall_persistent_root_config_path`: administrator-owned root file, always read-only to the role.
- `host_firewall_persistent_include_path`: the only persistent policy file owned by the role.
- `host_firewall_approved_readback_sha256`: independently approved canonical `nft --json` policy digest.
- `host_firewall_authorization_contract`: exact productive action binding. A matching value alone never authorizes a
  mutation while signed verification is unavailable.
- `host_firewall_change_id`: immutable transaction identifier.
- `host_firewall_positive_tests_passed`, `host_firewall_negative_tests_passed`, and
  `host_firewall_test_evidence_reference`: external confirmation evidence.

Deprecated aggregate variables (`host_firewall_controller_source_cidrs`, `host_firewall_recovery_source_cidrs`, and
`host_firewall_tang_consumer_cidrs`) are accepted by the interface only to return a fail-closed migration error; they
never affect the rendered policy.

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
        host_firewall_management_access:
          bootstrap_ssh:
            port: 22
            modes: [bootstrap]
            sources_ipv4: [198.51.100.20/32]
            sources_ipv6: []
          openssh:
            port: 1905
            modes: [bootstrap, hardened]
            sources_ipv4: [198.51.100.20/32]
            sources_ipv6: []
          dropbear:
            port: 2222
            modes: [bootstrap, hardened]
            sources_ipv4: [198.51.100.20/32]
            sources_ipv6: []
        host_firewall_tang_access:
          port: 80
          sources_ipv4:
            - 192.0.2.21/32
            - 192.0.2.22/32
            - 192.0.2.23/32
          sources_ipv6: []
```

## License

MIT

## Author

Lightning IT
