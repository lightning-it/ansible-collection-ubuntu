# lit.ubuntu.repos

Configure apt repository sources and apt proxy policy for Ubuntu hosts.

This role is repository policy only. Service roles should own package
installation.

## Requirements

None.

## Variables

- `repos_enabled`: enable or skip the role.
- `repos_proxy_enabled`: manage apt proxy config.
- `repos_proxy_url`: proxy URL such as `http://proxy.example.com:3128`.
- `repos_proxy_file`: apt proxy config path.
- `repos_custom`: list of apt repositories to manage.
- `repos_cleanup_files`: obsolete apt source files to remove before apt cache refresh.
- `repos_keyring_dir`: keyring directory to create.
- `repos_update_cache`: refresh apt cache after repository changes.
- `repos_no_log`: hide repository item details.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: ubuntu
  become: true
  roles:
    - role: lit.ubuntu.repos
      vars:
        repos_custom:
          - repo: "deb [arch=amd64 signed-by=/etc/apt/keyrings/example.asc] https://example.invalid/apt stable main"
            filename: example
            key_url: https://example.invalid/key.asc
            key_dest: /etc/apt/keyrings/example.asc
```

## License

MIT

## Author

Lightning IT
