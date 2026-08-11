from __future__ import annotations

import base64
import contextlib
import datetime as dt
import importlib.util
import json
import os
import stat
import sys
import tempfile
import threading
import time
import types
import unittest
from pathlib import Path
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
TRANSACTION_PROGRAM = REPOSITORY_ROOT / "roles" / "host_firewall" / "files" / "firewall_transaction.py"
SPEC = importlib.util.spec_from_file_location("firewall_transaction_under_test", TRANSACTION_PROGRAM)
assert SPEC is not None and SPEC.loader is not None
transaction = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = transaction
SPEC.loader.exec_module(transaction)


def nft_document(policy: str = "drop", *, handle: int = 1, packets: int = 1) -> bytes:
    return json.dumps(
        {
            "nftables": [
                {"metainfo": {"version": "1.0.9"}},
                {"table": {"family": "inet", "name": "lit_host_firewall", "handle": handle}},
                {
                    "chain": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "name": "input",
                        "policy": policy,
                        "handle": handle + 1,
                    }
                },
                {
                    "rule": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "chain": "input",
                        "expr": [{"counter": {"packets": packets, "bytes": packets * 8}}, {"drop": None}],
                        "handle": handle + 2,
                    }
                },
            ]
        }
    ).encode()


def table_inventory(present: bool) -> bytes:
    statements = [{"metainfo": {"version": "1.0.9"}}]
    if present:
        statements.append({"table": {"family": "inet", "name": "lit_host_firewall"}})
    return json.dumps({"nftables": statements}).encode()


def runtime_config(root: str = "/secure") -> transaction.RuntimeConfig:
    return transaction.RuntimeConfig(
        state_directory=Path(root) / "state",
        transactions_directory=Path(root) / "state" / "transactions",
        claims_directory=Path(root) / "state" / "claims",
        active_path=Path(root) / "state" / "active.json",
        lock_path=Path(root) / "state" / "transaction.lock",
        persistent_root=Path(root) / "nftables.conf",
        persistent_include=Path(root) / "nftables.d" / "host-firewall.nft",
        program_path=Path(root) / "bin" / "transaction",
        systemd_unit_directory=Path(root) / "systemd",
        confirmation_service="host-firewall-confirm.service",
        rollback_service="host-firewall-rollback.service",
        rollback_timer="host-firewall-rollback.timer",
        persistence_service="nftables.service",
        watchdog_timeout_seconds=300,
        command_timeout_seconds=15,
        lock_wait_timeout_seconds=30,
        expected_target="wunderbox01.prd.edge.pub.l-it.io",
        expected_egress_policy_sha256="a" * 64,
        expected_egress_status="approved",
        table_family="inet",
        table_name="lit_host_firewall",
        nft_binary=str(Path(root) / "bin" / "nft"),
        systemctl_binary=str(Path(root) / "bin" / "systemctl"),
        verifier_binary=str(Path(root) / "bin" / "verifier"),
    )


