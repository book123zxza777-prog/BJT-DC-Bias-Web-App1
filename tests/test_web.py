import unittest

from app import app


class TestIndexPage(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe",
                     "unit_r1", "unit_r2", "unit_rc", "unit_re"):
            self.assertIn(f'name="{name}"', html)
        self.assertIn('value="12"', html)      # ค่าเริ่มต้น VCC
        self.assertIn('value="100"', html)     # ค่าเริ่มต้น R1
        self.assertNotIn("ผลการคำนวณ", html)   # ยังไม่แสดงผลลัพธ์


if __name__ == "__main__":
    unittest.main()
