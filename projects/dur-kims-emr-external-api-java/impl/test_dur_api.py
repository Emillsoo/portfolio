import unittest
from dur_api import build_app


class Routing(unittest.TestCase):
    def setUp(self):
        self.app = build_app()

    def test_unknown_submit_id(self):
        r = self.app.dispatch("NOPE", {})
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, 404)

    def test_invalid_rrn_blocked(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "123", "drugs": ["DRUG_A"]})
        self.assertFalse(r.ok)
        self.assertEqual(r.error_code, 400)

    def test_rrn_not_leaked(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "badrrn", "drugs": []})
        self.assertNotIn("badrrn", r.message)


class Dur(unittest.TestCase):
    def setUp(self):
        self.app = build_app()

    def test_contraindication_detected(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "900101-1234567", "drugs": ["DRUG_A", "DRUG_B"]})
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(r.data["results"][0]["grade"], "병용금기")

    def test_multiple_interactions(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "900101-1234567", "drugs": ["DRUG_A", "DRUG_B", "DRUG_C"]})
        self.assertEqual(r.data["count"], 2)

    def test_null_defense(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "900101-1234567", "drugs": None})
        self.assertEqual(r.data["count"], 0)

    def test_hira_duplicate_send_guard(self):
        p = {"rrn": "900101-1234567", "drugs": ["DRUG_A", "DRUG_B"]}
        r1 = self.app.dispatch("DEMO_DUR_SCREEN", p)
        r2 = self.app.dispatch("DEMO_DUR_SCREEN", p)  # 같은 요청 재호출
        self.assertTrue(r1.data["hira_reported"])
        self.assertFalse(r2.data["hira_reported"])   # 중복 전송 차단

    def test_no_report_flag(self):
        r = self.app.dispatch("DEMO_DUR_SCREEN", {"rrn": "900101-1234567", "drugs": ["DRUG_A", "DRUG_B"], "report": False})
        self.assertFalse(r.data["hira_reported"])


class Kims(unittest.TestCase):
    def setUp(self):
        self.app = build_app()

    def test_med_history(self):
        r = self.app.dispatch("DEMO_MED_HISTORY", {"rrn": "900101-1234567"})
        self.assertEqual(r.data["count"], 2)

    def test_audit_recorded_without_rrn(self):
        app = build_app()
        app.dispatch("DEMO_DUR_SCREEN", {"rrn": "900101-1234567", "drugs": ["DRUG_A"]})
        audit = app.mgr.dao.audit
        self.assertEqual(len(audit), 1)
        # 감사로그에 원식별자(주민번호)가 남지 않음
        self.assertNotIn("900101", audit[0]["rid"])


if __name__ == "__main__":
    unittest.main()
