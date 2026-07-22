# lit.ubuntu.developer_tools

---
# lit.ubuntu.developer_tools

Install developer-oriented packages, Python packages, and optional CLI binaries on Ubuntu.

## Requirements

- Ubuntu / EL 9 host
- `become: true` for package and repository management
- Run `gh auth login --git-protocol ssh` manually after provisioning if GitHub access is needed

## Variables

See `defaults/main.yml` for the full interface. Key inputs:

```yaml
developer_tools_enabled: true
developer_tools_packages_present: []
developer_tools_pip_executable: pip3
developer_tools_pip_packages_present: []
developer_tools_pip_extra_args: ""

developer_tools_python_venv_enabled: false
developer_tools_python_venv_path: /opt/lit/developer-tools
developer_tools_python_venv_python: python3
developer_tools_python_venv_support_packages:
  - python3-venv
developer_tools_python_venv_packages:
  - ansible-core==2.18.18
developer_tools_python_venv_commands:
  - ansible
  - ansible-playbook
developer_tools_python_venv_link_dir: /usr/local/bin

developer_tools_nodejs_enabled: false
developer_tools_nodejs_package_source: os
developer_tools_nodejs_package_state: present
developer_tools_nodejs_packages_present:
  - nodejs
  - npm
developer_tools_node_executable: node
developer_tools_npm_executable: npm
developer_tools_npx_executable: npx
developer_tools_nodejs_validate: true
developer_tools_nodejs_expected_users:
  - ops-admin
developer_tools_npm_packages_present:
  - name: example-cli
    version: 1.2.3
developer_tools_node_options: ""

developer_tools_markdownlint_cli2_enabled: false
developer_tools_markdownlint_cli2_install_mode: global
developer_tools_markdownlint_cli2_package_name: markdownlint-cli2
developer_tools_markdownlint_cli2_version: ""
developer_tools_markdownlint_cli2_validate: true

developer_tools_github_cli_enabled: false
developer_tools_github_cli_package_name: gh
developer_tools_github_cli_repo_name: gh-cli
developer_tools_github_cli_repo_description: packages for the GitHub CLI
developer_tools_github_cli_repo_baseurl: https://cli.github.com/packages/rpm
developer_tools_github_cli_repo_gpgcheck: true
developer_tools_github_cli_repo_gpgkey: https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x23F3D4EA75716059

developer_tools_git_config_enabled: false
developer_tools_git_config_credential_helper: "!gh auth git-credential"
developer_tools_git_config_credential_url: https://github.com
developer_tools_git_config_credential_use_http_path: true
developer_tools_git_config_users:
  - user: ops-admin
    name: Ops Admin
    email: ops-admin@example.com
    username: ops-admin

developer_tools_terminal_config_enabled: false
developer_tools_terminal_config_users:
  - ops-admin
developer_tools_terminal_config_manage_tmux: true
developer_tools_terminal_config_manage_screen: true
developer_tools_terminal_config_tmux_path: .tmux.conf
developer_tools_terminal_config_screen_path: .screenrc

developer_tools_workspace_enabled: false
developer_tools_workspace_users:
  - ops-admin
developer_tools_workspace_directories:
  - sources
  - worktrees
  - artifacts
  - .cache/lit

developer_tools_release_binary_cache_dir: /var/cache/lit/developer-tools
developer_tools_release_binaries:
  - name: example
    version: 1.2.3
    url: https://downloads.example.com/example-1.2.3-linux-amd64
    filename: example-1.2.3-linux-amd64
    checksum: sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
    dest: /usr/local/bin/example
    archive: false

developer_tools_argocd_cli_enabled: false
developer_tools_argocd_cli_version: v3.3.3
developer_tools_argocd_cli_url: "https://github.com/argoproj/argo-cd/releases/download/{{ developer_tools_argocd_cli_version }}/argocd-linux-amd64"
developer_tools_argocd_cli_dest: /usr/local/bin/argocd

developer_tools_terragrunt_enabled: false
developer_tools_terragrunt_version: v0.93.8
developer_tools_terragrunt_arch: "{{ 'arm64' if ansible_architecture in ['aarch64', 'arm64'] else 'amd64' }}"
developer_tools_terragrunt_url: "https://github.com/gruntwork-io/terragrunt/releases/download/{{ developer_tools_terragrunt_version }}/terragrunt_linux_{{ developer_tools_terragrunt_arch }}"
developer_tools_terragrunt_dest: /usr/local/bin/terragrunt

developer_tools_actionlint_enabled: false
developer_tools_actionlint_version: 1.7.12
developer_tools_actionlint_arch: "{{ 'arm64' if ansible_architecture in ['aarch64', 'arm64'] else 'amd64' }}"
developer_tools_actionlint_archive_url: "https://github.com/rhysd/actionlint/releases/download/v{{ developer_tools_actionlint_version }}/actionlint_{{ developer_tools_actionlint_version }}_linux_{{ developer_tools_actionlint_arch }}.tar.gz"
developer_tools_actionlint_checksum_url: "https://github.com/rhysd/actionlint/releases/download/v{{ developer_tools_actionlint_version }}/actionlint_{{ developer_tools_actionlint_version }}_checksums.txt"
developer_tools_actionlint_archive_path: "/var/tmp/actionlint_{{ developer_tools_actionlint_version }}_linux_{{ developer_tools_actionlint_arch }}.tar.gz"
developer_tools_actionlint_extract_dir: "/var/tmp/actionlint-{{ developer_tools_actionlint_version }}"
developer_tools_actionlint_dest: /usr/local/bin/actionlint

developer_tools_packer_enabled: false
developer_tools_packer_version: 1.15.4
developer_tools_packer_arch: "{{ 'arm64' if ansible_architecture in ['aarch64', 'arm64'] else 'amd64' }}"
developer_tools_packer_archive_url: "https://releases.hashicorp.com/packer/{{ developer_tools_packer_version }}/packer_{{ developer_tools_packer_version }}_linux_{{ developer_tools_packer_arch }}.zip"
developer_tools_packer_archive_path: "/var/tmp/packer_{{ developer_tools_packer_version }}_linux_{{ developer_tools_packer_arch }}.zip"
developer_tools_packer_extract_dir: "/var/tmp/packer-{{ developer_tools_packer_version }}"
developer_tools_packer_dest: /usr/local/bin/packer
developer_tools_packer_checksum: ""  # Required when Packer is enabled.

developer_tools_oc_cli_enabled: false
developer_tools_oc_cli_version: 4.18.24
developer_tools_oc_cli_archive_url: "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{{ developer_tools_oc_cli_version }}/openshift-client-linux-{{ developer_tools_oc_cli_version }}.tar.gz"
developer_tools_oc_cli_checksum: ""  # Required when the OpenShift CLI is enabled.
developer_tools_oc_cli_archive_path: "/var/tmp/openshift-client-linux-{{ developer_tools_oc_cli_version }}.tar.gz"
developer_tools_oc_cli_extract_dir: "/var/tmp/openshift-client-{{ developer_tools_oc_cli_version }}"
developer_tools_oc_cli_dest: /usr/local/bin/oc

developer_tools_kubectl_cli_enabled: false
developer_tools_kubectl_cli_dest: /usr/local/bin/kubectl

developer_tools_ssh_agent_enabled: false
developer_tools_ssh_agent_users: []
developer_tools_ssh_agent_identity_files:
  - ~/.ssh/id_ed25519
developer_tools_ssh_agent_package_name: openssh-client
developer_tools_ssh_agent_service_name: ssh-agent.service
developer_tools_ssh_agent_socket: "%t/ssh-agent.socket"
developer_tools_ssh_agent_manage_shell_init: true
developer_tools_ssh_agent_shell_init_files:
  - .bash_profile
  - .bashrc
developer_tools_ssh_agent_manage_ssh_config: true
developer_tools_ssh_agent_add_keys_to_agent: true

developer_tools_ssh_private_keys_enabled: false
developer_tools_ssh_private_keys:
  - user: rene
    vault_kv_path: "{{ inventory_hostname }}/developer_tools/ssh_keys/rene"
developer_tools_ssh_private_keys_no_log: true
developer_tools_ssh_private_keys_path: .ssh/id_ed25519
developer_tools_ssh_private_keys_type: ed25519
developer_tools_ssh_private_keys_manage_public_keys: true
developer_tools_ssh_private_keys_known_hosts_entries: []
developer_tools_ssh_private_keys_vault_addr: https://vault.example.com:8200
developer_tools_ssh_private_keys_vault_validate_certs: true
developer_tools_ssh_private_keys_vault_kv_mount: stage-2c
developer_tools_ssh_private_keys_vault_token: "{{ lookup('ansible.builtin.env', 'VAULT_TOKEN') }}"
developer_tools_ssh_private_keys_vault_role_id: ""
developer_tools_ssh_private_keys_vault_secret_id: ""
```

