"""Invalid desktop inputs must fail before any host mutation."""
import copy
import os
import subprocess
import tempfile
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

    def test_tls_paths_reject_control_characters_relative_and_identical_inputs(self):
        task = next(task for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if task['name'].startswith('Require distinct absolute TLS paths'))
        for field in ('xrdp_tls_cert_path', 'xrdp_tls_key_path'):
            for value in ('relative.pem', '/tmp/leaf\nsecurity_layer=rdp', '/tmp/leaf\r', '/tmp/leaf\t', '/tmp/leaf\x00', '/tmp/leaf\x7f', '/etc/xrdp/../xrdp/leaf.pem', '/etc//xrdp/leaf.pem'):
                values = self.values(); values[field] = value
                gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
                self.assertFalse(gate.evaluate_conditional(Templar(DataLoader(), values), values))
        values = self.values(); values['xrdp_tls_key_path'] = values['xrdp_tls_cert_path']
        gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
        self.assertFalse(gate.evaluate_conditional(Templar(DataLoader(), values), values))
        values = self.values()
        self.assertTrue(gate.evaluate_conditional(Templar(DataLoader(), values), values))

    def test_home_traversal_probe_runs_as_the_user_before_package_mutations(self):
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        probes = [task for task in tasks if task['name'].startswith(('Verify personal home traversal', 'Verify personal home write'))]
        self.assertEqual(len(probes), 2)
        for task in probes:
            self.assertIs(task['become'], True)
            self.assertEqual(task['become_user'], '{{ item }}')
            self.assertIs(task['changed_when'], False)
            self.assertIs(task['check_mode'], False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); ancestor = root / 'ancestor'; ancestor.mkdir()
            home = ancestor / 'home'; home.mkdir(); home.chmod(0o700)
            argv = probes[0]['ansible.builtin.command']['argv'][:2] + [str(home)]
            self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 0)
            try:
                ancestor.chmod(0o700 & ~0o111)
                self.assertNotEqual(subprocess.run(argv, capture_output=True).returncode, 0)
            finally:
                ancestor.chmod(0o700)

    def test_optional_release_upgrade_config_must_exist_and_not_be_a_link(self):
        task = next(task for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if task['name'] == 'Require an existing regular release upgrade configuration')
        for stat, accepted in [({'exists': False}, False),
                ({'exists': True, 'isreg': True, 'islnk': True}, False),
                ({'exists': True, 'isreg': False, 'islnk': False}, False),
                ({'exists': True, 'isreg': True, 'islnk': False}, True)]:
            values = {'_xrdp_release_upgrade_preflight': {'stat': stat}}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)

    def test_auto_and_explicit_gnome_use_private_dbus_but_xfce_does_not(self):
        for desktop in ('auto', 'gnome', 'xfce'):
            values = self.values()
            values.update(xrdp_desktop=desktop, xrdp_gnome_private_dbus_session=True)
            values['_xrdp_desktop_effective'] = 'gnome' if desktop == 'auto' else desktop
            content = Templar(DataLoader(), values).template((ROLE / 'templates/startwm.sh.j2').read_text())
            self.assertIn(f'case "{desktop}" in', content)
            if desktop in ('auto', 'gnome'):
                self.assertIn('exec dbus-run-session -- gnome-session', content)
            else:
                xfce_branch = content.split('  xfce)', 1)[1].split('  auto|*)', 1)[0]
                self.assertIn('exec startxfce4', xfce_branch)
                self.assertNotIn('dbus-run-session', xfce_branch)

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
            values = {'item': {'item': 'p1005a', 'stat': {'exists': True, 'islnk': linked, 'isdir': directory, 'uid': 1001, 'gid': 1001, 'mode': '0700'}}, 'ansible_facts': {'getent_passwd': {'p1005a': ['x','1001','1001']}, 'getent_group': {'p1005a': ['x','1001']}}}
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

class ExistingDirectoryOwnershipTests(unittest.TestCase):
    def test_home_and_config_owned_by_other_account_fail_before_packages(self):
        init_plugin_loader()
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        for name in ('Refuse linked or missing personal home directories',
                     'Refuse linked or non-directory personal configuration paths'):
            task = next(task for task in tasks if task['name'] == name)
            for uid, gid, accepted in ((1001, 1001, True), (0, 1001, False), (1002, 1001, False), (1001, 0, False)):
                values = {'item': {'item': 'p1005a', 'stat': {'exists': True, 'isdir': True, 'islnk': False,
                                                            'uid': uid, 'gid': gid, 'mode': '0700'}},
                          'ansible_facts': {'getent_passwd': {'p1005a': ['x', '1001', '1001']},
                                            'getent_group': {'p1005a': ['x', '1001']}}}
                gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
                self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)

