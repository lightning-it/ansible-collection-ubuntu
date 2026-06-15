# lit.ubuntu.incus_image

Import Incus image artifacts into the local Incus image store and manage aliases.

This role assumes the image artifacts already exist on the Incus host or are
reachable as URLs. Use `lit.supplementary.artifacts` first when artifacts should
be downloaded from Hetzner Object Storage, S3-compatible storage, MinIO, or an
internal HTTPS endpoint.

## Requirements

- Ubuntu Incus host.
- `incus` CLI installed and usable by the Ansible connection user, or set
  `incus_image_command_user` to run Incus commands as another local user.
- Incus metadata tarball and optional rootfs/qcow2 artifact.

## Variables

- `incus_image_enabled` (bool, default: `true`): Enable the role.
- `incus_image_binary` (string, default: `incus`): Incus CLI path or command.
- `incus_image_force_local` (bool, default: `true`): Add `--force-local`.
- `incus_image_command_user` (string, default: `""`): Optional local user for Incus commands.
- `incus_image_default_project` (string, default: `""`): Optional Incus project.
- `incus_image_default_replace` (bool, default: `false`): Use `incus image import --reuse`.
- `incus_image_default_public` (bool, default: `false`): Import images as public.
- `incus_image_default_properties` (mapping, default: `{}`): Common image properties.
- `incus_image_items` (list, default: `[]`): Image definitions.

Each `incus_image_items` entry supports:

- `alias`: Local image alias without `local:` prefix.
- `metadata`: Path or URL to the metadata tarball.
- `rootfs`: Optional path or URL to a rootfs tarball or qcow2.
- `replace`: Override default replacement behavior.
- `public`: Override default public behavior.
- `project`: Override default Incus project.
- `properties`: Image properties passed to `incus image import` as `key=value`.

## Example

```yaml
---
- name: Import RHEL images into Incus
  hosts: incus_hosts
  become: true
  roles:
    - role: lit.ubuntu.incus_image
      vars:
        incus_image_command_user: github-runner
        incus_image_items:
          - alias: rhel10-aap-ci
            metadata: /srv/incus/images/rhel-10-cloud-metadata.tar.xz
            rootfs: /srv/incus/images/rhel-10-cloud.qcow2
            replace: true
            properties:
              description: RHEL 10 AAP CI image
```

## License

MIT
