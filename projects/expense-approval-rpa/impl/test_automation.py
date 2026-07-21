import unittest
from automation_core import (
    Automation, make_history, map_expense_to_variables, MemoryHistory, STEPS,
)

EXP = {"account_code": "5100", "amount": 30000, "approval_line": ["mgr", "dir"], "ref_doc": "RCPT-1"}


class FailingRedis:
    def ping(self):
        raise ConnectionError("redis down")


class WorkingRedis(MemoryHistory):
    def ping(self):
        return True


class Fallback(unittest.TestCase):
    def test_no_client_uses_memory(self):
        self.assertIsInstance(make_history(None), MemoryHistory)

    def test_redis_down_falls_back(self):
        self.assertIsInstance(make_history(FailingRedis()), MemoryHistory)

    def test_healthy_redis_used(self):
        r = WorkingRedis()
        self.assertIs(make_history(r), r)


class Mapping(unittest.TestCase):
    def test_mapping(self):
        v = map_expense_to_variables(EXP)
        self.assertEqual(v["ACCOUNT_CODE"], "5100")
        self.assertEqual(v["APPROVAL_LINE"], "mgr,dir")

    def test_missing_account_code(self):
        with self.assertRaises(ValueError):
            map_expense_to_variables({"amount": 1})


class Run(unittest.TestCase):
    def setUp(self):
        self.auto = Automation(make_history(None))

    def test_happy_path_all_steps(self):
        self.auto.start(EXP)
        t = self.auto.run_next()
        self.assertEqual(t.status, "success")
        self.assertEqual(t.events, STEPS)

    def test_failure_visibility(self):
        self.auto.start(EXP)
        t = self.auto.run_next(fail_at="approval_line")
        self.assertEqual(t.status, "failed")
        self.assertIn("approval_line", t.error)

    def test_timeout(self):
        self.auto.start(EXP)
        t = self.auto.run_next(timeout_at="iframe_switch")
        self.assertEqual(t.status, "failed")
        self.assertIn("timeout", t.error)

    def test_cancel_before_run(self):
        tid = self.auto.start(EXP)
        self.assertTrue(self.auto.cancel(tid))
        t = self.auto.run_next()
        self.assertEqual(t.status, "cancelled")

    def test_history_recorded(self):
        tid = self.auto.start(EXP)
        self.auto.run_next()
        self.assertEqual(self.auto.history.get(tid)["status"], "success")


if __name__ == "__main__":
    unittest.main()
