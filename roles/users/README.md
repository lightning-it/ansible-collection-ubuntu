# Users Role

Manage local users, their groups, and authorized SSH keys on Ubuntu hosts.

## Variables

### `users_accounts`

List of user definitions. Each item can include:

```yaml
users_accounts:
  - name: "ops-admin"         # required
    state: present            # present|absent (default: present)
    uid: 1001
    gid: ops                  # primary group name or GID
    groups: ["sudo", "devs"]  # supplementary groups
    shell: /bin/bash
    home: /home/ops-admin
    create_home: true
    update_password: on_create
    password_lock: false
    remove: false             # remove home on absent if true
    ssh_keys:
      - "ssh-ed25519 AAAA... comment"
```

### `users_manage_groups`

Whether to create any groups referenced in `users_accounts` before assignment. Default: `true`.

## Example

```yaml
- hosts: all
  become: true

  roles:
    - role: lit.ubuntu.users
      vars:
        users_manage_groups: true
        users_accounts:
          - name: ops-admin
            uid: 1001
            groups: ["sudo"]
            shell: /bin/bash
            ssh_keys:
              - "ssh-ed25519 AAAA... ops"
          - name: old-user
            state: absent
            remove: true
```
