"""Exercise exact container SSH guards and rendered input capabilities."""
from copy import deepcopy
import unittest

from ansible.errors import AnsibleError
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
import yaml

from test_published_https import ROLE, render, variables


def fixture():
    values = variables()
    values.update(host_firewall_mode="hardened",
                  host_firewall_observed_container_bridge_gateways_ipv4={"podman0": "10.88.0.1"})
    values["host_firewall_observed_ipv4_addresses"].append("10.88.0.1")
    return values


def enabled():
    values = fixture()
    values["host_firewall_container_ssh_access"] = {"console": {
        "interface": "podman0", "source_ipv4": "10.88.0.3/32",
        "destination_ipv4": "10.88.0.1", "port": 1905, "modes": ["hardened"],
    }}
    return values


def accepts(values):
    loader = DataLoader()
    for task in yaml.safe_load((ROLE / "tasks/container_ssh_assert.yml").read_text()):
        contexts = [values]
        if "loop" in task:
            contexts = [{**values, "item": item} for item in Templar(loader, values).template(task["loop"])]
        for context in contexts:
            gate = Conditional(loader=loader)
            gate.when = task["ansible.builtin.assert"]["that"]
            if not gate.evaluate_conditional(Templar(loader, context), context):
                return False
    return True


class ContainerSSHTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def test_disabled_default_has_no_new_input_capability_or_fingerprint(self):
        values = fixture()
        self.assertTrue(accepts(values))
        self.assertNotIn("ip saddr 10.88.0.3/32", render(values))
        material = Templar(DataLoader(), values).template(values["host_firewall_policy_material_effective"])
        self.assertNotIn("container_ssh_access", material)

    def test_disabled_role_validates_capabilities_before_exit(self):
        tasks = yaml.safe_load((ROLE / "tasks/main.yml").read_text())
        validation = next(i for i, task in enumerate(tasks) if task.get("ansible.builtin.import_tasks") == "container_ssh_assert.yml")
        exit_index = next(i for i, task in enumerate(tasks) if task.get("ansible.builtin.meta") == "end_role")
        self.assertLess(validation, exit_index)
        self.assertNotIn("when", tasks[validation])
        values = fixture(); values["host_firewall_enabled"] = False
        values["host_firewall_container_ssh_access"] = ["invalid"]
        self.assertFalse(accepts(values))

    def test_enabled_is_exact_and_bound_into_fingerprint(self):
        values = enabled()
        self.assertTrue(accepts(values))
        rule = 'iifname "podman0" ip saddr 10.88.0.3/32 ip daddr 10.88.0.1 tcp dport 1905 ct state new accept'
        self.assertEqual(render(values).count(rule), 1)
        self.assertIn("policy drop", render(values))
        material = Templar(DataLoader(), values).template(values["host_firewall_policy_material_effective"])
        self.assertEqual(material["container_ssh_access"], values["host_firewall_container_ssh_access"])

    def test_public_observed_gateway_and_host_spoofing_are_rejected(self):
        values = enabled()
        values["host_firewall_observed_container_bridge_gateways_ipv4"]["podman0"] = "8.8.8.8"
        values["host_firewall_observed_ipv4_addresses"].append("8.8.8.8")
        values["host_firewall_container_ssh_access"]["console"]["destination_ipv4"] = "8.8.8.8"
        self.assertFalse(accepts(values))
        for source in ("10.88.0.1", "10.88.0.2"):
            values = enabled()
            values["host_firewall_observed_ipv4_addresses"].append("10.88.0.2")
            values["host_firewall_container_ssh_access"]["console"]["source_ipv4"] = source + "/32"
            self.assertFalse(accepts(values))

    def test_widened_or_unobserved_grants_fail_closed(self):
        for change in ({"source_ipv4": "10.88.0.0/24"}, {"source_ipv4": "8.8.8.8/32"},
                       {"destination_ipv4": "192.0.2.10"}, {"destination_ipv4": "10.89.0.1"},
                       {"interface": "enp1s0"}, {"port": 22}, {"port": 3128},
                       {"modes": ["bootstrap", "hardened"]}, {"extra": True}):
            with self.subTest(change=change):
                values = deepcopy(enabled())
                values["host_firewall_container_ssh_access"]["console"].update(change)
                try:
                    self.assertFalse(accepts(values))
                except (AnsibleError, KeyError, TypeError):
                    pass


if __name__ == "__main__":
    unittest.main()
