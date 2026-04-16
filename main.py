import os
import time
from dotenv import load_dotenv
from fetchers.stock_fetcher import StockFetcher
from fetchers.sd_fetcher import SDFetcher
from fetchers.fx_fetcher import FXFetcher
from models.yt_analyzer import YTAnalyzer
from models.weight_engine import WeightEngine
from utils.discord_notifier import DiscordNotifier

# 1. 환경 변수 로드
load_dotenv()
DISCORD_URL = os.getenv('DISCORD_WEBHOOK_URL')

def main():
    print("--- G-ensemble KOSPI Analysis Start ---")
    
    # 2. 데이터 수집 (Fetchers)
    print("[1/4] 데이터 수집 중...")
    stock_data = StockFetcher().fetch()
    time.sleep(2) # RPM 분산
    sd_data = SDFetcher().fetch()
    time.sleep(2) # RPM 분산
    fx_data = FXFetcher().fetch()
    
    # 3. 유튜브 센티멘트 분석
    print("[2/4] 유튜브 센티멘트 분석 중 (Gemini)...")
    analyzer = YTAnalyzer()
    video_id = analyzer.get_latest_video_id()
    time.sleep(3) # API 호출 전 충분한 간격 확보
    
    transcript = analyzer.get_transcript(video_id)
    yt_analysis = analyzer.analyze_sentiment(transcript)
    
    # 4. 앙상블 가중치 계산
    print("[3/4] 앙상블 지표 계산 중...")
    engine = WeightEngine()
    yt_input = {"score": yt_analysis.get('score', 50), "decay": 1.0}
    final_report = engine.calculate_ensemble(yt_input, stock_data, sd_data, fx_data)
    
    # 5. 결과 리포트 전송
    print("[4/4] 분석 리포트 발송 중...")
    final_report['yt_reason'] = yt_analysis.get('reason', '분석 실패')
    
    notifier = DiscordNotifier(DISCORD_URL)
    notifier.send_report(final_report)
    
    print("--- Analysis Completed Successfully! ---")

if __name__ == "__main__":
    main()