class CanonicalNftJsonTests(unittest.TestCase):
    def test_runtime_fields_and_set_order_do_not_change_digest(self) -> None:
        first = json.loads(nft_document(handle=4, packets=9))
        first["nftables"].insert(
            2,
            {
                "set": {
                    "family": "inet",
                    "table": "lit_host_firewall",
                    "name": "sources",
                    "type": "ipv4_addr",
                    "elem": ["198.51.100.21", "198.51.100.20"],
                    "handle": 5,
                }
            },
        )
        second = json.loads(json.dumps(first))
        second["nftables"][0]["metainfo"]["version"] = "1.1.0"
        second["nftables"][1]["table"]["handle"] = 400
        second["nftables"][2]["set"]["elem"].reverse()
        second["nftables"][4]["rule"]["expr"][0]["counter"] = {"packets": 1, "bytes": 2}
        self.assertEqual(
            transaction.canonicalize_nft_document(json.dumps(first).encode(), "inet", "lit_host_firewall"),
            transaction.canonicalize_nft_document(json.dumps(second).encode(), "inet", "lit_host_firewall"),
        )

    def test_policy_and_rule_order_remain_security_significant(self) -> None:
        baseline = transaction.canonicalize_nft_document(nft_document("drop"), "inet", "lit_host_firewall")
        drift = transaction.canonicalize_nft_document(nft_document("accept"), "inet", "lit_host_firewall")
        self.assertNotEqual(baseline, drift)

        document = json.loads(nft_document())
        document["nftables"].append(
            {
                "rule": {
                    "family": "inet",
                    "table": "lit_host_firewall",
                    "chain": "input",
                    "expr": [{"accept": None}],
                }
            }
        )
        reversed_document = json.loads(json.dumps(document))
        reversed_document["nftables"][-2:] = reversed(reversed_document["nftables"][-2:])
        self.assertNotEqual(
            transaction.canonicalize_nft_document(json.dumps(document).encode(), "inet", "lit_host_firewall"),
            transaction.canonicalize_nft_document(
                json.dumps(reversed_document).encode(), "inet", "lit_host_firewall"
            ),
        )

    def test_foreign_table_and_duplicate_json_keys_are_rejected(self) -> None:
        with self.assertRaisesRegex(transaction.TransactionError, "escaped"):
            transaction.canonicalize_nft_document(
                b'{"nftables":[{"table":{"family":"inet","name":"foreign"}}]}',
                "inet",
                "lit_host_firewall",
            )
        with self.assertRaisesRegex(transaction.TransactionError, "duplicate JSON key"):
            transaction.canonicalize_nft_document(
                b'{"nftables":[{"table":{"family":"inet","name":"lit_host_firewall","name":"foreign"}}]}',
                "inet",
                "lit_host_firewall",
            )


class NftStateClassificationTests(unittest.TestCase):
    def test_rc_one_permission_or_netlink_failure_is_never_classified_as_absence(self) -> None:
        failure = transaction.CommandResult(1, b"", b"Operation not permitted")
        with mock.patch.object(transaction, "run_command", return_value=failure):
            with self.assertRaisesRegex(transaction.TransactionError, "inventory failed with rc=1"):
                transaction.read_nft_table_state("/nft", "inet", "lit_host_firewall")


