import os
import time
from dotenv import load_dotenv
try:
    import functions_framework
    _HAS_FF = True
except ImportError:
    _HAS_FF = False
from fetchers.stock_fetcher import StockFetcher
from fetchers.sd_fetcher import SDFetcher
from fetchers.fx_fetcher import FXFetcher
from fetchers.global_fetcher import GlobalFetcher
from fetchers.holiday_fetcher import HolidayFetcher
from models.yt_analyzer import YTAnalyzer
from models.weight_engine import WeightEngine
from utils.discord_notifier import DiscordNotifier
from datetime import datetime

# 1. 환경 변수 로드
load_dotenv()
DISCORD_URL = os.getenv('DISCORD_WEBHOOK_URL')

def main():
    print("--- G-ensemble KOSPI Analysis Start ---")
    
    # 2. 휴일 정보 로드 및 갱신 (매달 1일 또는 파일 부재 시)
    hf = HolidayFetcher()
    is_first_day = datetime.now().day == 1
    
    # GCP 환경 대응: hf.file_path를 직접 체크
    if is_first_day or not os.path.exists(hf.file_path):
        holidays = hf.fetch_and_save()
    else:
        holidays = hf.get_holidays()
    
    # 환경 변수 유효성 체크 로그 (값은 가림)
    print(f"DEBUG: KIS_APP_KEY exists: {bool(os.getenv('KIS_APP_KEY'))}")
    print(f"DEBUG: GEMINI_API_KEY exists: {bool(os.getenv('GEMINI_API_KEY'))}")
    
    # 3. 데이터 수집 (Fetchers)
    print("[1/4] 데이터 수집 중...")
    stock_data = StockFetcher().fetch(holidays.get('US', {}))
    time.sleep(1.5)
    sd_data = SDFetcher().fetch(holidays.get('KR', {}))
    time.sleep(1.5)
    fx_data = FXFetcher().fetch()
    time.sleep(1.5)
    global_data = GlobalFetcher().fetch()
    # 4. 유튜브 센티멘트 분석 (추론 및 요약 통합)
    print("[2/4] 유튜브 센티멘트 분석 및 내용 추론 중 (Gemini)...")
    analyzer = YTAnalyzer()
    video_id = analyzer.get_latest_video_id()
    time.sleep(3) 

    # 이제 analyze_sentiment가 제목, URL, 요약을 모두 포함한 객체를 반환함
    yt_analysis = analyzer.analyze_sentiment(video_id)

    # 5. 앙상블 가중치 계산
    print("[3/4] 앙상블 지표 계산 중...")
    engine = WeightEngine()
    yt_input = {"score": yt_analysis.get('score', 50), "decay": 1.0}
    final_report = engine.calculate_ensemble(yt_input, stock_data, sd_data, fx_data, global_data)

    # [수정] 종합 분석 리포트 생성 (AI가 생성한 summary 전달)
    print("[3.5/4] 종합 분석 리포트 생성 중 (Gemini)...")
    final_report['yt_title'] = yt_analysis.get('yt_title', 'N/A')
    final_report['yt_url'] = yt_analysis.get('yt_url', 'N/A')
    final_report['yt_summary'] = yt_analysis.get('summary', 'N/A') # AI 요약본 추가

    comp_analysis = analyzer.analyze_market_comprehensive(final_report)
    final_report['analysis'] = comp_analysis  # 종합 분석 결과 통합

    # 6. 결과 리포트 전송
    print("[4/4] 분석 리포트 발송 중...")
    final_report['yt_reason'] = yt_analysis.get('reason', '분석 실패')

    
    notifier = DiscordNotifier(DISCORD_URL)
    notifier.send_report(final_report)
    
    print("--- Analysis Completed Successfully! ---")

# GCP Cloud Functions Entry Point
def gensemble_handler(request):
    """GCP Cloud Functions (2nd Gen) 단일 엔트리포인트 — URL path 기반 분기

    Cloud Scheduler 라우팅:
      - GET $uri/kis_token_handler  (06:00 KST): KIS API 토큰 갱신만 수행
      - GET $uri                    (09:10 KST): 전체 분석 + 디스코드 리포트
    """
    path = request.path or '/'

    if 'kis_token' in path:
        return _handle_token_refresh()
    else:
        return _handle_analysis()


def _handle_token_refresh():
    """06:00 KST — KIS API 토큰 갱신 전용 (리포트 발행 없음)"""
    print("--- [06:00] KIS Token Refresh Only ---")

    if datetime.now().weekday() >= 5:
        print("☕ 주말 — 토큰 갱신 건너뜀")
        return "Skipped (Weekend)", 200

    try:
        from fetchers.sd_fetcher import SDFetcher
        fetcher = SDFetcher()
        token = fetcher._get_access_token()
        if token:
            print("✅ KIS Token refreshed at 06:00")
            return "Token Refreshed", 200
        else:
            print("❌ KIS Token refresh failed at 06:00")
            return "Token Refresh Failed", 500
    except Exception as e:
        print(f"❌ Token Error: {e}")
        return f"Error: {e}", 500


def _handle_analysis():
    """09:10 KST — 전체 분석 파이프라인 + 디스코드 리포트"""
    print("--- [09:10] G-ensemble Full Analysis ---")
    try:
        main()
        return "Success", 200
    except Exception as e:
        print(f"Error: {e}")
        return f"Error: {e}", 500


# GCP 환경에서만 HTTP 핸들러 데코레이터 등록
if _HAS_FF:
    gensemble_handler = functions_framework.http(gensemble_handler)

if __name__ == "__main__":
    main()
