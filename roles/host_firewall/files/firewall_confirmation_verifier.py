#!/usr/bin/env python3
"""Verify an exact target-and-candidate operator confirmation."""

from __future__ import annotations

import base64
import hashlib
import json
import sys


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("ascii")


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


if sys.argv[1:] != ["verify-host-firewall-claim"]:
    fail("unsupported verifier operation")

try:
    claim = json.loads(sys.stdin.buffer.read())
except (UnicodeDecodeError, json.JSONDecodeError):
    fail("authorization is not valid JSON")

if not isinstance(claim, dict) or claim.get("schema") != "lit.host_firewall.authorization/v2":
    fail("unsupported authorization envelope")

action_prefix = {
    "apply": "APPLY-HOST-FIREWALL",
    "confirm": "CONFIRM-HOST-FIREWALL",
    "rollback": "ROLLBACK-HOST-FIREWALL",
}.get(claim.get("action"))
if action_prefix is None:
    fail("unsupported authorization action")

expected = f"{action_prefix}:{claim.get('target', '')}:{claim.get('candidate_sha256', '')}"
try:
    supplied = base64.b64decode(claim.get("signature", ""), validate=True).decode("ascii")
except (ValueError, UnicodeDecodeError):
    fail("confirmation token is not strict base64 ASCII")
if supplied != expected:
    fail("confirmation token does not bind the exact action, target, and candidate")

receipt = {
    "schema": "lit.host_firewall.authorization-verification/v1",
    "claim_id": claim.get("claim_id"),
    "authorization_sha256": hashlib.sha256(canonical(claim)).hexdigest(),
    "valid": True,
}
sys.stdout.buffer.write(canonical(receipt))
