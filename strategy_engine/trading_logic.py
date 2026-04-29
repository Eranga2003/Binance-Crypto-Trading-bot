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
        # Time filter is handled in main.py, so we proceed with evaluation here
        from technical_analysis.support_resistance import identify_pivots, get_strongest_levels
        
        current_price = df_micro['close'].iloc[-1]
        
        # Calculate Macro (5m) Pivots
        df_macro_pivots = identify_pivots(df_macro)
        levels_macro = get_strongest_levels(df_macro_pivots, current_price, lookback=100, tolerance=0.002)
        
        latest_res = f"{levels_macro['resistance']:.2f}" if levels_macro['resistance'] else "None"
        latest_sup = f"{levels_macro['support']:.2f}" if levels_macro['support'] else "None"
        
        # For testing, we hardcode ❌ since the math logic isn't fully returning True/False yet
        c1, c2, c3, c4 = "❌", "❌", "❌", "❌"
        
        print(f"{symbol} - [{c1} 5m Break | {c2} 1m Break | {c3} ChoCh | {c4} Trendline] (Price: {current_price:.2f})")
        
        return "HOLD"
