import unittest
from automation_core import Automation, make_history, map_expense_to_variables, MemoryHistory, STEPS

EXP = {"account_code": "5100", "amount": 30000, "approval_line": ["mgr", "dir"], "ref_doc": "RCPT-1"}


class T(unittest.TestCase):
    def setUp(self):
        self.auto = Automation(make_history(redis_available=False))

    def test_redis_fallback_to_memory(self):
        self.assertIsInstance(make_history(False), MemoryHistory)

    def test_mapping(self):
        v = map_expense_to_variables(EXP)
        self.assertEqual(v["ACCOUNT_CODE"], "5100")
        self.assertEqual(v["APPROVAL_LINE"], "mgr,dir")

    def test_happy_path_all_steps(self):
        self.auto.start(EXP)
        t = self.auto.run_next()
        self.assertEqual(t.status, "success")
        self.assertEqual(t.events, STEPS[1:])

    def test_failure_visibility(self):
        self.auto.start(EXP)
        t = self.auto.run_next(fail_at="approval_line")
        self.assertEqual(t.status, "failed")
        self.assertIn("approval_line", t.error)

    def test_history_recorded(self):
        tid = self.auto.start(EXP)
        self.auto.run_next()
        self.assertEqual(self.auto.history.get(tid)["status"], "success")


if __name__ == "__main__":
    unittest.main()
