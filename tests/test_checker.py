"""Unit and subprocess CLI tests; all fixtures are synthetic."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from checker import validate_response

ROOT = Path(__file__).resolve().parents[1]


def example():
    return {"code": 0, "data": {"items": [
        {"id": "A", "name": "demo", "price": 10.5, "stock": 2}
    ]}}


class ValidationTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_response(example()), [])

    def test_input_is_not_mutated(self):
        payload = example()
        before = copy.deepcopy(payload)
        validate_response(payload)
        self.assertEqual(payload, before)

    def test_root_wrong_type(self):
        for value in (None, [], "x", 1):
            with self.subTest(value=value):
                self.assertEqual(validate_response(value)[0].path, "$")

    def test_missing_root_fields(self):
        self.assertEqual([x.path for x in validate_response({})], ["$.code", "$.data"])

    def test_code_boolean_is_rejected(self):
        payload = example()
        payload["code"] = False
        self.assertEqual(validate_response(payload)[0].code, "type")

    def test_nonzero_code(self):
        payload = example()
        payload["code"] = 500
        self.assertEqual(validate_response(payload)[0].code, "value")

    def test_data_wrong_type(self):
        self.assertEqual(validate_response({"code": 0, "data": None})[0].path, "$.data")

    def test_missing_items(self):
        self.assertEqual(validate_response({"code": 0, "data": {}})[0].code, "missing")

    def test_items_wrong_type(self):
        self.assertEqual(validate_response({"code": 0, "data": {"items": {}}})[0].code, "type")

    def test_empty_items_is_valid(self):
        self.assertEqual(validate_response({"code": 0, "data": {"items": []}}), [])

    def test_item_wrong_type(self):
        self.assertEqual(validate_response({"code": 0, "data": {"items": [None]}})[0].path,
                         "$.data.items[0]")

    def test_all_item_fields_required(self):
        issues = validate_response({"code": 0, "data": {"items": [{}]}})
        self.assertEqual(len(issues), 4)
        self.assertTrue(all(x.code == "missing" for x in issues))

    def test_blank_strings(self):
        payload = example()
        payload["data"]["items"][0].update(id=" ", name="\t")
        self.assertEqual([x.code for x in validate_response(payload)], ["empty", "empty"])

    def test_null_is_type_error_not_missing(self):
        payload = example()
        payload["data"]["items"][0].update(id=None, name=None, price=None, stock=None)
        self.assertEqual([x.code for x in validate_response(payload)], ["type"] * 4)

    def test_duplicate_id(self):
        payload = example()
        payload["data"]["items"].append(copy.deepcopy(payload["data"]["items"][0]))
        self.assertEqual(validate_response(payload)[0].path, "$.data.items[1].id")
        self.assertEqual(validate_response(payload)[0].code, "duplicate")

    def test_boolean_numeric_fields(self):
        payload = example()
        payload["data"]["items"][0].update(price=True, stock=False)
        self.assertEqual([x.code for x in validate_response(payload)], ["type", "type"])

    def test_negative_numeric_fields(self):
        payload = example()
        payload["data"]["items"][0].update(price=-1, stock=-1)
        self.assertEqual([x.code for x in validate_response(payload)], ["value", "value"])

    def test_zero_values_are_valid(self):
        payload = example()
        payload["data"]["items"][0].update(price=0, stock=0)
        self.assertEqual(validate_response(payload), [])

    def test_float_stock_is_rejected(self):
        payload = example()
        payload["data"]["items"][0]["stock"] = 1.0
        self.assertEqual(validate_response(payload)[0].code, "type")

    def test_nonfinite_price(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                payload = example()
                payload["data"]["items"][0]["price"] = value
                self.assertEqual(validate_response(payload)[0].code, "value")

    def test_unknown_fields_are_allowed(self):
        payload = example()
        payload["trace_id"] = "synthetic"
        payload["data"]["items"][0]["optional"] = "extra"
        self.assertEqual(validate_response(payload), [])

    def test_invalid_sample_has_six_exact_issues(self):
        payload = json.loads((ROOT / "samples/invalid.json").read_text(encoding="utf-8"))
        self.assertEqual([(x.path, x.code) for x in validate_response(payload)], [
            ("$.data.items[0].name", "empty"),
            ("$.data.items[0].price", "value"),
            ("$.data.items[0].stock", "type"),
            ("$.data.items[1].id", "duplicate"),
            ("$.data.items[1].price", "type"),
            ("$.data.items[1].stock", "missing"),
        ])


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "checker.py"), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", timeout=10)

    def test_valid_exit_zero(self):
        run = self.run_cli(ROOT / "samples/valid.json")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("PASS: 0", run.stdout)

    def test_invalid_exit_one_and_report(self):
        with tempfile.TemporaryDirectory() as folder:
            report = Path(folder) / "report.json"
            run = self.run_cli(ROOT / "samples/invalid.json", "--report", report)
            self.assertEqual(run.returncode, 1, run.stderr)
            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertFalse(data["valid"])
            self.assertEqual(data["issue_count"], 6)
            self.assertEqual(len(data["issues"]), 6)

    def test_bad_json_exit_two(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for raw in ('{', '{"x":NaN}', '{"x":Infinity}', '{"x":1,"x":2}'):
                with self.subTest(raw=raw):
                    path.write_text(raw, encoding="utf-8")
                    self.assertEqual(self.run_cli(path).returncode, 2)

    def test_missing_file_exit_two(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(self.run_cli(Path(folder) / "absent.json").returncode, 2)

    def test_input_overwrite_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            original = json.dumps(example())
            path.write_text(original, encoding="utf-8")
            self.assertEqual(self.run_cli(path, "--report", path).returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), original)

    def test_existing_report_is_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text("keep", encoding="utf-8")
            self.assertEqual(self.run_cli(ROOT / "samples/valid.json", "--report", path).returncode, 2)
            self.assertEqual(path.read_text(encoding="utf-8"), "keep")

    def test_utf8_bom_is_accepted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_text(json.dumps(example()), encoding="utf-8-sig")
            self.assertEqual(self.run_cli(path).returncode, 0)

    def test_overflowed_number_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "input.json"
            path.write_text('{"code":0,"data":{"items":[{"id":"A","name":"a",'
                            '"price":1e400,"stock":0}]}}', encoding="utf-8")
            self.assertEqual(self.run_cli(path).returncode, 1)


if __name__ == "__main__":
    unittest.main()
