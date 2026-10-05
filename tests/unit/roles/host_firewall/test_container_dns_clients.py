"""Exercise actual per-client DNS guards, rendering and policy fingerprinting."""

from copy import deepcopy
import unittest

from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
import yaml

from test_published_https import ROLE, render, variables


def enabled_variables():
    values = variables()
    values.update({
        "host_firewall_container_interfaces": ["edgea", "edgeb"],
        "host_firewall_observed_container_bridge_gateways_ipv4": {
            "edgea": "10.88.10.1", "edgeb": "10.88.20.1"},
        "host_firewall_observed_ipv4_addresses": ["10.88.10.1", "10.88.20.1"],
        "host_firewall_container_dns_clients": {
            "service_a": {"interface": "edgea", "source_ipv4": "10.88.10.2/32", "destination_ipv4": "10.88.10.1"},
            "service_b": {"interface": "edgeb", "source_ipv4": "10.88.20.2/32", "destination_ipv4": "10.88.20.1"},
        },
    })
    return values


def guard_accepts(values):
    loader = DataLoader()
    tasks = yaml.safe_load((ROLE / "tasks/container_dns_clients_assert.yml").read_text())
    for task in tasks:
        contexts = [values]
        if "loop" in task:
            items = Templar(loader, values).template(task["loop"])
            contexts = [{**values, "item": item} for item in items]
        for context in contexts:
            gate = Conditional(loader=loader)
            gate.when = task["ansible.builtin.assert"]["that"]
            if not gate.evaluate_conditional(Templar(loader, context), context):
                return False
    return True


class ContainerDnsClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def rejected(self, values):
        try:
            self.assertFalse(guard_accepts(values))
        except (AnsibleError, KeyError, TypeError):
            pass

    def test_empty_default_preserves_fingerprint_material(self):
        values = variables()
        self.assertTrue(guard_accepts(values))
        material = Templar(DataLoader(), values).template(values["host_firewall_policy_material_effective"])
        self.assertNotIn("container_dns_clients", material)

    def test_two_distinct_gateways_are_bound_into_exact_udp_rules(self):
        values = enabled_variables()
        self.assertTrue(guard_accepts(values))
        material = Templar(DataLoader(), values).template(values["host_firewall_policy_material_effective"])
        self.assertEqual(material["container_dns_clients"], values["host_firewall_container_dns_clients"])
        policy = render(values)
        for client in values["host_firewall_container_dns_clients"].values():
            prefix = (f'iifname "{client["interface"]}" ip saddr {client["source_ipv4"]} '
                      f'ip daddr {client["destination_ipv4"]}')
            self.assertIn(prefix + " udp dport 53 ct state new accept", policy)
            self.assertNotIn(prefix + " tcp dport 53", policy)
        self.assertNotIn('iifname "edgea" ip saddr 10.88.10.2/32 ip daddr 10.88.20.1', policy)

    def test_cross_gateway_missing_evidence_public_or_broad_source_rejected(self):
        for key, value in (
            ("destination_ipv4", "10.88.20.1"),
            ("destination_ipv4", "8.8.8.8"),
            ("source_ipv4", "10.88.10.0/29"),
            ("source_ipv4", "8.8.8.8/32"),
            ("source_ipv4", "127.0.0.1/32"),
            ("source_ipv4", "10.88.10.1/32"),
            ("source_ipv4", "10.88.20.1/32"),
            ("interface", "eth0"),
            ("interface", 'edgea" accept'),
        ):
            values = enabled_variables()
            values["host_firewall_container_dns_clients"]["service_a"][key] = value
            with self.subTest(key=key, value=value):
                self.rejected(values)
        values = enabled_variables()
        del values["host_firewall_observed_container_bridge_gateways_ipv4"]["edgea"]
        self.rejected(values)

    def test_non_gateway_host_address_cannot_be_a_dns_client(self):
        values = enabled_variables()
        values['host_firewall_observed_ipv4_addresses'].append('192.168.40.5')
        values['host_firewall_container_dns_clients']['service_a']['source_ipv4'] = '192.168.40.5/32'
        self.rejected(values)

    def test_closed_schema_and_legacy_mutual_exclusion(self):
        values = enabled_variables()
        values["host_firewall_container_dns_clients"]["service_a"]["protocol"] = "tcp"
        self.rejected(values)
        values = enabled_variables()
        values["host_firewall_container_dns_access"] = {"enabled": True}
        self.rejected(values)
        values = enabled_variables()
        values["host_firewall_container_dns_clients"] = []
        self.rejected(values)

    def test_each_client_changes_the_authorization_fingerprint(self):
        values = enabled_variables()
        changed = deepcopy(values)
        changed["host_firewall_container_dns_clients"]["service_b"]["source_ipv4"] = "10.88.20.3/32"
        fingerprint = lambda data: Templar(DataLoader(), data).template(data["host_firewall_policy_fingerprint"])
        self.assertNotEqual(fingerprint(values), fingerprint(changed))
