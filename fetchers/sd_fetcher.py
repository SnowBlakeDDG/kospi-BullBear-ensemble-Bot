import requests
import json
import os
import time
from datetime import datetime
from .base_fetcher import BaseFetcher

class SDFetcher(BaseFetcher):
    """
    KOSPI 수급(Spot & Futures) 데이터 수집기
    한국투자증권(KIS) Open API를 활용합니다.
    """
    def __init__(self, app_key=None, app_secret=None):
        self.app_key = app_key or os.getenv('KIS_APP_KEY')
        self.app_secret = app_secret or os.getenv('KIS_APP_SECRET')
        self.base_url = "https://openapi.koreainvestment.com:9443"
        
        # GCP 환경(K_SERVICE 존재)이면 /tmp 사용, 로컬이면 기존 경로 사용
        if os.environ.get('K_SERVICE'):
            self.token_file = "/tmp/kis_token.txt"
        else:
            self.token_file = os.path.join(os.path.dirname(__file__), "../KIS_open_api_test/kis_token.txt")
            os.makedirs(os.path.dirname(self.token_file), exist_ok=True)

    def _get_access_token(self):
        """저장된 Access Token 읽기 및 필요 시 신규 발급 (최대 3회 재시도)"""
        # 1. 기존 토큰 파일 확인 및 유효성 검사
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 2:
                        saved_token = lines[0].strip()
                        expire_time = float(lines[1].strip())
                        if time.time() < expire_time:
                            print("🔑 기존 KIS Token 재사용")
                            return saved_token
            except: pass
        
        # 2. 토큰이 없거나 만료된 경우 신규 발급 (최대 3회 재시도)
        print("🔑 KIS Token이 없거나 만료되었습니다. 신규 발급을 시도합니다...")
        url = f"{self.base_url}/oauth2/tokenP"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        for attempt in range(3):
            try:
                res = requests.post(url, data=json.dumps(payload), timeout=15)
                if res.status_code == 200:
                    data = res.json()
                    token = data.get('access_token')
                    expire_at = time.time() + data.get('expires_in', 86400) - 3600
                    with open(self.token_file, "w") as f:
                        f.write(f"{token}\n{expire_at}")
                    print("✅ KIS Token issued and saved successfully.")
                    return token
                else:
                    print(f"❌ KIS Token [{res.status_code}] (시도 {attempt+1}/3): {res.text[:100]}")
            except Exception as e:
                print(f"❌ KIS Token Error (시도 {attempt+1}/3): {e}")
            
            if attempt < 2:
                wait = 3 * (attempt + 1)  # 3초, 6초
                print(f"⏳ {wait}초 후 재시도...")
                time.sleep(wait)
        
        print("❌ KIS Token 발급 최종 실패")
        return None

    def _fetch_trend(self, token, market_code, sub_code):
        """시장별 투자자매매동향 API 호출 (최대 2회 재시도)"""
        url = f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHPTJ04030000",
            "custtype": "P"
        }
        params = {
            "fid_input_iscd": market_code,
            "fid_input_iscd_2": sub_code
        }
        
        for attempt in range(3):
            try:
                res = requests.get(url, headers=headers, params=params, timeout=15)
                if res.status_code == 200:
                    output = res.json().get('output', [])
                    return output[0] if isinstance(output, list) and output else output
                else:
                    print(f"⚠️ KIS [{market_code}] HTTP {res.status_code} (시도 {attempt+1}/3)")
            except Exception as e:
                print(f"⚠️ KIS [{market_code}] 에러 (시도 {attempt+1}/3): {e}")
            
            if attempt < 2:
                time.sleep(2 * (attempt + 1))  # 2초, 4초
        
        print(f"❌ KIS [{market_code}] 데이터 수집 최종 실패")
        return {}

    def fetch(self, kr_holidays={}):
        data = {
            'individual': 0, 
            'foreign': 0, 
            'foreign_futures': 0, 
            'is_holiday': False
        }
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 1. 주말 체크 (5: 토요일, 6: 일요일)
        if now.weekday() >= 5:
            data['is_holiday'] = True
            data['holiday_name'] = "주말 휴장"
            return data

        # 2. 공휴일 체크
        if today_str in kr_holidays:
            data['is_holiday'] = True
            data['holiday_name'] = kr_holidays[today_str]['name']
            return data

        token = self._get_access_token()
        if not token:
            return data

        # 1. 코스피 현물 (KSP / 0001)
        spot = self._fetch_trend(token, "KSP", "0001")
        # KIS API 대금 단위는 '백만원' 기준인 경우가 많으므로 확인 필요.
        # 테스트 결과 -19,496.2억 형태였으므로 int() 변환 시 억 단위 유지됨.
        data['individual'] = int(spot.get('prsn_ntby_tr_pbmn', 0))
        data['foreign'] = int(spot.get('frgn_ntby_tr_pbmn', 0))

        # 2. 코스피 200 선물 (K2I / F001)
        futures = self._fetch_trend(token, "K2I", "F001")
        data['foreign_futures'] = int(futures.get('frgn_ntby_tr_pbmn', 0))

        return data
