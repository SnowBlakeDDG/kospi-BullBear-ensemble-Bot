import requests
import json
import os
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# KIS API 설정
APP_KEY = os.getenv('KIS_APP_KEY')
APP_SECRET = os.getenv('KIS_APP_SECRET')
BASE_URL = "https://openapi.koreainvestment.com:9443"
TOKEN_FILE = "KIS_open_api_test/kis_token.txt"

def get_access_token():
    """Access Token 발급 및 캐싱 (24시간 유효)"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            lines = f.readlines()
            if len(lines) >= 2:
                saved_token = lines[0].strip()
                expire_time = float(lines[1].strip())
                if time.time() < expire_time:
                    return saved_token

    url = f"{BASE_URL}/oauth2/tokenP"
    payload = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    res = requests.post(url, data=json.dumps(payload))
    if res.status_code == 200:
        data = res.json()
        token = data.get('access_token')
        expire_at = time.time() + data.get('expires_in', 86400) - 3600
        with open(TOKEN_FILE, "w") as f:
            f.write(f"{token}\n{expire_at}")
        return token
    return None

def fetch_market_investor_trend(token, market_code, sub_code):
    """
    시장별 투자자매매동향(시세) 조회
    TR ID: FHPTJ04030000
    """
    url = f"{BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market"
    
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHPTJ04030000",
        "custtype": "P"
    }
    
    params = {
        "fid_input_iscd": market_code,
        "fid_input_iscd_2": sub_code
    }
    
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        data = res.json()
        output = data.get('output', [])
        # 리스트로 오면 첫 번째 요소(최신 데이터) 반환, 객체면 그대로 반환
        return output[0] if isinstance(output, list) and output else output
    else:
        print(f"❌ API Error [{market_code}/{sub_code}]: {res.status_code}, {res.text}")
        return None

def main():
    print("--- KIS Open API Integrated Market Data Test ---")
    token = get_access_token()
    if not token:
        print("❌ Failed to get Access Token.")
        return

    # 1. 코스피 현물 수급 (KSP / 0001)
    print("\n[1] Fetching KOSPI Spot Data...")
    spot_data = fetch_market_investor_trend(token, "KSP", "0001")
    if spot_data:
        # ntby_tr_pbmn: 순매수 거래 대금
        foreign = int(spot_data.get('frgn_ntby_tr_pbmn', 0))
        individual = int(spot_data.get('prsn_ntby_tr_pbmn', 0))
        institution = int(spot_data.get('orgn_ntby_tr_pbmn', 0))
        print(f"✅ KOSPI Spot -> Foreign: {foreign/100:,.1f}억, Individual: {individual/100:,.1f}억, Inst: {institution/100:,.1f}억")

    time.sleep(0.5) # API 호출 간격

    # 2. 코스피 200 선물 수급 (K2I / F001)
    print("\n[2] Fetching KOSPI 200 Futures Data...")
    futures_data = fetch_market_investor_trend(token, "K2I", "F001")
    if futures_data:
        # 선물도 동일한 필드명 사용
        f_foreign = int(futures_data.get('frgn_ntby_tr_pbmn', 0))
        f_individual = int(futures_data.get('prsn_ntby_tr_pbmn', 0))
        print(f"✅ KOSPI Futures -> Foreign: {f_foreign/100:,.1f}억, Individual: {f_individual/100:,.1f}억")
        
        # 상세 데이터 확인용 출력
        # print(json.dumps(futures_data, indent=2, ensure_ascii=False))

    print("\n--- Test Completed ---")

if __name__ == "__main__":
    main()
