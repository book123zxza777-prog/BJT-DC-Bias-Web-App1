import re
import unittest

from app import app


def visible_text(html: str) -> str:
    """Rendered text of the page, tags removed and whitespace collapsed."""
    without_tags = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+", " ", without_tags)


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


VALID = {
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "beta": "100", "vbe": "0.70",
    "unit_r1": "kohm", "unit_r2": "kohm", "unit_rc": "kohm", "unit_re": "kohm",
}


class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_valid_post_shows_computed_results(self):
        res = self.client.post("/calculate", data=VALID)
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        for expected in ("1.942", "1.242", "9.294", "8.052", "1.230", "18.03"):
            self.assertIn(expected, html)
        self.assertIn("Active", html)

    def test_form_echoes_submitted_values(self):
        data = dict(VALID, r1="99", unit_r1="ohm")
        html = self.client.post("/calculate", data=data).get_data(as_text=True)
        self.assertIn('value="99"', html)
        self.assertIn('value="ohm" selected', html)

    def test_invalid_resistor_returns_400(self):
        res = self.client.post("/calculate", data=dict(VALID, r1="0"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("มากกว่า 0", res.get_data(as_text=True))

    def test_non_numeric_returns_400(self):
        res = self.client.post("/calculate", data=dict(VALID, vcc="abc"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("ตัวเลข", res.get_data(as_text=True))

    def test_empty_form_returns_400_with_errors(self):
        res = self.client.post("/calculate", data={})
        self.assertEqual(res.status_code, 400)
        html = res.get_data(as_text=True)
        self.assertIn("ตัวเลข", html)

    def test_empty_form_reports_every_field(self):
        html = self.client.post("/calculate", data={}).get_data(as_text=True)
        # 7 ช่องตัวเลข + 4 ช่องหน่วย = 11 ข้อความ ต้องอยู่ข้างช่องของตัวเอง
        self.assertEqual(html.count('class="field-error"'), 11)
        summary = visible_text(html)
        for label in ("VCC", "R1", "R2", "RC", "RE", "β", "VBE",
                      "หน่วย R1", "หน่วย R2", "หน่วย RC", "หน่วย RE"):
            self.assertIn(f"{label}: กรุณากรอกตัวเลข" if label in ("VCC", "R1", "R2", "RC", "RE", "β", "VBE")
                          else f"{label}: หน่วยไม่ถูกต้อง", summary)

    def test_error_is_shown_beside_its_own_field(self):
        html = self.client.post("/calculate", data=dict(VALID, vcc="abc")).get_data(as_text=True)
        self.assertEqual(html.count('class="field-error"'), 1)
        self.assertIn("VCC: กรุณากรอกตัวเลข", visible_text(html))

    def test_nan_input_returns_400(self):
        res = self.client.post("/calculate", data=dict(VALID, vcc="nan"))
        self.assertEqual(res.status_code, 400)
        self.assertIn("ขอบเขตจำกัด", res.get_data(as_text=True))

    def test_kohm_and_ohm_forms_agree(self):
        as_kohm = self.client.post(
            "/calculate", data=dict(VALID, r1="100", unit_r1="kohm")
        ).get_data(as_text=True)
        as_ohm = self.client.post(
            "/calculate", data=dict(VALID, r1="100000", unit_r1="ohm")
        ).get_data(as_text=True)
        for value in ("1.942", "9.294", "8.052", "1.230"):
            self.assertIn(value, as_kohm)
            self.assertIn(value, as_ohm)

    def test_invalid_unit_returns_400(self):
        data = dict(VALID, unit_r1="megohm")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 400)
        self.assertIn("หน่วย", res.get_data(as_text=True))

    def test_cutoff_shows_warning(self):
        data = dict(VALID, r2="1")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Cutoff", res.get_data(as_text=True))

    def test_saturation_shows_warning(self):
        data = dict(VALID, rc="20")
        res = self.client.post("/calculate", data=data)
        self.assertEqual(res.status_code, 200)
        self.assertIn("Saturation", res.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
