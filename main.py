import time
import datetime
from data_engine.data_fetcher import DataFetcher
from strategy_engine.trading_logic import TradingStrategy
from risk_manager.position_sizing import calculate_position
from execution_engine.orders import OrderExecutor

# ─────────────────────────────────────────────────────────────────────────────
#  POSITION TRACKER
# ─────────────────────────────────────────────────────────────────────────────

def _progress_bar(pct, width=20):
    """Renders a simple ASCII progress bar. pct = 0–100."""
    filled = int(width * pct / 100)
    bar = '█' * filled + '░' * (width - filled)
    return f"[{bar}] {pct:.1f}%"


def _print_order_banner(symbol, side, entry, sl, tp, order_id, size):
    """Prints a rich banner when a new order is placed."""
    side_emoji = '🟢 LONG' if side == 'buy' else '🔴 SHORT'
    tp_dist    = abs(tp - entry) / entry * 100
    sl_dist    = abs(sl - entry) / entry * 100
    rr         = tp_dist / sl_dist if sl_dist else 0
    print(f"""
╔══════════════════════════════════════════════════════╗
  ORDER PLACED ON BINANCE — {symbol}
  {side_emoji}  |  Size: {size:.4f}  |  ID: {order_id}
  ──────────────────────────────────────────────────
  Entry  : {entry:.4f}
  TP     : {tp:.4f}   (+{tp_dist:.2f}% from entry)
  SL     : {sl:.4f}   (-{sl_dist:.2f}% from entry)
  R:R    : 1 : {rr:.2f}
╚══════════════════════════════════════════════════════╝""")


