import pandas as pd

def check_liquidity_hunt(df, index, level, is_resistance):
    """
    Checks if a candle wicks past a key level but the body closes back inside.
    This signifies a liquidity sweep/hunt.
    """
    high = df['high'].iloc[index]
    low = df['low'].iloc[index]
    close = df['close'].iloc[index]
    
    if is_resistance:
        # Sweeps liquidity above resistance, but fails to close above it
        return high > level and close < level
    else:
        # Sweeps liquidity below support, but fails to close below it
        return low < level and close > level

def detect_choch(df, index, trend='bullish'):
    """
    Detects a Change of Character (ChoCh) on lower timeframes.
    A ChoCh happens when market structure is broken in the opposite direction.
    For example, in a bullish trend, a ChoCh is formed when a previous higher low is broken.
    """
    # This is a simplified proxy: looking for a strong momentum shift candle
    # In a fully fleshed out system, this requires tracking structural pivot points
    
    current_candle = df.iloc[index]
    prev_candle = df.iloc[index-1]
    
    if trend == 'bullish':
        # Potential ChoCh to Bearish: strong bearish close breaking previous low
        return current_candle['close'] < prev_candle['low'] and current_candle['close'] < current_candle['open']
    else:
        # Potential ChoCh to Bullish: strong bullish close breaking previous high
        return current_candle['close'] > prev_candle['high'] and current_candle['close'] > current_candle['open']
