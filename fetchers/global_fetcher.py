import time
import yfinance as yf
from .base_fetcher import BaseFetcher

class GlobalFetcher(BaseFetcher):
    """
    글로벌 선행 및 보조 지표 수집기 (VIX, S&P500, DXY, SOXX)
    5거래일 조회 및 재시도 메커니즘을 적용하여 09:10 누락/0값 현상을 방어합니다.
    """
    def __init__(self):
        self.tickers = {
            'VIX': '^VIX',
            'S&P500': '^GSPC',
            'DXY': 'DX-Y.NYB', # 달러 인덱스
            'SOXX': 'SOXX'     # 필라델피아 반도체 ETF (코스피 선행지표)
        }

    def fetch(self):
        data = {}
        for name, ticker in self.tickers.items():
            success = False
            # 최대 2회 시도
            for attempt in range(2):
                try:
                    t = yf.Ticker(ticker)
                    # 5일치 데이터를 확보하여 주말/공휴일 직후에도 최소 2거래일 종가 보장
                    hist = t.history(period='5d')
                    if not hist.empty and len(hist) >= 2:
                        # 유효한 종가만 추출
                        closes = hist['Close'].dropna()
                        if len(closes) >= 2:
                            last_close = float(closes.iloc[-1])
                            prev_close = float(closes.iloc[-2])
                            pct_change = ((last_close / prev_close) - 1) * 100
                            
                            data[name] = {
                                'last_close': round(last_close, 2),
                                'pct_change': round(pct_change, 2)
                            }
                            success = True
                            break
                    elif not hist.empty and len(hist) == 1:
                        last_close = float(hist['Close'].iloc[-1])
                        data[name] = {
                            'last_close': round(last_close, 2),
                            'pct_change': 0.0
                        }
                        success = True
                        break
                except Exception as e:
                    print(f"⚠️ {name} ({ticker}) 수집 재시도 ({attempt+1}/2) 실패: {e}")
                
                if attempt == 0:
                    time.sleep(1.5)
            
            if not success:
                print(f"❌ {name} ({ticker}) 수집 최종 실패 - 기본값(0) 설정")
                data[name] = {'last_close': 0.0, 'pct_change': 0.0}
        
        return data
