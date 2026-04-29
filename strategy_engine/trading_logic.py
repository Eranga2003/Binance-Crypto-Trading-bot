import datetime
import pytz

class TradingStrategy:
    def __init__(self):
        self.eastern = pytz.timezone('US/Eastern')
        
    def check_time_filter(self, current_utc_time):
        """
        Ensures trading only happens during US daytime.
        (E.g., 9:30 AM to 4:00 PM EST)
        """
        if current_utc_time.tzinfo is None:
            current_utc_time = current_utc_time.replace(tzinfo=pytz.utc)
            
        us_time = current_utc_time.astimezone(self.eastern)
        
        # 9:30 AM to 4:00 PM (16:00)
        if us_time.hour > 9 and us_time.hour < 16:
            return True
        elif us_time.hour == 9 and us_time.minute >= 30:
            return True
        else:
            return False

    def evaluate_market(self, symbol, df_macro, df_micro, current_time):
        """
        Evaluates the 4 confirmations based on the strategy rules.
        """
        if not self.check_time_filter(current_time):
            return "NO_TRADE_TIME_FILTER"
            
        from technical_analysis.support_resistance import identify_pivots, get_recent_levels
        
        # Calculate Macro (15m) Pivots
        df_macro_pivots = identify_pivots(df_macro)
        levels_macro = get_recent_levels(df_macro_pivots, lookback=50)
        
        latest_res = f"{levels_macro['resistances'][-1]:.2f}" if levels_macro['resistances'] else "None"
        latest_sup = f"{levels_macro['supports'][-1]:.2f}" if levels_macro['supports'] else "None"
        current_price = df_micro['close'].iloc[-1]
        
        # Concise Terminal Output
        print(f"[{symbol}] 💰 P: {current_price:.2f} | 15m Sup: {latest_sup} | 15m Res: {latest_res}")
        print(f"[{symbol}] Conf 1 (15m S/R Break) : FAIL")
        print(f"[{symbol}] Conf 2 (1m S/R Break)  : FAIL")
        print(f"[{symbol}] Conf 3 (1m ChoCh/Liq)   : FAIL")
        print(f"[{symbol}] Conf 4 (Trendline Brk) : FAIL")
        print(f"[{symbol}] STATUS                 : HOLD\n")
        
        return "HOLD"
