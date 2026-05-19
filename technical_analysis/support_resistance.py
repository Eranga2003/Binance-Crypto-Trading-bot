import pandas as pd
import numpy as np

def identify_pivots(df, window=5):
    """
    Identifies pivot highs and lows.
    """
    df = df.copy()
    df['pivot_high'] = False
    df['pivot_low'] = False

    for i in range(window, len(df) - window):
        is_pivot_high = True
        is_pivot_low = True

        for j in range(1, window + 1):
            if df['high'].iloc[i] < df['high'].iloc[i - j] or df['high'].iloc[i] < df['high'].iloc[i + j]:
                is_pivot_high = False
            if df['low'].iloc[i] > df['low'].iloc[i - j] or df['low'].iloc[i] > df['low'].iloc[i + j]:
                is_pivot_low = False

        if is_pivot_high:
            df.at[df.index[i], 'pivot_high'] = True
        if is_pivot_low:
            df.at[df.index[i], 'pivot_low'] = True

    return df

def group_levels(prices, volumes, tolerance=0.005):
    """
    Groups nearby price levels together within a percentage tolerance.
    Returns a list of dicts: {'price': avg_price, 'touches': count, 'volume': total_vol}
    """
    if not prices:
        return []
    
    # Sort together by price
    sorted_pairs = sorted(zip(prices, volumes), key=lambda x: x[0])
    
    zones = []
    current_group = [sorted_pairs[0]]
    
    for i in range(1, len(sorted_pairs)):
        price, vol = sorted_pairs[i]
        avg_group_price = sum(p for p, v in current_group) / len(current_group)
        
        if abs(price - avg_group_price) / avg_group_price <= tolerance:
            current_group.append((price, vol))
        else:
            # Finalize group
            avg_p = sum(p for p, v in current_group) / len(current_group)
            total_v = sum(v for p, v in current_group)
            zones.append({'price': avg_p, 'touches': len(current_group), 'volume': total_v})
            current_group = [(price, vol)]
            
    if current_group:
        avg_p = sum(p for p, v in current_group) / len(current_group)
        total_v = sum(v for p, v in current_group)
        zones.append({'price': avg_p, 'touches': len(current_group), 'volume': total_v})
        
    return zones

def find_zones(df, num_support=5, num_resistance=5, window=5, tolerance=0.005):
    """
    Finds top support and resistance zones based on pivot touches and volume.
    """
    current_price = df['close'].iloc[-1]
    
    df_pivots = identify_pivots(df, window)
    
    highs = df_pivots[df_pivots['pivot_high']]['high'].tolist()
    high_vols = df_pivots[df_pivots['pivot_high']]['volume'].tolist()
    
    lows = df_pivots[df_pivots['pivot_low']]['low'].tolist()
    low_vols = df_pivots[df_pivots['pivot_low']]['volume'].tolist()
    
    res_zones = group_levels(highs, high_vols, tolerance)
    sup_zones = group_levels(lows, low_vols, tolerance)
    
    # Filter by current price (Resistance > current, Support < current)
    valid_res = [z for z in res_zones if z['price'] > current_price]
    valid_sup = [z for z in sup_zones if z['price'] < current_price]
    
    # Score: combinations of touches and volume.
    def compute_score(zone, all_zones):
        if not all_zones: return 0
        max_touches = max(z['touches'] for z in all_zones) or 1
        max_vol = max(z['volume'] for z in all_zones) or 1
        return (zone['touches'] / max_touches) * 0.6 + (zone['volume'] / max_vol) * 0.4

    for z in valid_res: z['score'] = compute_score(z, valid_res)
    for z in valid_sup: z['score'] = compute_score(z, valid_sup)
    
    # Sort by score descending
    valid_res.sort(key=lambda x: x['score'], reverse=True)
    valid_sup.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'resistance': valid_res[:num_resistance],
        'support': valid_sup[:num_support]
    }

def validate_zones(df, zones, top_n=5, tolerance=0.005):
    """
    Takes an existing list of zones and counts how many times they've been touched
    on this new dataframe (lower timeframe).
    zones format: [{'price': X, ...}, ...]
    """
    validated = []
    for zone in zones:
        p = zone['price']
        upper = p * (1 + tolerance)
        lower = p * (1 - tolerance)
        
        # Check how many candles' high/low span crossed this price band
        touches = len(df[(df['high'] >= lower) & (df['low'] <= upper)])
        validated.append({
            'price': p,
            'touches': touches,  # the number of confirmations on this TF
            'original_score': zone.get('score', 0)
        })
        
    # Sort by number of touches in this new timeframe
    validated.sort(key=lambda x: x['touches'], reverse=True)
    return validated[:top_n]
