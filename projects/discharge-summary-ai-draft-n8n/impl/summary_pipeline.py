"""가상 재구현: 입퇴원 요약 AI 초안 파이프라인 (합성 임상노트).

실제 환자 임상데이터·EMR 인증·LLM 키는 포함하지 않는다. LLM 호출은 규칙기반
mock으로 대체하고, 원본의 '항목별 5분담 + 합류 게이트 + 휴먼리뷰 게이트'만 재현한다.

핵심 재현:
  - CLOB 조각조회 대체(chunk merge)
  - 항목별 요약 5분담 -> Merge 동기화 게이트(모두 도착해야 진행)
  - 환각 방지: 원문 없으면 [원문 없음] -> None 정규화
  - 임시저장 초안(status=DRAFT) — 최종 확정은 의사 서명(휴먼리뷰 게이트)
"""
from __future__ import annotations

ITEMS = ["초진", "치료과정", "검사결과", "투약처방", "추후계획"]


def read_clob_chunks(note: str, size: int = 1000) -> str:
    """CLOB 조각조회 후 병합 재현."""
    return "".join(note[i:i + size] for i in range(0, len(note), size))


def mock_llm_summarize(item: str, source: str | None) -> str | None:
    """규칙기반 mock. 원문 없으면 환각 대신 None."""
    if not source or source.strip() == "":
        return None  # [원문 없음] 정규화
    first = source.strip().splitlines()[0][:60]
    return f"[{item}] {first}"


def summarize_all(sources: dict[str, str | None]) -> dict[str, str | None] | None:
    """5분담 실행 후 합류 게이트: 5개 항목 결과가 모두 존재해야 병합 진행."""
    partial = {}
    for item in ITEMS:
        partial[item] = mock_llm_summarize(item, sources.get(item))
    # Merge 동기화 게이트: 항목 수가 정확히 ITEMS와 일치해야 함
    if set(partial.keys()) != set(ITEMS):
        return None
    return partial


def build_draft(patient_id: str, sources: dict[str, str | None]) -> dict:
    merged = summarize_all(sources)
    if merged is None:
        return {"status": "ABORT", "reason": "merge gate not satisfied"}
    # 참조기록이 하나도 없으면 적재 안 함
    if all(v is None for v in merged.values()):
        return {"status": "SKIP", "reason": "no source records"}
    return {
        "status": "DRAFT",          # EMR 임시저장 (espiseq=0 대응)
        "patient_id": patient_id,
        "items": merged,
        "signed": False,            # 휴먼리뷰 게이트: 의사 서명 전
    }


def doctor_sign(draft: dict) -> dict:
    if draft.get("status") != "DRAFT":
        raise ValueError("only DRAFT can be signed")
    return {**draft, "status": "FINAL", "signed": True}


if __name__ == "__main__":
    src = {
        "초진": "발열과 기침으로 내원",
        "치료과정": "수액 및 항생제 투여",
        "검사결과": "흉부 X선 정상",
        "투약처방": "경구 항생제 5일",
        "추후계획": "",  # 원문 없음
    }
    d = build_draft("P001", src)
    print(d["status"], d["items"])
    print(doctor_sign(d)["status"])
