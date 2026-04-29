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

def get_strongest_levels(df, current_price, lookback=100, tolerance=0.002):
    """
    Get the most powerful support and resistance levels by checking historical touches.
    Resistance must be strictly > current_price.
    Support must be strictly < current_price.
    Tolerance is the % deviation allowed to count as a 'touch'.
    """
    recent_df = df.tail(lookback)
    
    # Extract all pivot highs and lows in the lookback window
    all_resistances = recent_df[recent_df['pivot_high'] == True]['high'].tolist()
    all_supports = recent_df[recent_df['pivot_low'] == True]['low'].tolist()
    
    # Filter strictly above/below current price
    valid_resistances = [r for r in all_resistances if r > current_price]
    valid_supports = [s for s in all_supports if s < current_price]
    
    best_res = None
    best_res_score = -1
    
    for r in valid_resistances:
        # Count touches (how many candles' highs came within the tolerance band)
        lower_bound = r * (1 - tolerance)
        upper_bound = r * (1 + tolerance)
        touches = len(recent_df[(recent_df['high'] >= lower_bound) & (recent_df['high'] <= upper_bound)])
        
        # Prefer the one with more touches. If equal, prefer the one closer to current price (smaller R)
        if touches > best_res_score or (touches == best_res_score and (best_res is None or r < best_res)):
            best_res_score = touches
            best_res = r
            
    best_sup = None
    best_sup_score = -1
    
    for s in valid_supports:
        # Count touches (how many candles' lows came within the tolerance band)
        lower_bound = s * (1 - tolerance)
        upper_bound = s * (1 + tolerance)
        touches = len(recent_df[(recent_df['low'] >= lower_bound) & (recent_df['low'] <= upper_bound)])
        
        # Prefer the one with more touches. If equal, prefer the one closer to current price (larger S)
        if touches > best_sup_score or (touches == best_sup_score and (best_sup is None or s > best_sup)):
            best_sup_score = touches
            best_sup = s
            
    return {
        'resistance': best_res,
        'support': best_sup,
        'res_touches': best_res_score,
        'sup_touches': best_sup_score
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
