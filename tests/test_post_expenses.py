import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.app import create_app


class PostExpensesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.sqlite3"
        self.app = create_app({"DATABASE": str(self.db_path), "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def post_expense(self, payload=None, key="request-1"):
        headers = {"Content-Type": "application/json"}
        if key is not None:
            headers["Idempotency-Key"] = key

        body = payload if payload is not None else {
            "amount": "123.45",
            "category": "Food",
            "description": "Lunch",
            "date": "2026-04-24",
        }
        return self.client.post("/expenses", data=json.dumps(body), headers=headers)

    def expense_count(self):
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]

    def test_creates_expense_with_valid_input(self):
        response = self.post_expense()

        self.assertEqual(response.status_code, 201)
        data = response.get_json()
        self.assertEqual(data["id"], 1)
        self.assertEqual(data["amount"], "123.45")
        self.assertEqual(data["amount_paise"], 12345)
        self.assertEqual(data["category"], "Food")
        self.assertEqual(data["description"], "Lunch")
        self.assertEqual(data["date"], "2026-04-24")
        self.assertRegex(data["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_rejects_invalid_amounts(self):
        invalid_amounts = ["0", "-1.00", "abc", "12.345", "1000000000.01"]

        for amount in invalid_amounts:
            with self.subTest(amount=amount):
                response = self.post_expense(
                    {
                        "amount": amount,
                        "category": "Food",
                        "description": "Lunch",
                        "date": "2026-04-24",
                    },
                    key=f"invalid-{amount}",
                )

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"], "VALIDATION_ERROR")

    def test_rejects_missing_required_fields(self):
        base_payload = {
            "amount": "12.34",
            "category": "Food",
            "description": "Lunch",
            "date": "2026-04-24",
        }

        for field in base_payload:
            with self.subTest(field=field):
                payload = dict(base_payload)
                payload.pop(field)
                response = self.post_expense(payload, key=f"missing-{field}")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"], "VALIDATION_ERROR")

    def test_rejects_blank_or_null_text_fields(self):
        invalid_payloads = [
            {
                "amount": "12.34",
                "category": "   ",
                "description": "Lunch",
                "date": "2026-04-24",
            },
            {
                "amount": "12.34",
                "category": None,
                "description": "Lunch",
                "date": "2026-04-24",
            },
            {
                "amount": "12.34",
                "category": "Food",
                "description": "",
                "date": "2026-04-24",
            },
            {
                "amount": "12.34",
                "category": "Food",
                "description": None,
                "date": "2026-04-24",
            },
        ]

        for index, payload in enumerate(invalid_payloads):
            with self.subTest(index=index):
                response = self.post_expense(payload, key=f"invalid-text-{index}")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"], "VALIDATION_ERROR")

    def test_rejects_missing_idempotency_key(self):
        response = self.post_expense(key=None)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "VALIDATION_ERROR")

    def test_replay_with_same_key_returns_same_expense_without_duplicate(self):
        first = self.post_expense(key="retry-key")
        second = self.post_expense(key="retry-key")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.get_json(), second.get_json())
        self.assertEqual(self.expense_count(), 1)

    def test_same_key_with_different_payload_returns_conflict(self):
        first = self.post_expense(key="conflict-key")
        second = self.post_expense(
            {
                "amount": "999.00",
                "category": "Food",
                "description": "Lunch",
                "date": "2026-04-24",
            },
            key="conflict-key",
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()["error"], "IDEMPOTENCY_KEY_CONFLICT")
        self.assertEqual(self.expense_count(), 1)

    def test_date_validation(self):
        valid = self.post_expense(key="valid-date")
        invalid = self.post_expense(
            {
                "amount": "12.34",
                "category": "Food",
                "description": "Lunch",
                "date": "2026-02-30",
            },
            key="invalid-date",
        )

        self.assertEqual(valid.status_code, 201)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()["error"], "VALIDATION_ERROR")


if __name__ == "__main__":
    unittest.main()
