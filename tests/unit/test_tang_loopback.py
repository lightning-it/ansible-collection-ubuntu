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

    def test_existing_unit_check_mode_previews_service_drift(self):
        tasks = yaml.safe_load((ROOT / 'tasks/main.yml').read_text())
        service = next(task for task in tasks if 'ansible.builtin.systemd_service' in task)
        for check, load_state, expected in [(False, '', True), (True, 'loaded', True), (True, 'not-found', False),
                                             (True, 'masked', True), (True, 'error', True),
                                             (True, 'bad-setting', True), (True, '', True)]:
            with self.subTest(check=check, load_state=load_state):
                values = {'tang_deploy_enabled': True, 'tang_deploy_manage_service': True,
                          'ansible_check_mode': check, '_tang_deploy_unit_load_state': {'stdout': load_state}}
                gate = Conditional(loader=DataLoader()); gate.when = service['when']
                self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)

    def test_package_reconciliation_preserves_explicit_stopped_state(self):
        tasks = yaml.safe_load((ROOT / 'tasks/main.yml').read_text())
        packages = next(task for task in tasks if 'ansible.builtin.apt' in task)
        self.assertIn('Tang deploy | Restart socket', packages['notify'])
        handler = next(t for t in yaml.safe_load((ROOT / 'handlers/main.yml').read_text())
                       if t['name'] == 'Tang deploy | Restart socket')
        for state, enabled, check, accepted in [('started', True, False, True), ('stopped', True, False, False),
                ('started', False, False, False), ('started', True, True, False)]:
            values = {'tang_deploy_manage_service': True, 'tang_deploy_enabled': enabled,
                      'tang_deploy_socket_state': state, 'ansible_check_mode': check}
            gate = Conditional(loader=DataLoader()); gate.when = handler['when']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)

    def test_externally_managed_package_lifecycle_is_not_suppressed(self):
        packages = next(t for t in yaml.safe_load((ROOT / 'tasks/main.yml').read_text()) if 'ansible.builtin.apt' in t)
        expression = packages['ansible.builtin.apt']['policy_rc_d']
        for managed, expected in [(True, '101'), (False, 'OMIT_FIXTURE')]:
            values = {'tang_deploy_manage_service': managed, 'omit': 'OMIT_FIXTURE'}
            self.assertEqual(Templar(DataLoader(), values).template(expression), expected)
