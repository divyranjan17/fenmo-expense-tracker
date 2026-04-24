import json
import tempfile
import unittest
from pathlib import Path

from backend.app import create_app


class GetExpensesTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.sqlite3"
        self.app = create_app({"DATABASE": str(self.db_path), "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def post_expense(self, amount, category, description, expense_date, key):
        return self.client.post(
            "/expenses",
            data=json.dumps(
                {
                    "amount": amount,
                    "category": category,
                    "description": description,
                    "date": expense_date,
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": key,
            },
        )

    def seed_expense(self, amount, category, description, expense_date, key):
        response = self.post_expense(amount, category, description, expense_date, key)
        self.assertEqual(response.status_code, 201)
        return response.get_json()

    def test_empty_database_returns_empty_list_and_zero_total(self):
        response = self.client.get("/expenses")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {
                "expenses": [],
                "total": "0.00",
                "total_paise": 0,
            },
        )

    def test_returns_created_expenses(self):
        first = self.seed_expense("12.34", "Food", "Lunch", "2026-04-23", "expense-1")
        second = self.seed_expense("45.67", "Travel", "Taxi", "2026-04-24", "expense-2")

        response = self.client.get("/expenses")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["expenses"], [second, first])
        self.assertEqual(data["total"], "58.01")
        self.assertEqual(data["total_paise"], 5801)

    def test_filters_by_category_case_insensitively(self):
        food = self.seed_expense("10.00", "Food", "Breakfast", "2026-04-24", "expense-1")
        self.seed_expense("20.00", "Travel", "Train", "2026-04-24", "expense-2")
        groceries = self.seed_expense("30.00", "food", "Groceries", "2026-04-23", "expense-3")

        response = self.client.get("/expenses?category= FOOD ")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["expenses"], [food, groceries])
        self.assertEqual(data["total"], "40.00")
        self.assertEqual(data["total_paise"], 4000)

    def test_rejects_blank_category_filter(self):
        response = self.client.get("/expenses?category=%20%20%20")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                "error": "VALIDATION_ERROR",
                "message": "Invalid input: category filter cannot be blank",
            },
        )

    def test_sorts_by_date_desc_when_requested(self):
        oldest = self.seed_expense("10.00", "Food", "Oldest", "2026-04-22", "expense-1")
        newest = self.seed_expense("20.00", "Food", "Newest", "2026-04-24", "expense-2")
        middle = self.seed_expense("30.00", "Food", "Middle", "2026-04-23", "expense-3")

        response = self.client.get("/expenses?sort=date_desc")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["expenses"], [newest, middle, oldest])
        self.assertEqual(data["total"], "60.00")
        self.assertEqual(data["total_paise"], 6000)

    def test_sorts_same_date_rows_deterministically(self):
        first = self.seed_expense("10.00", "Food", "First", "2026-04-24", "expense-1")
        second = self.seed_expense("20.00", "Food", "Second", "2026-04-24", "expense-2")
        third = self.seed_expense("30.00", "Food", "Third", "2026-04-24", "expense-3")

        response = self.client.get("/expenses?sort=date_desc")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["expenses"], [third, second, first])

    def test_rejects_invalid_sort_value(self):
        response = self.client.get("/expenses?sort=amount_desc")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {
                "error": "VALIDATION_ERROR",
                "message": "Invalid input: sort must be date_desc",
            },
        )

    def test_total_reflects_filtered_rows_only(self):
        self.seed_expense("10.00", "Food", "Breakfast", "2026-04-24", "expense-1")
        self.seed_expense("20.25", "Travel", "Train", "2026-04-24", "expense-2")
        self.seed_expense("30.50", "Food", "Dinner", "2026-04-23", "expense-3")

        response = self.client.get("/expenses?category=Food")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["expenses"]), 2)
        self.assertEqual(data["total"], "40.50")
        self.assertEqual(data["total_paise"], 4050)


if __name__ == "__main__":
    unittest.main()
