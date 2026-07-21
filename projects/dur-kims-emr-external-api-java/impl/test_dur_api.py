import unittest
from dur_api import build_app


class T(unittest.TestCase):
    def setUp(self):
        self.app = build_app()

    def test_invalid_rrn_blocked(self):
        r = self.app.req_dur_screen("123", ["DRUG_A"])
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, 400)

    def test_rrn_not_leaked_in_message(self):
        r = self.app.req_dur_screen("badrrn", ["DRUG_A"])
        self.assertNotIn("badrrn", r.message)

    def test_contraindication_detected(self):
        r = self.app.req_dur_screen("900101-1234567", ["DRUG_A", "DRUG_B"])
        self.assertTrue(r.ok)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["grade"], "병용금기")

    def test_null_defense(self):
        r = self.app.req_dur_screen("900101-1234567", None)
        self.assertTrue(r.ok)
        self.assertEqual(r.data["count"], 0)

    def test_multiple_interactions(self):
        r = self.app.req_dur_screen("900101-1234567", ["DRUG_A", "DRUG_B", "DRUG_C"])
        self.assertEqual(r.data["count"], 2)


if __name__ == "__main__":
    unittest.main()
