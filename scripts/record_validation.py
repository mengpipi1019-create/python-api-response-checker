"""Regenerate local evidence using only the Python standard library."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)


def main():
    evidence = ROOT / "evidence"
    evidence.mkdir(exist_ok=True)
    tests = run("-m", "unittest", "discover", "-s", "tests", "-v")
    valid = run("checker.py", "samples/valid.json")
    invalid = run("checker.py", "samples/invalid.json")
    for name, result in (("unittest", tests), ("valid", valid), ("invalid", invalid)):
        (evidence / f"{name}.txt").write_text(result.stdout + result.stderr, encoding="utf-8")
    files = ["checker.py", "tests/test_checker.py", "samples/valid.json", "samples/invalid.json",
             "scripts/record_validation.py"]
    passed = tests.returncode == 0 and valid.returncode == 0 and invalid.returncode == 1
    summary = {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "all_expected_exit_codes": passed,
        "exit_codes": {"tests": tests.returncode, "valid": valid.returncode, "invalid": invalid.returncode},
        "sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files},
        "scope": "Synthetic local fixtures only; not production/API integration results.",
    }
    (evidence / "validation.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