- When `developer_tools_github_cli_enabled` is true, the role configures the official GitHub CLI RPM repository and installs `gh`.
- When `developer_tools_git_config_enabled` is true, the role configures per-user Git identity and credential helper
  settings. Passwords and tokens are not written by this role; with the default `!gh auth git-credential` helper,
  users authenticate with `gh auth login`, and `gh` manages the credential secret store.
- When `developer_tools_terminal_config_enabled` is true, the role writes base `~/.tmux.conf` and `~/.screenrc`
  files for the configured users. Install `tmux` and `screen` through `developer_tools_packages_present` when needed.
- When `developer_tools_nodejs_enabled` is true, the role installs Node.js/npm/npx from the configured OS package
  source and validates `node --version`, `npm --version`, and `npx --version`. The default package source is `os`;
  external repositories such as NodeSource must be configured separately and explicitly before overriding package names.
- `developer_tools_npm_packages_present` installs only explicitly versioned global npm packages. Authentication remains
  user-scoped and must not be supplied through this list.
- `developer_tools_node_options` supplies an optional Node.js `NODE_OPTIONS` string to npm/npx operations, for example
  `--dns-result-order=ipv4first` when a host has no working IPv6 egress (default: empty).
- `developer_tools_python_venv_enabled` creates one isolated, pinned Python toolchain and exposes only the listed
  command entry points through stable symlinks. This avoids `--break-system-packages` on Ubuntu 24.
