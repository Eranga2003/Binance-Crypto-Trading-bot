import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
#  PIVOT DETECTION
# ─────────────────────────────────────────────

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
            if df['high'].iloc[i] <= df['high'].iloc[i - j] or df['high'].iloc[i] <= df['high'].iloc[i + j]:
                is_pivot_high = False
            if df['low'].iloc[i] >= df['low'].iloc[i - j] or df['low'].iloc[i] >= df['low'].iloc[i + j]:
                is_pivot_low = False

        if is_pivot_high:
            df.at[df.index[i], 'pivot_high'] = True
        if is_pivot_low:
            df.at[df.index[i], 'pivot_low'] = True

    return df


# ─────────────────────────────────────────────
#  S/R LEVEL DETECTION
# ─────────────────────────────────────────────

def get_strongest_levels(df, current_price, lookback=100, tolerance=0.002):
    """
    Get the most powerful support and resistance levels by checking historical touches.
    Resistance must be strictly > current_price.
    Support must be strictly < current_price.
    Tolerance is the % deviation allowed to count as a 'touch'.
    """
    recent_df = df.tail(lookback)

    all_resistances = recent_df[recent_df['pivot_high'] == True]['high'].tolist()
    all_supports    = recent_df[recent_df['pivot_low']  == True]['low'].tolist()

    valid_resistances = [r for r in all_resistances if r > current_price]
    valid_supports    = [s for s in all_supports    if s < current_price]

    best_res, best_res_score = None, -1
    for r in valid_resistances:
        lb = r * (1 - tolerance)
        ub = r * (1 + tolerance)
        touches = len(recent_df[(recent_df['high'] >= lb) & (recent_df['high'] <= ub)])
        if touches > best_res_score or (touches == best_res_score and (best_res is None or r < best_res)):
            best_res_score = touches
            best_res = r

    best_sup, best_sup_score = None, -1
    for s in valid_supports:
        lb = s * (1 - tolerance)
        ub = s * (1 + tolerance)
        touches = len(recent_df[(recent_df['low'] >= lb) & (recent_df['low'] <= ub)])
        if touches > best_sup_score or (touches == best_sup_score and (best_sup is None or s > best_sup)):
            best_sup_score = touches
            best_sup = s

    return {
        'resistance': best_res,
        'support': best_sup,
        'res_touches': best_res_score,
        'sup_touches': best_sup_score
    }


def detect_level_touch(df, level, tolerance=0.002):
    """
    Returns True if the latest candle's high/low came within the tolerance band of the level.
    Works for both resistance (candle high approaches from below) and support (candle low approaches from above).
    """
    latest = df.iloc[-1]
    lower = level * (1 - tolerance)
    upper = level * (1 + tolerance)
    # Either the high or low is inside the tolerance band
    return (lower <= latest['high'] <= upper) or (lower <= latest['low'] <= upper)


def detect_body_breakout(df, index, level, is_resistance):
    """
    Detects if a breakout happened with a body close, not just a wick.
    is_resistance=True  → look for bullish body close ABOVE resistance level
    is_resistance=False → look for bearish body close BELOW support level
    """
    close_price = df['close'].iloc[index]
    open_price  = df['open'].iloc[index]

    if is_resistance:
        return close_price > level and close_price > open_price
    else:
        return close_price < level and close_price < open_price


def detect_break(df, level, is_resistance):
    """
    Checks the latest candle for a body-close breakout beyond `level`.
    """
    return detect_body_breakout(df, -1, level, is_resistance)


def detect_pullback_to_level(df, level, is_resistance, tolerance=0.003):
    """
    After a breakout, checks if price has pulled back to touch the broken level
    (now a flipped zone) on the latest candle of the 5m timeframe.

    After resistance is broken (bullish), the old resistance becomes new support.
    A pullback means price comes back DOWN to that level → low touches it.

    After support is broken (bearish), the old support becomes new resistance.
    A pullback means price comes back UP to that level → high touches it.
    """
    latest = df.iloc[-1]
    lower  = level * (1 - tolerance)
    upper  = level * (1 + tolerance)

    if is_resistance:
        # Bullish break: old Res is now Sup. Pullback = candle low touches it.
        return lower <= latest['low'] <= upper
    else:
        # Bearish break: old Sup is now Res. Pullback = candle high touches it.
        return lower <= latest['high'] <= upper


