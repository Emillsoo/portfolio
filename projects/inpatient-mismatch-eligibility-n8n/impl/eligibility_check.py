"""가상 재구현: 재원환자 보험자격 불일치 대조 (합성 데이터).

실제 [의료기관] EMR/공단 연동 코드는 포함하지 않는다. 화면 판단 로직을
SQL로 복제했던 원본의 '핵심 알고리즘'만 순수 파이썬으로 재현한다.

핵심 재현 포인트
- 환자별 최신 공단결과 1건 선택 (ROW_NUMBER 대체)
- 거짓 불일치 방지 3중 가드
    1) 공단 미수신(None) 환자는 비교 제외
    2) 다기관 데이터 혼입 차단 (기관코드 일치만 비교)
    3) 차상위 코드 변환 표준화 (E+장애인 -> F)
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class NhicResult:
    inst_cd: str          # 기관코드
    patient_id: str       # 합성 식별자
    insurance_type: str | None  # 공단 자격 (None = 미수신)
    disabled: bool
    queried_at: str       # ISO ts, 최신 선택용


@dataclass(frozen=True)
class InHouse:
    inst_cd: str
    patient_id: str
    insurance_type: str


def normalize_type(code: str | None, disabled: bool) -> str | None:
    """차상위 변환 표준화: 'E'(차상위) + 장애인 -> 'F'."""
    if code is None:
        return None
    if code == "E" and disabled:
        return "F"
    return code


def latest_per_patient(rows: list[NhicResult]) -> dict[tuple[str, str], NhicResult]:
    """ROW_NUMBER() OVER (PARTITION BY inst,pid ORDER BY queried_at DESC) = 1."""
    best: dict[tuple[str, str], NhicResult] = {}
    for r in rows:
        key = (r.inst_cd, r.patient_id)
        cur = best.get(key)
        if cur is None or r.queried_at > cur.queried_at:
            best[key] = r
    return best


def find_mismatches(in_house: list[InHouse], nhic: list[NhicResult]) -> list[dict]:
    latest = latest_per_patient(nhic)
    out: list[dict] = []
    for h in in_house:
        key = (h.inst_cd, h.patient_id)
        n = latest.get(key)
        # 가드 1: 공단 미수신 제외
        if n is None or n.insurance_type is None:
            continue
        # 가드 2: 다기관 혼입 차단 (키가 inst_cd 포함이라 이미 기관 일치만 매칭)
        # 가드 3: 표준화 후 비교
        h_type = normalize_type(h.insurance_type, n.disabled)
        n_type = normalize_type(n.insurance_type, n.disabled)
        if h_type != n_type:
            out.append({
                "inst_cd": h.inst_cd,
                "patient_id": h.patient_id,
                "in_house": h_type,
                "nhic": n_type,
            })
    return out


if __name__ == "__main__":
    in_house = [
        InHouse("H01", "P001", "N"),   # 일치
        InHouse("H01", "P002", "E"),   # 장애인 차상위 -> F 표준화로 일치
        InHouse("H01", "P003", "N"),   # 불일치 (공단 G)
        InHouse("H01", "P004", "N"),   # 공단 미수신 -> 제외
        InHouse("H02", "P001", "N"),   # 타기관, 공단 결과 없음 -> 제외
    ]
    nhic = [
        NhicResult("H01", "P001", "N", False, "2026-07-20T09:00:00"),
        NhicResult("H01", "P002", "E", True,  "2026-07-20T09:00:00"),
        NhicResult("H01", "P003", "G", False, "2026-07-19T09:00:00"),
        NhicResult("H01", "P003", "G", False, "2026-07-20T09:00:00"),  # 최신
        # P004 공단 미수신 (행 없음)
    ]
    result = find_mismatches(in_house, nhic)
    print(f"불일치 대상자 {len(result)}건")
    for r in result:
        print(r)
