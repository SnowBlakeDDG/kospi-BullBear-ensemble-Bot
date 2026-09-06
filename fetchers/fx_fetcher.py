import time
import yfinance as yf
from .base_fetcher import BaseFetcher

class FXFetcher(BaseFetcher):
    """
    원/달러 환율 데이터 수집기
    3개월치 데이터를 가져와 60영업일 통계 및 Z-score를 산출합니다.
    """
    def fetch(self):
        ticker = 'USDKRW=X'
        data = {'is_bullet': False, 'bullets': []}
        
        for attempt in range(2):
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period='3mo')
                
                if not hist.empty and len(hist) >= 2:
                    closes = hist['Close'].dropna()
                    if len(closes) >= 2:
                        last_val = float(closes.iloc[-1])
                        prev_val = float(closes.iloc[-2])
                        diff = last_val - prev_val
                        
                        # 최근 60영업일 종가 기준 통계 계산
                        close_prices = closes.iloc[-60:] if len(closes) >= 60 else closes
                        mean_val = float(close_prices.mean())
                        std_val = float(close_prices.std())
                        
                        # Z-score 계산 (최근 환율 트렌드 대비 상대적 변동성 판정)
                        zscore = (last_val - mean_val) / std_val if std_val > 0 else 0.0
                        
                        # 환율 불렛 상황 판별 (전일 대비 +-30원)
                        if abs(diff) >= 30:
                            data['is_bullet'] = True
                            data['bullets'].append('FX_OUTLIER')
                            
                            # 엔-달러 보조 지표 수집
                            try:
                                jpy_t = yf.Ticker('JPYUSD=X')
                                jpy_hist = jpy_t.history(period='1d')
                                if not jpy_hist.empty:
                                    data['USDJPY'] = round(1 / float(jpy_hist['Close'].iloc[-1]), 2)
                            except Exception as je:
                                print(f"⚠️ [FXFetcher] 엔-달러 수집 실패: {je}")

                        data['USDKRW'] = round(last_val, 2)
                        data['USDKRW_mean'] = round(mean_val, 2)
                        data['USDKRW_std'] = round(std_val, 2)
                        data['USDKRW_zscore'] = round(zscore, 4)
                        data['diff'] = round(diff, 2)
                        return data
            except Exception as e:
                print(f"⚠️ [FXFetcher] 환율 수집 재시도 ({attempt+1}/2) 실패: {e}")
                if attempt == 0:
                    time.sleep(1.5)
        
        print("❌ [FXFetcher] 환율 수집 최종 실패 - 기본값 반환")
        data['USDKRW'] = 1350.0
        data['USDKRW_zscore'] = 0.0
        data['diff'] = 0.0
        return data
