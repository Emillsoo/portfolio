import unittest
from meeting_logic import (
    Member, Attendee, get_meeting_type, suggest_report_order,
    get_next_secretary, record_secretary_served,
)


class MeetingType(unittest.TestCase):
    def test_monday_weekly(self):
        self.assertEqual(get_meeting_type("2026-07-20"), "weekly")  # 월

    def test_other_daily(self):
        self.assertEqual(get_meeting_type("2026-07-21"), "daily")   # 화


class ReportOrder(unittest.TestCase):
    def setUp(self):
        self.m = {t: Member(i, t, t) for i, t in enumerate(["의장", "과장", "사원", "계장"], 1)}

    def test_chair_excluded(self):
        att = [Attendee(self.m["의장"]), Attendee(self.m["사원"])]
        out = suggest_report_order(att)
        chair = next(a for a in out if a.member.title == "의장")
        self.assertEqual(chair.report_order, -1)

    def test_inverse_rank_order(self):
        att = [Attendee(self.m["과장"]), Attendee(self.m["사원"]), Attendee(self.m["계장"])]
        out = [a for a in suggest_report_order(att) if a.report_order is not None and a.report_order >= 0]
        titles = [a.member.title for a in sorted(out, key=lambda a: a.report_order)]
        self.assertEqual(titles, ["사원", "계장", "과장"])

    def test_absent_last(self):
        att = [Attendee(self.m["사원"], is_present=False), Attendee(self.m["과장"], is_present=True)]
        out = suggest_report_order(att)
        present = next(a for a in out if a.member.title == "과장")
        absent = next(a for a in out if a.member.title == "사원")
        self.assertLess(present.report_order, absent.report_order)


class Secretary(unittest.TestCase):
    def setUp(self):
        self.members = [
            Member(1, "A", "의장"), Member(2, "B", "실장"),
            Member(3, "C", "과장"), Member(4, "D", "사원"),
        ]

    def test_excludes_chair_and_director(self):
        s = get_next_secretary(self.members, {3: "2026-07-01", 4: "2026-07-02"})
        self.assertNotIn(s.title, {"의장", "실장"})

    def test_no_history_first(self):
        # C는 이력 있음, D는 없음 → D 우선
        s = get_next_secretary(self.members, {3: "2026-07-01"})
        self.assertEqual(s.id, 4)

    def test_least_recent_chosen(self):
        s = get_next_secretary(self.members, {3: "2026-07-01", 4: "2026-07-10"})
        self.assertEqual(s.id, 3)  # 더 오래 전

    def test_record_updates(self):
        hist: dict[int, str] = {}
        record_secretary_served(hist, 4, "2026-07-20")
        self.assertEqual(hist[4], "2026-07-20")

    def test_none_when_no_candidates(self):
        only = [Member(1, "A", "의장"), Member(2, "B", "실장")]
        self.assertIsNone(get_next_secretary(only, {}))


if __name__ == "__main__":
    unittest.main()