def _monitor_positions(open_positions, current_prices):
    """
    Checks each tracked open position against the current price.
    - Prints TP progress % each cycle
    - Fires TP hit or SL hit alerts
    Returns list of symbols whose positions should be removed (TP/SL hit).
    """
    to_remove = []

    if not open_positions:
        return to_remove

    print("\n  --- Open Positions ---")
    for symbol, pos in open_positions.items():
        current = current_prices.get(symbol)
        if current is None:
            continue

        side        = pos['side']       # 'buy' or 'sell'
        entry       = pos['entry']
        tp          = pos['tp']
        sl          = pos['sl']
        order_id    = pos['order_id']

        # ── TP/SL hit detection ──────────────────────────────────────────
        tp_hit = (side == 'buy'  and current >= tp) or \
                 (side == 'sell' and current <= tp)
        sl_hit = (side == 'buy'  and current <= sl) or \
                 (side == 'sell' and current >= sl)

        if tp_hit:
            profit_pct = abs(tp - entry) / entry * 100
            print(f"  {symbol} | ID:{order_id}")
            print(f"  🎯🎉 TP HIT! Price reached {current:.4f} | Profit: +{profit_pct:.2f}% | TRADE CLOSED")
            to_remove.append(symbol)
            continue

        if sl_hit:
            loss_pct = abs(sl - entry) / entry * 100
            print(f"  {symbol} | ID:{order_id}")
            print(f"  ❌ SL HIT. Price reached {current:.4f} | Loss: -{loss_pct:.2f}% | TRADE CLOSED")
            to_remove.append(symbol)
            continue

        # ── Progress toward TP ───────────────────────────────────────────
        total_range = abs(tp - entry)
        if total_range == 0:
            progress_pct = 0.0
        elif side == 'buy':
            progress_pct = max(0.0, min(100.0, (current - entry) / total_range * 100))
        else:
            progress_pct = max(0.0, min(100.0, (entry - current) / total_range * 100))

        side_label  = 'LONG' if side == 'buy' else 'SHORT'
        pnl_pct     = ((current - entry) / entry * 100) if side == 'buy' else ((entry - current) / entry * 100)
        pnl_emoji   = '📈' if pnl_pct >= 0 else '📉'

        print(f"  {symbol} | {side_label} | ID:{order_id}")
        print(f"  Entry:{entry:.4f}  Now:{current:.4f}  TP:{tp:.4f}  SL:{sl:.4f}")
        print(f"  PnL: {pnl_emoji} {pnl_pct:+.2f}%  |  To TP: {_progress_bar(progress_pct)}")

    print("  " + "-" * 52)
    return to_remove


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("Starting Binance Price Action & SMC Trading Bot...")
    fetcher  = DataFetcher()
    strategy = TradingStrategy()
    executor = OrderExecutor(fetcher.exchange)

    symbols_to_trade = [
        'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT',
        'ADA/USDT', 'DOGE/USDT'
    ]

    # Simulated account balance for position sizing
    account_balance = 1000  # USD

    # Tracks all open positions: { symbol: { side, entry, tp, sl, size, order_id } }
    open_positions = {}
    current_prices = {}     # Latest close price per symbol this cycle

    while True:
        try:
            current_time = datetime.datetime.now(datetime.UTC)

            # 1. Check if we are in valid US market hours
            if not strategy.check_time_filter(current_time):
                pass  # Ignoring filter silently for testing

            print(f"\n{'='*54}\n[{current_time.strftime('%H:%M:%S UTC')}]  Starting Analysis Scan...\n{'='*54}")

            # ── Scan every symbol ────────────────────────────────────────
            for symbol in symbols_to_trade:
                # 2. Fetch Data (5m Macro, 1m Micro)
                df_macro = fetcher.fetch_ohlcv(symbol, '5m', limit=100)
                df_micro = fetcher.fetch_ohlcv(symbol, '1m', limit=100)

                if df_macro is None or df_micro is None:
                    print(f"[{symbol}] Warning: Failed to fetch market data. Skipping...")
                    continue

                current_price = df_micro['close'].iloc[-1]
                current_prices[symbol] = current_price

                # Skip signal evaluation if position already open for this symbol
                if symbol in open_positions:
                    continue

                # 3. Evaluate Strategy
                signal = strategy.evaluate_market(symbol, df_macro, df_micro, current_time)

                if signal in ["BUY", "SELL"]:
                    print(f"\n[{symbol}] *** STRATEGY SIGNAL: {signal} ***")

                    # 4. Calculate Risk & Position Sizing
                    entry_price = current_price

                    if signal == "BUY":
                        stop_loss_price = entry_price * 0.98
                    else:
                        stop_loss_price = entry_price * 1.02

                    pos = calculate_position(account_balance, entry_price, stop_loss_price)

                    if pos:
                        side = 'buy' if signal == 'BUY' else 'sell'

                        # 5. Send order to Binance
                        order = executor.place_order(
                            symbol,
                            side,
                            pos['position_size_crypto'],
                            stop_loss=pos['stop_loss_price'],
                            take_profit=pos['take_profit_price']
                        )

                        if order:
                            order_id = order.get('id', 'N/A')

                            # 6. Print rich order banner
                            _print_order_banner(
                                symbol   = symbol,
                                side     = side,
                                entry    = entry_price,
                                sl       = pos['stop_loss_price'],
                                tp       = pos['take_profit_price'],
                                order_id = order_id,
                                size     = pos['position_size_crypto'],
                            )

                            # 7. Track position for monitoring
                            open_positions[symbol] = {
                                'side':     side,
                                'entry':    entry_price,
                                'tp':       pos['take_profit_price'],
                                'sl':       pos['stop_loss_price'],
                                'size':     pos['position_size_crypto'],
                                'order_id': order_id,
                            }
                        else:
                            print(f"[{symbol}] ORDER FAILED — check execution_engine logs above")

            # ── Monitor open positions ───────────────────────────────────
            hits = _monitor_positions(open_positions, current_prices)
            for sym in hits:
                open_positions.pop(sym, None)

            print(f"\nScan complete. Sleeping for 1 second...")
            time.sleep(1)

        except Exception as e:
            import traceback
            print(f"Error in main loop: {e}")
            print(traceback.format_exc())
            time.sleep(60)


if __name__ == "__main__":
    main()
