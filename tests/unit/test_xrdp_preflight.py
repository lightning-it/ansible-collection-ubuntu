"""Invalid desktop inputs must fail before any host mutation."""
import copy
import unittest
from pathlib import Path

import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar

ROLE = Path(__file__).resolve().parents[2] / 'roles/xrdp'

class XrdpPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_plugin_loader()

    def values(self):
        return yaml.safe_load((ROLE / 'defaults/main.yml').read_text())

    def accepts(self, values):
        for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())[:2]:
            contexts = [values]
            if 'loop' in task:
                contexts = [{**values, 'item': item} for item in values['xrdp_gnome_provisioned_users']]
            for context in contexts:
                gate = Conditional(loader=DataLoader())
                gate.when = task['ansible.builtin.assert']['that']
                if not gate.evaluate_conditional(Templar(DataLoader(), context), context):
                    return False
        return True

    def test_defaults_and_personal_accounts_are_valid(self):
        values = self.values()
        self.assertTrue(self.accepts(values))
        values['xrdp_gnome_provisioned_users'] = ['p1005a', 'p1006u']
        self.assertTrue(self.accepts(values))

    def test_preflight_precedes_package_file_and_command_tasks(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        self.assertEqual(tasks[1]['ansible.builtin.import_tasks'], 'assert.yml')
        self.assertEqual(set(tasks[0]) - {'name', 'when'}, {'ansible.builtin.meta'})

    def test_invalid_accounts_desktop_and_session_cannot_reach_mutations(self):
        for field, value in (
            ('xrdp_gnome_provisioned_users', ['../../root']),
            ('xrdp_gnome_provisioned_users', ['p1005a', 'p1005a']),
            ('xrdp_desktop', 'unknown'),
            ('xrdp_listen_port', 65536),
            ('xrdp_listen_address', ''),
            ('xrdp_gnome_session', 'gnome; id'),
            ('xrdp_gnome_private_dbus_session', 'true'),
            ('xrdp_release_upgrade_prompt', 'anything'),
        ):
            with self.subTest(field=field):
                values = copy.deepcopy(self.values())
                values[field] = value
                self.assertFalse(self.accepts(values))

    def test_auto_and_explicit_gnome_use_private_dbus_but_xfce_does_not(self):
        for desktop in ('auto', 'gnome', 'xfce'):
            values = self.values()
            values.update(xrdp_desktop=desktop, xrdp_gnome_private_dbus_session=True)
            values['_xrdp_desktop_effective'] = 'gnome' if desktop == 'auto' else desktop
            content = Templar(DataLoader(), values).template((ROLE / 'templates/startwm.sh.j2').read_text())
            self.assertIn(f'case "{values["_xrdp_desktop_effective"]}" in', content)
            if desktop in ('auto', 'gnome'):
                self.assertIn('exec dbus-run-session -- gnome-session', content)

    def test_marker_changes_run_as_the_account_not_root(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        selected = [task for task in tasks if task['name'] in (
            'Ensure provisioned GNOME user configuration directories',
            'Mark declared GNOME users as configured by automation')]
        self.assertEqual(len(selected), 2)
        for task in selected:
            self.assertIs(task['become'], True)
            self.assertEqual(task['become_user'], '{{ item }}')

    def test_symlink_or_file_configuration_path_is_rejected(self):
        task = next(task for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if task['name'] == 'Refuse linked or non-directory personal configuration paths')
        for linked, directory, accepted in ((True, True, False), (False, False, False), (False, True, True)):
            values = {'item': {'stat': {'exists': True, 'islnk': linked, 'isdir': directory}}}
            gate = Conditional(loader=DataLoader())
            gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)
