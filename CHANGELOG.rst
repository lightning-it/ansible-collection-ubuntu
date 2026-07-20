===================================================
Lightning IT Collection Release Notes Release Notes
===================================================

.. contents:: Topics

v1.9.0
======

Minor Changes
-------------

- Harden the cis_ubuntu24 integration with separate fail-closed remediation and audit modes, exact native-profile validation, an inventory exception schema, immutable remediation and audit dependency metadata, and idempotent handling of the package AIDE service when the cron scheduler is selected. Preserve a traversable audit log directory when inventory disables the pinned upstream role's defective recursive file-mode remediation, and persist the network sysctls whose pinned audit persistence checks are malformed.
- Reconcile the root Incus SubUID/SubGID allocation before daemon operations.
- collection_tooling - Synchronize the centrally managed Renovate policy and guarded automation workflows.
- developer_tools - Add isolated pinned Python tooling, pinned global npm packages, private workspace directories, and SHA-256-verified standalone release binaries for reproducible development hosts.
- github_runner - Add a backward-compatible, data-driven multi-instance interface with isolated installation and work directories, per-instance registration lifecycle with distinct registration and removal tokens, and independent systemd service management. Organization runner groups and declarative cleanup of externally managed legacy services are supported for controlled migrations.
- incus - Add fail-closed JSON discovery, optional preseed initialization, and declarative project and profile reconciliation for Incus hosts.
- podman - Exercise the role in its basic Molecule scenario with isolated, non-mutating inputs instead of a syntax-only marker stub.
- users - Add opt-in exact supplementary-group and exclusive authorized-key reconciliation for security-sensitive developer accounts.

Breaking Changes / Porting Guide
--------------------------------

- Raise collection minimum ``requires_ansible`` from ``>=2.16.1`` to ``>=2.18``. Consumers running ansible-core below 2.18 must upgrade before using this collection release.

Bugfixes
--------

- Guard external GitHub runner service metadata when the optional unit-file check is skipped.
- Make GitHub runner instance validation compatible with strict Ansible boolean conditionals and redact token-bearing instance data on failures.
- Pass ``--no-profiles`` when an instance explicitly declares an empty profile list.
- developer_tools - Bound npm registry fetch timeouts and retries so global Workbench CLI installation cannot hang indefinitely on transient network failures.
- developer_tools - Install Python virtual-environment support before creating the isolated toolchain on Ubuntu hosts.
- developer_tools - Require an exact Packer archive checksum and prevent the OpenShift client archive from reporting changes on every run.
- incus - Prevent initialization, project, and profile mutations during Ansible check mode.
- incus - Treat the recognized uninitialized-daemon response as empty storage state while failing closed for unrelated discovery errors.
- users - Reject malformed SSH key declarations before authorized-key reconciliation.

v1.8.0
======

Minor Changes
-------------

- luks_unlock - Add an explicitly non-idempotent, one-run recovery option to rebuild initramfs after an existing Clevis binding passes every verifier.

Bugfixes
--------

- luks_unlock - Enforce the declared Tang signing thumbprint during preflight and cached-advertisement enrollment, verify persisted bindings using Clevis's URL-only representation, and bound an exact-keyslot online unlock test without exposing key material.

v1.7.0
======

Minor Changes
-------------

- Add the inventory-driven ``lit.ubuntu.openssh_server`` role with validated multi-port transition support, Ubuntu systemd socket-activation reconciliation, check-mode coverage, directive-injection protection, and secure public-key-only defaults.
- Added guarded Ubuntu LUKS initramfs unlock automation with a secret-free Hetzner installimage Dropbear bootstrap, pinned Clevis Tang bindings, and a minimal Tang socket deployment role.
- developer_tools - Add configurable Node.js/npm/npx installation and markdownlint-cli2 validation support.
- docs - Apply the shared enterprise README structure.
- docs - Consolidate generated governance metadata and license policy on shared-assets-lit.
- netplan - Add validated rendering support for tagged VLAN interfaces.
- release_model - Add managed compatibility matrix documentation and structured release evidence fields.

Bugfixes
--------

- shared_tooling - Dispatch collection publishing from protected main with the managed release environment and Galaxy credential, make lint compatibility detection rely on the execution environment, and ignore generated local collection-install and Python cache artifacts.

v1.6.0
======

Minor Changes
-------------

- developer_tools - Add optional actionlint installation from the upstream release archive with checksum verification.

v1.5.0
======

Minor Changes
-------------

- molecule - Run Docker-driver light scenarios with host networking so they clean up reliably through the rootless Podman API socket.
- podman - Add optional system and rootless user Podman API socket management for workbench container flows without Docker.

v1.4.0
======

Minor Changes
-------------

- lit.ubuntu - Verify automated collection release workflow cycle 2.

v1.3.0
======

Minor Changes
-------------

- lit.ubuntu - Verify automated collection release workflow cycle 1.

v1.2.0
======

Bugfixes
--------

- ubuntu - Restore collection roles, Molecule scenarios, and collection dependency metadata on the develop branch after the shared-assets-lit release workflow migration.

v1.1.0
======

Bugfixes
--------

- ubuntu - Restore collection roles, Molecule scenarios, and collection dependency metadata on the develop branch after the shared-assets-lit release workflow migration.
