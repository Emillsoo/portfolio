"""가상 재구현: 지출결의서 자동화 백엔드 코어 (외부 의존 없음).

실제 그룹웨어/계정/Selenium/Robot Framework 코드는 포함하지 않는다. 운영 서비스의
핵심 설계만 순수 파이썬으로 재현한다.

재현 범위
  - 작업 큐(TaskQueue) + 상태 전이(pending→running→success/failed/cancelled)
  - Redis 이력(없으면 메모리 폴백) — graceful degradation
  - 진행 6단계 이벤트 스트림        (원본: RF stdout 파싱 → WebSocket 진행률)
  - 데이터 매핑                     (지출 데이터 → RPA 변수)
  - 취소/타임아웃 처리, 실패 원인 가시화
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field

# 진행 6단계 (원본: 로그인→iframe→계정과목→승인선→저장)
STEPS = ["login", "iframe_switch", "account_select", "form_fill", "approval_line", "save"]


# ── 이력 저장소: Redis 폴백 ─────────────────────────────────────────
class HistoryStore:
    def set(self, k: str, v: dict) -> None: ...
    def get(self, k: str) -> dict | None: ...


class MemoryHistory(HistoryStore):
    def __init__(self):
        self._d: dict[str, dict] = {}

    def set(self, k, v):
        self._d[k] = dict(v)

    def get(self, k):
        return self._d.get(k)


def make_history(redis_client=None) -> HistoryStore:
    """graceful degradation: Redis 클라이언트 없거나 ping 실패 시 메모리 폴백."""
    if redis_client is not None:
        try:
            redis_client.ping()
            return redis_client  # 실제 환경에서 Redis 이력 사용
        except Exception:
            pass
    return MemoryHistory()


# ── 데이터 매핑 ─────────────────────────────────────────────────────
def map_expense_to_variables(expense: dict) -> dict:
    """ExpenseDataMapper 재현: 지출 데이터 -> RPA 변수(계정과목/승인선/참조문서)."""
    if not expense.get("account_code"):
        raise ValueError("account_code required")
    return {
        "ACCOUNT_CODE": expense["account_code"],
        "AMOUNT": str(expense["amount"]),
        "APPROVAL_LINE": ",".join(expense.get("approval_line", [])),
        "REF_DOC": expense.get("ref_doc", ""),
    }


# ── RPA 실행부 (mock 러너) ──────────────────────────────────────────
class RobotTimeout(Exception):
    pass


def mock_robot_run(variables: dict, fail_at: str | None = None, timeout_at: str | None = None):
    """RF subprocess stdout → 진행 이벤트 스트림 재현 (제너레이터)."""
    for step in STEPS:
        if timeout_at == step:
            raise RobotTimeout(f"timeout at {step}")
        if fail_at == step:
            raise RuntimeError(f"robot failed at {step}")
        yield step


# ── 작업 & 큐 ───────────────────────────────────────────────────────
@dataclass
class Task:
    id: str
    variables: dict
    step: str = "queued"
    events: list[str] = field(default_factory=list)
    status: str = "pending"          # pending|running|success|failed|cancelled
    error: str | None = None
    cancelled: bool = False


class Automation:
    def __init__(self, history: HistoryStore):
        self.history = history
        self.queue: list[Task] = []
        self._tasks: dict[str, Task] = {}

    def _save(self, t: Task):
        self.history.set(t.id, {"status": t.status, "step": t.step, "error": t.error})

    def start(self, expense: dict) -> str:
        t = Task(id=uuid.uuid4().hex[:8], variables=map_expense_to_variables(expense))
        self.queue.append(t)
        self._tasks[t.id] = t
        self._save(t)
        return t.id

    def cancel(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        if t and t.status in ("pending", "running"):
            t.cancelled = True
            return True
        return False

    def run_next(self, fail_at=None, timeout_at=None) -> Task:
        t = self.queue.pop(0)
        t.status = "running"
        self._save(t)
        try:
            for step in mock_robot_run(t.variables, fail_at, timeout_at):
                if t.cancelled:                          # 협조적 취소 지점
                    t.status = "cancelled"
                    self._save(t)
                    return t
                t.step = step
                t.events.append(step)                    # WebSocket 진행 이벤트
            t.status = "success"
        except RobotTimeout as e:
            t.status = "failed"
            t.error = f"timeout: {e}"                     # 타임아웃 kill 대응
        except RuntimeError as e:
            t.status = "failed"
            t.error = str(e)                             # 실패 원인 가시화(스크린샷/로그)
        self._save(t)
        return t


if __name__ == "__main__":
    auto = Automation(make_history(redis_client=None))   # Redis 없음 → 메모리 폴백
    tid = auto.start({"account_code": "5100", "amount": 30000,
                      "approval_line": ["mgr", "dir"], "ref_doc": "RCPT-1"})
    task = auto.run_next()
    print(tid, task.status, task.events)
