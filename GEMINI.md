# 🚀 G-ensemble KOSPI 분석 봇 프로젝트 가이드

## 📌 프로젝트 개요
- **목표**: 매일 오전 9시 10분(KST), 유튜브 센티멘트와 시장 지표를 앙상블 분석하여 디스코드로 리포트 전송.
- **주요 경로**: `D:\G-ensemble`
- **배포 환경**: GCP Cloud Run (Cloud Scheduler 매일 09:10 KST 정기 실행)

## 🛠 현재 시스템 상태 (2026-09-06 업데이트)
### 1. AI 모델 및 라이브러리
- **SDK**: `google-genai` 최신 버전 적용.
- **주력 모델**: `gemini-3.8-flash` (5단계 폴백 체인: `3.8-flash` → `3.7-flash` → `3.6-flash` → `3.5-flash` → `2.5-flash`).
- **런타임**: Python 3.14 호환 완료.
- **데이터 정합성**: Holiday/Bullet 감지 로직 구현 완료.

### 2. 배포 환경
- **실행 환경**: **GCP Cloud Run (Always Free 티어)** — Cloud Scheduler(`09:10 KST`) 단일 정기 실행 (`g-ensemble-bot-job`).
- **06시 토큰 잡 완전 퇴역**: KIS 토큰은 09:10 실행 시 인메모리로 발급. 과거 06:00 잡(`g-ensemble-bot-token-job`)은 영구 삭제됨 (재생성 금지).
- **Artifact Registry 과금 방지**: `containerscanning`/`containeranalysis` API 비활성화 유지 (Always Free 보호).
- **GitHub Actions**: cron 스케줄 비활성화 (2026-07-25). `workflow_dispatch`(수동)만 유지.
- **GitHub**: 버전 관리(소스코드 관리) 전용.

## 🚀 배포 및 인프라 정책
- **표준 절차**: 모든 배포는 `docs/DEPLOYMENT.md`에 명시된 표준 프로세스를 반드시 준수할 것.
- **리비전 관리**: `--update-labels` 옵션을 사용하여 `[타입]-[내용]-[버전]` 규칙에 따라 리비전을 기록할 것.
- **환경 변수**: 로컬 `.env` 기반 임시 `env_vars.yaml`을 생성하여 주입하며, 배포 직후 즉시 삭제할 것. (GitHub Secrets는 수동 테스트용 동기화 유지)
- **저의존성 우선 원칙**: 작업 계획 수립 및 리팩토링 시 타 모듈/라이브러리 의존성이 적은 작업부터 순차 진행할 것.
- **상세 가이드**: 구체적인 명령어 및 트러블슈팅은 `docs/DEPLOYMENT.md`를 참조할 것.
- **알고리즘 스펙**: 가중치 산출 및 시장 판정 기준은 `docs/ALGORITHM.md`를 참조할 것.

> **에이전트 행동 규칙** (세션 훅, 문서화 원칙, 보안 등)은 `.agents/AGENTS.md`에서 관리합니다.
