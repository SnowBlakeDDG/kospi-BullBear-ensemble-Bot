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
                elif res.status_code == 401:
                    print(f"⚠️ KIS [{market_code}] 토큰 만료(401) 감지. 캐시 삭제 후 재발급 시도...")
                    if os.path.exists(self.token_file):
                        try: os.remove(self.token_file)
                        except: pass
                    new_token = self._get_access_token()
                    if new_token:
                        headers["authorization"] = f"Bearer {new_token}"
                else:
                    print(f"⚠️ KIS [{market_code}] HTTP {res.status_code} (시도 {attempt+1}/3)")
            except Exception as e:
                print(f"⚠️ KIS [{market_code}] 에러 (시도 {attempt+1}/3): {e}")
            
            if attempt < 2:
                wait_sec = 2 * (attempt + 1)
                time.sleep(wait_sec)
        
        print(f"❌ KIS [{market_code}] 데이터 수집 최종 실패")
        return {}

    @staticmethod
    def _safe_to_int(val, default=0):
        """실수형 문자열('-19496.2'), 콤마, 공백, None 등을 안전하게 int로 변환"""
        if val is None:
            return default
        try:
            s = str(val).strip().replace(',', '')
            if not s:
                return default
            return int(round(float(s)))
        except (ValueError, TypeError):
            return default

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
            print("⚠️ [SDFetcher] 토큰 부재로 수급 데이터 기본값(0) 반환")
            return data

        # 1. 코스피 현물 (KSP / 0001)
        spot = self._fetch_trend(token, "KSP", "0001")
        # KIS API 대금 단위는 '백만원' 기준인 경우가 많으므로 확인 필요.
        # 실수형 문자열("-19496.2") 및 빈 문자열 안전 파싱
        data['individual'] = self._safe_to_int(spot.get('prsn_ntby_tr_pbmn', 0))
        data['foreign'] = self._safe_to_int(spot.get('frgn_ntby_tr_pbmn', 0))

        # 2. 코스피 200 선물 (K2I / F001)
        futures = self._fetch_trend(token, "K2I", "F001")
        data['foreign_futures'] = self._safe_to_int(futures.get('frgn_ntby_tr_pbmn', 0))

        print(f"📊 [SDFetcher] 수집 완료: 개인 {data['individual']:,}억 | 외인 {data['foreign']:,}억 | 외인선물 {data['foreign_futures']:,}억")
        return data
