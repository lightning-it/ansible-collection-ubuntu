# CIS Ubuntu 24 Role

Thin wrapper around `ansible-lockdown.ubuntu24_cis`.

## Requirements

The execution environment must install `ansible-lockdown.ubuntu24_cis` as a Galaxy role.

## Variables

Set `cis_ubuntu24_profile_tag` to exactly one native upstream profile tag:
`level1-server`, `level1-workstation`, `level2-server`, or
`level2-workstation`. For remediation, set
`cis_ubuntu24_execution_mode: remediate` and invoke Ansible with that same
single `--tags` value. For the independent audit, set
`cis_ubuntu24_execution_mode: audit` and invoke Ansible with exactly
`--tags setup_audit`; the inventory profile remains the authority for
post-processing applicability. The wrapper rejects untagged, broad-tagged,
mixed-profile, and `--skip-tags` runs.

The wrapper requires `ubtu24cis_level_1` and `ubtu24cis_level_2` to match the
declared profile. They shape upstream audit content but do not select
remediation tasks. Audit mode additionally requires `setup_audit`, `run_audit`,
`audit_only`, and `fetch_audit_output` to be true, JSON output, and the pinned
Git audit source. Configure other upstream variables such as
`ubtu24cis_disruption_high` through inventory.

`cis_ubuntu24_exceptions` is the inventory-owned exception registry. Each item
records control IDs, scope, reason, compensating control, effective upstream
variables, and audit visibility. Omitted controls remain exceptions and must
never be reported as passes.

When upstream AIDE remediation uses its default cron scheduler, the wrapper
masks the unused package-provided `dailyaidecheck.service`. This preserves the
cron job while preventing the upstream role from repeatedly attempting to
disable a static systemd unit. Selecting the upstream timer scheduler removes
only that wrapper-owned `/dev/null` mask before the upstream role configures
the timer units. The absolute path defaults to
`/etc/systemd/system/dailyaidecheck.service`; override
`cis_ubuntu24_aide_service_path` only when the target uses another systemd unit
directory or for an isolated integration test.

The upstream 6.2.4.1 remediation recursively applies a file-only mode to the
audit log directory. When inventory explicitly disables that defective
control while retaining 6.2.4.4, the wrapper preserves `/var/log/audit` as a
traversable mode-0750 directory. Inventory must separately document the
6.2.4.1 exception and its audit-log-file compensating control.
Override `cis_ubuntu24_audit_log_directory` only when auditd uses a different
absolute log directory.

The persistent network-control file remains `root:root` by default. Setting
`cis_ubuntu24_network_sysctl_owner` and
`cis_ubuntu24_network_sysctl_group` to null preserves the current ownership;
this is intended for an isolated, non-root integration-test path only.

## Dependencies

External Galaxy role: `ansible-lockdown.ubuntu24_cis`.

- Remediation: `ansible-lockdown/UBUNTU24-CIS` release `1.6.0`, commit
  `c893ca6836fb32b1ea067d4a63c341e39693074b`, MIT.
- Audit: `ansible-lockdown/UBUNTU24-CIS-Audit` benchmark `v1.0.0`, commit
  `87efcc6d409d1a998a7cb809c5ce5a6afedf84c7`, MIT.

The remediation role is updated through `requirements.yml`. Audit content has
no upstream release, so update its immutable commit and archive checksum
together after reviewing compatibility with the remediation release.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.cis_ubuntu24
  hosts: ubuntu24_cis_targets
  become: true
  vars:
    cis_ubuntu24_profile_tag: level1-server
  roles:
    - role: lit.ubuntu.cis_ubuntu24
```

Invoke the example with `--tags level1-server`.

## License

MIT

## Author

Lightning IT
