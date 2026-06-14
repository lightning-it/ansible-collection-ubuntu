# lit.ubuntu.xrdp

XRDP server role for Ubuntu.

## Repo policy
This role **never enables repository sources**.
Enable repositories via `lit.ubuntu.repos` (or your internal mirror policy).

## What it does
- Precheck: fails fast if xrdp packages are not available in enabled repos
- Installs XRDP packages
- Configures `/etc/xrdp/xrdp.ini` and `/etc/xrdp/startwm.sh`
- Optional TLS, firewalld port open
