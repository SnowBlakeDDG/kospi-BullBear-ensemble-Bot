<#
.SYNOPSIS
    G-ensemble GCP Cloud Functions (Gen 2) Windows 배포 스크립트
.DESCRIPTION
    .env 파일에서 필수 환경 변수를 추출하여 임시 env_vars.yaml을 생성하고,
    GCP Cloud Functions로 배포한 뒤 임시 파일을 안전하게 삭제합니다.
.PARAMETER Version
    배포 버전 레이블 (기본값: feat-python314-v1)
.PARAMETER Runtime
    Python 런타임 (기본값: python314)
.EXAMPLE
    .\deploy.ps1
    .\deploy.ps1 -Version "feat-update-v2" -Runtime "python314"
#>
param(
    [string]$Version = "feat-python314-v1",
    [string]$Runtime = "python314",
    [string]$Region = "asia-northeast3",
    [string]$FunctionName = "g-ensemble-bot",
    [string]$EntryPoint = "gensemble_handler"
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "🚀 G-ensemble GCP Deploy (Windows PowerShell)" -ForegroundColor Cyan
Write-Host "   Version : $Version" -ForegroundColor Yellow
Write-Host "   Runtime : $Runtime" -ForegroundColor Yellow
Write-Host "   Region  : $Region" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

# 1. 환경 변수 준비
$envFile = ".env"
$yamlFile = "env_vars.yaml"
$envKeys = @("GEMINI_API_KEY", "DISCORD_WEBHOOK_URL", "KIS_APP_KEY", "KIS_APP_SECRET", "KRX_AUTH_KEY")

if (-not (Test-Path $envFile)) {
    Write-Error "❌ .env 파일이 존재하지 않습니다. 배포를 중단합니다."
}

if (Test-Path $yamlFile) {
    Remove-Item $yamlFile -Force
}

Write-Host "⚙️  환경 변수 추출 및 YAML 생성 중..." -ForegroundColor Gray
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line -split '=', 2
        $key = $parts[0].Trim()
        if ($envKeys -contains $key) {
            $val = $parts[1].Trim().Trim('"').Trim("'")
            Add-Content -Path $yamlFile -Value ($key + ': "' + $val + '"')
        }
    }
}

try {
    Write-Host "☁️  Cloud Functions (Gen 2) 배포 시작..." -ForegroundColor Green
    gcloud functions deploy $FunctionName `
        --gen2 `
        --runtime=$Runtime `
        --region=$Region `
        --source=. `
        --entry-point=$EntryPoint `
        --trigger-http `
        --allow-unauthenticated `
        --env-vars-file=$yamlFile `
        --timeout=120s `
        --update-labels "version=$Version"

    if ($LASTEXITCODE -ne 0) {
        throw "gcloud functions deploy failed with exit code $LASTEXITCODE"
    }

    Write-Host "⏰ Cloud Scheduler (09:10 KST) 동기화..." -ForegroundColor Green
    $uri = (gcloud functions describe $FunctionName --region=$Region --format='value(serviceConfig.uri)')
    
    gcloud scheduler jobs update http "$FunctionName-job" `
        --location=$Region `
        --uri=$uri `
        --schedule="10 9 * * *" `
        --time-zone="Asia/Seoul"

    # [가드레일] 과거 레거시 06:00 토큰 잡 자동 감지 및 영구 삭제
    $legacyJob = "$FunctionName-token-job"
    $checkLegacy = gcloud scheduler jobs list --location=$Region --filter="name:$legacyJob" --format="value(ID)"
    if ($checkLegacy) {
        Write-Host "🧹 [가드레일] 퇴역된 레거시 스케줄러($legacyJob) 감지됨. 자동 삭제합니다..." -ForegroundColor Yellow
        gcloud scheduler jobs delete $legacyJob --location=$Region --quiet
    }

    Write-Host "✅ 배포 및 스케줄러 동기화 완료!" -ForegroundColor Cyan
}
finally {
    # 보안을 위해 임시 생성된 env_vars.yaml 반드시 삭제
    if (Test-Path $yamlFile) {
        Remove-Item $yamlFile -Force
        Write-Host "🧹 임시 $yamlFile 삭제 완료." -ForegroundColor Gray
    }
}
