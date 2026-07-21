# 보안 검수 게이트

게시(GitHub/Notion) **직전** 반드시 통과해야 하는 관문.

## 스캐너
`scan.py` — 순수 파이썬 비밀·PII 스캐너(gitleaks 대체/보완).
- 탐지: 주민번호·휴대폰·계좌, API키/토큰(Notion `ntn_`/GitHub `gh*_`/OpenAI `sk-`/AWS `AKIA`/Google `AIza`), 개인키, 내부 IP(10./192.168./172.16-31.)
- 사전 기반: `sensitive_terms.txt`(벤더 실명·EMR 코드네임·환자명·서브밋 접두)

## 실행
```
python security/scan.py projects --terms security/sensitive_terms.txt
# 종료코드 0 = 클린, 1 = hit 존재
```

## 현재 결과
- 대상: `projects/` (게시 대상 30개 파일)
- 최초 스캔: hit 4 (EMR 코드네임 ×2, 협력업체명 ×2) → 일반화 수정
- 재스캔: **hit 0 (클린)** — `scan_report.json`

## 게시 정책
- `inventory.yaml`(벤더명/서브밋 접두/제외사유 포함)은 **SSOT 내부 파일로 로컬 보관, 저장소에 push 금지**.
- 각 저장소는 push 직전 워킹트리 + git 히스토리 재스캔(G004에서 커밋 직전 수행). hit 발생 시 게시 보류.
- git 히스토리 오염 방지: 검수 통과 후 **클린 초기 커밋 1회**로 시작.
