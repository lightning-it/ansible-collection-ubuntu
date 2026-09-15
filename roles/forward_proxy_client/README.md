# lit.ubuntu.forward_proxy_client

Configures Ubuntu host and optional Podman-container clients to use the
standard LIT forward proxy. The distribution-neutral Squid container is owned
by `lit.supplementary.forward_proxy`; this role does not install Squid and does
not manage the proxy service.

## Requirements

Ubuntu 22.04 or 24.04, root privileges, and a separately deployed forward
proxy. The Ubuntu host firewall must bind outbound Internet traffic to the
exact proxy identity. Container propagation must stay disabled until the live
Podman bridge, gateway, subnet, and firewall rule have been read and pinned.

## Variables

See `roles/forward_proxy_client/defaults/main.yml`.

Important inputs include:

- `forward_proxy_client_enabled`: render or safely remove Ubuntu client state.
- `forward_proxy_client_proxy_url`: local host proxy URL.
- `forward_proxy_client_no_proxy`: exact local/internal bypass tokens.
- `forward_proxy_client_apt_direct_hosts`: restricted to host loopback.
- `forward_proxy_client_container_enabled`: opt in only after live network readback.
- `forward_proxy_client_restart_services`: exact existing systemd services for a controlled cutover.
- `forward_proxy_client_restart_now`: permits one restart only when this run actually changes managed client state;
  unchanged runs remain idempotent even if the switch remains true.
- `forward_proxy_client_upstream_ipv4`: exact resolved parent-proxy IPv4 identity used to bind upstream mode to the
  firewall's single `/32` destination.

The role writes APT, interactive shell, process, systemd-manager, and optional
Podman client defaults. Existing containers are not recreated automatically.
Podman image pulls are not affected automatically and remain a separate,
controlled bootstrap operation.

## Dependencies

- `lit.supplementary.forward_proxy` deployed separately by consumer automation
- `lit.ubuntu.host_firewall` or an equivalent enforced Ubuntu firewall policy

The dependency is operational rather than a `galaxy.yml` dependency, avoiding
a collection cycle and allowing Automation to pin each collection explicitly.

## Example Playbook

```yaml
- name: Configure Ubuntu forward proxy clients
  hosts: edge
  become: true
  roles:
    - role: lit.ubuntu.forward_proxy_client
      forward_proxy_client_enabled: true
      forward_proxy_client_firewall_egress:
        enabled: true
        status: approved
        owner_username: proxy
        mode: direct
        interface: eth0
        destinations_ipv4: [0.0.0.0/0]
        ports: [80, 443]
        residual: No non-proxy public egress is permitted.
```

## License

MIT

## Author

Lightning IT
