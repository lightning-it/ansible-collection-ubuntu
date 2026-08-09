# lit.ubuntu.host_firewall

Build and inspect a fail-closed nftables host policy for Ubuntu 24.04. The role owns exactly one `inet` table and one
dedicated persistence include. It never captures, flushes, restores, or persists the complete host ruleset, and it
never overwrites the administrator-owned root nftables configuration. Foreign tables and Podman/Netavark tables stay
outside the role boundary.

Management access is modeled per function. `bootstrap_ssh` uses TCP 22 only in bootstrap mode, `openssh` uses TCP
1905, and `dropbear` uses TCP 2222. Each function has an independent IPv4 `/32` source list. The same source may be
approved for more than one function without granting access to any other port. The active target baseline is
end-to-end IPv4-only; every IPv6 identity, observed address, source, destination, and explicit IPv6 allow path is
rejected.

`plan` renders the candidate and its closed authorization contract. `check` executes `nft --check` even when Ansible
runs in global check mode. Structured readback uses `nft --json`, removes only documented runtime fields, and compares
the resulting canonical SHA-256 with an independently approved policy artifact. Text comments are not acceptance
evidence.

Productive `apply`, `confirm`, and `rollback` use one static root-owned transaction routine and one exclusive lock.
The routine validates a short-lived, externally signed authorization, retains its signed envelope and verifier receipt,
consumes its claim exactly once, snapshots only the role-owned table and include, stages immutable transaction assets,
arms the rollback watchdog, and applies the candidate in one serialized operation. Static runtime installation uses
the same lock and cannot replace a program, unit, or trust anchor while a transaction is active. Confirmation
revalidates the authorization, metadata, verifier, every staged and static asset, root and included persistence files,
and structured runtime readback before and after stopping the watchdog. Explicit and watchdog rollback use the same
lock and record the exact restored runtime and persistence state.

Every external transaction command has a hard timeout, every lock acquisition has a shorter stale-lock timeout, and
the total apply budget reserves a separate rollback budget below the watchdog expiry. The rollback service retries a
failed stale-lock attempt. Evidence creates, terminal publication, watchdog disablement, and active-pointer removal
are ordered with file and parent-directory synchronization so a reboot cannot turn one transaction into contradictory
confirmation and rollback outcomes.

The role enforces output policy `drop`. Egress is expressed as separate fixed functions for DNS, NTP, Atlas Loki,
temporary bootstrap HTTPS, and an optional hardened management proxy. Bootstrap HTTPS is never confirmable. Hardened
confirmation requires an approved deny-by-default policy, disabled bootstrap HTTPS, external positive and negative
test evidence, and an independently approved canonical readback digest. A configured trusted signature verifier and
valid signed envelopes remain deployment prerequisites; repository tests do not constitute live host acceptance.

## Requirements

- Ubuntu 24.04 LTS with `nftables`, systemd, Python 3, and an enabled `nftables.service`.
- Root privileges for the productive lifecycle.
- Trusted host facts containing every expected IPv4 address and no IPv6 address.
- Exact per-function IPv4 `/32` source entries. IPv6 compatibility input is canonicalized only so that every spelling
  is rejected consistently by the target's IPv4-only boundary.
- An administrator-owned, root-owned, non-symlink root configuration containing exactly one literal include for an
  already existing valid role-owned placeholder file. The role will not add, edit, or remove the root include and will
  not accept a dangling include as a rollback baseline.
- Preprovisioned root-owned, non-symlink program and systemd unit directories. The role installs only its named files
  and never creates or changes permissions on these shared directories.
- A root-owned, non-symlink executable signature verifier that returns the exact verification-receipt schema expected
  by the transaction routine.
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
- `host_firewall_authorization_contract`: exact signed v2 productive-action envelope. It binds the target, action,
  candidate, readback, policy and egress digests, change ID, one-time claim, issue time, and expiry.
- `host_firewall_authorization_verifier_binary`: trusted root-owned verifier used for the signed envelope.
- `host_firewall_egress_policy`: complete target-specific v1 function contract. The empty default intentionally fails
  closed instead of granting generic network access.
- `host_firewall_cis_ipv6_required`: binds the surrounding CIS IPv6 decision. Confirmation fails when that decision
  requires IPv6 while this target's egress baseline is IPv4-only.
- `host_firewall_provider_ipv6_filter_enabled` and `host_firewall_provider_ipv6_filter_evidence_reference`: confirmation
  requires an enabled provider-side IPv6 filter and a durable evidence reference.
- `host_firewall_change_id`: immutable transaction identifier.
- `host_firewall_watchdog_timeout_seconds`, `host_firewall_command_timeout_seconds`, and
  `host_firewall_lock_wait_timeout_seconds`: bounded transaction budgets. Validation requires command and lock limits
  to leave an explicit rollback margin below the watchdog.
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
        host_firewall_egress_policy:
          schema: lit.host_firewall.egress/v1
          status: draft
          stance: bootstrap-restricted
          ipv4_only: true
          functions:
            dns_udp:
              enabled: true
              protocol: udp
              port: 53
              modes: [bootstrap, hardened]
              interface: enp1s0
              destinations_ipv4: [1.1.1.1/32, 8.8.8.8/32]
              destinations_ipv6: []
              declared_fqdns: []
              mtls_required: false
              status: approved
              residual: ""
            dns_tcp:
              enabled: true
              protocol: tcp
              port: 53
              modes: [bootstrap, hardened]
              interface: enp1s0
              destinations_ipv4: [1.1.1.1/32, 8.8.8.8/32]
              destinations_ipv6: []
              declared_fqdns: []
              mtls_required: false
              status: approved
              residual: ""
            ntp:
              enabled: true
              protocol: udp
              port: 123
              modes: [bootstrap, hardened]
              interface: enp1s0
              destinations_ipv4: [0.0.0.0/0]
              destinations_ipv6: []
              declared_fqdns: [ntp1.hetzner.de, ntp2.hetzner.com, ntp3.hetzner.net]
              mtls_required: false
              status: transitional-port-only
              residual: "Destination IPs remain unresolved and require later tightening."
            atlas_loki:
              enabled: true
              protocol: tcp
              port: 3100
              modes: [bootstrap, hardened]
              interface: enp1s0.4091
              destinations_ipv4: [10.10.30.24/32]
              destinations_ipv6: []
              declared_fqdns: []
              mtls_required: true
              status: approved
              residual: ""
            bootstrap_https:
              enabled: true
              protocol: tcp
              port: 443
              modes: [bootstrap]
              interface: enp1s0
              destinations_ipv4: [0.0.0.0/0]
              destinations_ipv6: []
              declared_fqdns: []
              mtls_required: false
              status: temporary-maintenance
              residual: "Must be removed before hardened confirmation."
            https_proxy:
              enabled: false
              protocol: tcp
              port: 3128
              modes: [hardened]
              interface: enp1s0.4091
              destinations_ipv4: []
              destinations_ipv6: []
              declared_fqdns: [mirror.hetzner.com, fsn1.your-objectstorage.com, api.github.com]
              mtls_required: false
              status: disabled-staged-transfer
              residual: "Controller-pull and staged transfer are used until a proxy is approved."
```

## License

MIT

## Author

Lightning IT
