# lit.ubuntu.xrdp

XRDP server role for Ubuntu.

## Requirements

None.

## Variables

`xrdp_listen_address` is a canonical literal IPv4 address; URLs, hostnames,
newlines, leading-zero octets and out-of-range octets are rejected before changes.


See `defaults/main.yml`.

Only the dedicated package-owned TLS groups `ssl-cert` and `xrdp` are allowed, including when no GNOME users are declared. The package-owned `ssl-cert` and `xrdp` groups may be created by the normal XRDP package installation; their existence is verified again before key permissions and daemon membership change.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.xrdp
  hosts: all
  become: true
  roles:
    - role: lit.ubuntu.xrdp
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Repo policy

This role **never enables repository sources**.
Enable repositories via `lit.ubuntu.repos` (or your internal mirror policy).

### What it does

- Precheck: fails fast if xrdp packages are not available in enabled repos
- Installs XRDP packages
- Configures `/etc/xrdp/xrdp.ini` and `/etc/xrdp/startwm.sh`
- Optional TLS, firewalld port open

`xrdp_gnome_provisioned_users` optionally marks explicitly declared existing
personal users under `/home` as configured by automation, avoiding GNOME's
first-login wizard. The default empty list preserves normal onboarding.
`xrdp_release_upgrade_prompt` optionally declares Ubuntu release-upgrade
prompting (`never`, `normal`, `lts`); the default leaves it unchanged. This
does not disable package or security updates.

TLS defaults use the package-provided `ssl-cert` group with mode `0640`. The role requires the declared key group to exist and appends the installed `xrdp` daemon to it before setting key permissions. Root-group and owner-only key settings are rejected because the configured unprivileged daemon must read its key.

TLS key groups are restricted to the dedicated package-owned `ssl-cert` and `xrdp` groups. Privileged and arbitrary custom groups are rejected before changes.

The default listener is loopback (`127.0.0.1`). Remote use requires an explicit
private interface address and a firewall policy limited to the intended gateway.
The WBN01 inventory declares that private bind separately. Existing certificate
and key paths must be regular files, never symlinks; this is checked before host
changes. Provision regular TLS files at explicit paths instead of using a package
snakeoil symlink. The materialized key is checked again before daemon group access
and permissions are changed, and permission changes do not follow links.
