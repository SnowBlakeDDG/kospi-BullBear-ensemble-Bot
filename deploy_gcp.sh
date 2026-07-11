#!/bin/bash

# GCP 프로젝트 설정
PROJECT_ID=$(gcloud config get-value project)
REGION="asia-northeast3"
FUNCTION_NAME="g-ensemble-bot"
ENTRY_POINT="gensemble_handler"

echo "--- Preparing environment variables ---"
# .env 파일에서 필요한 변수만 추출하여 env_vars.yaml 생성
ENV_FILE="env_vars.yaml"
echo "# Generated environment variables" > $ENV_FILE

# .env 파일을 읽어서 key: "value" 형식으로 저장 (필수 변수들)
keys=("GEMINI_API_KEY" "DISCORD_WEBHOOK_URL" "KIS_APP_KEY" "KIS_APP_SECRET" "KRX_AUTH_KEY")
for key in "${keys[@]}"; do
    val=$(grep "^$key=" .env | cut -d'=' -f2- | sed 's/^"//;s/"$//')
    if [ ! -z "$val" ]; then
        echo "$key: \"$val\"" >> $ENV_FILE
    fi
done

echo "--- Deploying G-ensemble to GCP Cloud Functions (2nd Gen) ---"

gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --runtime=python310 \
    --region=$REGION \
    --source=. \
    --entry-point=$ENTRY_POINT \
    --trigger-http \
    --allow-unauthenticated \
    --env-vars-file=$ENV_FILE \
    --timeout=120s \
    --update-labels=version=feat-ensemble-v2-0

# 보안을 위해 생성된 파일 삭제
rm $ENV_FILE

echo "--- Setting up Cloud Scheduler ---"
# URI 자동 추출
URI=$(gcloud functions describe $FUNCTION_NAME --region=$REGION --format='value(serviceConfig.uri)')

# 메인 분석 잡 (09:10)
gcloud scheduler jobs update http $FUNCTION_NAME-job \
    --location=$REGION \
    --uri=$URI \
    --schedule="10 9 * * *"

# 토큰 갱신 잡 (06:00)
gcloud scheduler jobs update http $FUNCTION_NAME-token-job \
    --location=$REGION \
    --uri="$URI/kis_token_handler" \
    --schedule="0 6 * * *"

echo "--- Deployment Finished! ---"
