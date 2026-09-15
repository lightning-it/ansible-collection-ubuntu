from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
ROLE_ROOT = REPOSITORY_ROOT / "roles" / "forward_proxy"


class ForwardProxyContractTests(unittest.TestCase):
    def test_host_integrations_require_loopback_listener_and_client(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("'127.0.0.1' in forward_proxy_listen_addresses", assertions)
        self.assertIn("'127.0.0.1/32' in forward_proxy_allowed_clients", assertions)

    def test_non_loopback_listener_requires_complete_container_boundary(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("or forward_proxy_container_enabled", assertions)
        self.assertIn("forward_proxy_container_firewall_access.interfaces | length > 0", assertions)
        self.assertIn("forward_proxy_container_firewall_access.sources_ipv4 | length > 0", assertions)
        self.assertNotIn("host_firewall_forward_proxy_access.interfaces", assertions)
        self.assertNotIn("host_firewall_container_interfaces", assertions)

    def test_upstream_hostname_is_validated_label_by_label(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("forward_proxy_upstream_host | length <= 253", assertions)
        self.assertIn("forward_proxy_upstream_host.split('.')", assertions)
        self.assertIn("[A-Za-z0-9-]{0,61}", assertions)

    def test_runtime_is_a_digest_pinned_non_root_container(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        pod = (ROLE_ROOT / "templates" / "squid-pod.yml.j2").read_text()
        tasks = (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        self.assertIn("docker.io/ubuntu/squid@sha256:", defaults)
        self.assertIn("forward_proxy_image_pull_policy: Never", defaults)
        self.assertIn("hostNetwork: true", pod)
        self.assertIn("runAsUser: {{ forward_proxy_runtime_uid }}", pod)
        self.assertIn("readOnlyRootFilesystem: true", pod)
        self.assertIn("capabilities:", pod)
        self.assertIn("name: lit.foundational.podman_systemd", tasks)
        self.assertIn("Verify the pinned Squid image was preloaded", tasks)
        self.assertIn("Wait for the local Squid listener", tasks)
        self.assertNotIn("ansible.builtin.apt", tasks)
        self.assertNotIn("squid.service", tasks)

    def test_steady_state_cannot_pull_the_proxy_image(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        pod = (ROLE_ROOT / "templates" / "squid-pod.yml.j2").read_text()
        self.assertIn("forward_proxy_image_pull_policy == 'Never'", assertions)
        self.assertIn("imagePullPolicy: {{ forward_proxy_image_pull_policy }}", pod)

    def test_apt_override_wins_and_encodes_exact_direct_hosts(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        template = (ROLE_ROOT / "templates" / "apt-proxy.conf.j2").read_text()
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("/etc/apt/apt.conf.d/99-lit-forward-proxy", defaults)
        self.assertIn('Acquire::http::Proxy::{{ host }} "DIRECT";', template)
        self.assertIn('Acquire::https::Proxy::{{ host }} "DIRECT";', template)
        self.assertIn("APT DIRECT exceptions are restricted to host-local loopback", assertions)
        self.assertIn("difference(['localhost', '127.0.0.1'])", assertions)

    def test_existing_systemd_clients_have_explicit_idempotent_cutover(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        tasks = (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        self.assertIn("forward_proxy_restart_services: []", defaults)
        self.assertIn("Reload systemd manager after changing proxy defaults", tasks)
        self.assertIn("forward_proxy_systemd_environment_result.changed", tasks)
        self.assertIn('loop: "{{ forward_proxy_restart_services }}"', tasks)

    def test_disabled_state_cleans_only_role_owned_managed_state(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        tasks = (
            (ROLE_ROOT / "tasks" / "main.yml").read_text()
            + (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        )
        self.assertIn("forward_proxy_state_marker_path", defaults)
        self.assertIn("Inspect the forward proxy managed-state marker", tasks)
        self.assertIn("Remove forward proxy managed configuration when disabled", tasks)
        self.assertIn("forward_proxy_state_marker.stat.exists", tasks)
        self.assertIn("Record that the role owns the managed forward proxy state", tasks)
        self.assertIn("forward_proxy_previous_state_manifest.managed_paths", tasks)
        self.assertIn("lit.ubuntu.forward_proxy.managed-state/v1", tasks)

    def test_role_does_not_flush_unrelated_handlers(self) -> None:
        tasks = (
            (ROLE_ROOT / "tasks" / "main.yml").read_text()
            + (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        )
        self.assertNotIn("ansible.builtin.meta: flush_handlers", tasks)
        self.assertIn("Reload systemd manager after changing proxy defaults", tasks)

    def test_squid_is_readonly_runtime_compatible(self) -> None:
        template = (ROLE_ROOT / "templates" / "squid.conf.j2").read_text()
        self.assertIn("acl lit_http_ports port 80", template)
        self.assertIn("http_access deny !lit_connect !lit_http_ports", template)
        self.assertIn("pid_filename /tmp/squid.pid", template)
        self.assertIn("cache_dir null /tmp", template)
        self.assertIn("access_log stdio:/dev/stdout", template)
        self.assertIn("cache_log /dev/stderr", template)
        self.assertNotIn("/var/log/squid", template)

    def test_container_proxy_destination_cannot_be_host_loopback(self) -> None:
        assertions = (REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml").read_text()
        self.assertIn("host_firewall_forward_proxy_access.destination_ipv4 != '127.0.0.1'", assertions)

    def test_proxy_client_networks_reject_global_ipv4_scope(self) -> None:
        role_assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        firewall_assertions = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml"
        ).read_text()
        self.assertIn("/(?:[1-9]|[12][0-9]|3[0-2])$", role_assertions)
        self.assertIn("/(?:[1-9]|[12][0-9]|3[0-2])$", firewall_assertions)


if __name__ == "__main__":
    unittest.main()