class RollbackRaceTests(unittest.TestCase):
    def test_watchdog_never_rolls_back_an_authoritative_confirmation_terminal(self) -> None:
        config = runtime_config()
        transaction_directory = config.transactions_directory / ("1" * 32)
        active = {
            "schema": "lit.host_firewall.active/v3",
            "transaction_id": "1" * 32,
            "transaction_path": str(transaction_directory),
            "metadata_sha256": "2" * 64,
        }
        terminal = {"schema": "lit.host_firewall.confirmation/v3", "transaction_id": "1" * 32}
        with (
            mock.patch.object(
                transaction,
                "load_active",
                return_value=(active, transaction_directory, transaction.transaction_paths(transaction_directory)),
            ),
            mock.patch.object(transaction, "load_terminal", return_value=terminal),
            mock.patch.object(transaction, "finalize_existing_terminal"),
            mock.patch.object(transaction, "validate_metadata_and_assets") as validate_assets,
        ):
            result = transaction.rollback_locked(config, explicit_request=None, watchdog=True)
        self.assertEqual(
            result,
            {"schema": "lit.host_firewall.rollback-result/v3", "status": "already-confirmed"},
        )
        validate_assets.assert_not_called()

    def test_explicit_rollback_keeps_static_verifier_binding(self) -> None:
        config = runtime_config()
        transaction_directory = config.transactions_directory / ("1" * 32)
        active = {
            "schema": "lit.host_firewall.active/v3",
            "transaction_id": "1" * 32,
            "transaction_path": str(transaction_directory),
            "metadata_sha256": "2" * 64,
        }
        paths = transaction.transaction_paths(transaction_directory)
        with (
            mock.patch.object(transaction, "load_active", return_value=(active, transaction_directory, paths)),
            mock.patch.object(transaction, "load_terminal", return_value=None),
            mock.patch.object(transaction, "validate_metadata_and_assets", return_value={}) as validate_assets,
            mock.patch.object(
                transaction,
                "validate_explicit_rollback_request",
                side_effect=transaction.TransactionError("stop after static validation"),
            ),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "stop after static validation"):
                transaction.rollback_locked(config, explicit_request={}, watchdog=False)
        validate_assets.assert_called_once_with(config, active, paths, validate_static=True)

    def test_watchdog_rollback_bypasses_only_static_drift(self) -> None:
        config = runtime_config()
        transaction_directory = config.transactions_directory / ("1" * 32)
        active = {
            "schema": "lit.host_firewall.active/v3",
            "transaction_id": "1" * 32,
            "transaction_path": str(transaction_directory),
            "metadata_sha256": "2" * 64,
        }
        paths = transaction.transaction_paths(transaction_directory)
        with (
            mock.patch.object(transaction, "load_active", return_value=(active, transaction_directory, paths)),
            mock.patch.object(transaction, "load_terminal", return_value=None),
            mock.patch.object(transaction, "validate_metadata_and_assets", return_value={}) as validate_assets,
            mock.patch.object(
                transaction,
                "validate_root_include",
                side_effect=transaction.TransactionError("stop after emergency validation"),
            ),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "stop after emergency validation"):
                transaction.rollback_locked(config, explicit_request=None, watchdog=True)
        validate_assets.assert_called_once_with(config, active, paths, validate_static=False)

    def test_active_activating_failed_and_unknown_rollback_states_block_confirmation(self) -> None:
        config = runtime_config()
        for state_name in (b"active\n", b"activating\n", b"failed\n", b"unknown\n"):
            with self.subTest(state=state_name):
                result = transaction.CommandResult(0, state_name, b"")
                with mock.patch.object(transaction, "run_command", return_value=result):
                    with self.assertRaisesRegex(transaction.TransactionError, "not quiescent"):
                        transaction.require_rollback_service_quiescent(config)

    def test_only_exact_inactive_rollback_state_is_quiescent(self) -> None:
        config = runtime_config()
        result = transaction.CommandResult(0, b"inactive\n", b"")
        with mock.patch.object(transaction, "run_command", return_value=result):
            transaction.require_rollback_service_quiescent(config)

    def test_root_include_must_remain_one_exact_literal_directive(self) -> None:
        config = runtime_config()
        duplicate = (
            f'include "{config.persistent_include}"\n'
            f'include "{config.persistent_include}"\n'
        ).encode()
        with mock.patch.object(transaction, "read_secure_bytes", return_value=duplicate):
            with self.assertRaisesRegex(transaction.TransactionError, "exactly one literal"):
                transaction.validate_root_include(config)

    def test_absence_requires_two_successful_structured_inventories(self) -> None:
        absent = transaction.CommandResult(0, table_inventory(False), b"")
        with mock.patch.object(transaction, "run_command", side_effect=[absent, absent]) as command:
            state = transaction.read_nft_table_state("/nft", "inet", "lit_host_firewall")
        self.assertFalse(state.present)
        self.assertEqual(command.call_count, 2)

    def test_snapshot_toctou_is_rejected(self) -> None:
        responses = [
            transaction.CommandResult(0, table_inventory(True), b""),
            transaction.CommandResult(0, nft_document("drop"), b""),
            transaction.CommandResult(0, b"table inet lit_host_firewall {}\n", b""),
            transaction.CommandResult(0, nft_document("accept"), b""),
        ]
        with mock.patch.object(transaction, "run_command", side_effect=responses):
            with self.assertRaisesRegex(transaction.TransactionError, "changed while"):
                transaction.read_nft_table_state("/nft", "inet", "lit_host_firewall")


