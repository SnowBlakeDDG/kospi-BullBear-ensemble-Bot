# 🚀 G-ensemble GCP 배포 및 버전 관리 규칙

이 문서는 GCP Cloud Functions 배포 시 레이블(Labels)을 이용한 일관된 버전 관리를 위한 규칙 및 표준 배포 절차를 정의합니다.

## 1. 버전 레이블(Version Label) 명명 규칙
배포 시 `--update-labels` 옵션의 `version` 키에 사용할 값은 아래 형식을 따릅니다.
형식: `[타입]-[내용]-[버전]` (모두 소문자, 하이픈 사용)

- **feat-**: 새로운 기능 추가 (예: `feat-kis-api-v1`)
- **fix-**: 버그 수정 (예: `fix-token-path-v2`)
- **perf-**: 성능 및 메모리 최적화 (예: `perf-memory-512-v1`)
- **env-**: 환경 변수나 설정 변경 (예: `env-update-api-key-v1`)
- **refactor-**: 코드 구조 개선 (예: `refactor-main-logic-v3`)

## 2. 배포 후 검증 절차
1. `gcloud functions call g-ensemble-bot --region=asia-northeast3 --gen2` 실행
2. 디스코드 알림 수신 및 표 양식(3열 격자) 확인
3. 에러 발생 시 로그 확인: `gcloud functions logs read g-ensemble-bot --region=asia-northeast3 --gen2 --limit=20`

## 🚀 최신 표준 배포 프로세스 (2026-04-24 업데이트)

### ⚠️ 인프라 운영 현황 (2026-07-25 업데이트)
- **실행 환경**: **GCP Cloud Run (Always Free 티어)** — Cloud Scheduler(09:10 KST)로 정기 실행.
- **GitHub Actions**: cron 스케줄 **비활성화** (2026-07-25). `workflow_dispatch`(수동 실행)만 유지.
- **GitHub**: 버전 관리(소스코드) 전용. Secrets 5개는 수동 테스트용으로 잔존.
- **배포 방식**: 로컬에서 `gcloud` 명령어를 통해 배포하며, 리비전 레이블을 반드시 첨부할 것.

KIS API 도입 및 토큰 갱신 이원화에 따른 최신 배포 절차입니다.

### 1. 환경 변수 주입 및 배포 (PowerShell)
PowerShell의 특수문자 파싱 문제를 피하기 위해 `env_vars.yaml` 파일을 임시로 생성하여 배포하는 방식을 권장합니다.

```powershell
# 1. 필수 환경 변수를 포함한 YAML 생성
$env_keys = "GEMINI_API_KEY", "DISCORD_WEBHOOK_URL", "KIS_APP_KEY", "KIS_APP_SECRET", "KRX_AUTH_KEY"
if (Test-Path "env_vars.yaml") { Remove-Item "env_vars.yaml" }
Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    if ($line -and $line.Contains("=")) {
        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        if ($env_keys -contains $key) {
            $val = $parts[1].Trim()
            Add-Content -Path "env_vars.yaml" -Value "$key: `"$val`""
        }
    }
}

# 2. Cloud Functions 배포
gcloud functions deploy g-ensemble-bot `
    --gen2 `
    --runtime=python310 `
    --region=asia-northeast3 `
    --source=. `
    --entry-point=gensemble_handler `
    --trigger-http `
    --allow-unauthenticated `
    --env-vars-file=env_vars.yaml `
    --update-labels=version=feat-kis-futures-v1-0

# 3. 임시 파일 삭제
Remove-Item env_vars.yaml
```

### 2. Cloud Scheduler 정기 실행 설정 (09:10 KST)
KIS API 토큰은 매 실행 시 자동 발급되므로 06시 별도 잡 없이 **09:10 메인 분석 잡만 단일 운영**합니다.

```powershell
# 함수 URI 추출
$uri = (gcloud functions describe g-ensemble-bot --region=asia-northeast3 --format='value(serviceConfig.uri)')

# 메인 분석 (매일 09:10 KST)
gcloud scheduler jobs update http g-ensemble-bot-job `
    --schedule="10 9 * * *" --time-zone="Asia/Seoul" --uri=$uri --http-method=GET --location=asia-northeast3
