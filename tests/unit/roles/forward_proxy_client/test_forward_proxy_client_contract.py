from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
ROLE_ROOT = REPOSITORY_ROOT / "roles" / "forward_proxy_client"


class ForwardProxyClientContractTests(unittest.TestCase):
    def test_adapter_contains_no_squid_runtime(self) -> None:
        role_text = "".join(path.read_text() for path in sorted(ROLE_ROOT.rglob("*")) if path.is_file())
        self.assertNotIn("ubuntu/squid@sha256", role_text)
        self.assertNotIn("podman_systemd", role_text)
        self.assertNotIn("squid-pod", role_text)
        self.assertNotIn("ansible.builtin.apt", role_text)

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
        self.assertIn("forward_proxy_client_restart_services: []", defaults)
        self.assertIn("forward_proxy_client_restart_now: false", defaults)
        self.assertIn("Reload systemd manager after changing proxy client defaults", tasks)
        self.assertIn("forward_proxy_client_systemd_environment_result.changed", tasks)
        self.assertIn('loop: "{{ forward_proxy_client_restart_services }}"', tasks)
        self.assertIn("forward_proxy_client_restart_now | bool", tasks)

    def test_container_boundary_matches_the_host_firewall(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        firewall_assertions = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml"
        ).read_text()
        self.assertIn("forward_proxy_client_container_firewall_access.interfaces | length > 0", assertions)
        self.assertIn("forward_proxy_client_container_firewall_access.sources_ipv4 | length > 0", assertions)
        self.assertIn("not forward_proxy_client_container_firewall_access.destination_ipv4.startswith('127.')", assertions)
        self.assertIn("192\\.168\\.", assertions)
        self.assertIn("192\\.168\\.", firewall_assertions)
        self.assertIn("172\\.(?:1[6-9]|2[0-9]|3[01])\\.", firewall_assertions)
        self.assertIn("/(?:[89]|[12][0-9]|3[0-2])$", assertions)
        self.assertIn("/(?:1[6-9]|2[0-9]|3[0-2])$", firewall_assertions)

    def test_disabled_state_cleans_only_adapter_owned_state(self) -> None:
        tasks = "".join(path.read_text() for path in sorted((ROLE_ROOT / "tasks").glob("*.yml")))
        variables = (ROLE_ROOT / "vars" / "main.yml").read_text()
        self.assertIn("Inspect the forward proxy client managed-state marker", tasks)
        self.assertIn("forward_proxy_client_previous_state_manifest.managed_paths", tasks)
        self.assertIn("lit.ubuntu.forward_proxy_client.managed-state/v2", tasks)
        self.assertNotIn("managed-state/v1", variables)
        self.assertIn("checksum_algorithm: sha256", tasks)
        self.assertIn("item.stat.isreg", tasks)
        self.assertIn("item.stat.islnk", tasks)
        self.assertIn("Refuse to adopt unowned forward proxy client target paths", tasks)
        self.assertIn("Refuse to adopt new unowned forward proxy client target paths", tasks)
        self.assertIn("not item.stat.exists", tasks)
        self.assertIn("Refuse unsafe forward proxy client managed directories", tasks)
        self.assertNotIn("_forward_proxy_client_", tasks)

    def test_firewall_mode_and_ports_match_service_upstream_mode(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("forward_proxy_client_firewall_egress.get('mode', '')", assertions)
        self.assertIn("forward_proxy_client_firewall_egress.get('ports', [])", assertions)
        self.assertIn("if forward_proxy_client_upstream_enabled", assertions)


if __name__ == "__main__":
    unittest.main()
