import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app import create_app


class FrontendServingTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "test.sqlite3"
        self.app = create_app({"DATABASE": str(self.db_path), "TESTING": True})
        self.client = self.app.test_client()

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_root_serves_frontend_html(self):
        response = self.client.get("/")
        try:
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response.headers["Content-Type"])
            self.assertIn(b"Expense Tracker", response.get_data())
        finally:
            response.close()


if __name__ == "__main__":
    unittest.main()
