# lit.ubuntu.forward_proxy

Runs the standard LIT Squid forward proxy as a persistent, digest-pinned
Podman container and makes it the common outbound path for apt, interactive
processes, opted-in system services, and optionally other containers. The
proxy permits only explicitly configured destination domains and may either
connect directly or chain every request to one customer/site upstream proxy.

This role never installs the Ubuntu Squid package and never manages a native
`squid.service`. Persistent runtime ownership is delegated to
`lit.foundational.podman_systemd`, which renders a system Quadlet for the Pod
manifest.

This is an egress component. It does not replace an ingress reverse proxy such
as NGINX, and it is not an open proxy.

## Security model

- The Canonical `ubuntu/squid` image is pinned by immutable multi-architecture
  digest and the runtime manifest enforces `imagePullPolicy: Never`.
- The image must be preloaded in a separate, controlled bootstrap transaction.
  The steady-state role cannot silently pull it from the Internet.
- Squid uses the host network but runs as the Ubuntu base identity UID/GID 13
  (`proxy`). This lets the host firewall grant TCP 80/443 only to that process
  identity while denying direct application and container egress.
- The container drops all capabilities, prohibits privilege escalation, and
  uses a read-only root filesystem with only an ephemeral `/tmp` volume.
- Clients and destinations are closed allowlists. A global client CIDR is
  rejected.
- Proxy environment variables are routing configuration, not the security
  boundary. The host firewall remains authoritative.

## Requirements

Ubuntu 24.04, rootful Podman with Quadlet support, systemd, and root
privileges. The exact Squid image must already be present locally before
runtime management is enabled. The host firewall must bind Internet egress to
the `proxy` identity.

The collection requires `lit.foundational` 1.32.0 for the shared
`podman_systemd` lifecycle.

## Important variables

- `forward_proxy_manage_runtime`: start/update/remove the Quadlet-managed
  container. Set false only for rendering or validation tests.
- `forward_proxy_image`: immutable `docker.io/ubuntu/squid@sha256:...` image.
- `forward_proxy_image_pull_policy`: fixed to `Never`.
- `forward_proxy_restart_services`: exact existing systemd client services to
  restart during a cutover.
- `forward_proxy_restart_clients`: explicit one-shot cutover action for the
  listed services. It is false by default, so ordinary idempotent runs do not
  restart clients. Set it true only for the controlled cutover, verify the
  effective environment, then return it to false.
- `forward_proxy_allowed_destination_domains`: mandatory closed destination
  allowlist when enabled.
- `forward_proxy_listen_addresses` and `forward_proxy_allowed_clients`: exact
  host/container entry points and client networks.
- `forward_proxy_upstream_enabled`, `forward_proxy_upstream_host`, and
  `forward_proxy_upstream_port`: optional customer proxy chain.
- `forward_proxy_no_proxy`: local and internal environment bypass entries.
- `forward_proxy_apt_direct_hosts`: only `localhost` and `127.0.0.1` are
  accepted. Site-local exceptions require a separately reviewed firewall
  grant.
- `forward_proxy_container_enabled`: render client-container propagation only
  after a non-loopback listener and matching, live-read firewall bridge policy
  are pinned.
- `forward_proxy_state_marker_path`: exact ownership manifest used for safe
  removal. Unknown content, unit drift, or managed-path drift stops fail-closed
  before any cleanup mutation.

The Podman client defaults affect newly created containers. Existing
containers must be recreated deliberately after activation. They do not make
Podman image pulls use the proxy; image preload is a separate bootstrap step.

Authenticated upstream proxies are intentionally unsupported until a
secret-backed interface exists. Credentials must never be committed or placed
in ordinary inventory.

## Example playbook

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

The example assumes the pinned image has already been preloaded and the
matching host-firewall owner rule has been approved. Activation, firewall
cutover, and client recreation remain controlled operational steps.

## License

MIT

## Author

Lightning IT
