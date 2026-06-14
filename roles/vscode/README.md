---
# lit.ubuntu.vscode

Shared internal role for the Visual Studio Code lifecycle roles in this collection:

- `lit.ubuntu.vscode_deploy`
- `lit.ubuntu.vscode_config`
- `lit.ubuntu.vscode_destroy`

This role centralizes:

- shared defaults
- user and CLI discovery
- repository helper tasks
- extension list merge logic
- current extension discovery
- extension install and removal helpers
- optional user settings rendering

This role is intentionally the shared helper role, not the main lifecycle role
for normal playbooks.

## Design note

The split keeps shared logic centralized, keeps lifecycle roles focused on one
responsibility, and minimizes duplication across deployment, configuration, and
teardown.

The curated default extension set is optimized for Ansible, Helm, Kubernetes,
YAML-heavy infrastructure work, container workflows, Terraform, Git-centric
platform engineering, and general developer workstation productivity on Ubuntu.

## Common variables

```yaml
vscode_users: []
vscode_user_home: ""
vscode_package_name: code

vscode_repo_enabled: true
vscode_repo_name: code
vscode_repo_key_url: https://packages.microsoft.com/keys/microsoft.asc
vscode_repo_key_dest: /etc/apt/keyrings/packages.microsoft.asc
vscode_repo: >-
  deb [arch=amd64 signed-by=/etc/apt/keyrings/packages.microsoft.asc]
  https://packages.microsoft.com/repos/code stable main

vscode_extensions_default:
  - redhat.ansible
  - redhat.vscode-yaml
  - hashicorp.terraform
vscode_extensions_extra: []
vscode_extensions_remove: []
vscode_extensions_file: ""

vscode_vsix_files: []

vscode_manage_user_settings: false
vscode_user_settings: {}

vscode_remove_extensions: false
vscode_remove_package: false
vscode_remove_repo: false
```

## Extension merge behavior

The shared role builds the effective extension list in this order:

1. `vscode_extensions_default`
2. `vscode_extensions_extra`
3. entries read from `vscode_extensions_file`
4. duplicate removal
5. subtraction of `vscode_extensions_remove`

Use `vscode_users` to manage multiple local users with the same extension and
settings baseline.

File-based extension lists are read on the controller and should contain one
extension ID per line. Empty lines and comment lines starting with `#` are
ignored.

## VSIX model

`vscode_vsix_files` is a list of mappings:

```yaml
vscode_vsix_files:
  - id: vendor.custom-extension
    path: files/vscode/vendor.custom-extension.vsix
```

The `id` field keeps VSIX installs idempotent by letting the role compare the
archive to the currently installed extension IDs.

Optional non-default extensions that often fit this role but are left out of
the baseline include:

- `tamasfe.even-better-toml`
- `golang.go`
- `redhat.java`

## Scope notes

- Repository and package state are handled by `lit.ubuntu.vscode_deploy`.
- User extension management and optional settings are handled by `lit.ubuntu.vscode_config`.
- Safe teardown is handled by `lit.ubuntu.vscode_destroy`.
