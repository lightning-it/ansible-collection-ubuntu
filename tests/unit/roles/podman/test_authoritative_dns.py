"""Evaluate the real role gates and rendered no-forwarding TOML offline."""

from copy import deepcopy
from pathlib import Path
import tomllib
import unittest

from ansible.parsing.dataloader import DataLoader
from ansible.playbook.conditional import Conditional
from ansible.template import Templar
import yaml

ROOT = Path(__file__).resolve().parents[4]
ROLE = ROOT / "roles/podman"


def load(path):
    return yaml.safe_load(path.read_text())


def accepted(task, variables):
    loader = DataLoader()
    gate = Conditional(loader=loader)
    gate.when = task["ansible.builtin.assert"]["that"]
    return gate.evaluate_conditional(Templar(loader, variables), variables)


class AuthoritativeDnsTests(unittest.TestCase):
    def test_input_gate_is_default_off_and_requires_exact_pins(self):
        gate = load(ROLE / "tasks/main.yml")[0]
        defaults = load(ROLE / "defaults/main.yml")
        self.assertTrue(accepted(gate, defaults))
        valid = {**defaults, "podman_dns_authoritative_only": True,
                 "podman_dns_resolver_executable": "/usr/lib/podman/aardvark-dns",
                 "podman_dns_resolver_sha256": "a" * 64}
        self.assertTrue(accepted(gate, valid))
        for key, value in (
            ("podman_dns_authoritative_only", "true"),
            ("podman_dns_resolver_executable", "aardvark-dns"),
            ("podman_dns_resolver_executable", "/usr/../tmp/aardvark-dns"),
            ("podman_dns_resolver_executable", "/usr//lib/aardvark-dns"),
            ("podman_dns_resolver_executable", "/usr/lib/other"),
            ("podman_dns_resolver_sha256", "A" * 64),
            ("podman_dns_resolver_sha256", "a" * 63),
        ):
            with self.subTest(key=key, value=value):
                self.assertFalse(accepted(gate, {**valid, key: value}))

    def test_binary_gate_rejects_unapproved_or_writable_objects(self):
        gate = next(task for task in load(ROLE / "tasks/dns_authoritative.yml")
                    if task["name"] == "Require an immutable approved resolver executable")
        stat = {"isreg": True, "islnk": False, "uid": 0, "wgrp": False,
                "woth": False, "executable": True, "checksum": "a" * 64}
        def check(candidate):
            return accepted(gate, {"podman_dns_resolver_stat": {"stat": candidate},
                                   "podman_dns_resolver_sha256": "a" * 64})
        self.assertTrue(check(stat))
        for key, value in (("isreg", False), ("islnk", True), ("uid", 1000),
                           ("wgrp", True), ("woth", True), ("executable", False),
                           ("checksum", "b" * 64)):
            candidate = deepcopy(stat)
            candidate[key] = value
            with self.subTest(key=key):
                self.assertFalse(check(candidate))
        self.assertFalse(check({}))

    def test_startup_configuration_appends_and_does_not_restart(self):
        tasks = load(ROLE / "tasks/dns_authoritative.yml")
        copy = tasks[-1]["ansible.builtin.copy"]
        config = tomllib.loads(copy["content"])
        self.assertEqual(config, {"engine": {"env": ["AARDVARK_NO_PROXY=1", {"append": True}]}})
        self.assertEqual(copy["owner"], "root")
        self.assertEqual(copy["mode"], "0644")
        for task in tasks:
            self.assertNotIn("ansible.builtin.systemd_service", task)
            self.assertNotIn("ansible.builtin.shell", task)
        include = next(task for task in load(ROLE / "tasks/main.yml")
                       if task.get("ansible.builtin.include_tasks") == "dns_authoritative.yml")
        self.assertEqual(include["when"], "podman_dns_authoritative_only")

    def test_version_gate_rejects_older_or_unrecognized_clients(self):
        gate = next(task for task in load(ROLE / "tasks/dns_authoritative.yml")
                    if task["name"] == "Require the supported append-capable Podman baseline")
        for version, expected in (("podman version 4.9.3", True),
                                  ("podman version 5.0.0", True),
                                  ("podman version 4.9.2", False),
                                  ("other client 4.9.3", False)):
            with self.subTest(version=version):
                self.assertEqual(accepted(gate, {"podman_dns_podman_version": {"stdout": version}}), expected)

    def test_existing_restrictive_directory_is_never_chmodded(self):
        task = next(task for task in load(ROLE / "tasks/dns_authoritative.yml")
                    if task["name"] == "Ensure the authoritative DNS configuration directory exists")
        loader = DataLoader()
        gate = Conditional(loader=loader)
        gate.when = [task["when"]]
        for exists, mode in ((True, "0700"), (True, "0750"), (True, "0755"), (False, "")):
            variables = {"podman_dns_config_ancestors": {"results": [
                {"stat": {}}, {"stat": {}}, {"stat": {"exists": exists, "mode": mode}}
            ]}}
            with self.subTest(exists=exists, mode=mode):
                self.assertEqual(gate.evaluate_conditional(Templar(loader, variables), variables), not exists)
