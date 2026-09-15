# lit.ubuntu.forward_proxy

Installs one host-local Squid forward proxy and makes it the common outbound
path for apt, interactive processes, opted-in system services, and containers.
The proxy permits only explicitly configured destination domains.
It can either connect directly or chain every request to one site/customer
upstream proxy.

This is an egress component. It does not replace an ingress reverse proxy such
as NGINX, and it is not an open proxy.

## Requirements

Ubuntu 24.04 and root privileges. The host firewall must restrict Internet
egress to the Squid service identity; proxy environment settings alone are not
a security boundary.

## Variables

See `defaults/main.yml`. Important inputs are:

- `forward_proxy_manage_package` and
  `forward_proxy_bootstrap_package_only`: an explicitly selected first phase
  that installs Squid over separately authorized temporary TCP 80 and TCP 443
  firewall functions. Package service activation is suppressed, the unit is
  stopped and masked, and the proxy port is read back as closed before the role
  ends. Normal activation leaves both values false and explicitly unmasks the
  configured service.
- `forward_proxy_restart_services`: exact pre-existing systemd client services
  to restart after the manager receives the new proxy environment. This is
  opt-in; operators must include every affected already-running service before
  enabling the hardened firewall boundary.
- `forward_proxy_allowed_destination_domains`: mandatory closed destination
  allowlist when enabled.
- `forward_proxy_listen_addresses` and `forward_proxy_allowed_clients`: exact
  local/container entry points and client networks.
- `forward_proxy_upstream_enabled`, `forward_proxy_upstream_host`, and
  `forward_proxy_upstream_port`: optional customer-proxy chain.
- `forward_proxy_no_proxy`: local and internal environment bypass entries.
- `forward_proxy_apt_direct_hosts`: exact APT hostnames or IPv4 addresses that
  receive explicit `DIRECT` rules. Only `localhost` and `127.0.0.1` are
  accepted. Any site-local exception needs its own reviewed firewall grant.
- `forward_proxy_container_url`: standard Podman host-gateway URL; containers
  never use host loopback as if it were their own proxy.
- `forward_proxy_container_enabled`: only render Podman propagation after a
  non-loopback Squid listener and matching firewall bridge policy are pinned.
- `forward_proxy_state_marker_path`: ownership marker used to remove the
  role-managed configuration and stop/mask the proxy when an existing managed
  deployment is disabled. A first disabled run does not remove package-owned
  defaults because the marker is absent.

The Podman configuration supplies proxy variables to created containers. It
does not alter the environment of an already running Ansible controller and
must not be treated as a guarantee that the Podman client itself proxies image
pulls. Bootstrap and pull tasks must pass the host proxy environment explicitly
or run from a process started after the host environment was refreshed.

Authenticated upstream proxies are intentionally not accepted until a
secret-backed interface exists; credentials must never be committed or placed
in ordinary inventory.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: edge
  become: true
  roles:
    - role: lit.ubuntu.forward_proxy
      forward_proxy_enabled: true
      forward_proxy_allowed_destination_domains:
        - .ubuntu.com
        - .quay.io
        - .redhat.com
```

The normal example assumes Squid is already installed. Package ownership is
intentionally in this Ubuntu operating-system collection (repository roles
manage package sources, while OS service roles own their required packages),
but installation remains default-off. For first installation, operators must
first apply a complete `lit.ubuntu.host_firewall` bootstrap policy through its
watchdog transaction. Only then may a separate `forward_proxy_manage_package`
and `forward_proxy_bootstrap_package_only` run install Squid. The forward-proxy
role validates the mapped bootstrap inputs; it never applies or weakens the
firewall itself. After the bootstrap run proves the listener is closed, normal
activation and the hardened firewall transaction remain separate controlled
steps.

## License

MIT

## Author

Lightning IT
