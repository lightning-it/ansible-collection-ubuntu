"""Regression contracts for the REP-60 protected review trust root."""

from __future__ import annotations

import argparse
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
MATERIALIZER = ROOT / "scripts" / "materialize-exact-revision-review.py"
RERUN_WORKFLOW = ROOT / ".github" / "workflows" / "current-revision-rerun.yml"


def load_materializer():
    spec = importlib.util.spec_from_file_location("materialize_exact_revision_review", MATERIALIZER)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the exact-revision materializer.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Rep60TrustRootContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.materializer = load_materializer()

    def test_dispatch_is_bound_to_the_exact_selected_base_commit(self) -> None:
        workflow = RERUN_WORKFLOW.read_text(encoding="utf-8")
        dispatch_case = workflow.split("workflow_dispatch)", maxsplit=1)[1].split(";;", maxsplit=1)[0]

        self.assertIn('test "${GITHUB_REF}" = "refs/heads/${EVENT_BASE_REF}"', dispatch_case)
        self.assertIn('test "${GITHUB_SHA}" = "${EXPECTED_BASE}"', dispatch_case)

    def test_live_pull_request_rejects_valid_non_object_json(self) -> None:
        arguments = argparse.Namespace(
            repository="lightning-it/ansible-collection-ubuntu",
            pull_request=499,
            base_ref="main",
            expected_base="a" * 40,
            expected_head="b" * 40,
        )

        for payload in ("null", "[]", '"text"', "1"):
            with self.subTest(payload=payload):
                result = SimpleNamespace(stdout=payload)
                with (
                    patch.object(self.materializer, "executable", return_value="gh"),
                    patch.object(self.materializer, "command_environment", return_value={}),
                    patch.object(self.materializer, "run", return_value=result),
                    self.assertRaisesRegex(
                        self.materializer.MaterializationError,
                        "non-object pull-request JSON",
                    ),
                ):
                    self.materializer.read_live_pull_request(arguments, home=ROOT)


if __name__ == "__main__":
    unittest.main()
