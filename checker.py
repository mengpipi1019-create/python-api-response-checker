"""Validate a simulated product-list response. Python standard library only."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import sys


@dataclass(frozen=True)
class Issue:
    path: str
    code: str
    message: str


def validate_response(payload: object) -> list[Issue]:
    """Collect schema/business-rule violations without modifying the input."""
    issues: list[Issue] = []

    def add(path: str, code: str, message: str) -> None:
        issues.append(Issue(path, code, message))

    def required(obj: dict, key: str, path: str) -> bool:
        if key not in obj:
            add(path, "missing", "required field is missing")
            return False
        return True

    if not isinstance(payload, dict):
        return [Issue("$", "type", "expected an object")]
    if required(payload, "code", "$.code"):
        if type(payload["code"]) is not int:
            add("$.code", "type", "expected an integer, not a boolean")
        elif payload["code"] != 0:
            add("$.code", "value", "expected success code 0")
    if not required(payload, "data", "$.data"):
        return issues
    data = payload["data"]
    if not isinstance(data, dict):
        add("$.data", "type", "expected an object")
        return issues
    if not required(data, "items", "$.data.items"):
        return issues
    items = data["items"]
    if not isinstance(items, list):
        add("$.data.items", "type", "expected an array")
        return issues

    seen_ids: set[str] = set()
    for index, item in enumerate(items):
        base = f"$.data.items[{index}]"
        if not isinstance(item, dict):
            add(base, "type", "expected an object")
            continue
        for key in ("id", "name"):
            path = f"{base}.{key}"
            if not required(item, key, path):
                continue
            value = item[key]
            if not isinstance(value, str):
                add(path, "type", "expected a string")
            elif not value.strip():
                add(path, "empty", "must not be blank")
            elif key == "id":
                if value in seen_ids:
                    add(path, "duplicate", "product id must be unique")
                seen_ids.add(value)
        if required(item, "price", f"{base}.price"):
            price = item["price"]
            if type(price) not in (int, float):
                add(f"{base}.price", "type", "expected a number, not a boolean")
            elif isinstance(price, float) and not math.isfinite(price):
                add(f"{base}.price", "value", "must be finite")
            elif price < 0:
                add(f"{base}.price", "value", "must be non-negative")
        if required(item, "stock", f"{base}.stock"):
            stock = item["stock"]
            if type(stock) is not int:
                add(f"{base}.stock", "type", "expected an integer, not a boolean")
            elif stock < 0:
                add(f"{base}.stock", "value", "must be non-negative")
    return issues


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON number: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 JSON response file")
    parser.add_argument("--report", type=Path, help="create a NEW JSON report file")
    args = parser.parse_args(argv)
    try:
        # Do not overwrite a source file or an existing report.
        if args.report is not None and args.report.resolve() == args.input.resolve():
            raise ValueError("report path must differ from input path")
        payload = json.loads(
            args.input.read_text(encoding="utf-8-sig"),
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
        issues = validate_response(payload)
        report = {
            "schema": "simulated-product-list/v1",
            "valid": not issues,
            "issue_count": len(issues),
            "issues": [asdict(issue) for issue in issues],
        }
        if args.report is not None:
            # Exclusive create makes repeated runs safe for existing files.
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(f"{'PASS' if not issues else 'FAIL'}: {len(issues)} issue(s)")
        for issue in issues:
            print(f"{issue.path} [{issue.code}] {issue.message}")
        return 1 if issues else 0
    except (OSError, ValueError, RecursionError) as error:
        print(f"INPUT/OUTPUT ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
