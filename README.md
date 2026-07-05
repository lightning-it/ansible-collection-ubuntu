# ansible-collection-ubuntu

<!-- BEGIN LIT_QUALITY_BADGES -->

[![CI](https://github.com/lightning-it/ansible-collection-ubuntu/actions/workflows/collection-ci.yml/badge.svg?branch=develop)](https://github.com/lightning-it/ansible-collection-ubuntu/actions/workflows/collection-ci.yml)
[![Latest Release](https://img.shields.io/github/v/release/lightning-it/ansible-collection-ubuntu?sort=semver)](https://github.com/lightning-it/ansible-collection-ubuntu/releases/latest)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/lightning-it/ansible-collection-ubuntu/badge)](https://scorecard.dev/viewer/?uri=github.com/lightning-it/ansible-collection-ubuntu)
[![Ansible Galaxy](https://img.shields.io/ansible/collection/v/lit/ubuntu?label=Ansible%20Galaxy)](https://galaxy.ansible.com/ui/repo/published/lit/ubuntu/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

<!-- END LIT_QUALITY_BADGES -->

<!-- BEGIN LIT_COMPATIBILITY_MATRIX -->

## Compatibility Matrix

| Collection Version | Role/Scenario | Platform | Product | Test Type | Validation |
|---|---|---|---|---|---|
| Current release | collection-sanity | ubuntu-latest | ansible-core, molecule, incus | Collection sanity | See GitHub Release evidence |
| Current release | molecule-light | ubuntu-latest | ansible-core, molecule, incus | Molecule light | See GitHub Release evidence |
| Current release | molecule-heavy-incus | ubuntu-latest | ansible-core, molecule, incus | Heavy Incus | See GitHub Release evidence |
| Current release | galaxy-build | ubuntu-latest | ansible-core, molecule, incus | Galaxy build/publish | See GitHub Release evidence |
| Current release | collection-sanity | ubuntu-lts | ansible-core, molecule, incus | Collection sanity | See GitHub Release evidence |
| Current release | molecule-light | ubuntu-lts | ansible-core, molecule, incus | Molecule light | See GitHub Release evidence |
| Current release | molecule-heavy-incus | ubuntu-lts | ansible-core, molecule, incus | Heavy Incus | See GitHub Release evidence |
| Current release | galaxy-build | ubuntu-lts | ansible-core, molecule, incus | Galaxy build/publish | See GitHub Release evidence |

Validation proof for each released version is stored in the corresponding GitHub Release evidence.

<!-- END LIT_COMPATIBILITY_MATRIX -->

<!-- BEGIN LIT_RELEASE_QUALITY_MODEL -->

## Release and Quality Model

This repository follows the Lightning IT shared release and quality model.
The README shows the current supported and tested matrix.
Exact per-version proof is stored with every GitHub Release as `release-evidence.md` and `release-evidence.json`.

See:

- [RELEASE.md](./RELEASE.md)
- [TESTING.md](./TESTING.md)
- [GitHub Releases](../../releases)

Repository classification: **Ansible Collection**.
Required test profiles: `pre-commit, lint, light, molecule-light, molecule-heavy-incus, release-validation`.
Publishing targets: `github-release, ansible-galaxy`.

Release evidence records the exact GitHub Actions run, validated matrix rows, built artifacts, publish result, and security status for each release.

<!-- END LIT_RELEASE_QUALITY_MODEL -->


[![Collection CI](https://github.com/lightning-it/ansible-collection-ubuntu/actions/workflows/collection-ci.yml/badge.svg?branch=develop)](https://github.com/lightning-it/ansible-collection-ubuntu/actions/workflows/collection-ci.yml)

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
- `lit.ubuntu.netplan`
  Render and apply Ubuntu netplan interface configuration.
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
