# 지출결의서 자동 상신 (RPA · 백엔드)

> ⚠️ 공개본 안내: 실제 그룹웨어 URL·기관명·사업자번호·[협력업체]명·계정(.env)은 포함하지 않습니다. 외부 데모 골격에서 출발했으므로 "최초 개발"로 표기하지 않으며, 핵심 기능(백엔드·RPA·매핑·안전장치)은 직접 구현했습니다.

## 문제
그룹웨어 지출결의서를 담당자가 매 건 수기로 작성하고, 영수증 정보를 손으로 옮겨 입력했다. 계정과목·승인선 선택이 팝업·iframe으로 번거롭고 오타·시간 소모가 컸다.

## 접근
구조화된 지출 데이터를 받아 그룹웨어에 지출결의서를 자동 작성하는 **백엔드 + RPA 엔드투엔드** 서비스. 진행상황을 실시간 확인하고 실패 원인을 가시화한다. 앞단 영수증 OCR/데이터화는 AI 플랫폼([협력업체]) 연계.

## 아키텍처
```
(AI 영수증 OCR → 구조화 [협력업체])
  → HTTP POST /api/automation/start
  → Flask 작업 큐(TaskQueue) + Redis 이력(없으면 메모리 폴백)
  → RobotManager: Robot Framework subprocess 실행 (변수파일 동적 생성)
  → Robot: 로그인 → MAIN iframe 전환 → 계정과목 팝업 검색/선택 → 폼 입력 → 승인선 지정 → 저장
  → stdout 파싱 → 진행 6단계 이벤트 → WebSocket(SocketIO) 실시간 회신
```

## 핵심 기술 / 안전장치
- Flask REST(`/api/automation/start|status|result|logs|cancel`) + Flask-SocketIO 실시간 진행률
- **선택적 의존성 폴백**: Redis 장애 시 메모리 이력으로 graceful degradation
- **레거시 웹 자동화 안정화**: iframe 전환 유틸·팝업 처리 키워드 분리, 셀렉터 안정화
- `ExpenseDataMapper`: 지출 데이터 → Robot 변수(계정과목코드·승인선·참조문서) 매핑
- 실패 가시화: 타임아웃 kill, 취소 API, 실패 스크린샷 + 로그 다운로드
- 자격증명은 `.env` 관리(코드 하드코딩 지양)

## 사용 기술
Python, Flask, Flask-SocketIO, Redis(선택), Robot Framework, SeleniumLibrary, ChromeDriver, 스레딩 큐.

## 역할
자동화 서비스(백엔드 + RPA) 핵심 기능 직접 개발. 결함 추적(iframe/승인선) 문서 기반 개선.

## 보여주는 역량
백엔드 + RPA + AI 연계의 엔드투엔드 아키텍처, 실시간 진행 피드백 설계, 레거시 웹 자동화 안정화.

## 가상 재구현
`impl/` — 가상 그룹웨어(iframe/팝업 포함)에 대한 Flask+SocketIO+RF 데모(합성 지출 데이터).
