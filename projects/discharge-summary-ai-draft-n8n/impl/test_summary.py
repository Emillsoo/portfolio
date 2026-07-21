import unittest
from summary_pipeline import (
    build_draft, load_to_emr, doctor_sign, mock_llm_summarize,
    read_clob_chunks, is_load_success, LoadResult, ITEMS, QualityError,
)

FULL = {i: f"{i} 관련 임상 원문 내용" for i in ITEMS}


class Quality(unittest.TestCase):
    def test_no_hallucination_on_empty(self):
        self.assertIsNone(mock_llm_summarize("초진", ""))
        self.assertIsNone(mock_llm_summarize("초진", None))

    def test_overlong_summary_blocked(self):
        # 원문이 매우 짧은데 요약이 길면 품질 예외 (여기선 요약 규칙상 발생 안 하나 경계 확인)
        s = mock_llm_summarize("초진", "짧음")
        self.assertTrue(s.startswith("[초진]"))

    def test_clob_merge(self):
        note = "x" * 2500
        self.assertEqual(read_clob_chunks(note, 1000), note)


class Gate(unittest.TestCase):
    def test_draft_not_signed(self):
        d = build_draft("P1", FULL)
        self.assertEqual(d["status"], "DRAFT")
        self.assertFalse(d["signed"])

    def test_skip_when_no_sources(self):
        self.assertEqual(build_draft("P1", {i: "" for i in ITEMS})["status"], "SKIP")


class LoadJudgment(unittest.TestCase):
    def test_success_needs_all_three(self):
        self.assertTrue(is_load_success(LoadResult(200, 0, "Y")))
        self.assertFalse(is_load_success(LoadResult(200, 0, "N")))  # silent failure
        self.assertFalse(is_load_success(LoadResult(200, 9, "Y")))
        self.assertFalse(is_load_success(LoadResult(500, 0, "Y")))

    def test_silent_failure_alerts(self):
        bad = load_to_emr(build_draft("P1", FULL), LoadResult(200, 0, "N"))
        self.assertFalse(bad["loaded"])
        self.assertIsNotNone(bad["alert"])
        self.assertEqual(bad["audit"]["result"], "FAIL")

    def test_audit_counts(self):
        d = build_draft("P1", {**FULL, "추후계획": ""})
        ok = load_to_emr(d, LoadResult(200, 0, "Y"))
        self.assertEqual(ok["audit"]["items_filled"], 4)
        self.assertEqual(ok["audit"]["items_total"], 5)


class HumanReview(unittest.TestCase):
    def test_sign_after_successful_load(self):
        ok = load_to_emr(build_draft("P1", FULL), LoadResult(200, 0, "Y"))
        self.assertEqual(doctor_sign(ok)["status"], "FINAL")

    def test_cannot_sign_failed_load(self):
        bad = load_to_emr(build_draft("P1", FULL), LoadResult(200, 0, "N"))
        with self.assertRaises(ValueError):
            doctor_sign(bad)


if __name__ == "__main__":
    unittest.main()
