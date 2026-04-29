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
        # ccxt.binanceusdm is the correct class for Binance USDT-M Perpetual Futures.
        # ccxt.binance with defaultType='swap' does NOT correctly route the sandbox
        # URL to testnet.binancefuture.com — binanceusdm does.
        self.exchange = ccxt.binanceusdm({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET,
            'enableRateLimit': True,
        })

        if TESTNET:
            # Routes all requests to https://testnet.binancefuture.com (Binance Demo Trading)
            self.exchange.set_sandbox_mode(True)
            print("[DataFetcher] Demo Trading mode ON — connected to Binance Futures Testnet")
        else:
            print("[DataFetcher] LIVE Trading mode ON — connected to Binance Futures LIVE")

        try:
            self.exchange.load_markets()
            print("[DataFetcher] Markets loaded successfully.")
        except Exception as e:
            print(f"[DataFetcher] Warning: Could not load markets: {e}")


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
