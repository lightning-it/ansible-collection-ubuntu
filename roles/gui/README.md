# lit.ubuntu.gui

Install a GUI stack on Ubuntu. Supports **GNOME** and **XFCE** (best-effort).

## Requirements

None.

## Variables

- `gui_variant`: `gnome` or `xfce`
- `gui_set_graphical_target`: set default boot target to `graphical.target` (default true)
- `gui_enable_display_manager`: enable/start `gdm` for GNOME (default true)

## Dependencies

None.

## Example Playbook

```yaml
---
- name: Use lit.ubuntu.gui
  hosts: all
  become: true
  roles:
    - role: lit.ubuntu.gui
```

## License

MIT

## Author

Lightning IT

## Additional Notes

### Usage

```yaml
- hosts: ubuntu_hosts
  become: true
  roles:
    - role: lit.ubuntu.gui
      vars:
        gui_variant: gnome   # or xfce
```

### Notes

- GNOME uses the Ubuntu group **"Server with GUI"**.
- XFCE is best-effort and may require additional repositories depending on your environment.
- For GNOME, this role can enable/start `gdm` when `gui_enable_display_manager: true`.
- For XFCE, no display manager is enforced by default (XRDP doesn't require it).
