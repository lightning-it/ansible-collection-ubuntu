"""Loopback binding guards reject widening and socket directive injection."""
import unittest
from pathlib import Path
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
ROOT = Path(__file__).resolve().parents[2] / 'roles/tang_deploy'

class LoopbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def accepts(self, values):
        gate = Conditional(loader=DataLoader())
        gate.when = yaml.safe_load((ROOT / 'tasks/assert.yml').read_text())[1]['ansible.builtin.assert']['that']
        return gate.evaluate_conditional(Templar(DataLoader(), values), values)

    def test_loopback_socket_is_explicit(self):
        values = yaml.safe_load((ROOT / 'defaults/main.yml').read_text())
        values.update(tang_deploy_enabled=True, tang_deploy_manage_socket_override=True,
                      tang_deploy_listen_address='127.0.0.1', tang_deploy_listen_port=7500)
        self.assertTrue(self.accepts(values))
        config = Templar(DataLoader(), values).template((ROOT / 'templates/tangd.socket.conf.j2').read_text())
        self.assertIn('ListenStream=127.0.0.1:7500', config)
        for invalid in ('0.0.0.0', '::', '127.0.0.1\nListenStream=80'):
            values['tang_deploy_listen_address'] = invalid
            self.assertFalse(self.accepts(values))
        values['tang_deploy_listen_address'] = '127.0.0.1'
        values['tang_deploy_manage_socket_override'] = False
        self.assertFalse(self.accepts(values))
