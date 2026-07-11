import requests
import os
from datetime import datetime
from .base_fetcher import BaseFetcher

class KRXOpenFetcher(BaseFetcher):
    """
    openapi.krx.co.kr 공식 API를 이용한 수급 데이터 수집기
    """
    def __init__(self, auth_key):
        self.auth_key = auth_key
        self.base_url = "http://openapi.krx.co.kr/svc/apis"
        self.headers = {
            "AUTH_KEY": self.auth_key
        }

    def fetch(self, kr_holidays={}):
        data = {
            'individual': 0, 
            'foreign': 0, 
            'foreign_futures': 0, 
            'is_holiday': False
        }
        
        today = datetime.now()
        today_str = today.strftime("%Y-%m-%d")
        bas_dd = today.strftime("%Y%m%d")
        
        # 캘린더 기반 휴장 확인
        if today_str in kr_holidays:
            data['is_holiday'] = True
            data['holiday_name'] = kr_holidays[today_str]['name']
            return data

        # 1. 코스피 현물 수급 (시장별 합계)
        # 서비스명: sto/stk_bydd_trd (유가증권 시장별 일별매매정보) 또는 유사 서비스
        # mktId: STK(코스피)
        try:
            # 시장별 투자자 매매동향 엔드포인트 (가정: 명세서 기반)
            spot_url = f"{self.base_url}/sto/stk_inv_trd_mkt" 
            params = {
                "basDd": bas_dd,
                "mktId": "STK"
            }
            res = requests.get(spot_url, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                result = res.json().get('OutBlock_1', [])
                for row in result:
                    # 투자자구분명 또는 코드로 판별 (8000: 개인, 9000: 외국인)
                    invst_nm = row.get('invstNm', '')
                    net_buy_val = int(row.get('netBidVal', 0)) # 순매수대금 (원)
                    
                    if '개인' in invst_nm or row.get('invstTpCd') == '8000':
                        data['individual'] = net_buy_val // 100000000 # 억 단위
                    elif '외국인' in invst_nm or row.get('invstTpCd') == '9000':
                        data['foreign'] = net_buy_val // 100000000
        except Exception as e:
            print(f"⚠️ KRX Spot API Error: {e}")

        # 2. 코스피 200 선물 수급
        # 서비스명: der/fut_inv_trd (선물 투자자별 매매동향)
        try:
            fut_url = f"{self.base_url}/der/fut_inv_trd"
            params = {
                "basDd": bas_dd,
                "isuCd": "KR4101V30006" # KOSPI 200 선물 최근월물 (예시, 실제로는 조회가 필요할 수 있음)
            }
            res = requests.get(fut_url, headers=self.headers, params=params, timeout=10)
            if res.status_code == 200:
                result = res.json().get('OutBlock_1', [])
                for row in result:
                    if '외국인' in row.get('invstNm', '') or row.get('invstTpCd') == '9000':
                        data['foreign_futures'] = int(row.get('netBidVal', 0)) // 100000000
        except Exception as e:
            print(f"⚠️ KRX Futures API Error: {e}")

        return data
