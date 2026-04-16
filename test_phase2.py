import sys
import os
from datetime import datetime
# D:\G-ensemble 경로를 모듈 경로에 추가
sys.path.append('D:/G-ensemble')

from models.yt_analyzer import YTAnalyzer
from models.weight_engine import WeightEngine
from fetchers.stock_fetcher import StockFetcher
from fetchers.sd_fetcher import SDFetcher
from fetchers.fx_fetcher import FXFetcher

print("--- Phase 2: Integrated Model Test ---")

# 1. 유튜브 분석 (실제 최신 영상)
analyzer = YTAnalyzer()
video_id = analyzer.get_latest_video_id()
print(f"Latest Video ID: {video_id}")

transcript = analyzer.get_transcript(video_id)
print(f"Transcript Length: {len(transcript)}")

yt_result = analyzer.analyze_sentiment(transcript)
print(f"YT Sentiment Result: {yt_result}")

# 2. 기타 데이터 수집
stock_data = StockFetcher().fetch()
sd_data = SDFetcher().fetch()
fx_data = FXFetcher().fetch()

# 3. 앙상블 계산
engine = WeightEngine()
# 감쇠 계수는 테스트를 위해 오늘 업로드된 것으로 가정 (1.0)
yt_input = {"score": yt_result.get('score', 50), "decay": 1.0}
final_result = engine.calculate_ensemble(yt_input, stock_data, sd_data, fx_data)

print("\n--- Final Ensemble Report ---")
print(f"Final Score: {final_result['final_score']}")
print(f"Signal: {final_result['signal']}")
print(f"KORU Status: {final_result['details'].get('koru_status')}")
print(f"Reason: {yt_result.get('reason')}")
print("------------------------------")
