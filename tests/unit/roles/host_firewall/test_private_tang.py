"""Actual Tang ingress guards and nftables interface/destination isolation."""
import unittest
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
from test_published_https import ROLE, render, variables

class PrivateTangTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def accepts(self, values):
        task = next(t for t in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if t['name'] == 'Validate Tang function contract')
        gate = Conditional(loader=DataLoader())
        gate.when = task['ansible.builtin.assert']['that']
        return gate.evaluate_conditional(Templar(DataLoader(), values), values)

    def test_management_rule_has_no_public_interface_or_destination(self):
        values = variables()
        values['host_firewall_tang_network'] = 'management'
        self.assertTrue(self.accepts(values))
        rule = next(line for line in render(values).splitlines() if 'ip saddr @tang_sources_v4' in line)
        self.assertIn('"' + values['host_firewall_management_interface'] + '"', rule)
        self.assertIn('ip daddr ' + values['host_firewall_expected_management_ipv4'], rule)
        self.assertNotIn('"' + values['host_firewall_public_interface'] + '"', rule)
        self.assertNotIn('ip daddr ' + values['host_firewall_expected_public_ipv4'], rule)
        material = Templar(DataLoader(), values).template(values['host_firewall_policy_material_effective'])
        self.assertEqual(material['tang_network'], 'management')

    def test_unknown_network_fails_closed(self):
        for value in ('any', '', None, 'management\naccept'):
            values = variables()
            values['host_firewall_tang_network'] = value
            self.assertFalse(self.accepts(values))

    def test_management_ipv6_rejected(self):
        values = variables()
        values['host_firewall_tang_network'] = 'management'
        values['host_firewall_tang_access']['sources_ipv6'] = ['::1/128']
        self.assertFalse(self.accepts(values))

    def test_public_default_retains_original_rule(self):
        values = variables()
        self.assertTrue(self.accepts(values))
        rule = next(line for line in render(values).splitlines() if 'ip saddr @tang_sources_v4' in line)
        self.assertIn('"' + values['host_firewall_public_interface'] + '"', rule)
        self.assertIn('ip daddr ' + values['host_firewall_expected_public_ipv4'], rule)

    def test_public_default_preserves_original_policy_material_and_fingerprint(self):
        values = variables()
        engine = Templar(DataLoader(), values)
        base = engine.template(values['host_firewall_policy_material'])
        effective = engine.template(values['host_firewall_policy_material_effective'])
        self.assertNotIn('tang_network', base)
        self.assertNotIn('tang_network', effective)
        self.assertEqual(effective, base)
