"""가상 재구현: EMR 외부조회 API의 계층 구조(app/mgr/dao) 재현.

실제 EMR(Java/레거시 프레임워크/iBatis) 코드·서브밋ID·프로시저·테이블은 포함하지 않는다.
원본의 '레거시 컴포넌트 위에 안전하게 API를 얹는 구조'를 순수 파이썬으로 재현한다.

재현 범위
  - 계층 분리: app(외부노출 req*) -> mgr(오케스트레이션) -> dao(조회/기록)
  - 서브밋ID 기반 라우팅 (원본: /*.jnu?submit_id=... 디스패치)
  - 두 API: DUR 상호작용 점검 + 개인투약이력 조회
  - 안전 원칙: 주민번호 유효성 사전차단(로그 미출력), null 방어,
              부수효과(중복 전송) 가드, 감사로그, 표준 에러 응답
"""
from __future__ import annotations
from dataclasses import dataclass, field
import hashlib

# ── 합성 마스터 데이터 ───────────────────────────────────────────────
_INTERACTIONS = {
    frozenset({"DRUG_A", "DRUG_B"}): ("병용금기", "출혈 위험 증가"),
    frozenset({"DRUG_A", "DRUG_C"}): ("주의", "효과 감소 가능"),
    frozenset({"DRUG_D", "DRUG_E"}): ("병용금기", "QT 연장 위험"),
}
# 합성 개인투약이력 (요청식별자 -> 최근 처방 목록)
_MED_HISTORY = {
    "REQ4567": [
        {"drug": "DRUG_A", "days": 30, "org": "[협력의료기관]"},
        {"drug": "DRUG_C", "days": 14, "org": "[협력의료기관]"},
    ],
}


# ── DAO: 조회/기록 계층 ──────────────────────────────────────────────
class Dao:
    def __init__(self):
        self.audit: list[dict] = []          # 감사로그 (INSERT 재현)
        self._sent: set[str] = set()         # 중복 전송(HIRA) 방지 상태

    def screen_exec(self, drugs: list[str]) -> list[dict]:
        found = []
        for i, a in enumerate(drugs):
            for b in drugs[i + 1:]:
                hit = _INTERACTIONS.get(frozenset({a, b}))
                if hit:
                    found.append({"pair": sorted([a, b]), "grade": hit[0], "reason": hit[1]})
        return found

    def med_history(self, rid: str) -> list[dict]:
        return list(_MED_HISTORY.get(rid, []))

    def report_to_hira(self, dedup_key: str) -> bool:
        """실시간 HIRA 전송(부수효과). 이미 보낸 건은 재전송 안 함(중복 가드)."""
        if dedup_key in self._sent:
            return False
        self._sent.add(dedup_key)
        return True

    def audit_insert(self, api: str, rid: str, count: int) -> None:
        # 주민번호 등 원식별자는 기록하지 않음 (요청식별자만)
        self.audit.append({"api": api, "rid": rid, "count": count})


# ── MGR: 오케스트레이션 계층 ─────────────────────────────────────────
class Mgr:
    def __init__(self, dao: Dao):
        self.dao = dao

    def dur_screen(self, rid: str, drugs: list[str], report: bool = True) -> dict:
        drugs = [d for d in (drugs or []) if d]        # null/빈값 방어
        results = self.dao.screen_exec(drugs)
        reported = False
        if report and results:
            key = rid + ":" + hashlib.sha1(",".join(sorted(drugs)).encode()).hexdigest()[:8]
            reported = self.dao.report_to_hira(key)     # 중복 전송 가드
        self.dao.audit_insert("DUR", rid, len(results))
        return {"count": len(results), "results": results, "hira_reported": reported}

    def med_history(self, rid: str) -> dict:
        rows = self.dao.med_history(rid)
        self.dao.audit_insert("KIMS", rid, len(rows))
        return {"count": len(rows), "history": rows}


# ── APP: 외부노출 계층 (req*) + 서브밋 라우팅 ────────────────────────
@dataclass
class ApiResponse:
    ok: bool
    error_code: int
    message: str
    data: dict | None = None


def _valid_rrn(rrn: str) -> bool:
    """주민번호 형식 유효성(가상, 값은 로그/메시지에 절대 미출력)."""
    d = (rrn or "").replace("-", "")
    return len(d) == 13 and d.isdigit()


def _rid(rrn: str) -> str:
    """내부 요청식별자 — 끝 4자리만 사용(원식별자 미보존)."""
    return "REQ" + rrn.replace("-", "")[-4:]


class App:
    """서브밋ID -> 핸들러 라우팅 (원본 /*.jnu 디스패치 재현)."""

    # 서브밋ID는 가상(실제 코드 아님)
    ROUTES = {"DEMO_DUR_SCREEN": "req_dur_screen", "DEMO_MED_HISTORY": "req_med_history"}

    def __init__(self, mgr: Mgr):
        self.mgr = mgr

    def dispatch(self, submit_id: str, jparam: dict) -> ApiResponse:
        handler = self.ROUTES.get(submit_id)
        if not handler:
            return ApiResponse(False, 404, "unknown submit_id")
        return getattr(self, handler)(jparam)

    def req_dur_screen(self, jparam: dict) -> ApiResponse:
        rrn = jparam.get("rrn", "")
        if not _valid_rrn(rrn):
            return ApiResponse(False, 400, "invalid identifier")  # 값 미노출
        data = self.mgr.dur_screen(_rid(rrn), jparam.get("drugs"), jparam.get("report", True))
        return ApiResponse(True, 0, "ok", data)

    def req_med_history(self, jparam: dict) -> ApiResponse:
        rrn = jparam.get("rrn", "")
        if not _valid_rrn(rrn):
            return ApiResponse(False, 400, "invalid identifier")
        return ApiResponse(True, 0, "ok", self.mgr.med_history(_rid(rrn)))


def build_app() -> App:
    return App(Mgr(Dao()))


if __name__ == "__main__":
    app = build_app()
    r1 = app.dispatch("DEMO_DUR_SCREEN",
                      {"rrn": "900101-1234567", "drugs": ["DRUG_A", "DRUG_B", "DRUG_C"]})
    print("DUR:", r1)
    r2 = app.dispatch("DEMO_MED_HISTORY", {"rrn": "900101-1234567"})
    print("KIMS:", r2)
