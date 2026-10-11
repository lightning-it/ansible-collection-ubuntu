"""Verify optional pre-root LAN artifacts and reject unsafe boot inputs."""
import os,shutil,subprocess,tempfile,unittest
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
                 {'address':'999.1.1.1'},{'parent':'eno2;id'},{'mtu':100},{'prefix':33},{'prefix':32}):
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
  self.assertNotIn('always', task.get('tags', []))
  values=self.values();values.update(luks_unlock_execution_mode='installed',luks_unlock_manage_early_network=False,luks_unlock_early_vlans=[])
  gate=Conditional(loader=DataLoader());gate.when=task['when']
  self.assertTrue(gate.evaluate_conditional(Templar(DataLoader(),values),values))
  cleanup=next(t for t in yaml.safe_load((ROOT/'tasks/early_vlan_cleanup.yml').read_text()) if 'ansible.builtin.file' in t)
  self.assertEqual(cleanup['ansible.builtin.file']['state'],'absent')
  self.assertEqual(cleanup['notify'],'LUKS unlock | Rebuild initramfs')
  self.assertEqual(Templar(DataLoader(),values).template(cleanup['loop']),[values['luks_unlock_early_vlan_script_path'],values['luks_unlock_early_vlan_hook_path']])

 def test_rescue_guard_rejects_linked_output_and_ancestor_without_mutation(self):
  values=self.values();values.update(luks_unlock_dropbear_options_effective='-p 2222',
       luks_unlock_kernel_ip_argument_effective='ip=dhcp',luks_unlock_dropbear_authorized_keys=['ssh-ed25519 AAAATEST'])
  engine=Templar(DataLoader(),values);engine.environment.loader=FileSystemLoader(str(ROOT/'templates'))
  content=engine.environment.get_template('installimage-post-install.sh.j2').render(**values)
  function=content.split('lit_require_safe_output() {',1)[1].split('\n}\n',1)[0]
  function='lit_require_safe_output() {'+function+'\n}\n'
  for field in ('luks_unlock_early_vlan_script_path','luks_unlock_early_vlan_hook_path'):
   self.assertLess(content.index('lit_require_safe_output '+values[field]),content.index('cat >'+values[field]))
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);target=root/'target';target.write_text('UNCHANGED');target.chmod(0o640)
   link=root/'linked';link.symlink_to(target)
   directory=root/'directory';directory.mkdir();parent=root/'parent';parent.symlink_to(directory,target_is_directory=True)
   for unsafe in (link,parent/'artifact'):
    path=root/'guard.sh';path.write_text('set -euo pipefail\n'+function+'lit_require_safe_output "$1"\nprintf MODIFIED >"$1"\n')
    result=subprocess.run(['/bin/bash',str(path),str(unsafe)],capture_output=True,text=True)
    self.assertNotEqual(result.returncode,0)
    self.assertEqual(target.read_text(),'UNCHANGED');self.assertEqual(target.stat().st_mode & 0o777,0o640)
    self.assertFalse((directory/'artifact').exists())

 def test_installed_directory_guard_rejects_links_and_unsafe_ownership_before_changes(self):
  tasks=yaml.safe_load((ROOT/'tasks/early_vlan_preflight.yml').read_text())
  guard=next(t for t in tasks if t['name'].startswith('Reject unsafe early VLAN artifact directories'))
  for changes,accepted in [({},True),({'islnk':True},False),({'uid':1000},False),({'gid':1000},False),({'mode':'0777'},False),({'isdir':False},False)]:
   stat={'exists':True,'islnk':False,'isdir':True,'uid':0,'gid':0,'mode':'0755',**changes}
   values={'item':{'stat':stat}};gate=Conditional(loader=DataLoader());gate.when=guard['ansible.builtin.assert']['that']
   self.assertEqual(gate.evaluate_conditional(Templar(DataLoader(),values),values),accepted)
  with tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
   root=Path(temporary);target=root/'target';target.mkdir();target.chmod(0o750);link=root/'linked';link.symlink_to(target,target_is_directory=True)
   inspect=tasks[0].copy();inspect['loop']=[str(link)]
   play=[{'hosts':'localhost','gather_facts':False,'vars':{'luks_unlock_early_vlans':[{}]},'tasks':[inspect,guard]}]
   path=root/'play.yml';path.write_text(yaml.safe_dump(play));config=root/'ansible.cfg';config.write_text('[defaults]\n')
   result=subprocess.run([shutil.which('ansible-playbook'),'-i','localhost,','-c','local',str(path)],capture_output=True,text=True,
       env={**os.environ,'ANSIBLE_CONFIG':str(config)},timeout=30)
   self.assertNotEqual(result.returncode,0);self.assertTrue(link.is_symlink());self.assertEqual(target.stat().st_mode & 0o777,0o750)

 def test_cleanup_reuses_guard_for_linked_parents_and_directory_leaves(self):
  tasks=yaml.safe_load((ROOT/'tasks/early_vlan_cleanup.yml').read_text())
  self.assertEqual(tasks[0]['ansible.builtin.import_tasks'],'early_vlan_preflight.yml')
  self.assertIs(next(t for t in tasks if 'ansible.builtin.file' in t)['ansible.builtin.file']['follow'],False)
  preflight=yaml.safe_load((ROOT/'tasks/early_vlan_preflight.yml').read_text())
  guard=next(t for t in preflight if t['name'].startswith('Reject unsafe early VLAN output files'))
  for changes in ({'isreg':False,'isdir':True},{'islnk':True},{'uid':1000}):
   values={'item':{'stat':{'exists':True,'isreg':True,'islnk':False,'uid':0,'gid':0,'mode':'0755',**changes}}}
   gate=Conditional(loader=DataLoader());gate.when=guard['ansible.builtin.assert']['that']
   self.assertFalse(gate.evaluate_conditional(Templar(DataLoader(),values),values))

 def test_actual_cleanup_cannot_delete_linked_parent_targets_or_directory_leaves(self):
  for linked in (True,False):
   with tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
    root=Path(temporary);target=root/'target';target.mkdir();leaf=target/'artifact';leaf.mkdir();canary=leaf/'canary';canary.write_text('UNCHANGED')
    parent=root/'parent'
    if linked: parent.symlink_to(target,target_is_directory=True)
    else: parent=target
    values={'luks_unlock_early_vlans':[],'luks_unlock_early_vlan_script_path':str(parent/'artifact'),
       'luks_unlock_early_vlan_hook_path':str(root/'unused-hook')}
    play=[{'hosts':'localhost','gather_facts':False,'vars':values,'tasks':[{'ansible.builtin.import_tasks':str(ROOT/'tasks/early_vlan_cleanup.yml')}]}]
    path=root/'play.yml';path.write_text(yaml.safe_dump(play));config=root/'ansible.cfg';config.write_text('[defaults]\n')
    result=subprocess.run([shutil.which('ansible-playbook'),'-i','localhost,','-c','local',str(path)],capture_output=True,text=True,
        env={**os.environ,'ANSIBLE_CONFIG':str(config)},timeout=30)
    self.assertNotEqual(result.returncode,0);self.assertEqual(canary.read_text(),'UNCHANGED')

 def test_actual_disabled_vlan_cleanup_requires_rebuild_before_deletion(self):
  tasks=yaml.safe_load((ROOT/'tasks/early_vlan_cleanup.yml').read_text())
  guard=next(t for t in tasks if 'ansible.builtin.assert' in t)
  cleanup=next(t for t in tasks if 'ansible.builtin.file' in t)
  handler=next(t for t in yaml.safe_load((ROOT/'handlers/main.yml').read_text()) if t['name']=='LUKS unlock | Rebuild initramfs')
  for rebuild, present in ((False,True),(True,True),(False,False)):
   with self.subTest(rebuild=rebuild,present=present), tempfile.TemporaryDirectory(dir=os.environ['HOME']) as temporary:
    root=Path(temporary); script=root/'script'; hook=root/'hook'; marker=root/'rebuilt-image'
    if present:
     script.write_text('BOOT-SOURCE'); hook.write_text('BOOT-HOOK')
    import sys
    values={'luks_unlock_early_vlans':[], 'luks_unlock_early_vlan_script_path':str(script),
      'luks_unlock_early_vlan_hook_path':str(hook), 'luks_unlock_rebuild_initramfs':rebuild,
      'luks_unlock_update_initramfs_command':[sys.executable,'-c','from pathlib import Path; Path("'+str(marker)+'").write_text("REBUILT")']}
    inspect={'ansible.builtin.stat':{'path':'{{ item }}','follow':False},'loop':[str(script),str(hook)],'register':'luks_unlock_early_vlan_outputs'}
    play=[{'hosts':'localhost','gather_facts':False,'vars':values,'tasks':[inspect,guard,cleanup],'handlers':[handler]}]
    source=root/'play.yml';source.write_text(yaml.safe_dump(play));config=root/'ansible.cfg';config.write_text('[defaults]\n')
    result=subprocess.run([shutil.which('ansible-playbook'),'-i','localhost,','-c','local',str(source)],
      capture_output=True,text=True,timeout=30,env={**os.environ,'ANSIBLE_CONFIG':str(config)})
    if present and not rebuild:
     self.assertNotEqual(result.returncode,0);self.assertEqual(script.read_text(),'BOOT-SOURCE');self.assertEqual(hook.read_text(),'BOOT-HOOK');self.assertFalse(marker.exists())
    else:
     self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertFalse(script.exists());self.assertFalse(hook.exists());self.assertEqual(marker.exists(),present)
