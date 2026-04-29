import ccxt
import pandas as pd
import time
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BINANCE_API_KEY, BINANCE_API_SECRET, TESTNET

class DataFetcher:
    def __init__(self):
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap', # 'swap' is used for USDT Perpetual Futures in ccxt
            }
        })
        if TESTNET:
            self.exchange.set_sandbox_mode(True)
            try:
                self.exchange.load_markets()
            except Exception as e:
                print(f"Warning: Could not load markets initially: {e}")

    def fetch_ohlcv(self, symbol, timeframe, limit=1000):
        """
        Fetch OHLCV data from Binance.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            print(f"Error fetching data for {symbol} {timeframe}: {e}")
            return None

    def fetch_25m_ohlcv(self, symbol, limit=1000):
        """
        Binance does not support 25m candles natively.
        We fetch 5m candles and resample them into 25m candles.
        """
        # Fetch enough 5m candles to create the requested number of 25m candles
        df_5m = self.fetch_ohlcv(symbol, '5m', limit=limit * 5)
        if df_5m is None or df_5m.empty:
            return None
        
        df_5m.set_index('timestamp', inplace=True)
        # Resample to 25m
        df_25m = df_5m.resample('25min').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna().reset_index()
        
        return df_25m.tail(limit).reset_index(drop=True)

if __name__ == "__main__":
    fetcher = DataFetcher()
    print("Testing Binance Testnet Connection (Fetching 1H BTC/USDT Futures Candles)...")
    df_1h = fetcher.fetch_ohlcv('BTC/USDT', '1h', 5)
    print("\n1H Data:")
    print(df_1h)
    
    print("\nTesting 25m Resampling (Fetching 5m candles and resampling)...")
    df_25m = fetcher.fetch_25m_ohlcv('BTC/USDT', 5)
    print("\n25m Data:")
    print(df_25m)
