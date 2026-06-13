---
# lit.ubuntu.vscode_destroy

Remove Visual Studio Code managed state on Ubuntu using the shared
`lit.ubuntu.vscode` role.

## Scope

This role can:

- remove requested extensions
- remove the VS Code package
- remove the VS Code repository

It does not aggressively remove unrelated user data. Extension removal uses the
requested IDs in `vscode_extensions_remove`. Use `vscode_users` to remove the
same managed extension set from multiple users.

## Removal variables

```yaml
vscode_remove_extensions: true
vscode_remove_package: true
vscode_remove_repo: true
```

## Example

```yaml
- hosts: workstations
  become: true
  roles:
    - role: lit.ubuntu.vscode_destroy
      vars:
        vscode_users:
          - devuser
        vscode_remove_extensions: true
        vscode_remove_package: true
        vscode_remove_repo: true
```
