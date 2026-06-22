# lit.ubuntu.vscode_config

---
# lit.ubuntu.vscode_config

Configure Visual Studio Code on Ubuntu using the shared `lit.ubuntu.vscode`
role.

## Requirements

None.

## Variables

See `defaults/main.yml`.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.vscode_config
  hosts: all
  become: true
  roles:
    - role: lit.ubuntu.vscode_config
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Scope

This role:

- discovers the installed `code` CLI
- manages extensions as the target non-root user
- supports default, extra, and file-based extension IDs
- supports optional `.vsix` installation from controller-local files
- optionally manages `~/.config/Code/User/settings.json`
- can apply the same baseline to multiple users with `vscode_users`

This role does not install the VS Code package or repository. Use
`lit.ubuntu.vscode_deploy` for package state.

### Extension merge behavior

The effective extension list is built from:

1. `vscode_extensions_default`
2. `vscode_extensions_extra`
3. controller-local `vscode_extensions_file`
4. removal of duplicates
5. subtraction of `vscode_extensions_remove`

### File-based extension list

Example:

```yaml
vscode_extensions_file: files/vscode/extensions.txt
```

Example file contents:

```text
redhat.ansible
redhat.vscode-yaml
hashicorp.terraform
ms-kubernetes-tools.vscode-kubernetes-tools
tim-koehler.helm-intellisense
```

### VSIX handling

Example:

```yaml
vscode_vsix_files:
  - id: vendor.custom-extension
    path: files/vscode/vendor.custom-extension.vsix
```

### User settings

When `vscode_manage_user_settings: true`, the role writes
`~/.config/Code/User/settings.json` for the target user.

### Examples

```yaml
- hosts: workstations
  become: true
  roles:
    - role: lit.ubuntu.vscode_config
      vars:
        vscode_users:
          - rene
          - dirk
        vscode_extensions_extra:
          - tamasfe.even-better-toml
```

```yaml
- hosts: workstations
  become: true
  roles:
    - role: lit.ubuntu.vscode_config
      vars:
        vscode_users:
          - devuser
        vscode_extensions_file: files/vscode/extensions.txt
```

```yaml
- hosts: workstations
  become: true
  roles:
    - role: lit.ubuntu.vscode_config
      vars:
        vscode_users:
          - devuser
        vscode_manage_user_settings: true
        vscode_user_settings:
          editor.formatOnSave: true
          files.trimTrailingWhitespace: true
          yaml.format.enable: true
```
