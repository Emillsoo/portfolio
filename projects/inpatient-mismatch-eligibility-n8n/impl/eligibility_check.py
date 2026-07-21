"""가상 재구현: 재원환자 보험자격 불일치 대조 (합성 데이터).

실제 [의료기관] EMR/공단 연동 코드·테이블·서브밋은 포함하지 않는다.
운영 워크플로우의 '핵심 알고리즘'만 순수 파이썬으로 재현한다.

재현 범위
  1. 환자별 최신 공단결과 1건 선택      (원본: ROW_NUMBER() OVER (...) = 1)
  2. 거짓 불일치 방지 3중 가드
       G1) 공단 미수신(None) 환자 비교 제외
       G2) 다기관 데이터 혼입 차단(기관코드 일치만 비교)
       G3) 차상위 코드 변환 표준화(E + 장애인 -> F)
  3. 코드 -> 한글 라벨 변환            (알림 메일/시트 표기용)
  4. 시트 보존 가드 3중                (원본: 오래된 탭 자동정리 시 사고 방지)
"""
from __future__ import annotations
from dataclasses import dataclass
import datetime as dt
import re

# ── 보험 자격 코드 → 한글 라벨 (합성 예시 코드 체계) ──────────────────
INSURANCE_LABELS: dict[str, str] = {
    "N": "건강보험",
    "G": "의료급여",
    "E": "차상위",
    "F": "차상위(장애인)",
    "B": "보훈",
}


def to_label(code: str | None) -> str:
    return INSURANCE_LABELS.get(code or "", "미확인")


# ── 도메인 모델 ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class NhicResult:
    inst_cd: str                 # 기관코드
    patient_id: str              # 합성 식별자(주민번호 아님)
    insurance_type: str | None   # 공단 자격 (None = 미수신)
    disabled: bool
    queried_at: str              # ISO ts, 최신 선택용


@dataclass(frozen=True)
class InHouse:
    inst_cd: str
    patient_id: str
    insurance_type: str


# ── 1) 표준화 & 2) 최신 선택 ─────────────────────────────────────────
def normalize_type(code: str | None, disabled: bool) -> str | None:
    """차상위 변환 표준화: 'E'(차상위) + 장애인 -> 'F'."""
    if code is None:
        return None
    if code == "E" and disabled:
        return "F"
    return code


def latest_per_patient(rows: list[NhicResult]) -> dict[tuple[str, str], NhicResult]:
    """ROW_NUMBER() OVER (PARTITION BY inst_cd, patient_id ORDER BY queried_at DESC) = 1."""
    best: dict[tuple[str, str], NhicResult] = {}
    for r in rows:
        key = (r.inst_cd, r.patient_id)
        cur = best.get(key)
        if cur is None or r.queried_at > cur.queried_at:
            best[key] = r
    return best


# ── 3) 불일치 판정 ───────────────────────────────────────────────────
def find_mismatches(in_house: list[InHouse], nhic: list[NhicResult]) -> list[dict]:
    latest = latest_per_patient(nhic)
    out: list[dict] = []
    for h in in_house:
        n = latest.get((h.inst_cd, h.patient_id))
        # G1: 공단 미수신 제외
        if n is None or n.insurance_type is None:
            continue
        # G2: 다기관 혼입 차단 — 키가 (inst_cd, pid)라 기관 일치만 매칭됨
        # G3: 표준화 후 비교
        h_type = normalize_type(h.insurance_type, n.disabled)
        n_type = normalize_type(n.insurance_type, n.disabled)
        if h_type != n_type:
            out.append({
                "inst_cd": h.inst_cd,
                "patient_id": h.patient_id,
                "in_house": h_type,
                "nhic": n_type,
                "in_house_label": to_label(h_type),
                "nhic_label": to_label(n_type),
            })
    return out


# ── 4) 시트 보존 가드 ────────────────────────────────────────────────
_TAB_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # 명명규칙: YYYY-MM-DD 일자 탭만 관리 대상


def tabs_to_delete(tabs: list[str], today: str, keep_days: int = 7) -> list[str]:
    """오래된 일자 탭 정리 대상 계산 — 보존 가드 3중.

    - 명명규칙(YYYY-MM-DD) 외 탭은 절대 삭제하지 않음(보호)
    - 오늘 탭은 삭제하지 않음(보호)
    - 최소 1개 일자 탭은 남김(전체 삭제 방지)
    """
    today_d = dt.date.fromisoformat(today)
    managed = [t for t in tabs if _TAB_RE.match(t)]  # 관리 대상만
    old = []
    for t in managed:
        if t == today:                              # 오늘 보호
            continue
        age = (today_d - dt.date.fromisoformat(t)).days
        if age > keep_days:
            old.append(t)
    # 최소 1탭 보존: 관리탭을 전부 지우게 되면 가장 최신 1개는 남김
    if managed and len(old) >= len(managed):
        old_sorted = sorted(old)
        old = old_sorted[:-1]  # 가장 최신 1개 보존
    return old


if __name__ == "__main__":
    in_house = [
        InHouse("H01", "P001", "N"),   # 일치
        InHouse("H01", "P002", "E"),   # 장애인 차상위 -> F 표준화로 일치
        InHouse("H01", "P003", "N"),   # 불일치 (공단 G=의료급여)
        InHouse("H01", "P004", "N"),   # 공단 미수신 -> 제외
        InHouse("H02", "P001", "N"),   # 타기관, 공단 결과 없음 -> 제외
    ]
    nhic = [
        NhicResult("H01", "P001", "N", False, "2026-07-20T09:00:00"),
        NhicResult("H01", "P002", "E", True,  "2026-07-20T09:00:00"),
        NhicResult("H01", "P003", "G", False, "2026-07-19T09:00:00"),
        NhicResult("H01", "P003", "G", False, "2026-07-20T09:00:00"),  # 최신
    ]
    result = find_mismatches(in_house, nhic)
    print(f"불일치 대상자 {len(result)}건")
    for r in result:
        print(f"  {r['patient_id']}: 원내 {r['in_house_label']} vs 공단 {r['nhic_label']}")
    print("삭제 대상 탭:", tabs_to_delete(
        ["2026-07-01", "2026-07-13", "2026-07-20", "요약", "설정"], "2026-07-20"))
