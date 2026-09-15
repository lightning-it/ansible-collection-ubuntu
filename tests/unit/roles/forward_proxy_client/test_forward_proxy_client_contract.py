from __future__ import annotations

import unittest
from pathlib import Path

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
ROLE_ROOT = REPOSITORY_ROOT / "roles" / "forward_proxy_client"


class ForwardProxyClientContractTests(unittest.TestCase):
    def test_adapter_contains_no_squid_runtime(self) -> None:
        role_text = "".join(
            path.read_text() for path in sorted(ROLE_ROOT.rglob("*")) if path.is_file()
        )
        self.assertNotIn("ubuntu/squid@sha256", role_text)
        self.assertNotIn("podman_systemd", role_text)
        self.assertNotIn("squid-pod", role_text)
        self.assertNotIn("ansible.builtin.apt", role_text)

    def test_apt_override_wins_and_encodes_exact_direct_hosts(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        template = (ROLE_ROOT / "templates" / "apt-proxy.conf.j2").read_text()
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn("/etc/apt/apt.conf.d/99-lit-forward-proxy", defaults)
        self.assertIn('Acquire::http::Proxy::{{ host }} "DIRECT";', template)
        self.assertIn('Acquire::https::Proxy::{{ host }} "DIRECT";', template)
        self.assertIn(
            "APT DIRECT exceptions are restricted to host-local loopback", assertions
        )
        self.assertIn("difference(['localhost', '127.0.0.1'])", assertions)

    def test_existing_systemd_clients_have_explicit_idempotent_cutover(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        tasks = (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        self.assertIn("forward_proxy_client_restart_services: []", defaults)
        self.assertIn("forward_proxy_client_restart_now: false", defaults)
        self.assertIn(
            "Reload systemd manager after changing proxy client defaults", tasks
        )
        self.assertIn("forward_proxy_client_systemd_environment_result.changed", tasks)
        self.assertIn(
            'loop: "{{ forward_proxy_client_restart_pending_services_internal }}"',
            tasks,
        )
        self.assertIn("forward_proxy_client_restart_now | bool", tasks)
        self.assertIn(
            "forward_proxy_client_managed_state_changed_internal | bool", tasks
        )

    def test_container_boundary_matches_the_host_firewall(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        firewall_assertions = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml"
        ).read_text()
        self.assertIn(
            "forward_proxy_client_container_firewall_access.interfaces | length > 0",
            assertions,
        )
        self.assertIn(
            "forward_proxy_client_container_firewall_access.sources_ipv4 | length > 0",
            assertions,
        )
        self.assertIn(
            "not forward_proxy_client_container_firewall_access.destination_ipv4.startswith('127.')",
            assertions,
        )
        self.assertIn("192\\.168\\.", assertions)
        self.assertIn("192\\.168\\.", firewall_assertions)
        self.assertIn("172\\.(?:1[6-9]|2[0-9]|3[01])\\.", firewall_assertions)
        self.assertIn("/(?:[89]|[12][0-9]|3[0-2])\\Z", assertions)
        self.assertIn("/(?:1[6-9]|2[0-9]|3[0-2])\\Z", firewall_assertions)
        self.assertIn("2 ** (32 - (item.split('/')[1] | int))", assertions)
        self.assertIn("2 ** (32 - (item.split('/')[1] | int))", firewall_assertions)
        self.assertNotIn("[1-9]?[0-9]", assertions)

    def test_disabled_state_cleans_only_adapter_owned_state(self) -> None:
        tasks = "".join(
            path.read_text() for path in sorted((ROLE_ROOT / "tasks").glob("*.yml"))
        )
        variables = (ROLE_ROOT / "vars" / "main.yml").read_text()
        self.assertIn("Inspect the forward proxy client managed-state marker", tasks)
        self.assertIn(
            "forward_proxy_client_previous_state_manifest.managed_paths", tasks
        )
        self.assertIn("lit.ubuntu.forward_proxy_client.managed-state/v5", tasks)
        self.assertNotIn("managed-state/v1", variables)
        self.assertIn("checksum_algorithm: sha256", tasks)
        self.assertIn("item.stat.isreg", tasks)
        self.assertIn("item.stat.islnk", tasks)
        self.assertIn("item.stat.mode", tasks)
        self.assertIn("item.stat.pw_name", tasks)
        self.assertIn("item.stat.gr_name", tasks)
        self.assertIn(
            "Refuse to adopt unowned forward proxy client target paths", tasks
        )
        self.assertIn(
            "Refuse to adopt new unowned forward proxy client target paths", tasks
        )
        self.assertIn("not item.stat.exists", tasks)
        self.assertIn("Refuse unsafe forward proxy client managed directories", tasks)
        self.assertIn("Initialize empty previous forward proxy client state", tasks)
        self.assertIn("systemd_activation_pending", tasks)
        self.assertIn("restart_pending_services", tasks)
        self.assertIn("restart_activated_services", tasks)
        self.assertNotIn("_forward_proxy_client_", tasks)

    def test_firewall_mode_and_ports_match_service_upstream_mode(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        self.assertIn(
            "forward_proxy_client_firewall_egress.get('mode', '')", assertions
        )
        self.assertIn(
            "forward_proxy_client_firewall_egress.get('ports', [])", assertions
        )
        self.assertIn("if forward_proxy_client_upstream_enabled", assertions)
        self.assertIn("get('status', '') == 'approved'", assertions)
        self.assertIn("[forward_proxy_client_upstream_ipv4 ~ '/32']", assertions)
        self.assertIn("else ['0.0.0.0/0']", assertions)
        self.assertIn("get('interface', '')", assertions)
        self.assertIn("{1,15}", assertions)
        self.assertNotIn("forward_proxy_client_upstream_host", assertions)
        firewall_assertions = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml"
        ).read_text()
        self.assertIn("residual | trim | length >= 20", firewall_assertions)
        self.assertIn(
            "interface\n            is match('^[A-Za-z0-9_.:-]{1,15}\\Z')",
            firewall_assertions,
        )
        self.assertNotIn("(?:[0-9]{1,3}\\.){2}[0-9]{1,3}", firewall_assertions)

    def test_disabled_adapter_does_not_require_live_container_firewall_state(
        self,
    ) -> None:
        tasks = yaml.safe_load((ROLE_ROOT / "tasks" / "assert.yml").read_text())
        container_tasks = [
            task
            for task in tasks
            if task["name"]
            in {
                "Require the client-container firewall contract",
                "Validate the client-container firewall contract",
            }
        ]
        self.assertEqual(len(container_tasks), 2)
        for task in container_tasks:
            self.assertEqual(
                task["when"],
                [
                    "forward_proxy_client_enabled | bool",
                    "forward_proxy_client_container_enabled | bool",
                ],
            )

    def test_proxy_networks_are_unique_and_canonical(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        firewall_assertions = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "tasks" / "egress_assert.yml"
        ).read_text()
        firewall_defaults = (
            REPOSITORY_ROOT / "roles" / "host_firewall" / "defaults" / "main.yml"
        ).read_text()
        self.assertIn(
            "host_firewall_forward_proxy_access.sources_ipv4 | unique | list | length",
            firewall_assertions,
        )
        self.assertIn(
            "host_firewall_forward_proxy_access.interfaces | unique | list | length",
            firewall_assertions,
        )
        self.assertIn(
            "forward_proxy_client_container_firewall_access.interfaces\n"
            "        | unique | list | length",
            assertions,
        )
        self.assertIn(
            "or host_firewall_forward_proxy_egress.status == 'approved'",
            firewall_assertions,
        )
        self.assertNotIn("3[0-2])$'", firewall_assertions)
        self.assertIn("2 ** (32 - (item.split('/')[1] | int))", firewall_assertions)
        self.assertNotIn("[1-9]?[0-9]", firewall_assertions)
        self.assertNotIn("[1-9]?[0-9]", firewall_defaults)
        self.assertIn(
            "forward_proxy_client_listen_addresses | unique | list | length",
            assertions,
        )
        self.assertIn(
            "Validate Ubuntu forward proxy client listen addresses", assertions
        )
        self.assertIn(
            "forward_proxy_client_upstream_ipv4.split('.')[0] | int <= 223",
            assertions,
        )

    def test_restart_documentation_discloses_deferred_pending_work(self) -> None:
        readme = (ROLE_ROOT / "README.md").read_text()
        self.assertIn(
            "including work recorded by an earlier staged or failed activation", readme
        )
        self.assertIn("remain recorded", readme)

    def test_proxy_urls_are_derived_internal_values(self) -> None:
        defaults = (ROLE_ROOT / "defaults" / "main.yml").read_text()
        variables = (ROLE_ROOT / "vars" / "main.yml").read_text()
        argument_spec = (ROLE_ROOT / "meta" / "argument_specs.yml").read_text()
        readme = (ROLE_ROOT / "README.md").read_text()
        templates = "".join(
            path.read_text() for path in sorted((ROLE_ROOT / "templates").glob("*.j2"))
        )
        self.assertNotIn("forward_proxy_client_proxy_url:", defaults)
        self.assertNotIn("forward_proxy_client_container_url:", defaults)
        self.assertNotIn("forward_proxy_client_proxy_url:", argument_spec)
        self.assertNotIn("forward_proxy_client_container_url:", argument_spec)
        self.assertIn("forward_proxy_client_proxy_url_internal:", variables)
        self.assertIn("forward_proxy_client_container_url_internal:", variables)
        self.assertIn("forward_proxy_client_proxy_url_internal", templates)
        self.assertIn("forward_proxy_client_container_url_internal", templates)
        self.assertIn("cannot be overridden", readme)

    def test_parent_chain_and_no_proxy_tokens_fail_closed(self) -> None:
        assertions = (ROLE_ROOT / "tasks" / "assert.yml").read_text()
        main = (ROLE_ROOT / "tasks" / "main.yml").read_text()
        self.assertIn("forward_proxy_client_trusted_parent_paths", assertions)
        self.assertIn(
            "item | dirname in forward_proxy_client_trusted_parent_paths", assertions
        )
        self.assertIn('loop: "{{ forward_proxy_client_trusted_parent_paths }}"', main)
        self.assertIn("forward_proxy_client_approved_no_proxy_domains", assertions)
        self.assertIn("(?:/(?:[89]|[12][0-9]|3[0-2]))?", assertions)
        self.assertNotIn("(?:/[0-9]{1,3})?", assertions)
        self.assertIn("'/' not in item", assertions)
        argument_spec = (ROLE_ROOT / "meta" / "argument_specs.yml").read_text()
        self.assertIn("forward_proxy_client_trusted_parent_paths", argument_spec)
        self.assertIn("forward_proxy_client_approved_no_proxy_domains", argument_spec)

    def test_systemd_change_and_restart_conditions_have_complete_truth_table(
        self,
    ) -> None:
        tasks = yaml.safe_load((ROLE_ROOT / "tasks" / "enabled.yml").read_text())
        by_name = {task["name"]: task for task in tasks}
        reload_task = by_name[
            "Reload systemd manager after changing proxy client defaults"
        ]
        restart_task = by_name["Restart opted-in proxy client services"]

        def enabled(task: dict[str, object], **context: object) -> bool:
            condition_values = {
                "not ansible_check_mode": not bool(
                    context.get("ansible_check_mode", False)
                ),
                "forward_proxy_client_manage_systemd | bool": bool(
                    context["forward_proxy_client_manage_systemd"]
                ),
                "forward_proxy_client_systemd_activation_pending_internal | bool": bool(
                    context.get(
                        "forward_proxy_client_systemd_activation_pending_internal",
                        False,
                    )
                ),
                "forward_proxy_client_restart_now | bool": bool(
                    context.get("forward_proxy_client_restart_now", False)
                ),
                "forward_proxy_client_restart_pending_services_internal | length > 0": bool(
                    context.get(
                        "forward_proxy_client_restart_pending_services_internal", []
                    )
                ),
            }
            return all(condition_values[condition] for condition in task["when"])

        for manage_systemd in (False, True):
            for changed in (False, True):
                context = {
                    "forward_proxy_client_manage_systemd": manage_systemd,
                    "forward_proxy_client_systemd_activation_pending_internal": changed,
                }
                self.assertEqual(
                    enabled(reload_task, **context), manage_systemd and changed
                )

        for manage_systemd in (False, True):
            for restart_now in (False, True):
                for changed in (False, True):
                    context = {
                        "forward_proxy_client_manage_systemd": manage_systemd,
                        "forward_proxy_client_restart_now": restart_now,
                        "forward_proxy_client_restart_pending_services_internal": (
                            ["podman.service"] if changed else []
                        ),
                    }
                    self.assertEqual(
                        enabled(restart_task, **context),
                        manage_systemd and restart_now and changed,
                    )
        self.assertFalse(
            enabled(
                reload_task,
                ansible_check_mode=True,
                forward_proxy_client_manage_systemd=True,
                forward_proxy_client_systemd_activation_pending_internal=True,
            )
        )
        self.assertFalse(
            enabled(
                restart_task,
                ansible_check_mode=True,
                forward_proxy_client_manage_systemd=True,
                forward_proxy_client_restart_now=True,
                forward_proxy_client_restart_pending_services_internal=[
                    "podman.service"
                ],
            )
        )
        self.assertEqual(
            restart_task["ansible.builtin.systemd"]["state"],
            "restarted",
        )

    def test_existing_directories_keep_tighter_permissions(self) -> None:
        main = (ROLE_ROOT / "tasks" / "main.yml").read_text()
        ensure = (ROLE_ROOT / "tasks" / "ensure_directory.yml").read_text()
        enabled = (ROLE_ROOT / "tasks" / "enabled.yml").read_text()
        self.assertIn(
            "Create and revalidate each required proxy-client directory boundary", main
        )
        self.assertIn(
            "Trusted paths must therefore\n      be ordered from parent to child", ensure
        )
        self.assertIn(
            "Create only the validated proxy-client directory component", ensure
        )
        self.assertIn(
            "Reinspect the required proxy-client directory before rendering", ensure
        )
        self.assertIn(
            "when: not forward_proxy_client_directory_before.stat.exists", ensure
        )
        self.assertNotIn("Create forward proxy client managed directories", enabled)

    def test_previous_container_paths_retain_a_validated_cleanup_chain(self) -> None:
        tasks = (ROLE_ROOT / "tasks" / "main.yml").read_text()
        self.assertIn(
            "Bind previously managed proxy-client paths to the trusted parent chain",
            tasks,
        )
        self.assertIn(
            "forward_proxy_client_previous_state_manifest.managed_paths",
            tasks,
        )
        self.assertIn(
            "item | dirname in forward_proxy_client_trusted_parent_paths", tasks
        )

    def test_proxy_owner_rule_reaches_grammar_validating_nft_check(self) -> None:
        fixture = (
            REPOSITORY_ROOT / "molecule" / "host-firewall-basic" / "prepare.yml"
        ).read_text()
        verify = (
            REPOSITORY_ROOT / "molecule" / "host-firewall-basic" / "verify.yml"
        ).read_text()
        self.assertIn("grammar-validating nft command double", fixture)
        self.assertIn("proxy_rule_pattern", fixture)
        self.assertIn("'--check --file -'", verify)

    def test_disable_is_check_mode_safe_and_requires_service_cutover(self) -> None:
        tasks = yaml.safe_load((ROLE_ROOT / "tasks" / "main.yml").read_text())
        by_name = {task["name"]: task for task in tasks}
        reload_task = by_name[
            "Reload systemd manager after removing proxy client defaults"
        ]
        restart_task = by_name[
            "Restart opted-in services after disabling the proxy client"
        ]
        cutover_task = by_name[
            "Require explicit service cutover before disabling proxy client state"
        ]
        self.assertIn("not ansible_check_mode", reload_task["when"])
        self.assertIn("not ansible_check_mode", restart_task["when"])
        self.assertIn(
            "forward_proxy_client_disable_restart_services_internal | length == 0",
            cutover_task["ansible.builtin.assert"]["that"][1],
        )
        self.assertIn(
            "forward_proxy_client_systemd_environment_path",
            cutover_task["ansible.builtin.assert"]["that"][0],
        )
        self.assertEqual(
            restart_task["loop"],
            "{{ forward_proxy_client_disable_restart_services_internal | default([]) }}",
        )
        self.assertIn(
            "Preserve every pending service across proxy-client disable", by_name
        )
        preserve = by_name[
            "Preserve every pending service across proxy-client disable"
        ]["ansible.builtin.set_fact"]
        self.assertIn(
            "restart_activated_services",
            preserve["forward_proxy_client_disable_restart_services_internal"],
        )
        ensure = (ROLE_ROOT / "tasks" / "ensure_directory.yml").read_text()
        self.assertEqual(ensure.count("not ansible_check_mode"), 2)
        self.assertEqual(
            ensure.count("forward_proxy_client_directory_before.stat.exists"), 5
        )
        self.assertIn(
            "forward_proxy_client_planned_directories_internal", ensure
        )
        self.assertIn(
            "Initialize the check-mode proxy-client directory plan", by_name
        )

    def test_root_documentation_and_molecule_cover_public_adapter_modes(self) -> None:
        root_readme = (REPOSITORY_ROOT / "README.md").read_text()
        example = (REPOSITORY_ROOT / "playbooks" / "example.yml").read_text()
        verify = (
            REPOSITORY_ROOT / "molecule" / "forward-proxy-client-basic" / "verify.yml"
        ).read_text()
        self.assertIn("lit.ubuntu.forward_proxy_client", root_readme)
        self.assertIn("role: lit.ubuntu.forward_proxy_client", example)
        self.assertIn("forward_proxy_client_enabled: false", example)
        self.assertIn("forward_proxy_client_upstream_enabled: true", verify)
        self.assertIn("192.0.2.10/32", verify)
        self.assertIn("forward_proxy_client_upstream_port: 8080", verify)


if __name__ == "__main__":
    unittest.main()
