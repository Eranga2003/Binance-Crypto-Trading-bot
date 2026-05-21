import ccxt
import pandas as pd
import time
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import EXCHANGE, API_KEY, API_SECRET, TESTNET

class DataFetcher:
    def __init__(self):
        # Validate API credentials
        if not API_KEY or not API_SECRET:
            print("[DataFetcher] ERROR: API credentials not found!")
            print("[DataFetcher] Please ensure .env file has:")
            print("  EXCHANGE=bybit")
            print("  API_KEY=your_key_without_quotes")
            print("  API_SECRET=your_secret_without_quotes")
            raise ValueError("Missing API credentials")

        # Check for common mistakes (quotes in keys)
        if API_KEY.startswith('"') or API_KEY.startswith("'") or API_SECRET.startswith('"') or API_SECRET.startswith("'"):
            print("[DataFetcher] ERROR: API credentials have quotes around them!")
            print("[DataFetcher] Remove quotes from .env file. Use: API_KEY=value (no quotes)")
            raise ValueError("API credentials contain quotes - check .env file format")

        if EXCHANGE == 'bybit':
            self.exchange = ccxt.bybit({
                # 'apiKey': API_KEY,
                # 'secret': API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,
                },
            })
            if TESTNET:
                self.exchange.set_sandbox_mode(True)
            exchange_name = 'Bybit'
            symbol_note = 'BASE/USDT'
        elif EXCHANGE in ('binance', 'binanceusdm'):
            self.exchange = ccxt.binanceusdm({
                # 'apiKey': API_KEY,
                # 'secret': API_SECRET,
                'enableRateLimit': True,
            })
            exchange_name = 'Binance USDT-M Futures'
            symbol_note = 'BASE/USDT:USDT'
        else:
            raise ValueError(f"Unsupported exchange: {EXCHANGE}")

        mode = 'DEMO Trading' if TESTNET else 'LIVE Trading'
        print(f"[DataFetcher] Mode: {mode} — using {exchange_name}")
        print(f"[DataFetcher] API Key configured: {API_KEY[:10]}...{API_KEY[-4:]}")
        print(f"[DataFetcher] NOTE: Ensure your API keys are from the {exchange_name} account")
        print(f"[DataFetcher] Symbol format for this exchange: {symbol_note}")

        try:
            self.exchange.load_markets()
            print("[DataFetcher] Markets loaded successfully.")
        except ccxt.AuthenticationError as e:
            print(f"[DataFetcher] WARNING: Authentication issue during market load: {e}")
            print("[DataFetcher] This is normal if API permissions are not fully enabled.")
            print("[DataFetcher] Continuing anyway - OHLCV fetch will still work...")
        except Exception as e:
            print(f"[DataFetcher] Warning: Could not load markets: {e}")

    def get_account_balance(self):
        """
        Fetch real account balance from exchange.
        Returns the USDT balance available for trading.
        """
        try:
            balance = self.exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            if usdt_balance > 0:
                print(f"[DataFetcher] Account Balance: {usdt_balance:.2f} USDT")
                return usdt_balance
            else:
                print(f"[DataFetcher] WARNING: USDT balance is 0 or not found")
                print(f"[DataFetcher] Available balances: {[k for k, v in balance.items() if v.get('free', 0) > 0]}")
                return 0
        except Exception as e:
            print(f"[DataFetcher] ERROR fetching balance: {e}")
            print(f"[DataFetcher] Using fallback balance of 10 USDT for testing")
            return 10



    def fetch_ohlcv(self, symbol, timeframe, limit=1000):
        """
        Fetch OHLCV data from the configured exchange.
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except ccxt.AuthenticationError as e:
            print(f"[ERROR] Authentication failed for {symbol} {timeframe}: {e}")
            print("[ERROR] Check your API_KEY and API_SECRET in .env file")
            print("[ERROR] Keys should not have quotes around them")
            return None
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