class TlsPathSafetyTests(unittest.TestCase):
    def test_default_listener_is_loopback_in_defaults_and_argument_spec(self):
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        spec = yaml.safe_load((ROLE / 'meta/argument_specs.yml').read_text())
        self.assertEqual(defaults['xrdp_listen_address'], '127.0.0.1')
        self.assertEqual(spec['argument_specs']['main']['options']['xrdp_listen_address']['default'], '127.0.0.1')

    def test_default_tls_files_are_separate_from_package_symlinks(self):
        defaults = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        spec = yaml.safe_load((ROLE / 'meta/argument_specs.yml').read_text())
        for field, value in (('xrdp_tls_cert_path', '/etc/xrdp/lit-cert.pem'),
                             ('xrdp_tls_key_path', '/etc/xrdp/lit-key.pem')):
            self.assertEqual(defaults[field], value)
            self.assertEqual(spec['argument_specs']['main']['options'][field]['default'], value)
        content = Templar(DataLoader(), defaults).template((ROLE / 'templates/xrdp.ini.j2').read_text())
        self.assertIn('certificate=/etc/xrdp/lit-cert.pem', content)
        self.assertIn('key_file=/etc/xrdp/lit-key.pem', content)

    def test_tls_paths_fail_closed_before_generation_and_permission_changes(self):
        init_plugin_loader()
        preflight = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        task = next(task for task in preflight if task['name'].startswith('Refuse linked or non-regular XRDP'))
        for stat, accepted in (({'exists': False}, True),
                               ({'exists': True, 'islnk': False, 'isreg': True}, True),
                               ({'exists': True, 'islnk': True, 'isreg': True}, False),
                               ({'exists': True, 'islnk': False, 'isreg': False}, False)):
            values = {'item': {'stat': stat}, 'xrdp_tls_generate_self_signed': True}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)
        main = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        key_gate = next(task for task in main if task['name'].startswith('Require a regular materialized'))
        for exists, linked, regular, accepted in ((True, False, True, True), (True, True, True, False),
                                                  (False, False, False, False), (True, False, False, False)):
            values = {'_xrdp_key': {'stat': {'exists': exists, 'islnk': linked, 'isreg': regular}}}
            gate = Conditional(loader=DataLoader()); gate.when = key_gate['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)
        names = [task['name'] for task in main]
        self.assertLess(names.index(key_gate['name']), names.index('Give the installed XRDP daemon access to its declared key group'))
        chmod = next(task for task in main if task['name'] == 'Ensure permissions on XRDP TLS key')
        self.assertIs(chmod['ansible.builtin.file']['follow'], False)

    def test_real_stat_detects_tls_key_symlink_without_touching_its_target(self):
        with tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
            directory = Path(temporary)
            target = directory / 'target'; target.write_text('unrelated key material'); target.chmod(0o600)
            link = directory / 'key.pem'; link.symlink_to(target)
            tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
            selected = [task for task in tasks if task['name'].startswith(('Inspect existing XRDP TLS', 'Refuse linked or non-regular XRDP'))]
            config = directory / 'ansible.cfg'; config.write_text('[defaults]\n')
            source = directory / 'play.yml'; source.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'gather_facts': False,
                'vars': {'xrdp_tls_enable': True, 'xrdp_tls_cert_path': str(target), 'xrdp_tls_key_path': str(link)},
                'tasks': selected}]))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(source)],
                                    check=False, capture_output=True, text=True, timeout=30,
                                    env={**os.environ, 'ANSIBLE_CONFIG': str(config),
                                         'ANSIBLE_LOCAL_TEMP': str(directory / 'ansible')})
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Refuse linked or non-regular XRDP TLS', result.stdout)
            self.assertEqual(target.read_text(), 'unrelated key material')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_role_managed_defaults_generate_regular_files_beside_package_symlinks(self):
        with tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
            directory = Path(temporary)
            target = directory / 'snakeoil'; target.write_text('package-owned'); target.chmod(0o600)
            for name in ('cert.pem', 'key.pem'):
                (directory / name).symlink_to(target)
            values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
            for field in ('xrdp_tls_cert_path', 'xrdp_tls_key_path'):
                values[field] = str(directory / Path(values[field]).name)
            values['xrdp_tls_subject'] = '/CN=localhost'
            values['xrdp_tls_days'] = 1
            preflight = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
            main = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
            selected = [task for task in preflight if task['name'].startswith(('Inspect existing XRDP TLS', 'Refuse linked or non-regular XRDP'))]
            selected += [task for task in main if task['name'].startswith(('Check TLS certificate', 'Generate self-signed', 'Inspect materialized', 'Require a regular materialized'))]
            for task in selected:
                task.pop('notify', None)
            config = directory / 'ansible.cfg'; config.write_text('[defaults]\n')
            source = directory / 'play.yml'; source.write_text(yaml.safe_dump([{
                'hosts': 'localhost', 'gather_facts': False, 'vars': values, 'tasks': selected}]))
            result = subprocess.run(['ansible-playbook', '-i', 'localhost,', '-c', 'local', str(source)],
                                    check=False, capture_output=True, text=True, timeout=30,
                                    env={**os.environ, 'ANSIBLE_CONFIG': str(config),
                                         'ANSIBLE_LOCAL_TEMP': str(directory / 'ansible')})
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for field in ('xrdp_tls_cert_path', 'xrdp_tls_key_path'):
                path = Path(values[field]); self.assertTrue(path.is_file()); self.assertFalse(path.is_symlink())
            self.assertEqual(target.read_text(), 'package-owned')
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_external_tls_missing_paths_fail_in_preflight(self):
        init_plugin_loader()
        task = next(task for task in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if task['name'].startswith('Refuse linked or non-regular XRDP'))
        for exists, generate, expected in ((False, False, False), (True, False, True), (False, True, True)):
            values = {'item': {'stat': {'exists': exists, 'islnk': False, 'isreg': exists}},
                      'xrdp_tls_generate_self_signed': generate}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)

    def test_package_created_tls_tasks_defer_only_on_first_install_check_mode(self):
        tasks = yaml.safe_load((ROLE / 'tasks/main.yml').read_text())
        names = ('Require the TLS key group installed by packages or the operator',
                 'Give the installed XRDP daemon access to its declared key group',
                 'Ensure permissions on XRDP TLS key')
        for task in [task for task in tasks if task['name'] in names]:
            for check, installed, expected in ((True, False, False), (True, True, True), (False, False, True)):
                values = {'xrdp_tls_enable': True, 'xrdp_tls_key_path': '/etc/xrdp/lit-key.pem',
                          'ansible_check_mode': check, '_xrdp_installed': installed}
                gate = Conditional(loader=DataLoader()); gate.when = task['when']
                self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)

    def test_daemon_ignores_unvalidated_tls_aliases(self):
        values = yaml.safe_load((ROLE / 'defaults/main.yml').read_text())
        values.update(xrdp_tls_cert='/unvalidated-cert', xrdp_tls_key='/unvalidated-key')
        content = Templar(DataLoader(), values).template((ROLE / 'templates/xrdp.ini.j2').read_text())
        self.assertNotIn('/unvalidated', content)
        self.assertIn('certificate=' + values['xrdp_tls_cert_path'], content)
        self.assertIn('key_file=' + values['xrdp_tls_key_path'], content)

    def test_half_existing_self_signed_tls_pair_is_rejected(self):
        task = next(t for t in yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
                    if t['name'].startswith('Require both TLS outputs present'))
        for cert, key, expected in [(False, False, True), (True, True, True), (True, False, False), (False, True, False)]:
            values = {'_xrdp_tls_path_preflight': {'results': [{'stat': {'exists': cert}}, {'stat': {'exists': key}}]}}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), expected)

    def test_tls_ancestor_guard_rejects_links_writable_or_non_directory_components(self):
        task = yaml.safe_load((ROLE / 'tasks/tls_ancestor_preflight.yml').read_text())[1]
        for delta, accepted in [({}, True), ({'islnk': True}, False), ({'mode': '0777'}, False),
                ({'uid': 1000}, False), ({'isdir': False}, False)]:
            values = {'item': {'item': 2, 'stat': {'exists': True, 'islnk': False, 'isdir': True,
                'uid': 0, 'mode': '0755', **delta}}, 'xrdp_tls_output_path': '/etc/xrdp/lit-key.pem',
                'xrdp_tls_generate_self_signed': True}
            gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
            self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)

    def test_home_and_config_cannot_be_writable_by_other_accounts(self):
        tasks = yaml.safe_load((ROLE / 'tasks/assert.yml').read_text())
        for name in ('Refuse linked or missing personal home directories', 'Refuse linked or non-directory personal configuration paths'):
            task = next(t for t in tasks if t['name'] == name)
            for mode, accepted in [('0700', True), ('0750', True), ('0770', False), ('0777', False), ('0702', False)]:
                values = {'item': {'item': 'p1005a', 'stat': {'exists': True, 'islnk': False, 'isdir': True,
                    'uid': 1001, 'gid': 1001, 'mode': mode}}, 'ansible_facts': {
                    'getent_passwd': {'p1005a': ['x', '1001', '1001']}, 'getent_group': {'p1005a': ['x', '1001']}}}
                gate = Conditional(loader=DataLoader()); gate.when = task['ansible.builtin.assert']['that']
                self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(), values), values), accepted)
