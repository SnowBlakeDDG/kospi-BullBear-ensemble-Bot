import yfinance as yf
from .base_fetcher import BaseFetcher

class FXFetcher(BaseFetcher):
    def fetch(self):
        ticker = 'USDKRW=X'
        t = yf.Ticker(ticker)
        # 3개월치 데이터를 가져와 60영업일 통계 산출
        hist = t.history(period='3mo')
        data = {'is_bullet': False, 'bullets': []}
        
        if not hist.empty and len(hist) >= 2:
            last_val = hist['Close'].iloc[-1]
            prev_val = hist['Close'].iloc[-2]
            diff = last_val - prev_val
            
            # 최근 60영업일 종가 기준 통계 계산
            close_prices = hist['Close']
            mean_val = float(close_prices.mean())
            std_val = float(close_prices.std())
            
            # Z-score 계산 (최근 환율 트렌드 대비 상대적 변동성 판정)
            zscore = (last_val - mean_val) / std_val if std_val > 0 else 0.0
            
            # 환율 불렛 상황 판별 (전일 대비 +-30원)
            if abs(diff) >= 30:
                data['is_bullet'] = True
                data['bullets'].append('FX_OUTLIER')
                
                # 엔-달러 보조 지표 수집
                jpy_t = yf.Ticker('JPYUSD=X')
                jpy_hist = jpy_t.history(period='1d')
                if not jpy_hist.empty:
                    data['USDJPY'] = round(1 / jpy_hist['Close'].iloc[-1], 2)

            data['USDKRW'] = round(last_val, 2)
            data['USDKRW_mean'] = round(mean_val, 2)
            data['USDKRW_std'] = round(std_val, 2)
            data['USDKRW_zscore'] = round(zscore, 4)
            data['diff'] = round(diff, 2)
            
        return data
