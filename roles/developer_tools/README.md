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

developer_tools_github_cli_enabled: false
developer_tools_github_cli_package_name: gh
developer_tools_github_cli_repo_name: gh-cli
developer_tools_github_cli_repo_description: packages for the GitHub CLI
developer_tools_github_cli_repo_baseurl: https://cli.github.com/packages/rpm
developer_tools_github_cli_repo_gpgcheck: true
developer_tools_github_cli_repo_gpgkey: https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x23F3D4EA75716059

developer_tools_argocd_cli_enabled: false
developer_tools_argocd_cli_version: v3.3.3
developer_tools_argocd_cli_url: "https://github.com/argoproj/argo-cd/releases/download/{{ developer_tools_argocd_cli_version }}/argocd-linux-amd64"
developer_tools_argocd_cli_dest: /usr/local/bin/argocd

developer_tools_terragrunt_enabled: false
developer_tools_terragrunt_version: v0.93.8
developer_tools_terragrunt_arch: "{{ 'arm64' if ansible_architecture in ['aarch64', 'arm64'] else 'amd64' }}"
developer_tools_terragrunt_url: "https://github.com/gruntwork-io/terragrunt/releases/download/{{ developer_tools_terragrunt_version }}/terragrunt_linux_{{ developer_tools_terragrunt_arch }}"
developer_tools_terragrunt_dest: /usr/local/bin/terragrunt

developer_tools_oc_cli_enabled: false
developer_tools_oc_cli_version: 4.18.24
developer_tools_oc_cli_archive_url: "https://mirror.openshift.com/pub/openshift-v4/clients/ocp/{{ developer_tools_oc_cli_version }}/openshift-client-linux-amd64-linux-{{ developer_tools_oc_cli_version }}.tar.gz"
developer_tools_oc_cli_archive_path: "/var/tmp/openshift-client-linux-amd64-linux-{{ developer_tools_oc_cli_version }}.tar.gz"
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
- When `developer_tools_terragrunt_enabled` is true, the role downloads the Terragrunt standalone binary from the official GitHub release assets.
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
          - podman
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
