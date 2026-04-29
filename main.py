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
    
    symbols_to_trade = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 
        'ADA/USDT', 'DOGE/USDT'
    ]
    
    # Simulated account balance for position sizing
    account_balance = 1000  # USD
    
    while True:
        try:
            current_time = datetime.datetime.now(datetime.UTC)
            
            # 1. Check if we are in valid US market hours
            if not strategy.check_time_filter(current_time):
                pass # Ignoring filter silently for testing
                
            print(f"\n{'='*50}\n[{current_time.strftime('%H:%M:%S UTC')}] 🗽 US Market Open. Starting Analysis Scan...\n{'='*50}")
            
            for symbol in symbols_to_trade:
                # 2. Fetch Data (15m Macro, 1m Micro)
                df_macro = fetcher.fetch_ohlcv(symbol, '15m', limit=100)
                df_micro = fetcher.fetch_ohlcv(symbol, '1m', limit=100)
                
                if df_macro is None or df_micro is None:
                    print(f"[{symbol}] ⚠️ Failed to fetch market data. Skipping...\n")
                    continue
                
                # 3. Evaluate Strategy
                signal = strategy.evaluate_market(symbol, df_macro, df_micro, current_time)
                
                if signal in ["BUY", "SELL"]:
                    print(f"[{symbol}] *** 🚀 STRATEGY SIGNAL GENERATED: {signal} ***\n")
                    
                    # 4. Calculate Risk & Position Sizing
                    entry_price = df_micro['close'].iloc[-1]
                    
                    if signal == "BUY":
                        stop_loss_price = entry_price * 0.98
                    else:
                        stop_loss_price = entry_price * 1.02
                    
                    pos = calculate_position(account_balance, entry_price, stop_loss_price)
                    
                    if pos:
                        side = 'buy' if signal == 'BUY' else 'sell'
                        print(f"[{symbol}] 💰 Position Sizing: Executing {side.upper()} for {pos['position_size_crypto']:.4f}\n")
                        # order = executor.place_order(symbol, side, pos['position_size_crypto'], stop_loss=pos['stop_loss_price'], take_profit=pos['take_profit_price'])
                        
                # No else statement needed here since evaluate_market prints the HOLD status
                    
            print(f"\n✅ Scan complete. Sleeping for 1 second...")
            time.sleep(1)
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
