# lit.ubuntu.forward_proxy

Installs one host-local Squid forward proxy and makes it the common outbound
path for apt, interactive processes, system services, Podman pulls, and
containers. The proxy permits only explicitly configured destination domains.
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
  that installs Squid and ends the role without configuring or starting it.
  Normal activation leaves both values false.
- `forward_proxy_allowed_destination_domains`: mandatory closed destination
  allowlist when enabled.
- `forward_proxy_listen_addresses` and `forward_proxy_allowed_clients`: exact
  local/container entry points and client networks.
- `forward_proxy_upstream_enabled`, `forward_proxy_upstream_host`, and
  `forward_proxy_upstream_port`: optional customer-proxy chain.
- `forward_proxy_no_proxy`: local and internal endpoints that must never leave
  the host/site.
- `forward_proxy_container_url`: standard Podman host-gateway URL; containers
  never use host loopback as if it were their own proxy.
- `forward_proxy_container_enabled`: only render Podman propagation after a
  non-loopback Squid listener and matching firewall bridge policy are pinned.

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
      forward_proxy_manage_package: true
      forward_proxy_bootstrap_package_only: true
      forward_proxy_manage_service: false
      forward_proxy_allowed_destination_domains:
        - .ubuntu.com

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

## License

MIT

## Author

Lightning IT
