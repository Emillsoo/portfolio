# 의료 IT · AX 업무자동화 포트폴리오

> 의료기관의 업무·시스템을 이해하고, 인프라·운영 경험을 바탕으로 **n8n·자동화·API 개발**로 실제 병원 업무를 개선하는 AX 엔지니어의 프로젝트 모음입니다.

## ⚠️ 공개 원칙
이 저장소의 모든 코드/데이터는 **가상 재구현·구성도·핵심 알고리즘 발췌**입니다.
- 실제 의료기관 EMR 소스·환자정보·기관/협력업체 실명·크리덴셜은 **일절 포함하지 않습니다.**
- 모든 예시 데이터는 합성(synthetic)입니다.
- 게시 전 자동 비밀·PII 스캔(`security/scan.py`)을 통과했습니다.

## 대표 프로젝트
| 프로젝트 | 유형 | 핵심 역량 |
|---|---|---|
| [재원환자 불일치 자격확인 알림](projects/inpatient-mismatch-eligibility-n8n) | n8n·데이터연계 | 화면로직 SQL 복제 · 거짓불일치 3중 가드 · 시간대 버그 해결 |
| [입퇴원 요약 AI 초안](projects/discharge-summary-ai-draft-n8n) | n8n·LLM | 항목별 LLM 5분담 · 합류 게이트 · 휴먼리뷰 게이트 |
| [DUR/개인투약이력 EMR 외부조회 API](projects/dur-kims-emr-external-api-java) | API·Java | 레거시 EMR 내부→외부 API 확장 · 정적+실검증 |
| [지출결의서 자동 상신 (RPA)](projects/expense-approval-rpa) | RPA·백엔드 | Flask+SocketIO+큐 · Redis 폴백 · RPA 엔드투엔드 |

각 대표 프로젝트의 `impl/`에는 합성 데이터 기반 **실행 가능한 가상 재구현 + 단위테스트**가 포함됩니다.

## 보조 프로젝트
- [위수탁검사비 수납처리 자동화](projects/outsourced-billing-automation-n8n) · 금전 자동화 안전설계(이중필터·부분수납 가드)
- [내시경 예약 재배정](projects/endoscopy-rebooking-n8n) · silent failure 규명 + DB 재조회 검증
- [건강증진팀 SMS 사전안내](projects/health-sms-notice-n8n) · DB 대조 모니터링 전환
- [콜당직 착신전환 (RPA)](projects/oncall-forwarding-rpa)
- [사내 OCR API 서비스 (FastAPI)](projects/internal-ocr-service-fastapi) · 동시성 가드·과부하 방어
- [건진 검사장비 수치연동](projects/exam-device-data-integration) · 데몬 + EAV 설계
- [형상관리 거버넌스 & 서버운영](projects/config-governance-ops)
- [콜프로그램/케어메시지 벤더연동 API](projects/vendor-integration-apis)
- [NHIC 자격조회 배치 서버이관](projects/nhic-eligibility-batch-migration) · 폐쇄망·32bit COM
- [AI 개발원칙 프롬프트 시스템](projects/ai-dev-principles-system)
- [CSI 개선활동 (EMR 데이터처리)](projects/csi-emr-data-improvement)
- [일일보고 자동등록 (Redmine API)](projects/daily-report-redmine-automation)
- [입원초진기록 초안 자동작성 (n8n·AI)](projects/admission-initial-record-n8n) · 입퇴원 요약과 동일 파이프라인의 확장
- [외래 대기안내 연동 배치 (WaitGuideMark)](projects/outpatient-simplification-batch) · Java 배치 시스템연동

## 그 외 경험
[요약 보기](projects/other-experience) — 진료실 대기 전광판 · 회의록 자동화 · 새롬 채용수납처리 · 전산개발위원회 과제 마스터 (규모가 작거나 직접 구현 범위 확정 전인 항목).

## 기술 스택
Python · Java · JavaScript · SQL · PowerShell / n8n · Robot Framework · Selenium · Playwright · FastAPI · Flask · Oracle · LLM 연계

## 보안
[SECURITY.md](SECURITY.md) 참조.
