"""가상 재구현: 입퇴원 요약 AI 초안 파이프라인 (합성 임상노트).

실제 환자 임상데이터·EMR 인증·LLM 키·양식코드는 포함하지 않는다. LLM 호출은
규칙기반 mock으로 대체하고, 운영 워크플로우의 설계 요소만 재현한다.

재현 범위
  - CLOB 조각조회 후 병합            (원본: 1,000자 x 12 조회 제약 우회)
  - 항목별 요약 5분담 + Merge 동기화 게이트(모두 도착해야 병합)
  - 품질 규칙: 환각 방지(원문 없음 -> None), 원문 길이 대비 과다생성 차단
  - 적재 성공판정 다중조건            (HTTP200 + ErrorCode0 + issuc=Y) — silent failure 대비
  - 감사로그 레코드 구성
  - 휴먼리뷰 게이트: 임시저장(DRAFT) -> 의사 서명(FINAL)
"""
from __future__ import annotations
from dataclasses import dataclass, field

ITEMS = ["초진", "치료과정", "검사결과", "투약처방", "추후계획"]


# ── CLOB 조각조회 ────────────────────────────────────────────────────
def read_clob_chunks(note: str, size: int = 1000) -> str:
    return "".join(note[i:i + size] for i in range(0, len(note), size))


# ── 품질 규칙 ────────────────────────────────────────────────────────
class QualityError(Exception):
    pass


def _quality_check(item: str, source: str, summary: str) -> None:
    """원문 대비 과다생성(환각 의심) 차단."""
    if len(summary) > max(60, len(source)):  # 요약이 원문보다 길면 의심
        raise QualityError(f"{item}: summary longer than source")


def mock_llm_summarize(item: str, source: str | None) -> str | None:
    """규칙기반 mock. 원문 없으면 환각 대신 None."""
    if not source or not source.strip():
        return None                                   # [원문 없음] 정규화
    summary = f"[{item}] " + source.strip().splitlines()[0][:60]
    _quality_check(item, source, summary)
    return summary


# ── 5분담 + Merge 동기화 게이트 ──────────────────────────────────────
def summarize_all(sources: dict[str, str | None]) -> dict[str, str | None] | None:
    partial = {item: mock_llm_summarize(item, sources.get(item)) for item in ITEMS}
    if set(partial.keys()) != set(ITEMS):             # Merge numberInputs 게이트
        return None
    return partial


# ── 적재 성공판정 (silent failure 대비) ──────────────────────────────
@dataclass
class LoadResult:
    http_status: int
    error_code: int
    issuc: str          # 'Y' / 'N'


def is_load_success(r: LoadResult) -> bool:
    """응답 성공(HTTP200)만으로 판단하지 않는다 — 3중 조건 모두 충족해야 성공."""
    return r.http_status == 200 and r.error_code == 0 and r.issuc == "Y"


# ── 감사로그 ─────────────────────────────────────────────────────────
def audit_record(patient_id: str, items: dict, load: LoadResult, success: bool) -> dict:
    filled = sum(1 for v in items.values() if v is not None)
    return {
        "patient_id": patient_id,
        "items_total": len(ITEMS),
        "items_filled": filled,
        "http": load.http_status,
        "error_code": load.error_code,
        "issuc": load.issuc,
        "result": "SUCCESS" if success else "FAIL",
    }


# ── 파이프라인 ───────────────────────────────────────────────────────
def build_draft(patient_id: str, sources: dict[str, str | None]) -> dict:
    merged = summarize_all(sources)
    if merged is None:
        return {"status": "ABORT", "reason": "merge gate not satisfied"}
    if all(v is None for v in merged.values()):       # 참조기록 없음 -> 적재 안 함
        return {"status": "SKIP", "reason": "no source records"}
    return {"status": "DRAFT", "patient_id": patient_id, "items": merged, "signed": False}


def load_to_emr(draft: dict, load: LoadResult) -> dict:
    """EMR 임시저장 적재 + 성공판정 + 감사로그."""
    if draft.get("status") != "DRAFT":
        raise ValueError("only DRAFT can be loaded")
    success = is_load_success(load)
    audit = audit_record(draft["patient_id"], draft["items"], load, success)
    return {**draft, "loaded": success, "audit": audit,
            "alert": None if success else "적재 실패(감사로그+메일 알림)"}


def doctor_sign(loaded: dict) -> dict:
    if not loaded.get("loaded"):
        raise ValueError("cannot sign a draft that was not loaded")
    return {**loaded, "status": "FINAL", "signed": True}


if __name__ == "__main__":
    src = {
        "초진": "발열과 기침으로 내원",
        "치료과정": "수액 및 항생제 투여",
        "검사결과": "흉부 X선 정상",
        "투약처방": "경구 항생제 5일",
        "추후계획": "",                # 원문 없음 -> None
    }
    d = build_draft("P001", src)
    ok = load_to_emr(d, LoadResult(200, 0, "Y"))
    print("적재:", ok["loaded"], ok["audit"])
    print("서명 후:", doctor_sign(ok)["status"])
    bad = load_to_emr(build_draft("P002", src), LoadResult(200, 0, "N"))  # silent fail
    print("silent fail 판정:", bad["loaded"], "| alert:", bad["alert"])
