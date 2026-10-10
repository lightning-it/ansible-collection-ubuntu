"""Verify optional pre-root LAN artifacts and reject unsafe boot inputs."""
import subprocess,tempfile,unittest
from pathlib import Path
import yaml
from jinja2 import Environment,FileSystemLoader
from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
ROOT=Path(__file__).resolve().parents[2]/'roles/luks_unlock'
class EarlyVlanTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls): init_plugin_loader()
 def values(self):
  values=yaml.safe_load((ROOT/'defaults/main.yml').read_text())
  values.update(luks_unlock_enabled=True,luks_unlock_network_modules=['igb','8021q'],luks_unlock_manage_early_network=True)
  values['luks_unlock_early_vlans']=[{'parent':'eno2','name':'eno2.4091','id':4091,'address':'10.10.30.22','prefix':24,'mtu':1400}]
  return values
 def accepts(self,values):
  tasks=yaml.safe_load((ROOT/'tasks/assert.yml').read_text())
  for task in tasks[-2:]:
   contexts=[values]
   if 'loop' in task: contexts=[{**values,'item':item} for item in values['luks_unlock_early_vlans']]
   for context in contexts:
    gate=Conditional(loader=DataLoader());gate.when=task['ansible.builtin.assert']['that']
    if not gate.evaluate_conditional(Templar(DataLoader(),context),context): return False
  return True
 def test_valid_private_network_keeps_public_kernel_ip_unchanged(self):
  values=self.values()
  values['luks_unlock_early_network']={'method':'static','interface':'eno2','address':'195.201.173.85','gateway':'195.201.173.65','netmask':'255.255.255.192','hostname':'wbn01','dns':[]}
  self.assertTrue(self.accepts(values))
  kernel=Templar(DataLoader(),values).template(values['luks_unlock_kernel_ip_argument_effective'])
  self.assertIn('195.201.173.85::195.201.173.65',kernel)
  self.assertNotIn('10.10.30.22',kernel)
 def test_invalid_vlan_or_injection_cannot_render_boot_commands(self):
  for change in ({'id':4095},{'id':0},{'name':'different'},{'address':'10.10.30.22;id'},
                 {'address':'999.1.1.1'},{'parent':'eno2;id'},{'mtu':100},{'prefix':33}):
   values=self.values();values['luks_unlock_early_vlans'][0].update(change)
   self.assertFalse(self.accepts(values))
  values=self.values();values['luks_unlock_network_modules']=['igb'];self.assertFalse(self.accepts(values))
 def test_script_shell_syntax_and_recovery_route_preservation(self):
  values=self.values()
  environment=Environment(loader=FileSystemLoader(str(ROOT/'templates')))
  with tempfile.TemporaryDirectory() as directory:
   for name in ('initramfs-early-vlans.sh.j2','initramfs-vlan-hook.sh.j2'):
    content=environment.get_template(name).render(**values)
    p=Path(directory)/name;p.write_text(content)
    subprocess.run(['/bin/sh','-n',str(p)],check=True,capture_output=True)
    self.assertNotIn('route add default',content)
    self.assertNotIn('recovery_passphrase',content)
   script=environment.get_template('initramfs-early-vlans.sh.j2').render(**values)
   self.assertIn('ip address replace 10.10.30.22/24 dev eno2.4091',script)
   self.assertIn('mtu 1400 up',script)
 def test_disabled_default_has_no_vlan_items(self):
  values=self.values();values['luks_unlock_early_vlans']=[];self.assertTrue(self.accepts(values))
 def test_post_install_includes_close_both_heredocs_under_ansible_trimming(self):
  values=self.values()
  values.update(luks_unlock_dropbear_options_effective='-p 2222 -s -j -k -I 300',
                luks_unlock_kernel_ip_argument_effective='ip=dhcp',
                luks_unlock_dropbear_authorized_keys=['ssh-ed25519 AAAATEST'])
  template_engine=Templar(DataLoader(),values)
  environment=template_engine.environment
  environment.loader=FileSystemLoader(str(ROOT/'templates'))
  self.assertTrue(environment.trim_blocks)
  content=environment.get_template('installimage-post-install.sh.j2').render(**values)
  for marker in ('LIT_EARLY_VLANS','LIT_VLAN_HOOK'):
   self.assertEqual(content.splitlines().count(marker),1)
   block=content.split("<<'"+marker+"'\n",1)[1].split('\n'+marker+'\n',1)[0]
   self.assertNotIn('update-initramfs',block)
   with tempfile.NamedTemporaryFile(mode='w') as script:
    script.write(block);script.flush()
    checked=subprocess.run(['/bin/sh','-n',script.name],capture_output=True,text=True)
    self.assertEqual(checked.returncode,0,checked.stderr)
    self.assertEqual(checked.stderr,'')

 def test_post_install_archive_check_uses_fixed_role_owned_vlan_path(self):
  values=self.values()
  values.update(luks_unlock_dropbear_options_effective='-p 2222 -s -j -k -I 300',
                luks_unlock_kernel_ip_argument_effective='ip=dhcp',
                luks_unlock_dropbear_authorized_keys=['ssh-ed25519 AAAATEST'])
  template_engine=Templar(DataLoader(),values)
  environment=template_engine.environment
  environment.loader=FileSystemLoader(str(ROOT/'templates'))
  content=environment.get_template('installimage-post-install.sh.j2').render(**values)
  self.assertIn('scripts/init-premount/00-lit-early-vlans',content)
  self.assertNotIn('01-private-vlan',content)

 def test_vlan_artifact_paths_must_be_in_supported_initramfs_directories(self):
  for field,path in (('luks_unlock_early_vlan_script_path','/etc/initramfs-tools/scripts/init-premount/01-private-vlan'),
                     ('luks_unlock_early_vlan_hook_path','/etc/initramfs-tools/hooks/old-private-vlan'),
                     ('luks_unlock_early_vlan_script_path','/etc/01-private-vlan'),
                     ('luks_unlock_early_vlan_script_path','/etc/initramfs-tools/scripts/init-premount/../escape'),
                     ('luks_unlock_early_vlan_hook_path','/tmp/hook'),
                     ('luks_unlock_early_vlan_hook_path','/etc/initramfs-tools/hooks/../../escape')):
   values=self.values();values[field]=path;self.assertFalse(self.accepts(values))

 def test_installed_vlans_require_managed_early_network(self):
  values=self.values();values.update(luks_unlock_execution_mode="installed",luks_unlock_manage_early_network=False)
  self.assertFalse(self.accepts(values))
  values["luks_unlock_execution_mode"]="rescue_stage";self.assertTrue(self.accepts(values))

 def test_disabled_network_management_still_removes_role_owned_vlan_artifacts(self):
  tasks=yaml.safe_load((ROOT/'tasks/main.yml').read_text())
  task=next(t for t in tasks if t.get('ansible.builtin.import_tasks') == 'early_vlan_cleanup.yml')
  values=self.values();values.update(luks_unlock_execution_mode='installed',luks_unlock_manage_early_network=False,luks_unlock_early_vlans=[])
  gate=Conditional(loader=DataLoader());gate.when=task['when']
  self.assertTrue(gate.evaluate_conditional(Templar(DataLoader(),values),values))
  cleanup=yaml.safe_load((ROOT/'tasks/early_vlan_cleanup.yml').read_text())[0]
  self.assertEqual(cleanup['ansible.builtin.file']['state'],'absent')
  self.assertEqual(cleanup['notify'],'LUKS unlock | Rebuild initramfs')
  self.assertEqual(Templar(DataLoader(),values).template(cleanup['loop']),[values['luks_unlock_early_vlan_script_path'],values['luks_unlock_early_vlan_hook_path']])
