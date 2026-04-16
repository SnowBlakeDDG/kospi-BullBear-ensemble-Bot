print("--- Phase 2: Integrated Model Test (Simulated API) ---")
print("Latest Video ID: W-aPReuaklc")
print("Title: ?? '????'? ???? ???? ?? ??")

# Gemini CLI ? ?? ??? ??? ??
yt_result = {'score': 82, 'reason': '????? ?? ?????? ??? ?? ??? ???? ???? ??? ??'}

# ?? ??? ?? (?? ?? ???)
from fetchers.stock_fetcher import StockFetcher
from fetchers.sd_fetcher import SDFetcher
from fetchers.fx_fetcher import FXFetcher
from models.weight_engine import WeightEngine

stock_data = StockFetcher().fetch()
sd_data = SDFetcher().fetch()
fx_data = FXFetcher().fetch()

# ??? ??
engine = WeightEngine()
yt_input = {"score": yt_result['score'], "decay": 1.0}
final_result = engine.calculate_ensemble(yt_input, stock_data, sd_data, fx_data)

print("\n--- Final Ensemble Report ---")
print(f"Final Score: {final_result['final_score']}")
print(f"Signal: {final_result['signal']}")
print(f"KORU Status: {final_result['details'].get('koru_status')}")
print(f"YT Analysis: {yt_result['reason']} (??? ??)")
print("------------------------------")
