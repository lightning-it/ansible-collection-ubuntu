---
# lit.ubuntu.firefox_deploy

Install Firefox on Ubuntu using the shared `lit.ubuntu.firefox` helper role.

## Scope

This role:

- validates shared Firefox inputs
- discovers shared Firefox state
- installs the Firefox package
- prepares the system-wide policy directory when enabled

This role does not manage ongoing browser settings, bookmarks, or user profile
preferences. Use `lit.ubuntu.firefox_config` for that.

## Example

```yaml
- hosts: workstations
  roles:
    - role: lit.ubuntu.firefox_deploy
```
