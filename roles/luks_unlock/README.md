# lit.ubuntu.luks_unlock

Configure early-boot access to an existing encrypted Ubuntu root filesystem. The role never partitions, formats,
unbinds, removes keyslots, or removes the manual recovery passphrase.

## Requirements

- Ubuntu with an existing LUKS2 device for Clevis operations.
- Root privileges.
- A trusted, out-of-band Tang signing thumbprint for `clevis_tang` mode.
- An externally stored LUKS header backup and recovery passphrase before adding a Clevis keyslot.
- Hetzner `installimage` when using `rescue_stage`; its `-x` hook is executed inside the installed system.

For first boot, use `rescue_stage` with `dropbear`. The generated script is secret-free, self-removes from the target,
and exposes its Rescue path as `luks_unlock_installimage_post_install_script_path`. Pass that fact to
`installimage -x`. Add Clevis only after the host has booted, Tang is online, and its thumbprint is verified. Keeping
Dropbear installed provides a manual fallback if Tang is unavailable.

After validating the generated initramfs, the hook prints only the dedicated Dropbear and normal OpenSSH Ed25519
SHA256 fingerprint markers. It also stores those two public fingerprints in
`/boot/lit-first-boot-hostkey-fingerprints` with mode `0644` so an operator can pin both first-boot identities even
when installimage output is suppressed.

## Variables

See `defaults/main.yml` for the complete interface. Important inputs are:

- `luks_unlock_enabled`: opt in to the role; defaults to `false`.
- `luks_unlock_execution_mode`: `installed` or `rescue_stage`.
- `luks_unlock_method`: `dropbear` or `clevis_tang`. Rescue staging accepts only `dropbear`.
- `luks_unlock_early_network`: structured static or DHCP early-boot network configuration. Static bootstrap currently
  accepts IPv4 addresses only.
- `luks_unlock_network_modules`: NIC drivers to force into the initramfs, for example `igb`.
- `luks_unlock_dropbear_authorized_keys`: raw public SSH keys. The role adds a forced `cryptroot-unlock` command and
  disables forwarding.
- `luks_unlock_rescue_stage_path`: secret-free executable rendered on the Rescue host.
- `luks_unlock_devices`: existing LUKS2 devices and deterministic free keyslots for Clevis. Select a device with an
  explicit absolute `device`, a known `crypttab_name`, or `crypttab_name: auto`. Automatic selection requires exactly
  one active non-comment entry in `/etc/crypttab`; UUID and PARTUUID sources are resolved with `findfs` and then
  canonicalized before inspection. This role manages early-root unlock, so `initramfs` must be `true`.
- `luks_unlock_clevis_tang_url` and `luks_unlock_clevis_tang_thumbprint`: pinned Tang policy.
- `luks_unlock_clevis_network_timeout_seconds`: socket timeout for the advertisement fetch and runtime before a
  Tang-dependent read-only Clevis subprocess is terminated. It defaults to 30 seconds, accepts values from 1 through
  600, and gives Clevis a five-second grace period before forced termination.
- `luks_unlock_existing_passphrases`: passphrases keyed by device id. Supply from a secret manager; tasks using these
  values use `no_log` and stdin.
- `luks_unlock_allow_luks_metadata_change` and `luks_unlock_header_backup_confirmed`: both must be `true` before a
  missing Clevis binding can be added.
- `luks_unlock_force_rebuild_initramfs`: exceptional recovery opt-in that queues a boot-image rebuild after an
  already-existing binding passes every verifier. It requires `luks_unlock_rebuild_initramfs: true` and does not
  authorize LUKS metadata changes. This force option intentionally reports a change and rebuilds on every enabled
  run, so enable it for one recovery run and then return it to `false`.

An existing mismatched or occupied keyslot fails safely. The role does not edit or replace it automatically. Clevis
uses the thumbprint to authenticate the Tang advertisement during enrollment, while `clevis luks list` reports only
the persisted URL. The role therefore fetches and verifies the pinned advertisement before mutation, uses that cached
advertisement for offline enrollment, verifies the reported pin and URL, and pipes `clevis luks pass` directly into a
read-only `cryptsetup --test-passphrase --key-slot` check. No decrypted key is placed in an Ansible or shell variable,
and the role never passes Clevis's trust-bypass (`-y`) option.

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Stage a secret-free first-boot unlock hook
  hosts: rescue_hosts
  become: true
  roles:
    - role: lit.ubuntu.luks_unlock
      vars:
        luks_unlock_enabled: true
        luks_unlock_execution_mode: rescue_stage
        luks_unlock_method: dropbear
        luks_unlock_early_network:
          method: static
          interface: enp1s0
          address: 192.0.2.10
          gateway: 192.0.2.1
          netmask: 255.255.255.0
          hostname: example-host
          dns:
            - 192.0.2.53
        luks_unlock_network_modules:
          - igb
        luks_unlock_dropbear_authorized_keys:
          - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIExampleOnly operator@example.invalid"
```

## Testing

The default Molecule scenario uses deterministic command doubles and runs in the normal collection gate:

```bash
bash scripts/devtools-molecule.sh luks-unlock-basic
```

The optional live scenario provisions Tang and a real LUKS2 loop device inside a disposable Ubuntu 24.04 container.
It requires a rootful Docker daemon and a privileged container, is intentionally excluded from ordinary PR checks,
and should run only on an isolated runner:

```bash
bash scripts/devtools-molecule.sh luks-unlock-tang_heavy
```

## License

MIT

## Author

Lightning IT
