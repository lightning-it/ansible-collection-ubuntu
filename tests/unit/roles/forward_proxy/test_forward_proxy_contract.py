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
        self.assertIn("host_firewall_forward_proxy_access.interfaces | length > 0", assertions)
        self.assertIn("host_firewall_forward_proxy_access.sources_ipv4 | length > 0", assertions)

    def test_upstream_hostname_is_validated_label_by_label(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("forward_proxy_upstream_host | length <= 253", assertions)
        self.assertIn("forward_proxy_upstream_host.split('.')", assertions)
        self.assertIn("[A-Za-z0-9-]{0,61}", assertions)

    def test_package_bootstrap_requires_both_apt_transports(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        tasks = (ROLE_ROOT / "tasks" / "main.yml").read_text()
        self.assertIn("{name: bootstrap_http, port: 80}", assertions)
        self.assertIn("{name: bootstrap_https, port: 443}", assertions)
        self.assertIn("temporary package-bootstrap transport", assertions)
        self.assertIn("policy_rc_d: 101", tasks)
        self.assertIn("masked: true", tasks)
        self.assertIn("forward_proxy_bootstrap_listener_readback.stdout", tasks)

    def test_apt_override_wins_and_encodes_exact_direct_hosts(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        template = (ROLE_ROOT / "templates" / "apt-proxy.conf.j2").read_text()
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("/etc/apt/apt.conf.d/99-lit-forward-proxy", defaults)
        self.assertIn("Acquire::http::Proxy::{{ host }} \"DIRECT\";", template)
        self.assertIn("Acquire::https::Proxy::{{ host }} \"DIRECT\";", template)
        self.assertIn("APT DIRECT exceptions must be exact hostnames", assertions)

    def test_existing_systemd_clients_have_explicit_idempotent_cutover(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        tasks = (ROLE_ROOT / "tasks" / "main.yml").read_text()
        handlers = (ROLE_ROOT / "handlers" / "main.yml").read_text()
        self.assertIn("forward_proxy_restart_services: []", defaults)
        self.assertIn("ansible.builtin.meta: flush_handlers", tasks)
        self.assertIn("forward_proxy_systemd_environment_result.changed", tasks)
        self.assertIn('loop: "{{ forward_proxy_restart_services }}"', tasks)
        self.assertIn("masked: false", handlers)


if __name__ == "__main__":
    unittest.main()