class PathBoundaryTests(unittest.TestCase):
    def test_all_configured_paths_must_be_pairwise_distinct(self) -> None:
        config = runtime_config()
        collision = transaction.RuntimeConfig(**{**config.__dict__, "program_path": config.persistent_root})
        with self.assertRaisesRegex(transaction.TransactionError, "pairwise distinct"):
            collision.validate_shape()

    def test_symlink_leaf_is_rejected(self) -> None:
        components = [Path("/"), Path("/secure"), Path("/secure/value")]
        stats = {
            "/": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755),
            "/secure": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755),
            "/secure/value": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFLNK | 0o777),
        }
        with (
            mock.patch.object(transaction, "path_components", return_value=components),
            mock.patch.object(Path, "lstat", new=lambda self: stats[str(self)]),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "symbolic links"):
                transaction.validate_secure_path_chain(Path("/secure/value"), expected_leaf="file")

    def test_group_writable_parent_is_rejected(self) -> None:
        components = [Path("/"), Path("/secure"), Path("/secure/value")]
        stats = {
            "/": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755),
            "/secure": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o775),
            "/secure/value": types.SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o600),
        }
        with (
            mock.patch.object(transaction, "path_components", return_value=components),
            mock.patch.object(Path, "lstat", new=lambda self: stats[str(self)]),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "group/world writable"):
                transaction.validate_secure_path_chain(Path("/secure/value"), expected_leaf="file")

    def test_transaction_lock_serializes_concurrent_callers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = runtime_config(temporary)
            config.state_directory.mkdir()
            events: list[str] = []

            def worker(name: str) -> None:
                with transaction.exclusive_transaction_lock(config):
                    events.append(f"{name}-start")
                    time.sleep(0.03)
                    events.append(f"{name}-end")

            real_fstat = os.fstat

            def root_fstat(descriptor: int) -> types.SimpleNamespace:
                current = real_fstat(descriptor)
                return types.SimpleNamespace(st_uid=0, st_mode=current.st_mode)

            with (
                mock.patch.object(transaction, "validate_secure_path_chain"),
                mock.patch.object(transaction.os, "fstat", side_effect=root_fstat),
            ):
                first = threading.Thread(target=worker, args=("first",))
                second = threading.Thread(target=worker, args=("second",))
                first.start()
                second.start()
                first.join()
                second.join()

            self.assertIn(
                events,
                [
                    ["first-start", "first-end", "second-start", "second-end"],
                    ["second-start", "second-end", "first-start", "first-end"],
                ],
            )

    def test_stale_transaction_lock_times_out_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = runtime_config(temporary)
            config = transaction.RuntimeConfig(**{**config.__dict__, "lock_wait_timeout_seconds": 1})
            config.state_directory.mkdir()
            real_fstat = os.fstat

            def root_fstat(descriptor: int) -> types.SimpleNamespace:
                current = real_fstat(descriptor)
                return types.SimpleNamespace(st_uid=0, st_mode=current.st_mode)

            with (
                mock.patch.object(transaction, "validate_secure_path_chain"),
                mock.patch.object(transaction.os, "fstat", side_effect=root_fstat),
                mock.patch.object(transaction.fcntl, "flock", side_effect=BlockingIOError),
                mock.patch.object(transaction.time, "monotonic", side_effect=[0.0, 2.0]),
            ):
                with self.assertRaisesRegex(transaction.TransactionError, "lock wait exceeded"):
                    with transaction.exclusive_transaction_lock(config):
                        self.fail("stale lock unexpectedly entered")


