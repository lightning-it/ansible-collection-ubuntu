# Test Matrix

This repository uses `Collection CI` as the main GitHub Actions workflow.
`CI Result` is the recommended GitHub branch protection status check so branch
protection does not need to track every matrix entry individually.

## Required Pull Request Gates

| Gate | Runner | Required |
|---|---|---:|
| ansible-lint and yamllint | GitHub-hosted Ubuntu | yes |
| Collection build/install smoke test | GitHub-hosted Ubuntu | yes |
| Docker Molecule scenarios | GitHub-hosted Ubuntu | yes |
| Desktop Molecule scenarios | GitHub-hosted Ubuntu | yes |

## Scheduled and Release Gates

| Gate | Runner | Required for release |
|---|---|---:|
| Incus Molecule scenarios | self-hosted Ubuntu Incus | yes |
| Heavy Molecule scenarios | self-hosted Ubuntu Incus Heavy | yes, when present |

Incus scenarios run on the nightly schedule, on pushes to protected branches,
and on manual workflow dispatch when `run_incus=true`. Heavy scenarios run on
the nightly schedule, on version-tag validation, and on manual workflow
dispatch when `run_heavy=true`.

Normal pull requests do not wait for the self-hosted Incus runners. This keeps
PR feedback available even when the Incus runner pool is offline.

## Scenario Coverage

| Scenario | Type | Runner |
|---|---|---|
| `automatic_updates_basic` | docker | GitHub-hosted Ubuntu |
| `baseline-basic` | docker | GitHub-hosted Ubuntu |
| `developer-tools-basic` | docker | GitHub-hosted Ubuntu |
| `github-runner-basic` | docker | GitHub-hosted Ubuntu |
| `hostname_basic` | docker | GitHub-hosted Ubuntu |
| `podman-basic` | docker | GitHub-hosted Ubuntu |
| `repos-basic` | docker | GitHub-hosted Ubuntu |
| `users-basic` | docker | GitHub-hosted Ubuntu |
| `firefox-basic` | desktop | GitHub-hosted Ubuntu |
| `firefox-config-basic` | desktop | GitHub-hosted Ubuntu |
| `firefox-deploy-basic` | desktop | GitHub-hosted Ubuntu |
| `firefox-destroy-basic` | desktop | GitHub-hosted Ubuntu |
| `gui-basic` | desktop | GitHub-hosted Ubuntu |
| `vscode-basic` | desktop | GitHub-hosted Ubuntu |
| `vscode-config-basic` | desktop | GitHub-hosted Ubuntu |
| `vscode-deploy-basic` | desktop | GitHub-hosted Ubuntu |
| `vscode-destroy-basic` | desktop | GitHub-hosted Ubuntu |
| `xrdp-basic` | desktop | GitHub-hosted Ubuntu |
| `incus-basic` | incus | GitHub-hosted Ubuntu (stateful CLI double) |
| `incus-image-basic` | incus | self-hosted Ubuntu Incus |
| `incus-instance-basic` | incus | self-hosted Ubuntu Incus |
| `netplan-basic` | incus/network | self-hosted Ubuntu Incus |

## Protected Incus Scenarios

Incus scenarios that require a real Incus daemon are marked with
`.molecule-mode` set to `protected-incus`. They only run when
`MOLECULE_RUN_PROTECTED=true`, which the workflow sets only for the self-hosted
Incus and heavy jobs. The light `incus-basic` contract test uses a stateful CLI
double and is intentionally safe on GitHub-hosted runners.

## Branch Protection

Use `CI Result` as the required branch protection check. It aggregates the
required pull request gates and only requires optional Incus or heavy jobs when
the workflow event explicitly requests them, such as scheduled validation,
protected-branch pushes, version tags, or manual dispatch inputs.
