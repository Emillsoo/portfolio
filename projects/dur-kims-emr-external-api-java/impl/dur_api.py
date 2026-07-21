"""가상 재구현: EMR 외부조회 API의 계층 구조(app/mgr/dao) 재현.

실제 EMR(Java/레거시 프레임워크/iBatis) 코드·서브밋ID·프로시저·테이블은 포함하지 않는다.
원본의 '레거시 컴포넌트 위에 안전하게 API를 얹는 구조'만 순수 파이썬으로 재현한다.

계층:
  app (외부노출 req*)  ->  mgr (오케스트레이션)  ->  dao (조회/기록)
안전 원칙 재현:
  - 주민번호 유효성 사전 차단 (로그 미출력)
  - null 방어
  - '실행'과 '조회'를 조합하는 오케스트레이션 (원본 reqScreeningEXEC + reqDurScrhList)
"""
from __future__ import annotations
from dataclasses import dataclass

# ---- 합성 마스터: 약물 상호작용 사전 (가상) ----
_INTERACTIONS = {
    frozenset({"DRUG_A", "DRUG_B"}): ("병용금기", "출혈 위험 증가"),
    frozenset({"DRUG_A", "DRUG_C"}): ("주의", "효과 감소 가능"),
}


class Dao:
    """조회/기록 계층 (가상 DB)."""

    def screen_exec(self, rid: str, drugs: list[str]) -> list[dict]:
        found = []
        for i, a in enumerate(drugs):
            for b in drugs[i + 1:]:
                hit = _INTERACTIONS.get(frozenset({a, b}))
                if hit:
                    found.append({"pair": [a, b], "grade": hit[0], "reason": hit[1]})
        return found

    def audit_insert(self, rid: str, count: int) -> None:
        # 실제로는 감사로그 INSERT. 여기서는 부수효과만 표현(주민번호 미기록).
        pass


class Mgr:
    """오케스트레이션: 실행(screen) + 조회(list) 조합."""

    def __init__(self, dao: Dao):
        self.dao = dao

    def dur_screen(self, rid: str, drugs: list[str]) -> dict:
        drugs = [d for d in (drugs or []) if d]  # null 방어
        results = self.dao.screen_exec(rid, drugs)
        self.dao.audit_insert(rid, len(results))
        return {"count": len(results), "results": results}


@dataclass
class ApiResponse:
    ok: bool
    error_code: int
    message: str
    data: dict | None = None


def _valid_rrn(rrn: str) -> bool:
    """주민번호 형식 유효성(가상, 로그 미출력)."""
    d = rrn.replace("-", "")
    return len(d) == 13 and d.isdigit()


class App:
    """외부노출 계층 (req*)."""

    def __init__(self, mgr: Mgr):
        self.mgr = mgr

    def req_dur_screen(self, rrn: str, drugs: list[str]) -> ApiResponse:
        if not rrn or not _valid_rrn(rrn):
            # 사전 차단 — 주민번호 값 자체는 메시지/로그에 넣지 않음
            return ApiResponse(False, 400, "invalid identifier")
        rid = "REQ" + rrn[-4:]  # 내부 요청식별(끝 4자리만)
        data = self.mgr.dur_screen(rid, drugs)
        return ApiResponse(True, 0, "ok", data)


def build_app() -> App:
    return App(Mgr(Dao()))


if __name__ == "__main__":
    app = build_app()
    r = app.req_dur_screen("900101-1234567", ["DRUG_A", "DRUG_B", "DRUG_C"])
    print(r)
