import requests
import json
import os
import time
from dotenv import load_dotenv

# 경로 설정 (GCP 호환성 반영)
if os.environ.get('K_SERVICE'):
    TOKEN_FILE = "/tmp/kis_token.txt"
    ENV_PATH = None # GCP는 환경변수에서 직접 읽음
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    TOKEN_FILE = os.path.join(BASE_DIR, "kis_token.txt")
    ENV_PATH = os.path.join(BASE_DIR, "../.env")

if ENV_PATH:
    load_dotenv(ENV_PATH)
else:
    load_dotenv() # Default 로드

APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')
BASE_URL = "https://openapi.koreainvestment.com:9443"

def refresh_kis_token():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting KIS Token Refresh...")
    url = f"{BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    
    try:
        res = requests.post(url, data=json.dumps(payload), timeout=10)
        if res.status_code == 200:
            data = res.json()
            token = data.get('access_token')
            # 24시간 유효하지만 안전하게 23시간으로 저장
            expire_at = time.time() + data.get('expires_in', 86400) - 3600
            
            with open(TOKEN_FILE, "w") as f:
                f.write(f"{token}\n{expire_at}")
            print("✅ KIS Token Refreshed and Saved Successfully.")
            return True
        else:
            print(f"❌ Token Refresh Failed: {res.text}")
    except Exception as e:
        print(f"❌ Token Refresh Error: {e}")
    return False

if __name__ == "__main__":
    refresh_kis_token()
