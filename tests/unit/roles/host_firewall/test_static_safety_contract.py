from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
ROLE_ROOT = REPOSITORY_ROOT / "roles" / "host_firewall"


class HostFirewallStaticSafetyTests(unittest.TestCase):
    def test_role_never_flushes_or_lists_the_whole_ruleset(self) -> None:
        role_text = "\n".join(path.read_text() for path in ROLE_ROOT.rglob("*") if path.is_file())
        self.assertNotIn("flush ruleset", role_text)
        self.assertNotIn("list\n      - ruleset", role_text)

    def test_all_mutation_programs_take_the_same_exclusive_lock(self) -> None:
        for name in ("apply.sh.j2", "confirm.sh.j2", "rollback.sh.j2"):
            content = (ROLE_ROOT / "templates" / name).read_text()
            self.assertIn("host_firewall_transaction_lock_path", content)
            self.assertIn('"${flock_binary}" --exclusive 9', content)

    def test_apply_and_confirm_refuse_active_rollback(self) -> None:
        for name in ("apply.sh.j2", "confirm.sh.j2"):
            content = (ROLE_ROOT / "templates" / name).read_text()
            self.assertIn('is-active --quiet "${rollback_service}"', content)

        confirmation = (ROLE_ROOT / "templates" / "confirm.sh.j2").read_text()
        self.assertIn('test ! -e "${rollback_record}"', confirmation)
        first_check = confirmation.index('is-active --quiet "${rollback_service}"')
        stop_timer = confirmation.index('stop "${rollback_timer}"')
        second_check = confirmation.index('is-active --quiet "${rollback_service}"', first_check + 1)
        persistent_write = confirmation.index('"${pending_config}" "${persistent_include}"')
        self.assertLess(first_check, stop_timer)
        self.assertLess(stop_timer, second_check)
        self.assertLess(second_check, persistent_write)

    def test_rollback_timer_and_confirmation_have_explicit_ordering(self) -> None:
        timer = (ROLE_ROOT / "templates" / "rollback.timer.j2").read_text()
        rollback = (ROLE_ROOT / "templates" / "rollback.service.j2").read_text()
        confirmation = (ROLE_ROOT / "templates" / "confirm.service.j2").read_text()
        self.assertIn("Persistent=true", timer)
        self.assertIn("Before={{ host_firewall_confirmation_service_name }}", rollback)
        self.assertNotIn("WantedBy=multi-user.target", rollback)
        self.assertIn("After=local-fs.target {{ host_firewall_rollback_timer_name }}", confirmation)

    def test_persistence_root_is_read_only_and_include_is_role_owned(self) -> None:
        confirmation = (ROLE_ROOT / "templates" / "confirm.sh.j2").read_text()
        rollback = (ROLE_ROOT / "templates" / "rollback.sh.j2").read_text()
        preflight = (ROLE_ROOT / "tasks" / "persistence_preflight.yml").read_text()
        role_tasks = "\n".join(path.read_text() for path in (ROLE_ROOT / "tasks").glob("*.yml"))
        self.assertNotIn('"${pending_config}" "${persistent_root}"', confirmation)
        self.assertIn('"${pending_config}" "${persistent_include}"', confirmation)
        self.assertNotIn('"${persistent_backup}" "${persistent_root}"', rollback)
        self.assertIn("exact include directive", preflight)
        self.assertIn("select('equalto', host_firewall_persistent_include_directive)", preflight)
        self.assertIn("length == 1", preflight)
        self.assertNotIn('dest: "{{ host_firewall_persistent_root_config_path }}"', role_tasks)

    def test_rollback_replays_only_the_role_owned_table(self) -> None:
        apply_tasks = (ROLE_ROOT / "tasks" / "apply.yml").read_text()
        rollback = (ROLE_ROOT / "templates" / "rollback.sh.j2").read_text()
        self.assertIn("destroy table {{ host_firewall_table_family }} {{ host_firewall_table_name }}", apply_tasks)
        self.assertIn('"${nft_binary}" --file "${runtime_backup}"', rollback)
        self.assertNotIn("ruleset", rollback)

    def test_shared_host_directories_are_never_created_or_chmodded(self) -> None:
        apply_tasks = (ROLE_ROOT / "tasks" / "apply.yml").read_text()
        state_task = apply_tasks.split("- name: Inspect shared host firewall program", maxsplit=1)[0]
        self.assertNotIn("host_firewall_systemd_unit_directory", state_task)
        self.assertNotIn("host_firewall_apply_script_path | dirname", state_task)
        self.assertIn("The role will not\n      create or chmod shared host directories", apply_tasks)

    def test_check_mode_forces_real_nft_validation(self) -> None:
        check_tasks = (ROLE_ROOT / "tasks" / "check.yml").read_text()
        self.assertIn("check_mode: false", check_tasks)
        self.assertIn("host_firewall_check_result.skipped", check_tasks)

    def test_authorization_and_egress_fail_closed_are_explicit(self) -> None:
        authorization = (ROLE_ROOT / "tasks" / "authorization.yml").read_text()
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("host_firewall_authorization_contract_expected", authorization)
        self.assertIn("signature verification", authorization)
        self.assertIn("Block confirmation while egress remains unresolved", assertions)

    def test_transaction_metadata_uses_exact_json_keys_and_hashes(self) -> None:
        confirmation = (ROLE_ROOT / "tasks" / "confirm.yml").read_text()
        rollback = (ROLE_ROOT / "tasks" / "rollback.yml").read_text()
        for content in (confirmation, rollback):
            self.assertIn("from_json", content)
            self.assertIn("keys() | list | sort", content)
        self.assertIn("host_firewall_pending_metadata_sha256", confirmation)
        self.assertIn("runtime_backup_sha256", rollback)

    def test_same_source_is_rendered_through_separate_function_sets(self) -> None:
        policy = (ROLE_ROOT / "templates" / "host-firewall.nft.j2").read_text()
        self.assertIn("{{ function.key }}_sources_v4", policy)
        self.assertIn("{{ function.key }}_sources_v6", policy)
        self.assertNotIn("management_sources_v4", policy)


if __name__ == "__main__":
    unittest.main()