def detect_choch(df, is_resistance, lookback=10):
    """
    Detects a Change of Character (ChoCh) — a structural reversal after a level touch.

    From Resistance: price touched resistance but did NOT break it.
    ChoCh = a recent candle prints a LOWER LOW than the candle before it,
    confirming bearish intent (market is turning down from resistance).

    From Support: price touched support but did NOT break it.
    ChoCh = a recent candle prints a HIGHER HIGH than the candle before it,
    confirming bullish intent (market is turning up from support).

    Uses the last `lookback` candles to find the structural shift.
    """
    if len(df) < lookback + 2:
        return False

    recent = df.tail(lookback)

    if is_resistance:
        # Bearish ChoCh: look for a lower low compared to previous candle's low
        for i in range(1, len(recent)):
            if recent['low'].iloc[i] < recent['low'].iloc[i - 1]:
                return True
    else:
        # Bullish ChoCh: look for a higher high compared to previous candle's high
        for i in range(1, len(recent)):
            if recent['high'].iloc[i] > recent['high'].iloc[i - 1]:
                return True

    return False


# ─────────────────────────────────────────────
#  TRENDLINE DETECTION
# ─────────────────────────────────────────────

def get_trendlines(df, window=5, lookback=60):
    """
    Detects the most recent descending resistance trendline and ascending support trendline
    by fitting a line through the last two valid pivot highs / pivot lows.

    Returns dict:
        {
            'res_trendline': {'slope': float, 'intercept': float, 'current_value': float} | None,
            'sup_trendline': {'slope': float, 'intercept': float, 'current_value': float} | None,
        }
    """
    df_pivots = identify_pivots(df.tail(lookback), window=window)
    n = len(df_pivots)

    # --- Descending Resistance Trendline (connecting pivot HIGHS) ---
    pivot_highs = df_pivots[df_pivots['pivot_high'] == True].copy()
    pivot_highs = pivot_highs.reset_index(drop=True)

    res_tl = None
    if len(pivot_highs) >= 2:
        # Use the last two pivot highs
        p1 = pivot_highs.iloc[-2]
        p2 = pivot_highs.iloc[-1]
        idx1 = df_pivots.index.get_loc(p1.name) if hasattr(p1, 'name') else len(pivot_highs) - 2
        idx2 = df_pivots.index.get_loc(p2.name) if hasattr(p2, 'name') else len(pivot_highs) - 1

        # Recalculate positional indices after reset
        ph_indices = list(pivot_highs.index)
        idx1, idx2 = ph_indices[-2], ph_indices[-1]

        slope = (p2['high'] - p1['high']) / (idx2 - idx1) if idx2 != idx1 else 0
        intercept = p1['high'] - slope * idx1
        current_value = slope * (n - 1) + intercept

        res_tl = {'slope': slope, 'intercept': intercept, 'current_value': current_value}

    # --- Ascending Support Trendline (connecting pivot LOWS) ---
    pivot_lows = df_pivots[df_pivots['pivot_low'] == True].copy()
    pivot_lows = pivot_lows.reset_index(drop=True)

    sup_tl = None
    if len(pivot_lows) >= 2:
        p1 = pivot_lows.iloc[-2]
        p2 = pivot_lows.iloc[-1]

        pl_indices = list(pivot_lows.index)
        idx1, idx2 = pl_indices[-2], pl_indices[-1]

        slope = (p2['low'] - p1['low']) / (idx2 - idx1) if idx2 != idx1 else 0
        intercept = p1['low'] - slope * idx1
        current_value = slope * (n - 1) + intercept

        sup_tl = {'slope': slope, 'intercept': intercept, 'current_value': current_value}

    return {'res_trendline': res_tl, 'sup_trendline': sup_tl}


def detect_trendline_touch(current_price, trendline, tolerance=0.002):
    """
    Returns True if the current price is within tolerance % of the trendline's current value.
    """
    if trendline is None:
        return False
    tl_val = trendline['current_value']
    if tl_val <= 0:
        return False
    return abs(current_price - tl_val) / tl_val <= tolerance


def detect_trendline_break(df, trendline, is_resistance, tolerance=0.002):
    """
    Returns True if the latest candle body-closed beyond the trendline value.
    is_resistance=True  → bullish break: close > trendline value (break above descending res TL)
    is_resistance=False → bearish break: close < trendline value (break below ascending sup TL)
    """
    if trendline is None:
        return False
    tl_val = trendline['current_value']
    close  = df['close'].iloc[-1]
    open_  = df['open'].iloc[-1]

    if is_resistance:
        return close > tl_val and close > open_
    else:
        return close < tl_val and close < open_


def detect_trendline_pullback(df, trendline, is_resistance, tolerance=0.003):
    """
    After a trendline break, checks if price pulls back to the trendline level.
    """
    if trendline is None:
        return False
    tl_val = trendline['current_value']
    if tl_val <= 0:
        return False
    latest = df.iloc[-1]
    lower  = tl_val * (1 - tolerance)
    upper  = tl_val * (1 + tolerance)

    if is_resistance:
        # Bullish TL break → old TL is now support → pullback = low touches it
        return lower <= latest['low'] <= upper
    else:
        # Bearish TL break → old TL is now resistance → pullback = high touches it
        return lower <= latest['high'] <= upper
