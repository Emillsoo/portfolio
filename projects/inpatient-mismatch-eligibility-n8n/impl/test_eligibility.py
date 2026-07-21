"""가상 재구현 테스트 — 3중 가드 검증 (표준 unittest)."""
import unittest
from eligibility_check import NhicResult, InHouse, find_mismatches, normalize_type, latest_per_patient


class T(unittest.TestCase):
    def test_guard1_unreceived_excluded(self):
        h = [InHouse("H01", "P1", "N")]
        self.assertEqual(find_mismatches(h, []), [])  # 공단 결과 없음 -> 제외

    def test_guard1_none_type_excluded(self):
        h = [InHouse("H01", "P1", "N")]
        n = [NhicResult("H01", "P1", None, False, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches(h, n), [])

    def test_guard2_cross_institution_no_match(self):
        h = [InHouse("H02", "P1", "N")]
        n = [NhicResult("H01", "P1", "G", False, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches(h, n), [])  # 기관 다르면 비교 안 함

    def test_guard3_low_income_disabled_normalized(self):
        self.assertEqual(normalize_type("E", True), "F")
        h = [InHouse("H01", "P1", "E")]
        n = [NhicResult("H01", "P1", "E", True, "2026-07-20T09:00:00")]
        self.assertEqual(find_mismatches(h, n), [])  # 표준화 후 일치

    def test_real_mismatch_detected(self):
        h = [InHouse("H01", "P3", "N")]
        n = [NhicResult("H01", "P3", "G", False, "2026-07-20T09:00:00")]
        r = find_mismatches(h, n)
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]["in_house"], "N")
        self.assertEqual(r[0]["nhic"], "G")

    def test_latest_selected(self):
        n = [
            NhicResult("H01", "P3", "N", False, "2026-07-19T09:00:00"),
            NhicResult("H01", "P3", "G", False, "2026-07-20T09:00:00"),
        ]
        latest = latest_per_patient(n)
        self.assertEqual(latest[("H01", "P3")].insurance_type, "G")


if __name__ == "__main__":
    unittest.main()
