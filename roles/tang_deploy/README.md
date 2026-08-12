# lit.ubuntu.tang_deploy

Install and validate the minimal, socket-activated Tang network binding service on Ubuntu. Tang does not escrow disk
keys; clients use its public advertisement as part of a cryptographic binding policy.

## Requirements

- Ubuntu with systemd when service management is enabled.
- Root privileges.
- Network and firewall policy managed separately. This role does not open a firewall port or publish DNS.

Treat the output in `tang_deploy_public_thumbprints` as public trust material. Transfer the selected signing
thumbprint to Clevis clients through a trusted, out-of-band path. Never copy or publish the private Tang database in
`/var/db/tang`.

## Variables

See `defaults/main.yml` for the complete interface. Important inputs are:

- `tang_deploy_enabled`: opt in to the role; defaults to `false`.
- `tang_deploy_manage_packages`: install the `tang` package.
- `tang_deploy_manage_service`: enable and start `tangd.socket`.
- `tang_deploy_manage_socket_override`: render a systemd socket override for `tang_deploy_listen_port`.
- `tang_deploy_validate`: validate the local advertisement and obtain public signing thumbprints.
- `tang_deploy_public_thumbprints`: public thumbprints recorded after validation.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Deploy a Tang binding service
  hosts: tang_servers
  become: true
  roles:
    - role: lit.ubuntu.tang_deploy
      vars:
        tang_deploy_enabled: true
        tang_deploy_manage_socket_override: true
        tang_deploy_listen_port: 80
```

## License

MIT

## Author

Lightning IT
