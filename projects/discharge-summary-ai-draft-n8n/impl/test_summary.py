import unittest
from summary_pipeline import build_draft, doctor_sign, mock_llm_summarize, read_clob_chunks, ITEMS

FULL = {i: f"{i} 원문" for i in ITEMS}


class T(unittest.TestCase):
    def test_no_hallucination_on_empty(self):
        self.assertIsNone(mock_llm_summarize("초진", ""))
        self.assertIsNone(mock_llm_summarize("초진", None))

    def test_clob_merge(self):
        note = "x" * 2500
        self.assertEqual(read_clob_chunks(note, 1000), note)

    def test_draft_not_signed(self):
        d = build_draft("P1", FULL)
        self.assertEqual(d["status"], "DRAFT")
        self.assertFalse(d["signed"])

    def test_skip_when_no_sources(self):
        d = build_draft("P1", {i: "" for i in ITEMS})
        self.assertEqual(d["status"], "SKIP")

    def test_human_review_gate(self):
        d = build_draft("P1", FULL)
        final = doctor_sign(d)
        self.assertEqual(final["status"], "FINAL")
        self.assertTrue(final["signed"])

    def test_cannot_sign_non_draft(self):
        with self.assertRaises(ValueError):
            doctor_sign({"status": "SKIP"})


if __name__ == "__main__":
    unittest.main()
