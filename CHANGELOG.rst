===================================================
Lightning IT Collection Release Notes Release Notes
===================================================

.. contents:: Topics

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