- `developer_tools_release_binaries` installs data-driven standalone binaries or archives only after an exact SHA-256
  checksum succeeds. Keep environment-specific versions, URLs, and checksums in inventory.
- `developer_tools_workspace_enabled` creates private source, worktree, artifact, and cache directories for existing
  users without cloning, deleting, or overwriting repositories.
- When `developer_tools_markdownlint_cli2_enabled` is true, the role installs `markdownlint-cli2` globally with npm
  by default and validates `npx markdownlint-cli2 --version`. Set `developer_tools_markdownlint_cli2_install_mode`
  to `npx` to avoid a global npm package and validate package execution through `npx --yes` instead.
- When `developer_tools_terragrunt_enabled` is true, the role downloads the Terragrunt standalone binary from the official GitHub release assets.
- When `developer_tools_actionlint_enabled` is true, the role downloads and installs the pinned `actionlint`
  standalone binary after verifying the upstream release checksum file.
- When `developer_tools_packer_enabled` is true, the role downloads and installs the pinned HashiCorp Packer binary
  from the official HashiCorp release assets. An exact `developer_tools_packer_checksum` is mandatory.
- When `developer_tools_ssh_agent_enabled` is true, the role configures a persistent `systemd --user` `ssh-agent`
  service, exports `SSH_AUTH_SOCK` in the selected shell init files, and adds an `~/.ssh/config` block that can
  auto-add the configured identity files to the agent on first SSH use.
- When `developer_tools_ssh_private_keys_enabled` is true, the role reads per-user SSH keys from Vault KV v2, generates
  a dedicated key locally on the control node when the secret is absent, stores it back into Vault, and writes the
  private key to `~/.ssh/id_ed25519` with mode `0600`. Secret-bearing tasks use `no_log: true`.

## Dependencies

None.

## Example Playbook

```yaml
- hosts: workbenches
  become: true
  roles:
    - role: lit.ubuntu.developer_tools
      vars:
        developer_tools_packages_present:
          - git
          - npm
          - nodejs
          - podman
          - screen
          - tmux
        developer_tools_nodejs_enabled: true
        developer_tools_markdownlint_cli2_enabled: true
        developer_tools_nodejs_expected_users:
          - ops-admin
        developer_tools_terminal_config_enabled: true
        developer_tools_terminal_config_users:
          - ops-admin
        developer_tools_ssh_agent_enabled: true
        developer_tools_ssh_agent_users:
          - ops-admin
        developer_tools_ssh_private_keys_enabled: true
        developer_tools_ssh_private_keys_vault_addr: https://vault.example.com:8200
        developer_tools_ssh_private_keys_vault_kv_mount: stage-2c
        developer_tools_ssh_private_keys_vault_token: "{{ lookup('ansible.builtin.env', 'VAULT_TOKEN') }}"
        developer_tools_ssh_private_keys:
          - user: ops-admin
            vault_kv_path: "{{ inventory_hostname }}/developer_tools/ssh_keys/ops-admin"
```

## License

MIT

## Author

Lightning IT
