---
# lit.ubuntu.firefox

Shared base role for the Firefox lifecycle roles in this collection:

- `lit.ubuntu.firefox_deploy`
- `lit.ubuntu.firefox_config`
- `lit.ubuntu.firefox_destroy`

This role centralizes:

- shared defaults
- discovery of installed state and user profile paths
- proxy normalization
- bookmark normalization
- enterprise policy generation
- per-user `user.js` generation helpers
- teardown helpers

This role is intentionally not the main lifecycle execution role.

## Design note

This split keeps shared logic centralized, keeps lifecycle roles small, avoids
duplicating defaults and helper tasks, and aligns with the collection pattern
used for enterprise workstation roles.

## Configuration model

The role set supports two practical models:

1. System-wide managed Firefox configuration through enterprise policies in
   `/etc/firefox/policies/policies.json`
2. Optional per-user profile-backed preferences through `user.js`

The role prefers enterprise policy for settings that Firefox supports cleanly on
Ubuntu, including:

- proxy
- homepage
- DNS over HTTPS
- telemetry-related settings
- default browser checks
- password manager availability
- corporate bookmarks
- download defaults

Per-user configuration is limited to preference-backed settings in `user.js`.
Per-user bookmark editing is intentionally not implemented because Firefox stores
user bookmarks in profile SQLite databases, which is not a clean declarative
target for Ansible. For reproducible corporate defaults, this role uses Firefox
enterprise bookmark policy.

## Common variables

```yaml
firefox_enabled: true
firefox_package_name: firefox
firefox_install_state: present

firefox_user: ""
firefox_manage_user_profile: false
firefox_profiles_ini_path: ""
firefox_profile_path: ""
firefox_profile_required: false

firefox_manage_system_policies: true
firefox_policy_dir: /etc/firefox/policies

firefox_proxy_enabled: false
firefox_proxy_mode: none
firefox_proxy_http_host: ""
firefox_proxy_http_port: 0
firefox_proxy_https_host: ""
firefox_proxy_https_port: 0
firefox_proxy_socks_host: ""
firefox_proxy_socks_port: 0
firefox_proxy_passthrough: []
firefox_proxy_use_same_for_all: true
firefox_proxy_autoconfig_url: ""

firefox_bookmarks_enabled: false
firefox_bookmarks_toolbar_name: Corporate
firefox_bookmarks_menu_name: Corporate
firefox_bookmarks: []

firefox_homepage: ""
firefox_disable_telemetry: false
firefox_disable_default_browser_check: false
firefox_disable_password_manager: false
firefox_enable_dns_over_https: false

firefox_remove_package: false
firefox_remove_config: false
firefox_remove_policies: false
firefox_remove_bookmarks: false
```

## Example configuration

```yaml
firefox_user: developer
firefox_manage_user_profile: true

firefox_proxy_enabled: true
firefox_proxy_mode: manual
firefox_proxy_http_host: proxy.corp.l-it.io
firefox_proxy_http_port: 3128
firefox_proxy_https_host: proxy.corp.l-it.io
firefox_proxy_https_port: 3128
firefox_proxy_use_same_for_all: true
firefox_proxy_passthrough:
  - localhost
  - 127.0.0.1
  - .corp.l-it.io

firefox_homepage: https://portal.corp.l-it.io

firefox_bookmarks_enabled: true
firefox_bookmarks:
  - name: GitLab
    url: https://gitlab.corp.l-it.io
    location: toolbar
    folder: Platform
  - name: Argo CD
    url: https://argocd.corp.l-it.io
    location: toolbar
    folder: Platform
  - name: Vault
    url: https://vault.corp.l-it.io
    location: menu
    folder: Security
```

## Scope notes

- Linux policy files are written to `/etc/firefox/policies`, which Firefox
  supports as a system-wide policy location.
- Bookmark placement uses the `Bookmarks` enterprise policy because it supports
  toolbar/menu placement and folders. This role does not use
  `ManagedBookmarks`, because that policy exposes bookmarks only through a
  managed toolbar button and does not fit the requested location model.
