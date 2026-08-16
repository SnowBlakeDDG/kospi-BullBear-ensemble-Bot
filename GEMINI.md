# 🚀 G-ensemble KOSPI 분석 봇 프로젝트 가이드

## 📌 프로젝트 개요
- **목표**: 매일 오전 9시 10분(KST), 유튜브 센티멘트와 시장 지표를 앙상블 분석하여 디스코드로 리포트 전송.
- **주요 경로**: `D:\G-ensemble`
- **배포 환경**: GitHub Actions (매일 00:10 UTC / 09:10 KST 실행)

## 🛠 현재 시스템 상태 (2026-08-16 업데이트)
### 1. AI 모델 및 라이브러리
- **SDK**: `google-genai` 최신 버전 적용.
- **주력 모델**: `gemini-3.7-flash` (폴백: `gemini-3.6-flash`).
- **데이터 정합성**: Holiday/Bullet 감지 로직 구현 완료.

### 2. 배포 환경
- **실행 환경**: **GCP Cloud Run (Always Free 티어)** — Cloud Scheduler(`09:10 KST`) 정기 실행.
- **GitHub Actions**: cron 스케줄 비활성화 (2026-07-25). `workflow_dispatch`(수동)만 유지.
- **GitHub**: 버전 관리(소스코드 관리) 전용.
- KIS 토큰은 매 실행 시 신규 발급 (별도 갱신 잡 불필요).

## 🚀 배포 및 인프라 정책
- **표준 절차**: 모든 배포는 `docs/DEPLOYMENT.md`에 명시된 표준 프로세스를 반드시 준수할 것.
- **리비전 관리**: `--update-labels` 옵션을 사용하여 `[타입]-[내용]-[버전]` 규칙에 따라 리비전을 기록할 것.
- **환경 변수**: 보안을 위해 `.env` 파일은 배포에서 제외하며, GitHub Secrets를 통한 주입 방식을 유지할 것.
- **상세 가이드**: 구체적인 명령어 및 트러블슈팅은 `docs/DEPLOYMENT.md`를 참조할 것.
- **알고리즘 스펙**: 가중치 산출 및 시장 판정 기준은 `docs/ALGORITHM.md`를 참조할 것.

> **에이전트 행동 규칙** (세션 훅, 문서화 원칙, 보안 등)은 `.agents/AGENTS.md`에서 관리합니다.
