from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CANONICALIZER = REPOSITORY_ROOT / "roles" / "host_firewall" / "files" / "canonicalize_nft_json.py"


def run_canonicalizer(document: str, family: str = "inet", table: str = "lit_host_firewall") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CANONICALIZER), "--family", family, "--table", table],
        input=document,
        text=True,
        capture_output=True,
        check=False,
    )


class CanonicalNftJsonTests(unittest.TestCase):
    def test_runtime_handles_and_counter_values_do_not_change_digest(self) -> None:
        first = {
            "nftables": [
                {"metainfo": {"version": "1.0.8"}},
                {"table": {"family": "inet", "name": "lit_host_firewall", "handle": 4}},
                {
                    "set": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "name": "openssh_sources_v4",
                        "type": "ipv4_addr",
                        "elem": ["198.51.100.21", "198.51.100.20"],
                        "handle": 5,
                    }
                },
                {
                    "rule": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "chain": "input",
                        "expr": [{"counter": {"packets": 9, "bytes": 99}}, {"accept": None}],
                        "handle": 6,
                    }
                },
            ]
        }
        second = json.loads(json.dumps(first))
        second["nftables"][0]["metainfo"]["version"] = "1.1.0"
        second["nftables"][1]["table"]["handle"] = 400
        second["nftables"][2]["set"]["elem"].reverse()
        second["nftables"][3]["rule"]["expr"][0]["counter"] = {"packets": 1, "bytes": 2}

        first_result = run_canonicalizer(json.dumps(first))
        second_result = run_canonicalizer(json.dumps(second))

        self.assertEqual(first_result.returncode, 0, first_result.stderr)
        self.assertEqual(second_result.returncode, 0, second_result.stderr)
        self.assertEqual(
            hashlib.sha256(first_result.stdout.encode()).hexdigest(),
            hashlib.sha256(second_result.stdout.encode()).hexdigest(),
        )

    def test_policy_drift_changes_digest(self) -> None:
        baseline = {
            "nftables": [
                {"table": {"family": "inet", "name": "lit_host_firewall"}},
                {
                    "chain": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "name": "input",
                        "type": "filter",
                        "hook": "input",
                        "prio": 10,
                        "policy": "drop",
                    }
                },
            ]
        }
        drift = json.loads(json.dumps(baseline))
        drift["nftables"][1]["chain"]["policy"] = "accept"

        baseline_result = run_canonicalizer(json.dumps(baseline))
        drift_result = run_canonicalizer(json.dumps(drift))

        self.assertEqual(baseline_result.returncode, 0, baseline_result.stderr)
        self.assertEqual(drift_result.returncode, 0, drift_result.stderr)
        self.assertNotEqual(baseline_result.stdout, drift_result.stdout)

    def test_rule_order_remains_security_significant(self) -> None:
        document = {
            "nftables": [
                {"table": {"family": "inet", "name": "lit_host_firewall"}},
                {
                    "rule": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "chain": "input",
                        "expr": [{"accept": None}],
                    }
                },
                {
                    "rule": {
                        "family": "inet",
                        "table": "lit_host_firewall",
                        "chain": "input",
                        "expr": [{"drop": None}],
                    }
                },
            ]
        }
        reversed_document = json.loads(json.dumps(document))
        reversed_document["nftables"][1:] = reversed(reversed_document["nftables"][1:])

        first = run_canonicalizer(json.dumps(document))
        second = run_canonicalizer(json.dumps(reversed_document))

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertNotEqual(first.stdout, second.stdout)

    def test_foreign_table_is_rejected(self) -> None:
        result = run_canonicalizer('{"nftables":[{"table":{"family":"inet","name":"foreign"}}]}')
        self.assertEqual(result.returncode, 2)
        self.assertIn("escaped", result.stderr)

    def test_duplicate_json_keys_are_rejected(self) -> None:
        result = run_canonicalizer(
            '{"nftables":[{"table":{"family":"inet","name":"lit_host_firewall",'
            '"name":"foreign"}}]}'
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate JSON key", result.stderr)

    def test_strict_base64_transport_preserves_exact_json(self) -> None:
        document = '{"nftables":[{"table":{"family":"inet","name":"lit_host_firewall"}}]}'
        result = subprocess.run(
            [
                sys.executable,
                str(CANONICALIZER),
                "--family",
                "inet",
                "--table",
                "lit_host_firewall",
                "--stdin-base64",
            ],
            input=base64.b64encode(document.encode()).decode(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, document)


if __name__ == "__main__":
    unittest.main()
