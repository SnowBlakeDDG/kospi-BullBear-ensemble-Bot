# 🚀 G-ensemble KOSPI 분석 봇 프로젝트 가이드

## 📌 프로젝트 개요
- **목표**: 매일 오전 9시 10분(KST), 유튜브 센티멘트와 시장 지표를 앙상블 분석하여 디스코드로 리포트 전송.
- **주요 경로**: `D:\G-ensemble`
- **배포 환경**: GitHub Actions (매일 00:10 UTC / 09:10 KST 실행)

## 🛠 현재 시스템 상태 (2026-04-22 업데이트)
### 1. AI 모델 및 라이브러리
- **SDK**: `google-genai` 최신 버전 적용.
- **주력 모델**: `gemini-2.5-flash`.
- **데이터 정합성**: Holiday/Bullet 감지 로직 구현 완료 (로컬).

### 2. 배포 환경
- **GCP 일원화**: GitHub Actions 스케줄러 중단 및 Cloud Scheduler(09:10 KST)로 통합 완료.

## 🚀 GCP 배포 및 인프라 정책
- **표준 절차**: 모든 배포는 `DEPLOYMENT.md`에 명시된 표준 프로세스를 반드시 준수할 것.
- **리비전 관리**: `--update-labels` 옵션을 사용하여 `[타입]-[내용]-[버전]` 규칙에 따라 리비전을 기록할 것.
- **환경 변수**: 보안을 위해 `.env` 파일은 배포에서 제외하며, `env_vars.yaml`을 통한 주입 방식을 유지할 것.
- **상세 가이드**: 구체적인 명령어 및 트러블슈팅은 `DEPLOYMENT.md`를 참조할 것.

## 🔄 세션 시작 자동 브리핑 (Session Entry Hook)
- **환경 설정**: 한글 깨짐 방지를 위해 세션 시작 즉시 아래 PowerShell 명령어를 실행하여 인코딩을 UTF-8로 맞출 것.
  - `chcp 65001; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8`
- **절차**: 인코딩 설정 후, **반드시** `IDEAs.md`의 **"지난 세션에 이어서 (To-Do)"** 섹션을 읽고 현재 상태를 브리핑할 것.

## 🏁 세션 종료 시 히스토리 정리 (Session Exit Hook)
- **트리거**: 사용자가 "요약 부탁해" 또는 히스토리 정리를 요청할 때만 정리를 시작할 것.
- **절차**: 당일 진행된 주요 작업과 트러블슈팅 내용을 요약하여 사용자에게 보고하고 승인을 받을 것.
- **문서화 원칙 (Style & Standard)**:
    - **파일 관리**: 월별 로그는 `docs/history/` 폴더에 `[YYYY]_monthly_[month].md` 형식으로 역순(최신순) 기록. (예: 2026_monthly_april.md)
    - **분리 보관 (Sustainability)**: 작업 성격에 따라 아래 문서에 즉시 분산 저장하여 최신성을 유지할 것.
        - 기술 가이드 및 인프라: `DEPLOYMENT.md`
        - 향후 과제 및 미완료 이슈: `IDEAs.md` (반드시 이관하여 지속성 유지)
        - 프로젝트 운영 정책: `GEMINI.md`
    - **리포트 표준 구조**:
        - **Main Tasks**: 분야별 변경 내용 및 적용 파일 요약.
        - **Technical Notes**: 발생한 이슈(Error) 및 대응책(Troubleshooting) 기록.
        - **Doc Updates**: 어떤 문서가 어떻게 업데이트되었는지 명시.
    - **수정 방식 (Efficiency)**: 파일 수정 시 전체 내용을 다시 쓰지 않고, `replace` 도구 등을 사용하여 변경이 필요한 단락이나 코드 블록 단위로 정밀하게 수정할 것. (맥락 유지 및 토큰 효율성 증대)


## ⚠️ 주의 사항
- **보안**: `.env` 파일 및 서비스 계정 키는 절대 GitHub에 푸시하지 말 것.
- **동기화**: API 키나 웹훅 변경 시 GitHub Secrets와 로컬 `.env`를 동시에 업데이트할 것.
- **인코딩**: 윈도우 환경에서 쉘 출력 시 한글 깨짐 방지를 위해 `chcp 65001`을 항상 우선 실행할 것.
