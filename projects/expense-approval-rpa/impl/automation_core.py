"""가상 재구현: 지출결의서 자동화의 백엔드 코어 (외부 의존 없음).

실제 그룹웨어/계정/Selenium/RF 코드는 포함하지 않는다. 원본의 핵심 설계인
'작업 큐 + Redis 이력(없으면 메모리 폴백) + 진행 6단계 이벤트 + 데이터 매핑'만
순수 파이썬으로 재현한다. RPA 실행부는 mock 러너로 대체한다.
"""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field

STEPS = ["queued", "login", "iframe", "account_select", "approval_line", "saved"]


class HistoryStore:
    """Redis 이력 저장소 인터페이스."""
    def set(self, k: str, v: dict) -> None: ...
    def get(self, k: str) -> dict | None: ...


class MemoryHistory(HistoryStore):
    """Redis 장애 시 자동 폴백되는 메모리 이력."""
    def __init__(self):
        self._d: dict[str, dict] = {}

    def set(self, k, v):
        self._d[k] = v

    def get(self, k):
        return self._d.get(k)


def make_history(redis_available: bool) -> HistoryStore:
    """graceful degradation: Redis 없으면 메모리로 폴백."""
    if redis_available:
        raise RuntimeError("real redis not used in demo")  # 데모에선 미사용
    return MemoryHistory()


def map_expense_to_variables(expense: dict) -> dict:
    """ExpenseDataMapper 재현: 지출 데이터 -> RPA 변수."""
    return {
        "ACCOUNT_CODE": expense["account_code"],
        "AMOUNT": str(expense["amount"]),
        "APPROVAL_LINE": ",".join(expense.get("approval_line", [])),
        "REF_DOC": expense.get("ref_doc", ""),
    }


@dataclass
class Task:
    id: str
    variables: dict
    step: str = "queued"
    events: list[str] = field(default_factory=list)
    status: str = "pending"
    error: str | None = None


def mock_robot_run(variables: dict, fail_at: str | None = None):
    """RF subprocess stdout 파싱 -> 진행 이벤트 스트림 재현 (제너레이터)."""
    for step in STEPS[1:]:
        if fail_at == step:
            raise RuntimeError(f"robot failed at {step}")
        yield step


class Automation:
    def __init__(self, history: HistoryStore):
        self.history = history
        self.queue: list[Task] = []

    def start(self, expense: dict) -> str:
        t = Task(id=uuid.uuid4().hex[:8], variables=map_expense_to_variables(expense))
        self.queue.append(t)
        self.history.set(t.id, {"status": t.status, "step": t.step})
        return t.id

    def run_next(self, fail_at: str | None = None) -> Task:
        t = self.queue.pop(0)
        try:
            for step in mock_robot_run(t.variables, fail_at):
                t.step = step
                t.events.append(step)  # WebSocket 진행 이벤트에 대응
            t.status = "success"
        except RuntimeError as e:
            t.status = "failed"
            t.error = str(e)  # 실패 원인 가시화 (스크린샷/로그 대응)
        self.history.set(t.id, {"status": t.status, "step": t.step, "error": t.error})
        return t


if __name__ == "__main__":
    auto = Automation(make_history(redis_available=False))
    tid = auto.start({"account_code": "5100", "amount": 30000,
                      "approval_line": ["mgr", "dir"], "ref_doc": "RCPT-1"})
    task = auto.run_next()
    print(tid, task.status, task.events)
