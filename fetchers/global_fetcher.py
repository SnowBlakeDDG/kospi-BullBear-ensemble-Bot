import yfinance as yf
from .base_fetcher import BaseFetcher

class GlobalFetcher(BaseFetcher):
    def __init__(self):
        self.tickers = {
            'VIX': '^VIX',
            'S&P500': '^GSPC',
            'DXY': 'DX-Y.NYB' # 달러 인덱스
        }

    def fetch(self):
        data = {}
        for name, ticker in self.tickers.items():
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period='2d')
                if not hist.empty:
                    last_close = hist['Close'].iloc[-1]
                    prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else last_close
                    pct_change = ((last_close / prev_close) - 1) * 100
                    
                    data[name] = {
                        'last_close': round(last_close, 2),
                        'pct_change': round(pct_change, 2)
                    }
            except Exception as e:
                print(f"⚠️ {name} ({ticker}) 수집 에러: {e}")
                data[name] = {'last_close': 0, 'pct_change': 0}
        
        return data
