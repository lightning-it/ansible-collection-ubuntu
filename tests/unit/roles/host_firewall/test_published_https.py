"""Exercise the real HTTPS input guards and rendered nftables boundaries."""

from copy import deepcopy
from pathlib import Path
import unittest

from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
import yaml

ROOT = Path(__file__).resolve().parents[4]
ROLE = ROOT / "roles/host_firewall"
SCENARIO = ROOT / "molecule/host-firewall-basic"


def variables():
    defaults = yaml.safe_load((ROLE / "defaults/main.yml").read_text())
    play = yaml.safe_load((SCENARIO / "converge.yml").read_text())[0]
    return {
        **defaults,
        **yaml.safe_load((SCENARIO / "vars/egress.yml").read_text()),
        **play["roles"][0]["vars"],
        "inventory_hostname": "host-firewall.example.test",
        "ansible_facts": {"getent_passwd": {"proxy": ["x", "13", "13"]}},
    }


def enabled_variables():
    result = variables()
    result["host_firewall_published_https_access"] = {
        "enabled": True,
        "host_proxy": False,
        "endpoints": [{"interface": "podman0", "ipv4": "10.88.0.2"}],
    }
    return result


def guard_accepts(values):
    loader = DataLoader()
    for task in yaml.safe_load((ROLE / "tasks/published_https_assert.yml").read_text()):
        contexts = [values]
        if "loop" in task:
            items = Templar(loader, values).template(task["loop"])
            contexts = [{**values, "item": item} for item in items]
        for context in contexts:
            gate = Conditional(loader=loader)
            if "when" in task:
                condition = task["when"]
                gate.when = condition if isinstance(condition, list) else [condition]
                if not gate.evaluate_conditional(Templar(loader, context), context):
                    continue
            gate.when = task["ansible.builtin.assert"]["that"]
            if not gate.evaluate_conditional(Templar(loader, context), context):
                return False
    return True


def render(values):
    return Templar(DataLoader(), values).template(
        (ROLE / "templates/host-firewall.nft.j2").read_text()
    )


class PublishedHttpsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def rejected(self, values):
        try:
            self.assertFalse(guard_accepts(values))
        except (AnsibleError, KeyError, TypeError):
            pass  # Undefined or malformed input must not reach rendering.

    def test_default_is_closed_and_does_not_change_fingerprint_material(self):
        values = variables()
        self.assertTrue(guard_accepts(values))
        self.assertNotIn("ct status dnat", render(values))
        material = Templar(DataLoader(), values).template(
            values["host_firewall_policy_material_effective"]
        )
        self.assertNotIn("published_https_access", material)

    def test_enabled_declaration_is_bound_into_fingerprint(self):
        values = enabled_variables()
        self.assertTrue(guard_accepts(values))
        material = Templar(DataLoader(), values).template(
            values["host_firewall_policy_material_effective"]
        )
        self.assertEqual(
            material["published_https_access"],
            values["host_firewall_published_https_access"],
        )

    def test_plan_reports_actual_forwarding_including_https_only(self):
        tasks = yaml.safe_load((ROLE / "tasks/render.yml").read_text())
        expression = tasks[1]["ansible.builtin.set_fact"]["host_firewall_plan"][
            "new_container_forwarding"
        ]
        values = enabled_variables()
        values["host_firewall_container_service_access"] = {}
        self.assertEqual(
            Templar(DataLoader(), values).template(expression), "restricted"
        )
        values["host_firewall_public_service_access"]["https"]["modes"] = ["hardened"]
        self.assertEqual(Templar(DataLoader(), values).template(expression), "denied")
        values["host_firewall_published_https_access"]["enabled"] = False
        values["host_firewall_public_service_access"] = {}
        self.assertEqual(Templar(DataLoader(), values).template(expression), "denied")

    def test_malformed_or_disabled_nonempty_contract_is_rejected(self):
        for contract in (
            {},
            [],
            "enabled",
            {"enabled": "true", "endpoints": [], "host_proxy": False},
            {"enabled": False, "endpoints": [], "host_proxy": True},
            {"enabled": True, "endpoints": [], "host_proxy": False},
            {"enabled": True, "endpoints": {}, "host_proxy": False},
            {"enabled": True, "endpoints": [], "host_proxy": "false"},
        ):
            with self.subTest(contract=contract):
                values = variables()
                values["host_firewall_published_https_access"] = contract
                self.rejected(values)

    def test_widened_public_service_or_missing_source_contract_is_rejected(self):
        for change in (
            {"protocol": "udp"},
            {"port": 8443},
            {"sources_ipv4": []},
            {"sources_ipv6": ["::1/128"]},
        ):
            with self.subTest(change=change):
                values = enabled_variables()
                values["host_firewall_public_service_access"]["https"].update(change)
                self.rejected(values)
        values["host_firewall_public_service_access"] = {}
        self.rejected(values)

    def test_arbitrary_interface_address_or_duplicate_endpoint_is_rejected(self):
        for change in (
            {"interface": "enp1s0"},
            {"interface": "lo"},
            {"interface": "unexpected"},
            {"ipv4": "0.0.0.0"},
            {"ipv4": "127.0.0.1"},
            {"ipv4": "192.0.2.2"},
            {"ipv4": "10.0.30.10"},
            {"ipv4": "10.88.0.0/24"},
            {"ipv4": "::1"},
            {"ipv4": "10.88.0.2\naccept"},
            {"ipv4": 168296450},
            {"port": 8080},
        ):
            with self.subTest(change=change):
                values = enabled_variables()
                values["host_firewall_published_https_access"]["endpoints"][0].update(
                    change
                )
                self.rejected(values)
        for endpoint in (
            {"interface": "podman0", "ipv4": "10.88.0.3"},
            {"interface": "podman1", "ipv4": "10.88.0.2"},
        ):
            values = enabled_variables()
            values["host_firewall_published_https_access"]["endpoints"].append(endpoint)
            self.rejected(values)

    def test_forward_rules_require_original_and_translated_endpoints(self):
        values = enabled_variables()
        policy = render(values)
        forward = policy.split("chain forward {", 1)[1].split("chain output {", 1)[0]
        rules = [line for line in forward.splitlines() if "ct status dnat" in line]
        self.assertEqual(len(rules), 4)
        for rule in rules:
            self.assertIn('"enp1s0"', rule)
            self.assertIn('"podman0"', rule)
            self.assertIn("10.88.0.2", rule)
            self.assertIn("ct original ip saddr @public_https_sources_v4", rule)
            self.assertIn("ct original ip daddr 192.0.2.10", rule)
            self.assertIn("ct original protocol tcp ct original proto-dst 443", rule)
        self.assertIn("ct direction original", rules[0])
        self.assertIn("ct direction reply", rules[1])
        self.assertIn("ct state established", rules[1])
        self.assertTrue(
            all(
                "ct state related" in line and "ip protocol icmp" in line
                for line in rules[2:]
            )
        )
        self.assertNotIn("ct status dnat", policy.split("chain output {", 1)[1])
        self.assertIn("iifname @container_interfaces goto container_guard", forward)
        self.assertIn("policy drop", forward)

    def test_hairpin_requires_validated_proxy_and_explicit_host_source(self):
        values = enabled_variables()
        values["host_firewall_published_https_access"]["host_proxy"] = True
        self.rejected(deepcopy(values))
        values["host_firewall_forward_proxy_egress"]["enabled"] = True
        self.rejected(deepcopy(values))
        values["host_firewall_public_service_access"]["https"]["sources_ipv4"].append(
            "192.0.2.10/32"
        )
        self.assertTrue(guard_accepts(values))
        output = render(values).split("chain output {", 1)[1]
        rules = [line for line in output.splitlines() if "ct status dnat" in line]
        self.assertEqual(len(rules), 1)
        for value in (
            "meta skuid 13",
            'oifname "podman0"',
            "ip daddr 10.88.0.2",
            "tcp dport 443",
            "ct original ip daddr 192.0.2.10",
            "ct original proto-dst 443",
            "ct direction original",
        ):
            self.assertIn(value, rules[0])

    def test_two_interfaces_are_individually_bound_and_modes_remain_enforced(self):
        values = enabled_variables()
        values["host_firewall_published_https_access"]["endpoints"].append(
            {"interface": "podman1", "ipv4": "10.89.0.2"}
        )
        self.assertTrue(guard_accepts(values))
        policy = render(values)
        self.assertEqual(policy.count("ct status dnat"), 8)
        values["host_firewall_public_service_access"]["https"]["modes"] = ["hardened"]
        self.assertNotIn("ct status dnat", render(values))


if __name__ == "__main__":
    unittest.main()
