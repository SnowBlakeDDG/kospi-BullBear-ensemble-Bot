import yfinance as yf
from .base_fetcher import BaseFetcher

class FXFetcher(BaseFetcher):
    def fetch(self):
        ticker = 'USDKRW=X'
        t = yf.Ticker(ticker)
        hist = t.history(period='1d')
        if not hist.empty:
            return {'USDKRW': round(hist['Close'].iloc[-1], 2)}
        return {}
