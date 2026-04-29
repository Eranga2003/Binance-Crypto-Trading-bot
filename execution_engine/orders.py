class OrderExecutor:
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        
    def place_order(self, symbol, side, amount, price=None, stop_loss=None, take_profit=None):
        """
        Places an order on Binance Futures.
        If price is None, it's a Market Order. Otherwise, Limit Order.
        """
        order_type = 'market' if price is None else 'limit'
        
        try:
            # Set leverage to 5x (Assuming symbol supports it)
            try:
                self.exchange.set_leverage(5, symbol)
            except Exception as lev_e:
                print(f"Could not set leverage or already set: {lev_e}")
            
            params = {}
            if stop_loss:
                params['stopLossPrice'] = stop_loss
            if take_profit:
                params['takeProfitPrice'] = take_profit
                
            order = self.exchange.create_order(
                symbol, 
                order_type, 
                side, 
                amount, 
                price, 
                params
            )
            return order
        except Exception as e:
            print(f"Error placing order: {e}")
            return None
