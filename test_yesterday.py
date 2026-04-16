import datetime
from pykrx import stock
try:
    # ?? ?? (2026-04-14) ??
    target_date = '20260414'
    print(f'--- Querying Data for {target_date} ---')
    df = stock.get_market_net_purchase_of_equities(target_date, target_date, 'KOSPI')
    if not df.empty:
        print(df[['??', '???', '????']])
    else:
        print('No data found for this date.')
except Exception as e:
    print(f'Error: {e}')
