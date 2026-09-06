# 📅 2026년 9월 작업 로그 (September History)

---

## 🚀 [2026-09-06] GCP 인프라 과금 차단, 06시 레거시 퇴역, 09:10 지표 복원력 강화 & Gemini 3.8 Flash 도입

### 1. Main Tasks
- **Artifact Registry 과금 차단 및 10개 CVE 원인 규명**:
  - `containerscanning.googleapis.com` 및 `containeranalysis.googleapis.com` API 비활성화.
  - 10건의 취약점이 GCP Cloud Buildpack 내부 Go 1.26.5 런처(`/cnb/lifecycle/launcher`) 이슈임을 규명하고 Always Free 티어 보호 조치 완료.
- **06:00 레거시 장전 리포트/토큰 잡 완전 퇴역 (Deprecation)**:
  - 2026-04-24 등록된 Cloud Scheduler `g-ensemble-bot-token-job` 영구 삭제.
  - `main.py`의 `gensemble_handler`에 비인가 경로(`/kis_token_handler`) 410 Gone 차단 가드레일 구축.
  - `deploy.ps1`에 레거시 스케줄러 자동 감지 및 삭제 로직 내장.
- **09:10 지표 무작위 누락/0값 복원력 강화**:
  - `fetchers/sd_fetcher.py`: 실수형(`"-19496.2"`), 콤마, 빈문자열 파싱용 `_safe_to_int` 정적 유틸 도입 및 401 토큰 자동 재발급 로직 구현.
  - `fetchers/global_fetcher.py`: `period='2d'`를 `period='5d'`로 확장, `dropna()` 적용, 2회 재시도 및 기본 키 보장.
  - `fetchers/stock_fetcher.py` & `fetchers/fx_fetcher.py`: 티커별 예외 격리 및 재시도 메커니즘 탑재.
- **장중 수급 기울기 트래킹 기능 블록 기획 반영**:
  - `docs/IDEAs.md`에 개인/외인/기관계 순매수량 및 기울기(속도) 기반 장중 트래킹 블록 신규 To-Do 등록.
- **AI 주력 모델 Gemini 3.8 Flash 승격 & 5단계 순차 폴백 체인 구축**:
  - 주력 모델을 `gemini-3.8-flash`로 업그레이드.
  - 5단계 폴백 체인: `gemini-3.8-flash` → `gemini-3.7-flash` → `gemini-3.6-flash` → `gemini-3.5-flash` → `gemini-2.5-flash`.
  - `test_runner.py` 실행 시 503 트래픽 집중 상황에서 3.8 → 3.7 → 3.6 → 3.5-flash로 자동 폴백되어 분석 완수 검증 완료.

### 2. Technical Notes
- **Error 1: Artifact Registry 유료 취약점 검사 과금**:
  - **원인**: Container Scanning API 활성화로 이미지 푸시마다 유료 스캔(약 $0.26) 발생.
  - **대응**: API 비활성화로 Always Free 티어 복구 완료.
- **Error 2: 06:00 장전 리포트 디스코드 무단 발송**:
  - **원인**: 과거 `g-ensemble-bot-token-job`이 남아있었고, Cloud Functions 단일 핸들러가 경로를 무시하고 `main()`을 실행함.
  - **대응**: 잡 삭제 + 엔드포인트 410 차단 + 배포 스크립트 자동 정리 3중 방어선 구축.
- **Error 3: 09:10 지표 무작위 0값/누락**:
  - **원인**: KIS 응답 실수 문자열 `int()` 호출 시 `ValueError`, yfinance `period='2d'`의 휴일 직후 데이터 부족.
  - **대응**: `_safe_to_int` 및 5거래일 조회(`period='5d'`)로 안정화 완료.
- **Error 4: yfinance 커스텀 세션 불가**:
  - **원인**: 최신 yfinance는 내부적으로 `curl_cffi` 기반 세션을 직접 관리함. 커스텀 requests 세션 주입 시 `YFDataException` 발생.
  - **대응**: 기본 세션을 유지하고 `period='5d'` 및 순수 재시도 루프로 안정성 확보.

### 3. Doc Updates
- `GEMINI.md`: 06시 잡 퇴역 명시, Always Free 보호 정책 추가, 주력 모델 `gemini-3.8-flash` 및 5단계 폴백 체인 반영.
- `.agents/AGENTS.md`: 06시 스케줄러 금지 및 유료 스캐닝 API 활성화 금지 영구 보안 룰 등록.
- `docs/DEPLOYMENT.md`: 트러블슈팅 4, 5번 및 배포 이력(`fix-infra-cost-guard-v1`, `feat-model-3-8-flash-v1`) 등록.
- `docs/IDEAs.md`: 장중 수급 기울기 트래킹 To-Do 등록 및 완료 작업 최신화.
- `models/yt_analyzer.py` & `test_runner.py`: 3.8-flash 메인 모델 및 5단계 폴백 체인 적용.
