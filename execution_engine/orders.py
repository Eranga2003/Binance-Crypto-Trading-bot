class OrderExecutor:
    def __init__(self, exchange_client):
        self.exchange = exchange_client

    def place_order(self, symbol, side, amount, price=None, stop_loss=None, take_profit=None):
        """
        Places a Market order on Binance Futures (Demo or Live), then attaches
        separate Stop-Loss and Take-Profit orders.

        Binance Futures does NOT support stopLossPrice/takeProfitPrice as inline
        params on the entry order — they must be placed as separate STOP_MARKET
        and TAKE_PROFIT_MARKET orders.
        """
        order_type = 'MARKET' if price is None else 'LIMIT'

        # The closing side is the opposite of the entry side
        close_side = 'sell' if side == 'buy' else 'buy'

        try:
            # ── Step 1: Set leverage ──────────────────────────────────────
            try:
                self.exchange.set_leverage(5, symbol)
            except Exception as lev_e:
                print(f"[Orders] Could not set leverage (may already be set): {lev_e}")

            # ── Step 2: Set margin type to ISOLATED ───────────────────────
            try:
                self.exchange.set_margin_mode('isolated', symbol)
            except Exception as margin_e:
                # Binance raises an error if margin mode is already set — safe to ignore
                pass

            # ── Step 3: Place the main entry order ────────────────────────
            entry_order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,  # None for market order
            )
            print(f"[Orders] Entry order placed: ID={entry_order.get('id')} | "
                  f"Side={side.upper()} | Type={order_type} | Amount={amount}")

            # ── Step 4: Place Stop-Loss (STOP_MARKET) order ───────────────
            if stop_loss:
                try:
                    sl_order = self.exchange.create_order(
                        symbol=symbol,
                        type='STOP_MARKET',
                        side=close_side,
                        amount=amount,
                        params={
                            'stopPrice': stop_loss,
                            'closePosition': True,  # Close the entire position
                            'workingType': 'MARK_PRICE',
                        }
                    )
                    print(f"[Orders] Stop-Loss order placed: ID={sl_order.get('id')} | "
                          f"StopPrice={stop_loss}")
                except Exception as sl_e:
                    print(f"[Orders] Failed to place Stop-Loss order: {sl_e}")

            # ── Step 5: Place Take-Profit (TAKE_PROFIT_MARKET) order ──────
            if take_profit:
                try:
                    tp_order = self.exchange.create_order(
                        symbol=symbol,
                        type='TAKE_PROFIT_MARKET',
                        side=close_side,
                        amount=amount,
                        params={
                            'stopPrice': take_profit,
                            'closePosition': True,
                            'workingType': 'MARK_PRICE',
                        }
                    )
                    print(f"[Orders] Take-Profit order placed: ID={tp_order.get('id')} | "
                          f"StopPrice={take_profit}")
                except Exception as tp_e:
                    print(f"[Orders] Failed to place Take-Profit order: {tp_e}")

            return entry_order

        except Exception as e:
            print(f"[Orders] ERROR placing entry order for {symbol}: {e}")
            return None
