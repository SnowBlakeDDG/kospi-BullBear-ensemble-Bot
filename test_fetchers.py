import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetchers.stock_fetcher import StockFetcher
from fetchers.sd_fetcher import SDFetcher
from fetchers.fx_fetcher import FXFetcher

print('--- Phase 1: Data Fetching Test ---')
stock = StockFetcher().fetch()
print(f'Stock Data: {stock}')
sd = SDFetcher().fetch()
print(f'Supply/Demand: {sd}')
fx = FXFetcher().fetch()
print(f'FX Data: {fx}')
print('-----------------------------------')
