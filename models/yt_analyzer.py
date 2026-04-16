import requests
import re
import google.generativeai as genai
from google.api_core import retry
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class YTAnalyzer:
    def __init__(self, model_name='models/gemini-1.5-flash'): 
        self.api_key = os.getenv('GEMINI_API_KEY')
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        self.channel_url = 'https://www.youtube.com/@moneydo/videos'
        self.model = genai.GenerativeModel(model_name)

    def get_latest_video_id(self):
        try:
            res = requests.get(self.channel_url, timeout=10)
            ids = re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', res.text)
            return list(dict.fromkeys(ids))[0] if ids else None
        except: return None

    def get_transcript(self, video_id):
        if not video_id: return "No Video"
        try:
            res = requests.get(f'https://www.youtube.com/watch?v={video_id}', timeout=10)
            title = re.search(r'<title>(.*?)</title>', res.text)
            return title.group(1).replace(' - YouTube', '') if title else "No Metadata"
        except: return "No Data"

    def analyze_sentiment(self, text):
        prompt = f'''당신은 퀀트 분석가입니다. 다음 유튜브 제목의 코스피 시장 전망을 0(비관)~100(낙관) 점수로 분석하시오. 
        역방향 지표임을 명심할 것 (낙관 점수 높으면 하락 신호).
        JSON 응답: {{"score": 80, "reason": "..."}}
        제목: {text}'''
        
        try:
            # retry=None 설정을 통해 쿼터 초과 시 무한 대기하지 않고 즉시 에러 반환
            resp = self.model.generate_content(prompt, request_options={'retry': None})
            match = re.search(r'\{.*\}', resp.text, re.DOTALL)
            return json.loads(match.group()) if match else {"score": 50, "reason": "Parse Error"}
        except Exception as e:
            # 에러 발생 시 사용자에게 명확한 이유 전달
            error_msg = str(e)
            if "429" in error_msg:
                return {"score": 50, "reason": "현재 Gemini API 사용 한도(Quota)가 모두 소진되었습니다. 내일 다시 시도해주세요."}
            return {"score": 50, "reason": f"API Error: {error_msg[:100]}"}
