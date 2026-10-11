"""Rendered Xorg session must reach the local session manager independently of RDP bind."""
import configparser,unittest
from pathlib import Path
import yaml
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import init_plugin_loader
from ansible.template import Templar
ROLE=Path(__file__).resolve().parents[2]/'roles/xrdp'
class XrdpLocalSessionTests(unittest.TestCase):
 def test_private_listener_keeps_xorg_session_manager_on_loopback(self):
  init_plugin_loader()
  values=yaml.safe_load((ROLE/'defaults/main.yml').read_text())
  values.update(xrdp_listen_address='10.1.2.3',xrdp_security_layer='tls')
  rendered=Templar(DataLoader(),values).template((ROLE/'templates/xrdp.ini.j2').read_text())
  config=configparser.ConfigParser();config.read_string(rendered)
  self.assertEqual(config['Globals']['port'],'tcp://10.1.2.3:3389')
  self.assertEqual(config['Xorg']['ip'],'127.0.0.1')
  self.assertEqual(config['Xorg']['port'],'-1')
  self.assertEqual(config['Xorg']['lib'],'libxup.so')
  self.assertEqual(config['Globals']['security_layer'],'tls')
