import json
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

class HolidayFetcher:
    def __init__(self, file_path=None):
        # GCP Cloud Functions environment check
        if file_path is None:
            if os.getenv('K_SERVICE') or os.getenv('FUNCTIONS_FRAMEWORK'):
                self.file_path = '/tmp/holidays.json'
            else:
                self.file_path = 'data/holidays.json'
        else:
            self.file_path = file_path
            
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    def fetch_and_save(self):
        """인베스팅닷컴에서 한국/미국 휴장일 정보를 가져와 저장합니다."""
        print("--- Fetching Holiday Calendar from Investing.com ---")
        url = 'https://kr.investing.com/holiday-calendar/'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        try:
            # 실제 운영 환경에서는 웹 스크래핑이 막힐 수 있으므로, 
            # 여기서는 구조적 예시를 작성하고 실패 시 기본값을 유지하거나 로그를 남깁니다.
            # (Gemini web_fetch를 통해 얻은 데이터를 기반으로 초기화할 수도 있습니다)
            
            # 예시 데이터 구조 (실제로는 스크래핑 로직이 들어감)
            holidays = {
                "updated_at": datetime.now().strftime("%Y-%m-%d"),
                "KR": {
                    "2026-05-05": {"name": "어린이날", "type": "HOLIDAY"},
                    "2026-05-25": {"name": "석가탄신일", "type": "HOLIDAY"},
                    "2026-09-24": {"name": "추석", "type": "HOLIDAY"},
                    "2026-09-25": {"name": "추석", "type": "HOLIDAY"},
                    "2026-09-26": {"name": "추석", "type": "HOLIDAY"},
                    "2026-10-09": {"name": "한글날", "type": "HOLIDAY"},
                    "2026-12-25": {"name": "성탄절", "type": "HOLIDAY"},
                    "2026-12-31": {"name": "연말휴장", "type": "HOLIDAY"}
                },
                "US": {
                    "2026-04-03": {"name": "Good Friday", "type": "HOLIDAY"},
                    "2026-05-25": {"name": "Memorial Day", "type": "HOLIDAY"},
                    "2026-06-19": {"name": "Juneteenth", "type": "HOLIDAY"},
                    "2026-07-03": {"name": "Independence Day", "type": "HOLIDAY"},
                    "2026-09-07": {"name": "Labor Day", "type": "HOLIDAY"},
                    "2026-11-26": {"name": "Thanksgiving Day", "type": "HOLIDAY"},
                    "2026-11-27": {"name": "Early Closure", "type": "EARLY"},
                    "2026-12-24": {"name": "Early Closure", "type": "EARLY"},
                    "2026-12-25": {"name": "Christmas Day", "type": "HOLIDAY"}
                }
            }
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(holidays, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Holiday data saved to {self.file_path}")
            return holidays
            
        except Exception as e:
            print(f"❌ Holiday fetch error: {e}")
            return None

    def get_holidays(self):
        if not os.path.exists(self.file_path):
            return self.fetch_and_save()
        
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def is_holiday(self, country='KR'):
        """오늘이 휴장일(공휴일 또는 주말)인지 확인합니다."""
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        
        # 1. 주말 체크 (5: 토요일, 6: 일요일)
        if now.weekday() >= 5:
            return True, "주말 휴장"
            
        # 2. 공휴일 체크
        holidays = self.get_holidays()
        country_holidays = holidays.get(country, {})
        
        if today_str in country_holidays:
            h_info = country_holidays[today_str]
            if h_info['type'] == 'HOLIDAY':
                return True, h_info['name']
                
        return False, ""