```

## ⚠️ 트러블슈팅 (Troubleshooting)

### 1. PowerShell 구문 오류 (`:` 및 특수문자)
- **현상**: PowerShell에서 `:` 문자가 변수 드라이브명으로 오인되어 `InvalidVariableReferenceWithDrive` 에러 발생.
- **대응**: 모든 키-값 쌍을 큰따옴표(`""`)로 감싸고, 파이프라인(`ForEach-Object`) 내에서 `Add-Content`를 사용하는 문자열 직결합 방식으로 해결.

### 2. Gen 2 리비전 이름 관리
- Cloud Functions Gen 2에서 수동 리비전 관리가 필요한 경우, `--revision-suffix` 대신 레이블(`--update-labels`)을 사용하는 방식을 기본으로 하며, 필요한 경우 Cloud Run 명령어를 별도로 검토한다.

### 3. GCP 파일 시스템 제한
- **현상**: 로컬 파일 시스템에 토큰이나 임시 데이터 저장 시 에러 발생.
- **대응**: GCP 환경(`K_SERVICE` 존재 시)에서는 반드시 `/tmp` 경로를 사용하도록 코드 내 분기 처리 적용.

## 📜 배포 이력 (Deployment History)

| 날짜 | 버전 레이블 (Version Label) | 변경 사항 및 비고 |
| :--- | :--- | :--- |
| 2026-04-22 | logic-v1.8_spec-v1 | `sd_fetcher` 버그 수정 및 최신 `Holiday/Bullet` 로직 반영. |
| 2026-04-24 | feat-logic-v1-8-final | v1.8 정밀 알고리즘 최종 반영 및 GCP `/tmp` 경로 최적화 완료. |
| 2026-04-24 | feat-kis-futures-v1-0 | KIS API 연동(현물/선물), GlobalFetcher(VIX/DXY) 추가, 토큰 갱신 스케줄러 분리 배포. |
| 2026-07-12 | ga-migration-v1-0 | **GCP → GitHub Actions 마이그레이션**. cron 09:10 KST, BOM 방어 로직, Secrets 5개 등록. |
| 2026-07-25 | — | **GA cron 비활성화**, GCP Cloud Run Always Free 티어로 운영 복귀. GitHub은 버전 관리 전용. |
| 2026-08-16 | feat-model-3-7-flash-v1 | AI 모델 업그레이드: 주력 `gemini-3.7-flash`, 폴백 `gemini-3.6-flash`. |
| 2026-08-16 | feat-python314-v1 | **Python 3.14 마이그레이션**: Python 3.10 EOL 대비 종속성 영향평가 완료, GA/GCP 런타임 3.14 갱신. |

## 🔀 GitHub Actions 운영 가이드 (2026-07-12~ / 비활성화: 2026-07-25)

### 인프라 전환 요약
- **Phase 1** (~ 2026-07-12): GCP Cloud Functions Gen2 + Cloud Scheduler (09:10 / 06:00 KST)
- **Phase 2** (2026-07-12 ~ 07-25): GitHub Actions cron (`'10 0 * * *'` = 09:10 KST)
- **Phase 3** (2026-07-25~): **GCP Cloud Run Always Free 복귀**. GA cron 비활성화, GitHub은 VCS 전용
- **06시 토큰 갱신**: 불필요 (GA에서는 매 실행 시 KIS 토큰 신규 발급)

### Secrets 관리
GitHub repo → Settings → Secrets → Actions에서 관리. `gh` CLI로도 가능:
```powershell
# BOM 방지: 반드시 --body 옵션 사용 (파이프 금지!)
gh secret set SECRET_NAME --repo SnowBlakeDDG/kospi-BullBear-ensemble-Bot --body "VALUE"
```

### 수동 실행
```powershell
gh workflow run "KOSPI G-ensemble Bot" --repo SnowBlakeDDG/kospi-BullBear-ensemble-Bot --ref main
```

