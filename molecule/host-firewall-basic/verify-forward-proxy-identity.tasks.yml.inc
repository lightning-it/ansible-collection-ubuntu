---
- name: Install the invalid local passwd fixture
  ansible.builtin.copy:
    dest: "{{ host_firewall_test_directory }}/passwd-fixture"
    mode: "0600"
    content: >-
      {{ host_firewall_invalid_identity_case.passwd_records | join('\n') }}

- name: Verify the invalid identity is rejected before rendering
  block:
    - name: Attempt to render with the invalid local proxy identity
      ansible.builtin.include_role:
        name: lit.ubuntu.host_firewall
      vars:
        host_firewall_action: check
        host_firewall_mode: hardened
        host_firewall_egress_policy: "{{ host_firewall_proxy_test_egress_policy }}"
        host_firewall_forward_proxy_egress:
          enabled: true
          status: approved
          mode: direct
          owner_username: proxy
          interface: enp1s0
          destinations_ipv4: [0.0.0.0/0]
          ports: [80, 443]
          residual: "Owner-bound negative identity test policy."
        host_firewall_forward_proxy_access:
          enabled: false
          port: 3128
          interfaces: []
          sources_ipv4: []
          destination_ipv4: ""

    - name: Reject an invalid identity accepted by the role
      ansible.builtin.fail:
        msg: >-
          The {{ host_firewall_invalid_identity_case.name }} fixture reached
          rendering instead of failing closed.
  rescue:
    - name: Confirm the local identity assertion caused the failure
      ansible.builtin.assert:
        that:
          - >-
            'Require the exact local forward proxy account before rendering nftables'
            in ansible_failed_task.name
        fail_msg: >-
          The {{ host_firewall_invalid_identity_case.name }} fixture failed at
          an unexpected boundary: {{ ansible_failed_task.name }}.
  always:
    - name: Remove the invalid local passwd fixture
      ansible.builtin.file:
        path: "{{ host_firewall_test_directory }}/passwd-fixture"
        state: absent
