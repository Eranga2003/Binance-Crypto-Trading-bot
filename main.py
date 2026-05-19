import time
import datetime
import traceback
from data_engine.data_fetcher import DataFetcher
from technical_analysis.support_resistance import find_zones, validate_zones
from config import EXCHANGE

def print_zones(title, support_zones, resistance_zones):
    print(title)
    if not support_zones and not resistance_zones:
        print("No zones detected.")
        return
        
    res_str = ", ".join([f"{z['price']:.4f}" for z in resistance_zones])
    sup_str = ", ".join([f"{z['price']:.4f}" for z in support_zones])
    
    print(f"Resistance: {res_str}")
    print(f"Support   : {sup_str}")
    print()

def main():
    print("Starting AI-powered Crypto S&R Scanner...")
    fetcher = DataFetcher()

    base_symbols = ['BTC/USDT']
    if EXCHANGE in ('binance', 'binanceusdm'):
        symbols_to_trade = [f"{symbol}:USDT" for symbol in base_symbols]
    else:
        symbols_to_trade = base_symbols

    while True:
        try:
            current_time = datetime.datetime.now(datetime.UTC)
            print(f"\n{'='*54}\n[{current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}]  Starting Multi-Timeframe Scan...\n{'='*54}\n")

            for symbol in symbols_to_trade:
                print(f"=== {symbol} ===")
                
                # Fetch Data
                # Fetching enough candles to find robust historical zones
                df_1d  = fetcher.fetch_ohlcv(symbol, '1d', limit=200)
                df_4h  = fetcher.fetch_ohlcv(symbol, '4h', limit=100)
                df_1h  = fetcher.fetch_ohlcv(symbol, '1h', limit=300)
                df_15m = fetcher.fetch_ohlcv(symbol, '15m', limit=500)
                df_1m  = fetcher.fetch_ohlcv(symbol, '1m', limit=500)

                if any(df is None for df in [df_1d, df_4h, df_1h, df_15m, df_1m]):
                    print(f"[{symbol}] Failed to fetch complete data. Skipping...")
                    continue

                # Step 1: 1D Analysis (10 major zones)
                # tolerance=0.01 (1%) for daily zones due to higher variance
                zones_1d = find_zones(df_1d, num_support=10, num_resistance=10, window=5, tolerance=0.01)
                
                # Step 2: 4H Confirmation (Validate 1D zones on 4H data, pick top 5)
                # tolerance=0.005 (0.5%) for validation
                confirmed_4h_sup = validate_zones(df_4h, zones_1d['support'], top_n=5, tolerance=0.005)
                confirmed_4h_res = validate_zones(df_4h, zones_1d['resistance'], top_n=5, tolerance=0.005)

                # Step 2.5: 1H Analysis
                # To fulfill the expected output format of "1 h sup and res"
                zones_1h = find_zones(df_1h, num_support=4, num_resistance=4, window=5, tolerance=0.005)

                # Step 3: 15M Refinement (4 intraday zones)
                # tolerance=0.003 (0.3%) for 15m
                zones_15m = find_zones(df_15m, num_support=4, num_resistance=4, window=8, tolerance=0.003)

                # Step 4: 1M Precision (2 scalping zones)
                # tolerance=0.001 (0.1%) for 1m
                zones_1m = find_zones(df_1m, num_support=2, num_resistance=2, window=10, tolerance=0.001)

                # Output exactly as user requested
                print_zones("4h sup and res", confirmed_4h_sup, confirmed_4h_res)
                print_zones("1 h sup  and  res", zones_1h['support'], zones_1h['resistance'])
                print_zones("15 min- sup and res", zones_15m['support'], zones_15m['resistance'])
                print_zones("1 min sup and re", zones_1m['support'], zones_1m['resistance'])
                
            print(f"Scan complete. Sleeping for 1 hour...")
            time.sleep(3600)  # Sleep for 1 hour

        except Exception as e:
            print(f"Error in main loop: {e}")
            print(traceback.format_exc())
            print("Sleeping for 60 seconds before retrying...")
            time.sleep(60)

if __name__ == "__main__":
    main()
