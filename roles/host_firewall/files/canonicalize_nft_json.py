#!/usr/bin/env python3
"""Canonicalize one nftables JSON table without weakening its semantic boundary."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from typing import Any


class DuplicateKeyError(ValueError):
    """Raised when an object contains duplicate JSON keys."""


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def normalize(value: Any, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key in sorted(value):
            if key == "handle":
                continue
            if parent_key == "counter" and key in {"bytes", "packets"}:
                continue
            normalized[key] = normalize(value[key], key)
        return normalized
    if isinstance(value, list):
        normalized_list = [normalize(item, parent_key) for item in value]
        if parent_key in {"elem", "set"}:
            return sorted(
                normalized_list,
                key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
            )
        return normalized_list
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--family", required=True)
    parser.add_argument("--table", required=True)
    parser.add_argument(
        "--stdin-base64",
        action="store_true",
        help="Decode strict RFC 4648 base64 from stdin before parsing JSON.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw_document = sys.stdin.buffer.read()
        if args.stdin_base64:
            raw_document = base64.b64decode(raw_document, validate=True)
        document = json.loads(
            raw_document.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, ValueError) as exc:
        print(f"invalid nftables JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(document, dict) or set(document) != {"nftables"}:
        print("nftables JSON must contain only the top-level nftables array", file=sys.stderr)
        return 2
    if not isinstance(document["nftables"], list):
        print("nftables must be an array", file=sys.stderr)
        return 2

    statements: list[dict[str, Any]] = []
    matching_tables = 0
    for statement in document["nftables"]:
        if not isinstance(statement, dict) or len(statement) != 1:
            print("every nftables statement must be a single-key object", file=sys.stderr)
            return 2
        statement_type, payload = next(iter(statement.items()))
        if statement_type == "metainfo":
            continue
        if not isinstance(payload, dict):
            print(f"{statement_type} payload must be an object", file=sys.stderr)
            return 2
        if payload.get("family") != args.family or payload.get("table", payload.get("name")) != args.table:
            print("readback escaped the approved family/table boundary", file=sys.stderr)
            return 2
        if statement_type == "table":
            matching_tables += 1
            if payload.get("name") != args.table:
                print("table identity does not match the requested table", file=sys.stderr)
                return 2
        statements.append({statement_type: payload})

    if matching_tables != 1:
        print("readback must contain exactly one matching table declaration", file=sys.stderr)
        return 2

    canonical = normalize({"nftables": statements})
    sys.stdout.write(json.dumps(canonical, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
