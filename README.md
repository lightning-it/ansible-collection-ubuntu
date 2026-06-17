# ansible-collection-ubuntu

Ubuntu-focused Ansible collection covering OS baseline, apt repositories,
automatic updates, users, developer tooling, desktop helpers, and day-2
operational tasks.

This collection is part of the ModuLix / Lightning IT ecosystem and follows the
same shared-assets collection structure as the RHEL collection, while using
Ubuntu-native package and repository management.

## Roles

- `lit.ubuntu.baseline`
  Install baseline packages and configure timezone/locale.
- `lit.ubuntu.repos`
  Configure apt repositories, apt signing key files, and optional apt proxy
  policy.
- `lit.ubuntu.automatic_updates`
  Schedule weekly `apt-get update && apt-get upgrade` runs via cron.
- `lit.ubuntu.users`
  Manage local Linux users and SSH keys.
- `lit.ubuntu.developer_tools`
  Install developer packages, Python packages, optional GitHub CLI, Argo CD,
  Terragrunt, OpenShift CLI, and SSH agent/private key helpers.
- `lit.ubuntu.incus`
  Configure an Ubuntu host as an Incus host.
- `lit.ubuntu.incus_image`
  Import Incus image artifacts and manage local image aliases.
- `lit.ubuntu.incus_instance`
  Manage Incus instance lifecycle, cloud-init injection, readiness waits, and
  optional generated inventory output.
- `lit.ubuntu.podman`, `lit.ubuntu.gui`, `lit.ubuntu.xrdp`,
  `lit.ubuntu.firefox`, and `lit.ubuntu.vscode`
  Provide optional workstation and remote desktop building blocks.

## Example

```yaml
---
- name: Configure Ubuntu hosts
  hosts: ubuntu
  become: true

  roles:
    - role: lit.ubuntu.repos
      vars:
        repos_update_cache: true

    - role: lit.ubuntu.baseline
      vars:
        baseline_timezone: Etc/UTC
        baseline_packages_present:
          - vim
          - jq
          - tar
          - bash-completion

    - role: lit.ubuntu.automatic_updates
      vars:
        automatic_updates_enabled: true

    - role: lit.ubuntu.users
      vars:
        users_accounts:
          - name: ops-admin
            groups: ["sudo"]
            shell: /bin/bash
```

## Development

This repository is designed to be used together with:

- `pre-commit` for local linting,
- the shared `wunder-devtools-ee` container for consistent tooling,
- Molecule scenarios for role-level testing.

Each role is expected to provide:

- `meta/main.yml` with Galaxy metadata,
- `defaults/main.yml` with documented variables,
- `README.md` with a clear description and examples.
