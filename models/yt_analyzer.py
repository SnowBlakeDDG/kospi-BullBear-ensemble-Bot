import requests
import re
import google.genai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

class YTAnalyzer:
    def __init__(self, model_name='gemini-3.7-flash'): 
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        
        # 모델 우선순위 체인: 3.7 -> 3.6 -> 3.5 -> 2.5
        configured_model = os.getenv('GEMINI_MODEL', model_name)
        candidates = [configured_model, 'gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']
        # 순서 유지 중복 제거
        self.model_chain = list(dict.fromkeys(candidates))
        self.channel_url = 'https://www.youtube.com/@moneydo/videos'
        self._cached_video_info = None

    def _parse_date_badge(self, raw_date, relative_text=None):
        """ISO 업로드 일자 또는 상대 일자 텍스트를 KST 기준 배지로 변환"""
        from datetime import datetime, timezone, timedelta
        kst = timezone(timedelta(hours=9))
        now_kst = datetime.now(kst)
        
        if raw_date:
            try:
                if 'T' in raw_date:
                    dt = datetime.fromisoformat(raw_date).astimezone(kst)
                else:
                    dt = datetime.strptime(raw_date[:10], '%Y-%m-%d').replace(tzinfo=kst)
                
                days_diff = (now_kst.date() - dt.date()).days
                date_str = dt.strftime('%Y-%m-%d')
                
                if days_diff == 0:
                    badge = f"📅 {date_str} (오늘 D-0)"
                elif days_diff == 1:
                    badge = f"📅 {date_str} (어제 D-1)"
                else:
                    badge = f"📅 {date_str} (D-{days_diff})"
                
                return date_str, badge, days_diff
            except Exception as e:
                pass

        if relative_text:
            return relative_text, f"📅 {relative_text}", 0
            
        today_str = now_kst.strftime('%Y-%m-%d')
        return today_str, f"📅 {today_str}", 0

    def get_latest_video_id(self):
        """전인구 솔로 영상 중 최신 video_id 반환 (게스트 출연 및 회원 전용 영상 제외)"""
        self._cached_video_info = None
        try:
            res = requests.get(self.channel_url, timeout=10)
            ids = list(dict.fromkeys(re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', res.text)))

            for vid in ids[:12]:  # 최대 12개 후보 검사
                video_info = self._fetch_video_info(vid)
                if not video_info or not video_info.get('title'):
                    continue
                
                title = video_info['title']
                
                # 1. 회원 전용 영상 체크
                if video_info.get('is_members_only'):
                    print(f"⏭️ 회원 전용(멤버십) 영상 건너뜀: {title}")
                    continue
                
                # 2. AI 기반 게스트/솔로 영상 판별
                if self._is_guest_video_by_ai(title):
                    print(f"⏭️ 게스트(초대석) 영상 건너뜀: {title}")
                    continue
                
                print(f"📺 솔로 분석 영상 선택: {title} [{video_info.get('date_badge', 'N/A')}]")
                self._cached_video_info = video_info
                self._cached_video_info['video_id'] = vid
                return vid

            # 필터링 통과 영상을 못 찾으면 최신 비멤버십 영상 사용 (폴백)
            if ids:
                for vid in ids[:5]:
                    info = self._fetch_video_info(vid)
                    if info and not info.get('is_members_only'):
                        print(f"⚠️ 필터링 매칭 실패로 차선책 비멤버십 영상 사용: {info['title']}")
                        self._cached_video_info = info
                        self._cached_video_info['video_id'] = vid
                        return vid
                return ids[0]
            return None
        except Exception as e:
            print(f"❌ 채널 스크래핑 에러: {e}")
            return None

    def _fetch_video_info(self, video_id):
        """영상 상세 페이지 HTML 및 자막 조회 권한을 확인하여 제목, 업로드일자, 회원전용 여부를 분석"""
        try:
            res = requests.get(f'https://www.youtube.com/watch?v={video_id}', timeout=10)
            html = res.text
            
            # 제목 추출
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(' - YouTube', '') if title_match else None
            
            # 업로드 일자 추출
            upload_date_m = re.search(r'itemprop="uploadDate" content="([^"]+)"', html)
            date_pub_m = re.search(r'itemprop="datePublished" content="([^"]+)"', html)
            relative_date_m = re.search(r'"relativeDateText":\{[^}]*?"simpleText":"([^"]+)"\}', html)
            
            raw_date = upload_date_m.group(1) if upload_date_m else (date_pub_m.group(1) if date_pub_m else None)
            rel_text = relative_date_m.group(1) if relative_date_m else None
            
            published_at, date_badge, days_ago = self._parse_date_badge(raw_date, rel_text)
            
            is_members_only = False
            
            # 1. youtube-transcript-api 권한 검사
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                api = YouTubeTranscriptApi()
                api.list(video_id)
            except Exception as e:
                err_name = type(e).__name__
                if err_name == 'VideoUnplayable' or 'members' in str(e).lower():
                    print(f"🔒 멤버십 권한 제약 감지 ({video_id}): {err_name}")
                    is_members_only = True
            
            # 2. HTML 백업 키워드 체크
            if not is_members_only:
                membership_keywords = [
                    "OFFER_TYPE_MEMBERSHIP", 
                    "Members-only", 
                    "멤버십 전용", 
                    "회원 전용 동영상", 
                    "이 동영상은 전용 동영상입니다"
                ]
                is_members_only = any(kw in html for kw in membership_keywords)
            
            return {
                'title': title,
                'published_at': published_at,
                'date_badge': date_badge,
                'days_ago': days_ago,
                'is_members_only': is_members_only
            }
        except Exception as e:
            print(f"⚠️ 영상 상세 정보 획득 실패 ({video_id}): {e}")
            return None

    def _is_guest_video_by_ai(self, title):
        """Gemini API를 호출하여 영상 제목을 보고 게스트 초대 대담인지 판별"""
        if not self.client:
            guest_keywords = ['교수', '박사', '대표', '소장', '기자', '작가', '대담', '인터뷰']
            if 'ft.' in title.lower():
                return any(kw in title for kw in guest_keywords)
            return False

        prompt = f'''유튜브 영상 제목을 분석하여 이 영상이 외부 게스트(교수, 박사, 애널리스트, 대표, 기자, 작가, 전문가 등 초대 손님)와 진행하는 인터뷰, 대담, 토론, 또는 초대석 영상인지 판별하세요.
        
        단, 전인구 소장이 외부 초대 손님 없이 혼자서 설명/분석하는 솔로 영상은 반드시 `false`로 판별해야 합니다.
        예를 들어, ft. 뒤에 사람이 아닌 주제(예: 'ft. 삼성전자 대응', 'ft. 반도체 전망', 'ft. 금리 인하')가 오거나, '7월 1주차 주식 시황' 같은 영상은 단독 분석이므로 `false`입니다.
        반면, 'ft. 김제경 박사', 'ft. 이경전 교수', 'ft. 금융 전문가' 등 실존 인물이나 직함이 나오는 인터뷰/대담은 `true`입니다.

        JSON 응답 형식:
        {{
            "is_guest": true 또는 false,
            "reason": "판단한 근거 1줄 요약"
        }}

        영상 제목: {title}'''

        try:
            result = self._call_gemini_chain(prompt)
            is_guest = result.get('is_guest', False)
            reason = result.get('reason', '')
            print(f"🤖 AI 판별 결과: {is_guest} ({reason}) | 제목: {title}")
            return is_guest
        except Exception as e:
            print(f"⚠️ AI 게스트 판별 오류 (기본 폴백 적용): {e}")
            
        fallback_keywords = [
            '교수', '박사', '대표', '작가', '소장', '기자', '스승님', 
            '대표', '위원', '애널리스트', '센터장', '연구원', '전문가', 
            '대담', '인터뷰', '초대석', '모셨습니다', '부사장', '이사', '본부장'
        ]
        return any(kw in title for kw in fallback_keywords)

    def get_transcript(self, video_id):
        """영상 제목 및 게시일자 정보를 수집하여 Gemini의 추론을 위한 기초 데이터 제공"""
        if not video_id: return "No Video"
        if self._cached_video_info and self._cached_video_info.get('video_id') == video_id:
            title = self._cached_video_info.get('title', 'No Title')
            date_badge = self._cached_video_info.get('date_badge', '')
        else:
            info = self._fetch_video_info(video_id)
            title = info['title'] if info else "No Title"
            date_badge = info['date_badge'] if info else ""
        return f"영상 제목: {title}\n게시일: {date_badge}\nURL: https://www.youtube.com/watch?v={video_id}"

    def analyze_sentiment(self, video_id):
        """video_id를 받아 메타데이터 수집 및 역지표 점수 추출을 한 번에 수행 (실패 시 AI Overview 폴백)"""
        if not self.client:
            return {"score": 50, "reason": "API Key Missing", "key_points": []}

        # 영상 탐색에 실패했거나 ID가 없는 경우 AI Overview 폴백 가동
        if not video_id or video_id == "dummy_id":
            return self._analyze_fallback_overview()

        # 메타데이터(제목, 날짜, URL) 수집
        metadata = self.get_transcript(video_id)
        video_info = self._cached_video_info or self._fetch_video_info(video_id) or {}
        
        prompt = f'''당신은 대한민국 최고의 퀀트 전략가이자 시장 심리 분석가입니다. 
        제공된 유튜브 영상 정보를 바탕으로 영상의 핵심 내용을 분석하여 한국 증시에 미치는 영향을 요약하고, 이를 '역지표' 관점에서 분석하세요.
        
        **분석 지침:**
        1. **영상 내용 분석**: 해당 채널(전인구경제연구소)의 최신 영상 내용을 분석하여, 해당 영상의 핵심 내용이 한국 증시에 긍정적(호재)인지 혹은 부정적(악재)인지 2-3문장으로 요약하세요.
        2. **핵심 요약 포인트 (2~3개)**: 영상에서 다루는 주요 이슈/테마를 2~3개의 핵심 불릿(`key_points`)으로 명확히 정리하세요. (각 15자~30자 내외)
        3. **강력한 역지표 원칙**:
           - **낙관 = 위험**: 유튜버가 시장을 긍정적으로 보고 매수를 추천할수록 점수를 높게(70~100) 주십시오. 이는 '과열' 신호입니다.
           - **비관 = 기회**: 유튜버가 공포를 조장하고 폭락을 경고할수록 점수를 낮게(0~30) 주십시오. 이는 '바닥' 신호입니다.
        4. **뉘앙스 통일**: "유튜버가 낙관하고 있으므로, 역지표 관점에서는 위험 신호로 해석된다"와 같이 논리적 방향을 명확히 하세요.
        
        **응답 형식 (JSON):**
        {{
            "score": (0~100 사이 정수),
            "summary": "영상 핵심 내용 및 한국 시장 연관성 요약 (호재/악재 판단 포함)",
            "key_points": [
                "핵심 포인트 1 (호재/악재 맥락)",
                "핵심 포인트 2 (호재/악재 맥락)"
            ],
            "reason": "역지표 관점의 점수 산정 근거 및 시장 경고/기회 메시지"
        }}

        입력 데이터:
        {metadata}'''
        
        try:
            result = self._call_gemini_chain(prompt)
            return self._enrich_sentiment_result(result, metadata, video_id, video_info)
        except Exception as e:
            return self._analyze_fallback_overview()

    def _enrich_sentiment_result(self, result, metadata, video_id, video_info):
        """수집된 메타데이터와 날짜 정보를 결과 객체에 병합"""
        title = video_info.get('title') or metadata.split('\n')[0].replace('영상 제목: ', '')
        result['yt_title'] = title
        result['yt_url'] = f"https://www.youtube.com/watch?v={video_id}"
        result['published_at'] = video_info.get('published_at', '')
        result['date_badge'] = video_info.get('date_badge', '')
        result['days_ago'] = video_info.get('days_ago', 0)
        if 'key_points' not in result or not isinstance(result['key_points'], list):
            result['key_points'] = [result.get('summary', '')[:40]]
        return result

    def _analyze_fallback_overview(self):
        """유튜브 탐색 실패 시 거시경제/투자심리 기반 AI Overview 생성 폴백"""
        print("🤖 [AI Overview] 유튜브 영상 탐색 폴백 가동: 거시경제 심리 기반 분석 생성")
        prompt = '''당신은 대한민국 최고의 퀀트 전략가입니다.
        현재 한국 코스피 및 글로벌 거시경제 시장의 대중 투자 심리를 종합 분석하여 역지표 점수를 산출하세요.

        **분석 지침:**
        1. 최근 주요 시장 이슈(금리, 환율, 반도체 및 빅테크 실적, 지정학적 리스크 등)를 바탕으로 대중 심리가 '과열(낙관)'인지 '공포(비관)'인지 평가하세요.
        2. 역지표 원칙: 대중 낙관 = 70~100 (위험), 대중 공포 = 0~30 (기회), 중립 = 40~60.
        3. 핵심 포인트 2~3개를 불릿으로 요약하세요.

        **응답 형식 (JSON):**
        {{
            "score": (0~100 사이 정수),
            "summary": "현재 시장 심리 및 거시경제 흐름 2-3문장 요약",
            "key_points": [
                "매크로 핵심 이슈 1",
                "매크로 핵심 이슈 2"
            ],
            "reason": "대중 심리 진단 및 역지표 관점의 시장 기회/위험 근거"
        }}'''
        
        try:
            res = self._call_gemini_chain(prompt)
            res['yt_title'] = "글로벌 매크로 & 국내 증시 투자심리 개요"
            res['yt_url'] = ""
            res['date_badge'] = "🤖 AI Overview (실시간 검색 보완)"
            res['published_at'] = ""
            res['days_ago'] = 0
            res['is_ai_overview'] = True
            return res
        except Exception as e:
            return {
                "score": 50,
                "summary": "시장 심리 지표 중립 유지",
                "key_points": ["글로벌 관망세 지속", "지표 변동성 제한적"],
                "reason": "데이터 수집 제한으로 기본 중립 적용",
                "yt_title": "매크로 기본 심리",
                "yt_url": "",
                "date_badge": "🤖 AI Overview (기본값)",
                "published_at": "",
                "days_ago": 0,
                "is_ai_overview": True
            }

    def analyze_market_comprehensive(self, market_data):
        """시장 지표와 유튜브 센티멘트를 결합하여 종합 분석 리포트 생성 (Single-Turn)"""
        if not self.client:
            return {"error": "API Key Missing"}

        prompt = f'''
        당신은 GENSE 시스템의 수석 퀀트 전략가입니다. 아래 데이터를 바탕으로 전문적이면서도 실행력 있는 투자 전략 리포트를 작성하세요.

        ### 입력 데이터:
        1. 유튜브 센티멘트: {market_data.get('yt_summary')} (제목: {market_data.get('yt_title')})
        2. 지표 스냅샷: {json.dumps(market_data.get('details'), ensure_ascii=False)}
        3. 앙상블 판정: 스코어 {market_data.get('final_score')} ({market_data.get('signal')}) / 모드 {market_data.get('mode')}

        ### 작성 규칙 (엄수):
        - **수치 중복 나열 금지**: 금액, 변동률, 환율 등 이미 스냅샷에 표시된 숫자를 본문에서 단순 반복하지 마세요.
        - **인사이트 & 맥락 중심**: "왜 시장이 이렇게 반응하는지", "그래서 어떻게 대응해야 하는지" 핵심 흐름에 집중하세요.
        - **market_summary**: 시장의 핵심 맥락을 2문장 이내로 명확하게 요약하세요.
        - **key_analysis**: 핵심 테마 2~3개 (각 테마명 5자 내외, 인사이트 1~2문장).
        - **yt_insight**: 유튜버/대중 심리를 역발상 관점에서 1~2문장으로 명쾌하게 진단하세요.
        - **strategy**: 구체적이고 단기 실행 가능한 가이드 3개 (예: "1. 3000선 이하 분할 매수 대응", "2. KORU 급등 시 분할 차익 실현", "3. 현금 비중 20% 유지").

        ### JSON 출력 구조:
        {{
            "one_liner": "핵심 한줄 요약 (15자 내외, 직관적이고 임팩트 있게)",
            "market_summary": "시장 상황 2문장 요약 (수치 반복 없이 흐름과 맥락만)",
            "key_analysis": [
                {{"title": "테마명", "content": "인사이트 1~2문장"}},
                {{"title": "테마명", "content": "인사이트 1~2문장"}}
            ],
            "yt_insight": "대중 심리 진단 1~2문장 (역지표 관점)",
            "strategy": {{
                "position": "포지션 (예: 적극 매수, 비중 축소, 관망/중립)",
                "guide": [
                    "구체적 실행 액션 1",
                    "구체적 실행 액션 2",
                    "구체적 실행 액션 3"
                ]
            }}
        }}
        '''

        try:
            return self._call_gemini_chain(prompt)
        except Exception as e:
            return {"error": f"All models in chain failed: {str(e)}"}

    def _call_gemini_chain(self, prompt):
        """3.7 -> 3.6 -> 3.5 -> 2.5 순서로 다중 순차 폴백 실행"""
        last_error = None
        
        for model in self.model_chain:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config={
                        'response_mime_type': 'application/json'
                    }
                )
                
                if response.text:
                    try:
                        data = json.loads(response.text)
                        print(f"🤖 [Gemini 호출 성공] 모델: {model}")
                        return data
                    except json.JSONDecodeError:
                        match = re.search(r'\{.*\}', response.text, re.DOTALL)
                        if match:
                            data = json.loads(match.group())
                            print(f"🤖 [Gemini 호출 성공 (정규식 파싱)] 모델: {model}")
                            return data
            except Exception as e:
                last_error = e
                err_msg = str(e)
                if "503" in err_msg or "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                    print(f"⚠️ [{model}] 쿼타/일시장해 ({err_msg[:40]}...) → 다음 모델로 폴백...")
                else:
                    print(f"⚠️ [{model}] 호출 에러: {err_msg[:50]} → 다음 모델로 폴백...")
                continue
                
        raise ValueError(f"All models in chain ({self.model_chain}) failed. Last error: {last_error}")
