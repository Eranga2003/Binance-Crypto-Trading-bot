import pandas as pd
import numpy as np

def identify_pivots(df, window=5):
    """
    Identifies pivot highs and pivot lows in a dataframe.
    Window specifies how many candles to the left and right must be lower/higher.
    """
    df = df.copy()
    df['pivot_high'] = False
    df['pivot_low'] = False
    
    for i in range(window, len(df) - window):
        is_pivot_high = True
        is_pivot_low = True
        
        for j in range(1, window + 1):
            # Check for pivot high
            if df['high'].iloc[i] <= df['high'].iloc[i - j] or df['high'].iloc[i] <= df['high'].iloc[i + j]:
                is_pivot_high = False
            # Check for pivot low
            if df['low'].iloc[i] >= df['low'].iloc[i - j] or df['low'].iloc[i] >= df['low'].iloc[i + j]:
                is_pivot_low = False
                
        if is_pivot_high:
            df.at[df.index[i], 'pivot_high'] = True
        if is_pivot_low:
            df.at[df.index[i], 'pivot_low'] = True
            
    return df

def get_recent_levels(df, lookback=50):
    """
    Get the most recent support (pivot low) and resistance (pivot high) levels.
    """
    recent_df = df.tail(lookback)
    
    resistances = recent_df[recent_df['pivot_high'] == True]['high'].tolist()
    supports = recent_df[recent_df['pivot_low'] == True]['low'].tolist()
    
    return {
        'resistances': resistances,
        'supports': supports
    }

def detect_body_breakout(df, index, level, is_resistance):
    """
    Detects if a breakout happened with a body close, not just a wick.
    is_resistance=True -> look for close above level
    is_resistance=False -> look for close below level
    """
    close_price = df['close'].iloc[index]
    open_price = df['open'].iloc[index]
    
    if is_resistance:
        # Bullish breakout: body closes above resistance level
        return close_price > level and close_price > open_price
    else:
        # Bearish breakout: body closes below support level
        return close_price < level and close_price < open_price
