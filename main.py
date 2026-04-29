import time
import datetime
from data_engine.data_fetcher import DataFetcher
from strategy_engine.trading_logic import TradingStrategy
from risk_manager.position_sizing import calculate_position
from execution_engine.orders import OrderExecutor

def main():
    print("Starting Binance Price Action & SMC Trading Bot...")
    fetcher = DataFetcher()
    strategy = TradingStrategy()
    executor = OrderExecutor(fetcher.exchange)
    
    symbol = 'BTC/USDT'
    
    # Simulated account balance for position sizing
    account_balance = 1000  # USD
    
    while True:
        try:
            current_time = datetime.datetime.utcnow()
            
            # 1. Check if we are in valid US market hours
            if not strategy.check_time_filter(current_time):
                print(f"[{current_time.strftime('%H:%M:%S UTC')}] Outside US Market Hours. Waiting...")
                time.sleep(60 * 15) # Check again in 15 mins
                continue
                
            print(f"[{current_time.strftime('%H:%M:%S UTC')}] US Market Open. Analyzing {symbol}...")
            
            # 2. Fetch Data
            df_1h = fetcher.fetch_ohlcv(symbol, '1h', limit=100)
            df_25m = fetcher.fetch_25m_ohlcv(symbol, limit=100)
            df_15m = fetcher.fetch_ohlcv(symbol, '15m', limit=100)
            
            if df_1h is None or df_15m is None or df_25m is None:
                print("Failed to fetch market data. Retrying...")
                time.sleep(60)
                continue
            
            # 3. Evaluate Strategy
            signal = strategy.evaluate_market(df_1h, df_25m, df_15m, current_time)
            
            if signal in ["BUY", "SELL"]:
                print(f"*** STRATEGY SIGNAL GENERATED: {signal} ***")
                
                # 4. Calculate Risk & Position Sizing
                entry_price = df_15m['close'].iloc[-1]
                
                # Example: Calculate Stop Loss based on recent swing low/high
                # Using a dummy 2% SL for structural demonstration
                if signal == "BUY":
                    stop_loss_price = entry_price * 0.98
                else:
                    stop_loss_price = entry_price * 1.02
                
                pos = calculate_position(account_balance, entry_price, stop_loss_price)
                
                if pos:
                    print(f"Position Sizing Details:\n{pos}")
                    
                    # 5. Execute Order
                    side = 'buy' if signal == 'BUY' else 'sell'
                    print(f"EXECUTING {side.upper()} ORDER for {pos['position_size_crypto']:.4f} {symbol}")
                    
                    # Uncomment to place live orders on testnet/mainnet:
                    # order = executor.place_order(symbol, side, pos['position_size_crypto'], stop_loss=pos['stop_loss_price'], take_profit=pos['take_profit_price'])
                    # print(f"Order response: {order}")
                    
            else:
                print("No valid trade confirmations found.")
                
            # Sleep before checking again (e.g., 5 minutes)
            time.sleep(60 * 5)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
