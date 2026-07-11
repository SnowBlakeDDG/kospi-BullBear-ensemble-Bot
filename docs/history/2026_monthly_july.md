# 📅 2026년 7월 — G-ensemble 월간 작업 로그

## 2026-07-12 (토) — GCP → GitHub Actions 마이그레이션

### Main Tasks

#### 1. 인프라 마이그레이션 (GCP Cloud Run → GitHub Actions)
- **배경**: GCP 무료 크레딧 만료(~7/18) 대비, 비용 0원 자동화 유지 필요
- **적용 파일**:
  - `.github/workflows/kospi_bot.yml` — cron `'10 0 * * *'` (09:10 KST) 활성화, KIS Secrets 5개 주입
  - `main.py` — `functions_framework` 조건부 import (`try/except`), BOM 방어 로직 (`.replace('\ufeff', '')`)
  - `.gitignore` — 보안 강화 (kis_token.txt, 대용량 JSON, __pycache__ 제외)

#### 2. GitHub 리포지토리 초기 Push
- 32 files, 3,426줄 커밋 및 push 완료
- `gh` CLI 설치 (`winget install GitHub.cli`) + 브라우저 인증 (`SnowBlakeDDG`)
- GitHub Secrets 5개 등록: `GEMINI_API_KEY`, `DISCORD_WEBHOOK_URL`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `KRX_AUTH_KEY`

#### 3. 워크플로우 테스트 (3회)
- 1차: 실행 성공, Discord BOM 에러 (`\ufeff\ufeff` prefix)
- 2차: `Get-Content -Raw` 파이프도 BOM 잔존
- 3차: `--body` 직접 전달 + 코드 방어 → **완전 성공 (1m32s)**

### Technical Notes
- **PowerShell BOM 오염**: `echo` / `Get-Content -Raw` 파이프 시 UTF-16 BOM 삽입 → `gh secret set` 값 오염
  - ❌ `echo "val" | gh secret set NAME` — BOM 삽입
  - ❌ `[IO.File]::WriteAllText() → Get-Content -Raw |` — 여전히 BOM
  - ✅ `gh secret set NAME --body "val"` — BOM-free 확정
- **Gemini ascii 에러**: BOM이 `GEMINI_API_KEY`에도 혼입 → `--body` 재등록으로 해결

### Doc Updates
- `IDEAs.md` — To-Do 갱신 (GA 안정성 확인, 06시 잡 정리, Node.js 경고 추가)
- `docs/history/2026_monthly_july.md` — 신규 생성 (본 문서)
