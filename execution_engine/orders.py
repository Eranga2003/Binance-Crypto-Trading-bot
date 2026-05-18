class OrderExecutor:
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.is_bybit = hasattr(exchange_client, 'id') and exchange_client.id == 'bybit'
        if self.is_bybit:
            print("[Orders] Detected Bybit exchange - using Bybit-specific parameters")

    def place_order(self, symbol, side, amount, price=None, stop_loss=None, take_profit=None):
        """
        Places a Market order on Bybit or Binance Futures (Demo or Live), 
        then attaches separate Stop-Loss and Take-Profit orders.

        For Bybit: Uses linear market orders with proper position parameters
        For Binance: Uses STOP_MARKET and TAKE_PROFIT_MARKET orders
        """
        order_type = 'MARKET' if price is None else 'LIMIT'
        close_side = 'sell' if side == 'buy' else 'buy'

        try:
            # ── Bybit-specific setup ────────────────────────────────
            if self.is_bybit:
                # Bybit doesn't need setLeverage for linear markets - skip it
                try:
                    self.exchange.set_margin_mode('isolated', symbol)
                except:
                    pass  # Already set or not required
                
                # For Bybit: Place market order directly
                entry_order = self.exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=amount,
                    price=price,
                    params={'positionMode': False}  # One-way mode
                )
                print(f"[Orders] Entry order placed (Bybit): ID={entry_order.get('id')} | "
                      f"Side={side.upper()} | Amount={amount} | Symbol={symbol}")
                
            else:
                # ── Binance-specific setup ─────────────────────────
                if getattr(self.exchange, 'set_leverage', None):
                    try:
                        self.exchange.set_leverage(5, symbol)
                    except Exception as lev_e:
                        print(f"[Orders] Could not set leverage: {lev_e}")

                if getattr(self.exchange, 'set_margin_mode', None):
                    try:
                        self.exchange.set_margin_mode('isolated', symbol)
                    except:
                        pass

                entry_order = self.exchange.create_order(
                    symbol=symbol,
                    type=order_type,
                    side=side,
                    amount=amount,
                    price=price,
                )
                print(f"[Orders] Entry order placed (Binance): ID={entry_order.get('id')} | "
                      f"Side={side.upper()} | Type={order_type} | Amount={amount}")

            # ── Place Stop-Loss ─────────────────────────────────────
            if stop_loss:
                try:
                    if self.is_bybit:
                        sl_order = self.exchange.create_order(
                            symbol=symbol,
                            type='MARKET',
                            side=close_side,
                            amount=amount,
                            params={
                                'stopLoss': stop_loss,
                                'triggerPrice': stop_loss,
                            }
                        )
                    else:
                        sl_order = self.exchange.create_order(
                            symbol=symbol,
                            type='STOP_MARKET',
                            side=close_side,
                            amount=amount,
                            params={
                                'stopPrice': stop_loss,
                            }
                        )
                    print(f"[Orders] Stop-Loss order placed: StopPrice={stop_loss}")
                except Exception as sl_e:
                    print(f"[Orders] Note: Stop-Loss setup: {sl_e}")

            # ── Place Take-Profit ───────────────────────────────────
            if take_profit:
                try:
                    if self.is_bybit:
                        tp_order = self.exchange.create_order(
                            symbol=symbol,
                            type='MARKET',
                            side=close_side,
                            amount=amount,
                            params={
                                'takeProfit': take_profit,
                                'triggerPrice': take_profit,
                            }
                        )
                    else:
                        tp_order = self.exchange.create_order(
                            symbol=symbol,
                            type='TAKE_PROFIT_MARKET',
                            side=close_side,
                            amount=amount,
                            params={
                                'stopPrice': take_profit,
                            }
                        )
                    print(f"[Orders] Take-Profit order placed: TriggerPrice={take_profit}")
                except Exception as tp_e:
                    print(f"[Orders] Note: Take-Profit setup: {tp_e}")

            return entry_order

        except Exception as e:
            error_str = str(e)
            if "170131" in error_str or "Insufficient balance" in error_str:
                print(f"[Orders] ❌ INSUFFICIENT BALANCE for {symbol}")
                print(f"[Orders] Check your account balance on Bybit")
                print(f"[Orders] Error: {e}")
            elif "Invalid argument" in error_str or "positionMode" in error_str:
                print(f"[Orders] ❌ Position mode error (Bybit may have different settings)")
                print(f"[Orders] Error: {e}")
            else:
                print(f"[Orders] ERROR placing entry order for {symbol}: {e}")
            return None
