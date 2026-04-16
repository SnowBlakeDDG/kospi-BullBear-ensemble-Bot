import yfinance as yf
import pandas as pd
from .base_fetcher import BaseFetcher

class StockFetcher(BaseFetcher):
    def __init__(self, tickers=['KORU', 'EWY', 'FLKR']):
        self.tickers = tickers

    def fetch(self):
        data = {}
        for ticker in self.tickers:
            t = yf.Ticker(ticker)
            hist = t.history(period='5d')
            if not hist.empty:
                data[ticker] = {
                    'last_close': hist['Close'].iloc[-1],
                    'prev_close': hist['Close'].iloc[-2],
                    'pct_change': ((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100,
                    'volatility_3d': hist['Close'].iloc[-3:].pct_change().std() * 100
                }
        return data