class DeadlineAndDurabilityTests(unittest.TestCase):
    def test_hung_nft_command_is_terminated_by_the_transaction_deadline(self) -> None:
        with mock.patch.object(
            transaction.subprocess,
            "run",
            side_effect=transaction.subprocess.TimeoutExpired(cmd=["/nft"], timeout=5),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "fail-closed timeout"):
                with transaction.bounded_command_deadline(10, command_timeout_seconds=5):
                    transaction.run_command(["/nft", "--json", "list", "tables"])

    def test_watchdog_rollback_uses_the_reserved_rollback_budget(self) -> None:
        config = runtime_config()
        self.assertEqual(
            config.transaction_budget_seconds("watchdog-rollback"),
            config.rollback_budget_seconds(),
        )

    def test_action_deadline_is_established_before_lock_acquisition(self) -> None:
        config = runtime_config()
        observed: dict[str, float | None] = {}

        @contextlib.contextmanager
        def observe_lock(
            _config: transaction.RuntimeConfig,
            *,
            absolute_deadline: float | None = None,
        ) -> object:
            observed["lock_deadline"] = absolute_deadline
            observed["command_deadline"] = transaction.COMMAND_DEADLINE.get()
            yield

        with (
            mock.patch.object(transaction.time, "monotonic", return_value=100.0),
            mock.patch.object(transaction, "exclusive_transaction_lock", side_effect=observe_lock),
        ):
            with transaction.transaction_scope(config, action="watchdog-rollback"):
                pass

        expected = 100.0 + config.rollback_budget_seconds()
        self.assertEqual(observed, {"lock_deadline": expected, "command_deadline": expected})

    def test_action_deadline_shortens_the_stale_lock_wait(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            config = runtime_config(temporary)
            config.state_directory.mkdir()
            real_fstat = os.fstat

            def root_fstat(descriptor: int) -> types.SimpleNamespace:
                current = real_fstat(descriptor)
                return types.SimpleNamespace(st_uid=0, st_mode=current.st_mode)

            with (
                mock.patch.object(transaction, "validate_secure_path_chain"),
                mock.patch.object(transaction.os, "fstat", side_effect=root_fstat),
                mock.patch.object(transaction.fcntl, "flock", side_effect=BlockingIOError),
                mock.patch.object(transaction.time, "monotonic", side_effect=[0.0, 11.0]),
                mock.patch.object(transaction.time, "sleep") as sleep,
            ):
                with self.assertRaisesRegex(transaction.TransactionError, "lock wait exceeded"):
                    with transaction.exclusive_transaction_lock(config, absolute_deadline=10.0):
                        self.fail("lock unexpectedly entered after the action deadline")
            sleep.assert_not_called()

    def test_exclusive_create_fsyncs_its_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "evidence.json"
            with (
                mock.patch.object(transaction, "validate_secure_path_chain"),
                mock.patch.object(transaction, "fsync_directory") as sync_directory,
            ):
                transaction.write_exclusive(destination, b"evidence")
            sync_directory.assert_called_once_with(destination.parent)

    def test_terminal_finalization_orders_create_before_durable_active_unlink(self) -> None:
        config = runtime_config()
        terminal_path = config.transactions_directory / ("1" * 32) / "terminal.json"
        events: list[str] = []
        with (
            mock.patch.object(
                transaction,
                "write_exclusive",
                side_effect=lambda *_args, **_kwargs: events.append("terminal-fsynced"),
            ),
            mock.patch.object(
                transaction,
                "durable_unlink",
                side_effect=lambda *_args, **_kwargs: events.append("active-unlinked-fsynced"),
            ),
            mock.patch.object(
                transaction,
                "systemctl",
                side_effect=lambda *_args, **_kwargs: events.append("watchdog-disabled"),
            ),
        ):
            transaction.write_terminal_disable_watchdog_and_clear_active(
                config,
                terminal_path,
                {"schema": "lit.host_firewall.confirmation/v3"},
            )
        self.assertEqual(events, ["terminal-fsynced", "watchdog-disabled", "active-unlinked-fsynced"])


class ClosedMetadataAndAuthorizationTests(unittest.TestCase):
    def test_metadata_rehash_detects_candidate_tampering(self) -> None:
        config = runtime_config()
        paths = transaction.transaction_paths(config.transactions_directory / ("1" * 32))
        assets = {
            "candidate": b"candidate",
            "apply_authorization": b"authorization",
            "apply_verification": b"verification",
            "runtime_backup": b"runtime",
            "runtime_canonical": b"canonical",
            "runtime_state": b"present\n",
            "persistent_backup": b"persistent",
            "persistent_state": b"present\n",
        }
        static_assets = {
            config.program_path: b"program",
            config.systemd_unit_directory / config.confirmation_service: b"confirm-unit",
            config.systemd_unit_directory / config.rollback_service: b"rollback-unit",
            config.systemd_unit_directory / config.rollback_timer: b"rollback-timer",
            Path(config.verifier_binary): b"verifier",
        }
        metadata = {
            "schema": "lit.host_firewall.transaction/v3",
            "transaction_id": "1" * 32,
            "target": config.expected_target,
            "action": "apply",
            "change_id": "WBX-G2-TEST",
            "claim_id": "claim-apply-001",
            "created_at": "2026-08-09T12:00:00Z",
            "mode": "hardened",
            "egress_status": "approved",
            "approved_readback_sha256": "2" * 64,
            "policy_fingerprint": "4" * 64,
            "egress_policy_sha256": "5" * 64,
            **{f"{name}_sha256": transaction.sha256_bytes(value) for name, value in assets.items()},
            "persistent_root_sha256": transaction.sha256_bytes(b"root"),
            "program_sha256": transaction.sha256_bytes(static_assets[config.program_path]),
            "confirmation_unit_sha256": transaction.sha256_bytes(
                static_assets[config.systemd_unit_directory / config.confirmation_service]
            ),
            "rollback_unit_sha256": transaction.sha256_bytes(
                static_assets[config.systemd_unit_directory / config.rollback_service]
            ),
            "rollback_timer_sha256": transaction.sha256_bytes(
                static_assets[config.systemd_unit_directory / config.rollback_timer]
            ),
            "verifier_path": config.verifier_binary,
            "verifier_sha256": transaction.sha256_bytes(static_assets[Path(config.verifier_binary)]),
        }
        metadata_raw = transaction.canonical_json(metadata)
        file_values = {paths[name]: value for name, value in assets.items()}
        file_values.update(static_assets)
        file_values[config.persistent_root] = b"root"
        file_values[paths["metadata"]] = metadata_raw
        file_values[paths["candidate"]] = b"tampered"
        active = {
            "schema": "lit.host_firewall.active/v3",
            "transaction_id": "1" * 32,
            "transaction_path": str(config.transactions_directory / ("1" * 32)),
            "metadata_sha256": transaction.sha256_bytes(metadata_raw),
        }
        with mock.patch.object(transaction, "read_secure_bytes", side_effect=lambda path: file_values[path]):
            with self.assertRaisesRegex(transaction.TransactionError, "asset changed: candidate"):
                transaction.validate_metadata_and_assets(config, active, paths)

        file_values[paths["candidate"]] = assets["candidate"]
        file_values[Path(config.verifier_binary)] = b"tampered-verifier"
        with mock.patch.object(transaction, "read_secure_bytes", side_effect=lambda path: file_values[path]):
            with self.assertRaisesRegex(transaction.TransactionError, "static transaction asset changed"):
                transaction.validate_metadata_and_assets(config, active, paths)

        file_values[Path(config.verifier_binary)] = static_assets[Path(config.verifier_binary)]
        file_values[paths["apply_authorization"]] = b"tampered-authorization"
        with mock.patch.object(transaction, "read_secure_bytes", side_effect=lambda path: file_values[path]):
            with self.assertRaisesRegex(transaction.TransactionError, "asset changed: apply_authorization"):
                transaction.validate_metadata_and_assets(config, active, paths)

    def test_missing_persistence_include_is_not_a_rollback_baseline(self) -> None:
        config = runtime_config()
        with mock.patch.object(transaction.os.path, "lexists", return_value=False):
            with self.assertRaisesRegex(transaction.TransactionError, "preprovisioned persistence include"):
                transaction.snapshot_persistent(config)

    def test_incomplete_confirmation_cannot_become_an_authoritative_terminal_state(self) -> None:
        paths = transaction.transaction_paths(Path("/secure/state/transactions") / ("1" * 32))
        invalid = transaction.canonical_json(
            {"schema": "lit.host_firewall.confirmation/v3", "transaction_id": "1" * 32}
        )
        with (
            mock.patch.object(transaction.os.path, "lexists", return_value=True),
            mock.patch.object(transaction, "read_secure_bytes", return_value=invalid),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "must contain exactly"):
                transaction.load_terminal(paths)

    def test_integer_true_verifier_receipt_is_rejected(self) -> None:
        config = runtime_config()
        now = dt.datetime(2026, 8, 9, 12, 0, tzinfo=dt.timezone.utc)
        authorization = {
            "schema": "lit.host_firewall.authorization/v2",
            "target": config.expected_target,
            "action": "apply",
            "change_id": "WBX-G2-TEST",
            "claim_id": "claim-apply-001",
            "candidate_sha256": "1" * 64,
            "approved_readback_sha256": "2" * 64,
            "policy_fingerprint": "3" * 64,
            "egress_policy_sha256": config.expected_egress_policy_sha256,
            "egress_status": "approved",
            "issued_at": "2026-08-09T11:59:00Z",
            "expires_at": "2026-08-09T12:01:00Z",
            "signature": base64.b64encode(b"s" * 64).decode(),
        }
        request = {
            key: authorization[key]
            for key in (
                "target",
                "action",
                "change_id",
                "candidate_sha256",
                "approved_readback_sha256",
                "policy_fingerprint",
                "egress_policy_sha256",
                "egress_status",
            )
        }
        request.update({"schema": "lit.host_firewall.transaction-request/v3", "mode": "hardened"})
        request["authorization"] = authorization

        def verifier_result(_argv: list[str], *, input_bytes: bytes | None = None) -> transaction.CommandResult:
            assert input_bytes is not None
            receipt = {
                "schema": "lit.host_firewall.authorization-verification/v1",
                "claim_id": authorization["claim_id"],
                "authorization_sha256": transaction.sha256_bytes(input_bytes),
                "valid": 1,
            }
            return transaction.CommandResult(0, transaction.canonical_json(receipt), b"")

        with (
            mock.patch.object(transaction, "validate_secure_path_chain"),
            mock.patch.object(transaction, "run_command", side_effect=verifier_result),
            mock.patch.object(transaction.os.path, "lexists", return_value=False),
        ):
            with self.assertRaisesRegex(transaction.TransactionError, "mismatched receipt"):
                transaction.validate_authorization(request, config, now=now)


class AddressNormalizationTests(unittest.TestCase):
    def test_ipv6_addresses_and_control_source_use_one_canonical_spelling(self) -> None:
        normalized = transaction.normalize_firewall_inputs(
            {
                "control_source_address": "2001:0DB8:0:0:0:0:0:20",
                "expected_public_ipv4": "192.0.2.10",
                "expected_management_ipv4": "10.0.30.10",
                "expected_public_ipv6": "2001:0DB8:0:0:0:0:0:10",
                "expected_management_ipv6": "FD00:0:0:30:0:0:0:10",
                "observed_ipv4_addresses": ["192.0.2.10", "10.0.30.10"],
                "observed_ipv6_addresses": ["2001:db8::10", "fd00:0:0:30::10"],
                "management_access": {
                    "openssh": {
                        "port": 1905,
                        "modes": ["bootstrap", "hardened"],
                        "sources_ipv4": [],
                        "sources_ipv6": ["2001:0DB8:0:0:0:0:0:20/128"],
                    }
                },
                "public_service_access": {},
                "tang_access": {"port": 80, "sources_ipv4": [], "sources_ipv6": []},
            }
        )
        self.assertEqual(normalized["expected_public_ipv6"], "2001:db8::10")
        self.assertEqual(normalized["expected_management_ipv6"], "fd00:0:0:30::10")
        self.assertEqual(normalized["control_source_address"], "2001:db8::20")
        self.assertEqual(normalized["management_access"]["openssh"]["sources_ipv6"], ["2001:db8::20/128"])


if __name__ == "__main__":
    unittest.main()
