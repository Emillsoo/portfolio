"""가상 재구현: 전산개발 회의 자동화의 회의 비즈니스 로직.

실제 [의료기관]·서버IP·부서원 실명·DB는 포함하지 않는다. 운영 시스템의
핵심 도메인 로직(회의 타입 판별 / 보고 순서 / 간사 로테이션)만 순수 파이썬으로 재현한다.

원본 스택: FastAPI + SQLAlchemy(SQLite) 백엔드 · Next.js 14 프론트 · Whisper(STT) + LLM(요약).
여기서는 DB/웹 계층 없이 로직만 in-memory로 재현.
"""
from __future__ import annotations
from dataclasses import dataclass
import datetime as dt

# 직급 보고 순서 가중치 (낮을수록 먼저 = 역직급 순). 일반 직급명.
TITLE_ORDER = {"사원": 0, "주임": 1, "계장": 2, "과장": 3, "차장": 4, "실장": 5, "의장": 6}
SECRETARY_EXCLUDED = {"의장", "실장"}   # 간사 미배정 직급
CHAIR_TITLE = "의장"                     # 보고 순서에서 제외


@dataclass
class Member:
    id: int
    name: str            # 합성 이름
    title: str
    is_active: bool = True


@dataclass
class Attendee:
    member: Member
    is_present: bool = True
    report_order: int | None = None


# ── 회의 타입 ────────────────────────────────────────────────────────
def get_meeting_type(meeting_date: str) -> str:
    """월요일 → weekly, 그 외 → daily."""
    return "weekly" if dt.date.fromisoformat(meeting_date).weekday() == 0 else "daily"


# ── 보고 순서 ────────────────────────────────────────────────────────
def suggest_report_order(attendees: list[Attendee]) -> list[Attendee]:
    """의장 제외 → 참석자 역직급 순 → 미참석자 뒤로. report_order 갱신."""
    chair = [a for a in attendees if a.member.title == CHAIR_TITLE]
    others = [a for a in attendees if a.member.title != CHAIR_TITLE]
    for a in chair:
        a.report_order = -1
    present = [a for a in others if a.is_present]
    absent = [a for a in others if not a.is_present]
    present_sorted = sorted(present, key=lambda a: TITLE_ORDER.get(a.member.title, 99))
    for i, a in enumerate(present_sorted):
        a.report_order = i
    for i, a in enumerate(absent):
        a.report_order = len(present_sorted) + i
    return chair + present_sorted + absent


# ── 간사 로테이션 ────────────────────────────────────────────────────
def get_next_secretary(members: list[Member], history: dict[int, str]) -> Member | None:
    """이력이 가장 오래된(또는 없는) 활성 멤버를 다음 간사로 추천.

    history: {member_id: last_served_date(YYYY-MM-DD)}. 이력 없으면 최우선.
    """
    candidates = [m for m in members if m.is_active and m.title not in SECRETARY_EXCLUDED]
    if not candidates:
        return None
    return sorted(candidates, key=lambda m: history.get(m.id, "1900-01-01"))[0]


def record_secretary_served(history: dict[int, str], member_id: int, served_date: str) -> None:
    history[member_id] = served_date


if __name__ == "__main__":
    members = [
        Member(1, "홍길동", "의장"),
        Member(2, "김철수", "과장"),
        Member(3, "이영희", "사원"),
        Member(4, "박민수", "계장"),
    ]
    att = [Attendee(members[0]), Attendee(members[1]), Attendee(members[2], is_present=False), Attendee(members[3])]
    ordered = suggest_report_order(att)
    print("타입:", get_meeting_type("2026-07-20"), "/", get_meeting_type("2026-07-21"))
    print("보고순서:", [(a.member.name, a.member.title, a.report_order) for a in ordered])
    hist: dict[int, str] = {2: "2026-07-01", 4: "2026-07-10"}
    print("다음 간사:", get_next_secretary(members, hist).name)  # 이력 없는 이영희(사원)
