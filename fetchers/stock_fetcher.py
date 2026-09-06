import time
import yfinance as yf
import pandas as pd
from datetime import datetime
from .base_fetcher import BaseFetcher

class StockFetcher(BaseFetcher):
    def __init__(self, tickers=['KORU', 'EWY', 'FLKR']):
        self.tickers = tickers

    def fetch(self, us_holidays={}):
        data = {'is_holiday': False, 'is_bullet': False, 'bullets': []}
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 캘린더 기반 휴장 확인
        if today_str in us_holidays:
            holiday_info = us_holidays[today_str]
            if holiday_info['type'] == 'HOLIDAY':
                data['is_holiday'] = True
                data['holiday_name'] = holiday_info['name']
            elif holiday_info['type'] == 'EARLY':
                data['is_early_closure'] = True
                data['holiday_name'] = f"{holiday_info['name']} (Early)"

        for ticker in self.tickers:
            for attempt in range(2):
                try:
                    t = yf.Ticker(ticker)
                    hist = t.history(period='5d')
                    if not hist.empty and len(hist) >= 2:
                        closes = hist['Close'].dropna()
                        if len(closes) >= 2:
                            last_close = float(closes.iloc[-1])
                            prev_close = float(closes.iloc[-2])
                            pct_change = ((last_close / prev_close) - 1) * 100
                            
                            # 실시간 거래량 기반 보조 휴장 판별 (주중 월~금만 적용)
                            today_weekday = datetime.now().weekday()
                            if ticker == 'KORU' and hist['Volume'].iloc[-1] == 0 and today_weekday < 5:
                                data['is_holiday'] = True

                            # KORU 불렛 상황 판별 (+-15%)
                            if ticker == 'KORU' and abs(pct_change) >= 15:
                                data['is_bullet'] = True
                                data['bullets'].append('KORU_OUTLIER')

                            data[ticker] = {
                                'last_close': round(last_close, 2),
                                'prev_close': round(prev_close, 2),
                                'pct_change': round(pct_change, 2),
                                'volatility_3d': round(float(closes.iloc[-3:].pct_change().std() * 100), 2) if len(closes) >= 3 else 0.0
                            }
                            break
                except Exception as e:
                    print(f"⚠️ [StockFetcher] {ticker} 수집 재시도 ({attempt+1}/2) 실패: {e}")
                    if attempt == 0:
                        time.sleep(1.5)

        # [주말/투심 분석] KORU/3 vs EWY 괴리율 체크
        if 'KORU' in data and 'EWY' in data:
            koru_adj = data['KORU']['pct_change'] / 3.0
            ewy_pct = data['EWY']['pct_change']
            deviation = abs(koru_adj - ewy_pct)
            data['deviation_val'] = round(deviation, 2)
            data['deviation_flag'] = deviation > 1.0
            
            if data['deviation_flag']:
                print(f"⚠️ 외인 투심 괴리 발생: KORU/3({koru_adj:.2f}%) vs EWY({ewy_pct:.2f}%) = {deviation:.2f}%")
        
        return data
