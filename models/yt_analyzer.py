import requests
import re
import google.genai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

class YTAnalyzer:
    def __init__(self, model_name='gemini-2.5-flash'): 
        self.api_key = os.getenv('GEMINI_API_KEY')
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None
        self.model_name = model_name
        self.fallback_model = 'gemini-2.5-flash-lite' 
        self.channel_url = 'https://www.youtube.com/@moneydo/videos'
        self._cached_title = None  # 게스트 필터링 시 제목 캐시

    def get_latest_video_id(self):
        """전인구 솔로 영상 중 최신 video_id 반환 (게스트 출연 및 회원 전용 영상 제외)"""
        self._cached_title = None
        try:
            res = requests.get(self.channel_url, timeout=10)
            ids = list(dict.fromkeys(re.findall(r'watch\?v=([a-zA-Z0-9_-]{11})', res.text)))

            for vid in ids[:12]:  # 최대 12개 후보 검사 (원하는 영상이 뒤에 있을 수 있으므로 탐색 범위 확장)
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
                
                print(f"📺 솔로 분석 영상 선택: {title}")
                self._cached_title = title
                return vid

            # 필터링 통과 영상을 못 찾으면 최신 비멤버십 영상 사용 (폴백)
            if ids:
                for vid in ids[:5]:
                    info = self._fetch_video_info(vid)
                    if info and not info.get('is_members_only'):
                        print(f"⚠️ 필터링 매칭 실패로 차선책 비멤버십 영상 사용: {info['title']}")
                        self._cached_title = info['title']
                        return vid
                return ids[0]
            return None
        except Exception as e:
            print(f"❌ 채널 스크래핑 에러: {e}")
            return None

    def _fetch_video_info(self, video_id):
        """영상 상세 페이지 HTML 및 자막 조회 권한을 확인하여 제목과 회원전용 여부를 분석"""
        try:
            res = requests.get(f'https://www.youtube.com/watch?v={video_id}', timeout=10)
            html = res.text
            
            # 제목 추출
            title_match = re.search(r'<title>(.*?)</title>', html)
            title = title_match.group(1).replace(' - YouTube', '') if title_match else None
            
            is_members_only = False
            
            # 1. youtube-transcript-api 권한 검사를 통한 정교한 멤버십(회원전용) 감지
            # 비로그인 상태에서 멤버십 전용 동영상은 자막 목록 획득 시 VideoUnplayable 에러가 발생합니다.
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                api = YouTubeTranscriptApi()
                api.list(video_id)  # 자막 조회 시도 (멤버십 락 시 VideoUnplayable 발생)
            except Exception as e:
                # VideoUnplayable 또는 멤버십 제한 관련 클래스명 검출
                err_name = type(e).__name__
                if err_name == 'VideoUnplayable' or 'members' in str(e).lower():
                    print(f"🔒 멤버십 권한 제약 감지 ({video_id}): {err_name}")
                    is_members_only = True
            
            # 2. HTML 백업 키워드 체크 (자막 조회가 우연히 통과된 특수 예외 케이스 방어)
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
                'is_members_only': is_members_only
            }
        except Exception as e:
            print(f"⚠️ 영상 상세 정보 획득 실패 ({video_id}): {e}")
            return None

    def _is_guest_video_by_ai(self, title):
        """Gemini API를 호출하여 영상 제목을 보고 게스트 초대 대담인지 판별"""
        if not self.client:
            # API 키가 없는 경우 기본 정규식 폴백
            guest_keywords = ['교수', '박사', '대표', '소장', '기자', '작가', '대담', '인터뷰']
            # ft. 패턴 매칭 시 뒤에 직함 등이 있는지 약식 판별
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
            # 피크 타임 503 에러 대응을 위한 최대 3회 재시도 루프
            for attempt in range(3):
                try:
                    response = self.client.models.generate_content(
                        model=self.fallback_model,
                        contents=prompt,
                        config={
                            'response_mime_type': 'application/json'
                        }
                    )
                    if response.text:
                        result = json.loads(response.text)
                        is_guest = result.get('is_guest', False)
                        reason = result.get('reason', '')
                        print(f"🤖 AI 판별 결과: {is_guest} ({reason}) | 제목: {title}")
                        return is_guest
                except Exception as ex:
                    # 503 에러 등 임시 장해의 경우 대기 후 재시도
                    if "503" in str(ex) and attempt < 2:
                        wait_time = 2 * (attempt + 1)
                        print(f"⚠️ AI 판별 503 에러 발생 (시도 {attempt+1}/3), {wait_time}초 후 재시도... 에러: {ex}")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise ex
        except Exception as e:
            print(f"⚠️ AI 게스트 판별 오류 (기본 폴백 적용): {e}")
            
        # 오류 시 기본 키워드 폴백 (확장된 키워드 사전 적용)
        fallback_keywords = [
            '교수', '박사', '대표', '작가', '소장', '기자', '스승님', 
            '대표', '위원', '애널리스트', '센터장', '연구원', '전문가', 
            '대담', '인터뷰', '초대석', '모셨습니다', '부사장', '이사', '본부장'
        ]
        return any(kw in title for kw in fallback_keywords)

    def get_transcript(self, video_id):
        """영상 제목 정보를 수집하여 Gemini의 추론을 위한 기초 데이터 제공"""
        if not video_id: return "No Video"
        if self._cached_title:
            title = self._cached_title
        else:
            info = self._fetch_video_info(video_id)
            title = info['title'] if info else "No Title"
        return f"영상 제목: {title}\nURL: https://www.youtube.com/watch?v={video_id}"

    def analyze_sentiment(self, video_id):
        """video_id를 받아 메타데이터 수집 및 역지표 점수 추출을 한 번에 수행"""
        if not self.client:
            return {"score": 50, "reason": "API Key Missing"}

        # 메타데이터(제목, URL) 수집
        metadata = self.get_transcript(video_id)
        
        prompt = f'''당신은 대한민국 최고의 퀀트 전략가이자 시장 심리 분석가입니다. 
        제공된 유튜브 영상 정보를 바탕으로 영상의 핵심 내용을 분석하여 한국 증시에 미치는 영향을 요약하고, 이를 '역지표' 관점에서 분석하세요.
        
        **분석 지침:**
        1. **영상 내용 분석**: 해당 채널(전인구경제연구소)의 최신 영상 내용을 분석하여, 해당 영상의 핵심 내용이 한국 증시에 긍정적(호재)인지 혹은 부정적(악재)인지 2-3문장으로 요약하세요.
        2. **강력한 역지표 원칙**:
           - **낙관 = 위험**: 유튜버가 시장을 긍정적으로 보고 매수를 추천할수록 점수를 높게(70~100) 주십시오. 이는 '과열' 신호입니다.
           - **비관 = 기회**: 유튜버가 공포를 조장하고 폭락을 경고할수록 점수를 낮게(0~30) 주십시오. 이는 '바닥' 신호입니다.
        3. **뉘앙스 통일**: "유튜버가 낙관하고 있으므로, 역지표 관점에서는 위험 신호로 해석된다"와 같이 논리적 방향을 명확히 하세요.
        
        **응답 형식 (JSON):**
        {{
            "score": (0~100 사이 정수),
            "summary": "영상 핵심 내용 및 한국 시장 연관성 요약 (호재/악재 판단 포함)",
            "reason": "역지표 관점의 점수 산정 근거 및 시장 경고/기회 메시지"
        }}

        입력 데이터:
        {metadata}'''
        
        try:
            result = self._call_gemini(self.model_name, prompt)
            # 수집된 메타데이터를 결과에 통합
            result['yt_title'] = metadata.split('\n')[0].replace('영상 제목: ', '')
            result['yt_url'] = f"https://www.youtube.com/watch?v={video_id}"
            return result
        except Exception as e:
            try:
                result = self._call_gemini(self.fallback_model, prompt)
                result['yt_title'] = metadata.split('\n')[0].replace('영상 제목: ', '')
                result['yt_url'] = f"https://www.youtube.com/watch?v={video_id}"
                return result
            except:
                return {"score": 50, "reason": "API Error", "yt_title": "N/A", "yt_url": f"https://www.youtube.com/watch?v={video_id}"}

    def analyze_market_comprehensive(self, market_data):
        """시장 지표와 유튜브 센티멘트를 결합하여 종합 분석 리포트 생성 (Single-Turn)"""
        if not self.client:
            return {"error": "API Key Missing"}

        # 간결한 인사이트 중심 프롬프트 (수치 반복 금지)
        prompt = f'''
        당신은 GENSE 시스템의 수석 전략가입니다. 아래 데이터를 바탕으로 간결한 투자 전략 리포트를 작성하세요.

        ### 입력 데이터:
        1. 유튜브 분석: {market_data.get('yt_summary')} (제목: {market_data.get('yt_title')})
        2. 지표 데이터: {json.dumps(market_data.get('details'), ensure_ascii=False)}
        3. 최종: {market_data.get('final_score')} ({market_data.get('signal')}) / {market_data.get('mode')}

        ### 작성 규칙 (엄수):
        - **수치 반복 금지**: 외인 수급 금액, KORU 변동률, 환율 등 수치 데이터는 이미 대시보드에 표시됩니다. 본문에서 같은 숫자를 다시 언급하지 마세요.
        - **인사이트 중심**: "왜 그런지", "그래서 어떻게 해야 하는지"에 집중하세요.
        - **간결성**: market_summary는 2문장 이내. key_analysis의 content는 각 1~2문장. guide는 즉시 실행 가능한 1줄 액션.
        - **역지표 해석**: 유튜버의 낙관/비관을 반드시 역방향으로 해석하세요.

        ### JSON 출력 구조:
        {{
            "one_liner": "핵심 한줄 (15자 내외, 임팩트 있게)",
            "market_summary": "시장 상황 2문장 요약 (수치 반복 없이 흐름과 맥락만)",
            "key_analysis": [
                {{"title": "테마명 (5자 내외)", "content": "인사이트 1~2문장"}},
                {{"title": "테마명", "content": "인사이트 1~2문장"}}
            ],
            "yt_insight": "대중 심리 진단 1~2문장 (역지표 관점)",
            "strategy": {{
                "position": "포지션 (예: 중립, 비중 축소)",
                "guide": ["액션 1", "액션 2", "액션 3"]
            }}
        }}
        '''

        try:
            return self._call_gemini(self.model_name, prompt)
        except Exception as e:
            print(f"⚠️ {self.model_name} 분석 실패: {e}")
            try:
                return self._call_gemini(self.fallback_model, prompt)
            except Exception as e2:
                return {"error": f"All models failed: {str(e2)}"}

    def _call_gemini(self, model, prompt):
        # 최신 SDK 호출 방식 - JSON 응답 강제
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                'response_mime_type': 'application/json'
            }
        )
        
        if response.text:
            try:
                return json.loads(response.text)
            except json.JSONDecodeError:
                # 폴백: 텍스트에서 JSON 추출 시도
                match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if match:
                    return json.loads(match.group())
        
        raise ValueError(f"Empty or Invalid JSON from {model}")
