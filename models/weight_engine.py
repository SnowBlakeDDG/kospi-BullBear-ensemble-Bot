import pandas as pd

class WeightEngine:
    def __init__(self):
        self.weights = {
            "youtube": 0.3,
            "koru": 0.3,
            "supply_demand": 0.2,
            "fx": 0.2
        }

    def get_strength(self, score):
        abs_score = abs(score)
        if abs_score < 0.2: return "Weak"
        elif abs_score < 0.5: return "Moderate"
        else: return "Strong"

    def calculate_ensemble(self, yt_data, stock_data, sd_data, fx_data):
        results = {}
        
        # 1. YouTube (역방향)
        yt_raw = (50 - yt_data.get('score', 50)) / 50.0 
        results['youtube'] = {
            "val": yt_raw * yt_data.get('decay', 1.0),
            "dir": "Bear" if yt_raw < 0 else "Bull",
            "str": self.get_strength(yt_raw)
        }

        # 2. KORU (변동성 차단)
        koru = stock_data.get('KORU', {})
        koru_vol = koru.get('volatility_3d', 0)
        koru_change = koru.get('pct_change', 0) / 10.0 # 스케일링
        
        if koru_vol > 5.0:
            ewy_f = (stock_data.get('EWY', {}).get('pct_change', 0) + stock_data.get('FLKR', {}).get('pct_change', 0)) / 6.0
            results['koru'] = {"val": ewy_f, "dir": "Bull" if ewy_f > 0 else "Bear", "str": self.get_strength(ewy_f), "status": "⚠️ EWY/FLKR 대체"}
        else:
            results['koru'] = {"val": koru_change, "dir": "Bull" if koru_change > 0 else "Bear", "str": self.get_strength(koru_change), "status": "✅ KORU 정상"}

        # 3. 수급 (개인 매수 역방향)
        sd_raw = (sd_data.get('foreign', 0) - sd_data.get('individual', 0)) / 10000.0
        sd_val = max(min(sd_raw, 1.0), -1.0)
        results['supply_demand'] = {"val": sd_val, "dir": "Bull" if sd_val > 0 else "Bear", "str": self.get_strength(sd_val)}

        # 4. 환율
        fx_raw = (1350 - fx_data.get('USDKRW', 1350)) / 100.0
        results['fx'] = {"val": fx_raw, "dir": "Bull" if fx_raw > 0 else "Bear", "str": self.get_strength(fx_raw)}

        final_score = (
            results['youtube']['val'] * self.weights['youtube'] +
            results['koru']['val'] * self.weights['koru'] +
            results['supply_demand']['val'] * self.weights['supply_demand'] +
            results['fx']['val'] * self.weights['fx']
        )

        return {
            "final_score": round(final_score, 4),
            "details": results,
            "signal": "BUY" if final_score > 0.1 else "SELL" if final_score < -0.1 else "HOLD"
        }
