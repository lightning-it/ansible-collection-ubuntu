"""Invalid desktop inputs must fail before any host mutation."""
import copy
import unittest
import os
import subprocess
import tempfile
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
        self.assertEqual(tasks[0]['ansible.builtin.import_tasks'], 'assert.yml')
        self.assertEqual(tasks[0]['tags'], 'always')
        self.assertEqual(set(tasks[1]) - {'name', 'when'}, {'ansible.builtin.meta'})

    def test_invalid_accounts_desktop_and_session_cannot_reach_mutations(self):
        for field, value in (
            ('xrdp_gnome_provisioned_users', ['../../root']),
            ('xrdp_gnome_provisioned_users', ['p1005a', 'p1005a']),
            ('xrdp_desktop', 'unknown'),
            ('xrdp_listen_port', 65536),
            ('xrdp_listen_address', ''),
            ('xrdp_listen_address', '127.0.0.1\nsecurity_layer=rdp'),
            ('xrdp_listen_address', '999.1.1.1'),
            ('xrdp_listen_address', '01.2.3.4'),
            ('xrdp_listen_address', 'example.test'),
            ('xrdp_listen_address', 'tcp://127.0.0.1'),
            ('xrdp_gnome_session', 'gnome; id'),
            ('xrdp_gnome_private_dbus_session', 'true'),
            ('xrdp_release_upgrade_prompt', 'anything'),
            ('xrdp_tls_key_group', 'root'),
            ('xrdp_tls_key_group', 'docker'),
            ('xrdp_tls_key_group', 'lxd'),
            ('xrdp_tls_key_group', 'disk'),
            ('xrdp_tls_key_group', 'custom'),
            ('xrdp_tls_key_group', 'bad;group'),
            ('xrdp_tls_key_mode', '0600'),
            ('xrdp_tls_key_mode', '0644'),
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
            self.assertIn(f'case "{desktop}" in', content)
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

    def test_two_provisioned_accounts_survive_database_discovery(self):
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        reads = [task for task in tasks if 'ansible.builtin.getent' in task]
        self.assertEqual(len(reads), 2)
        for task in reads:
            self.assertNotIn('loop', task)
            self.assertNotIn('key', task['ansible.builtin.getent'])
        account_gate = next(task for task in tasks if task['name'].startswith('Require every declared'))
        home_gate = next(task for task in tasks if task['name'] == 'Validate discovered home directories')
        facts = {'getent_passwd': {name: ['x', '1001', '1001', '', '/home/' + name, '/bin/bash']
                                  for name in ('p1005a', 'p1006u')},
                 'getent_group': {name: ['x', '1001', ''] for name in ('p1005a', 'p1006u')}}
        for name in ('p1005a', 'p1006u'):
            values = {'ansible_facts': facts, 'item': name}
            for task in (account_gate, home_gate):
                gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
                self.assertTrue(gate.evaluate_conditional(Templar(DataLoader(), values), values))
        values = {'ansible_facts': facts, 'item': 'missing'}
        gate = Conditional(loader=DataLoader()); gate.when = account_gate['ansible.builtin.assert']['that']
        self.assertFalse(gate.evaluate_conditional(Templar(DataLoader(), values), values))

    def test_tang_network_is_an_inline_role_argument(self):
        spec = yaml.safe_load((ROLE.parent / 'host_firewall/meta/argument_specs.yml').read_text())
        self.assertEqual(spec['argument_specs']['main']['options']['host_firewall_tang_network'],
                         {'type': 'str', 'choices': ['public', 'management']})

    def test_missing_custom_tls_group_is_rejected_with_no_gnome_users(self):
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        read = next(task for task in tasks if task['name'] == 'Discover existing personal GNOME groups before changes')
        gate = Conditional(loader=DataLoader()); gate.when = [read['when']]
        values = {**self.values(), 'ansible_facts': {'getent_group': {}}}
        self.assertTrue(gate.evaluate_conditional(Templar(DataLoader(), values), values))
        task = next(task for task in tasks if task['name'].startswith('Require a known package-owned'))
        gate.when = task['ansible.builtin.assert']['that']
        for group, present, expected in [('missing-custom', False, False), ('custom', True, False),
                                         ('ssl-cert', False, True), ('xrdp', False, True)]:
            values['xrdp_tls_key_group'] = group
            values['ansible_facts']['getent_group'] = {group: []} if present else {}
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)

    def test_real_getent_discovery_keeps_two_accounts(self):
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        reads = [task for task in tasks if 'ansible.builtin.getent' in task]
        with tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
            directory = Path(temporary)
            config = directory / 'ansible.cfg'; config.write_text('[defaults]\n')
            play = [{'hosts': 'localhost', 'gather_facts': False,
                     'vars': {'xrdp_gnome_provisioned_users': ['root', 'bin']},
                     'tasks': reads + [{'ansible.builtin.assert': {'that': [
                         "'root' in ansible_facts.getent_passwd", "'bin' in ansible_facts.getent_passwd",
                         "'root' in ansible_facts.getent_group", "'bin' in ansible_facts.getent_group"]}}]}]
            source = directory / 'play.yml'; source.write_text(yaml.safe_dump(play))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(source)],
                                    check=False, capture_output=True, text=True, timeout=30,
                                    env={**os.environ, 'ANSIBLE_CONFIG': str(config),
                                         'ANSIBLE_LOCAL_TEMP': str(directory / 'ansible')})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_same_named_group_requires_actual_membership(self):
        task = next(task for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if task['name'].startswith('Require every declared'))
        for primary, members, expected in [('1001', '', True), ('1002', 'p1005a', True),
                                            ('1002', 'someoneelse', False)]:
            values = {'item': 'p1005a', 'ansible_facts': {
                'getent_passwd': {'p1005a': ['x', '1001', primary, '', '/home/p1005a', '/bin/bash']},
                'getent_group': {'p1005a': ['x', '1001', members]}}}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)
