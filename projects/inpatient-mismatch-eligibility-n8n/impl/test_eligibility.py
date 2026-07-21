"""가상 재구현 테스트 — 3중 가드 + 라벨 + 시트 보존 가드."""
import unittest
from eligibility_check import (
    NhicResult, InHouse, find_mismatches, normalize_type,
    latest_per_patient, to_label, tabs_to_delete,
)


class Guards(unittest.TestCase):
    def test_guard1_unreceived_excluded(self):
        self.assertEqual(find_mismatches([InHouse("H01", "P1", "N")], []), [])

    def test_guard1_none_type_excluded(self):
        n = [NhicResult("H01", "P1", None, False, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches([InHouse("H01", "P1", "N")], n), [])

    def test_guard2_cross_institution_no_match(self):
        n = [NhicResult("H01", "P1", "G", False, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches([InHouse("H02", "P1", "N")], n), [])

    def test_guard3_low_income_disabled_normalized(self):
        self.assertEqual(normalize_type("E", True), "F")
        n = [NhicResult("H01", "P1", "E", True, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches([InHouse("H01", "P1", "E")], n), [])


class Detection(unittest.TestCase):
    def test_real_mismatch_with_labels(self):
        n = [NhicResult("H01", "P3", "G", False, "2026-07-20T09:00:00")]
        r = find_mismatches([InHouse("H01", "P3", "N")], n)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["in_house_label"], "건강보험")
        self.assertEqual(r[0]["nhic_label"], "의료급여")

    def test_latest_selected(self):
        n = [
            NhicResult("H01", "P3", "N", False, "2026-07-19T09:00:00"),
            NhicResult("H01", "P3", "G", False, "2026-07-20T09:00:00"),
        ]
        self.assertEqual(latest_per_patient(n)[("H01", "P3")].insurance_type, "G")

    def test_label_unknown(self):
        self.assertEqual(to_label(None), "미확인")
        self.assertEqual(to_label("F"), "차상위(장애인)")


class SheetGuard(unittest.TestCase):
    def test_non_pattern_tab_protected(self):
        out = tabs_to_delete(["요약", "설정", "2026-06-01"], "2026-07-20")
        self.assertNotIn("요약", out)
        self.assertNotIn("설정", out)

    def test_today_protected(self):
        out = tabs_to_delete(["2026-07-20"], "2026-07-20")
        self.assertEqual(out, [])

    def test_keeps_at_least_one(self):
        # 전부 오래됨 -> 가장 최신 1개는 보존
        out = tabs_to_delete(["2026-01-01", "2026-01-02", "2026-01-03"], "2026-07-20")
        self.assertNotIn("2026-01-03", out)
        self.assertEqual(len(out), 2)

    def test_within_retention_kept(self):
        out = tabs_to_delete(["2026-07-18", "2026-07-01"], "2026-07-20", keep_days=7)
        self.assertIn("2026-07-01", out)
        self.assertNotIn("2026-07-18", out)


if __name__ == "__main__":
    unittest.main()
