import os, sys, traceback
sys.path.append(os.path.abspath('.'))
from data_engine.data_fetcher import DataFetcher
import pandas as pd
try:
    fetcher = DataFetcher()
    df = fetcher.fetch_ohlcv('BTC/USDT', '4h', limit=5)
    if df is not None:
        print('--- df ---')
        print(df.head())
        print(df.dtypes)
        print('--- time conversion ---')
        df['time'] = df['timestamp'].apply(lambda x: int(x.timestamp()) if pd.notnull(x) else 0)
        df = df.drop_duplicates(subset=['time'], keep='last')
        df = df.sort_values('time')
        print(df['time'])
        print('--- iterrows ---')
        for _, row in df.iterrows():
            print(int(row['time']))
    else:
        print("df is None")
except Exception as e:
    print(traceback.format_exc())
