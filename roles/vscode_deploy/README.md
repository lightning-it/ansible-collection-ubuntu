# lit.ubuntu.vscode_deploy

---
# lit.ubuntu.vscode_deploy

Install Visual Studio Code on Ubuntu using the shared `lit.ubuntu.vscode` role.

## Requirements

None.

## Variables

See `defaults/main.yml`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: workstations
  become: true
  roles:
    - role: lit.ubuntu.vscode_deploy
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Scope

This role:

- loads shared VS Code defaults and discovery
- configures the Microsoft VS Code repository
- installs the VS Code package
- verifies that the `code` CLI is available

This role does not manage user extensions or user settings. Use
`lit.ubuntu.vscode_config` for that.
