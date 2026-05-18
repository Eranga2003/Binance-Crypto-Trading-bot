import datetime
import pytz

# ─────────────────────────────────────────────────────────────────────────────
#  STATE CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────
IDLE      = 'IDLE'
TOUCHED   = 'TOUCHED'
BROKEN    = 'BROKEN'
LIQ_HUNT  = 'LIQ_HUNT'   # Waiting for pullback after break
CHOCH     = 'CHOCH'      # Change of Character confirmed → immediate entry

# How far (%) price must drift from a touched level before we reset to IDLE
RESET_DISTANCE_PCT = 0.01  # 1%


def _fresh_sr_state():
    return {
        'state':         IDLE,       # Current pipeline stage
        'direction':     None,       # 'BUY' or 'SELL'
        'level':         None,       # The S/R level being tracked
        'level_type':    None,       # 'resistance' or 'support'
        'is_resistance': None,       # bool shortcut
    }


def _fresh_tl_state():
    return {
        'state':         IDLE,
        'direction':     None,
        'is_resistance': None,       # True = broke descending res TL (BUY), False = broke sup TL (SELL)
        'trendline':     None,       # Snapshot of trendline dict at time of break
    }


def _pipeline_str(label, state, direction):
    """Renders a 4-step pipeline status line."""
    touch_icon = '✅' if state in (TOUCHED, BROKEN, LIQ_HUNT, CHOCH) else '❌'
    break_icon = '✅' if state in (BROKEN, LIQ_HUNT)                  else ('✅' if state == CHOCH else '❌')
    choch_icon = '✅' if state == CHOCH                                else '❌'
    liq_icon   = '✅' if state == LIQ_HUNT                             else '❌'

    if state == CHOCH:
        return (f"Status: {label} ➔ [{touch_icon} Touched] ➔ "
                f"[{choch_icon} ChoCh ✅] ➔ [— Liq Hunt] ➔ [🚀 ENTRY {direction}]")
    elif state == LIQ_HUNT:
        return (f"Status: {label} ➔ [{touch_icon} Touched] ➔ "
                f"[✅ Break] ➔ [{liq_icon} Liq Hunt ✅] ➔ [🚀 ENTRY {direction}]")
    elif state == BROKEN:
        return (f"Status: {label} ➔ [{touch_icon} Touched] ➔ "
                f"[✅ Break] ➔ [⏳ Liq Hunt…] ➔ [⏳ Waiting]")
    elif state == TOUCHED:
        return (f"Status: {label} ➔ [{touch_icon} Touched] ➔ "
                f"[❌ ChoCh] ➔ [❌ Liq Hunt] ➔ [⏳ Waiting]")
    else:
        return (f"Status: {label} ➔ [❌ Touch] ➔ "
                f"[❌ ChoCh] ➔ [❌ Liq Hunt] ➔ [⏳ Waiting]")


# ─────────────────────────────────────────────────────────────────────────────
#  TRADING STRATEGY
# ─────────────────────────────────────────────────────────────────────────────

class TradingStrategy:
    def __init__(self):
        self.eastern = pytz.timezone('US/Eastern')
        # Per-symbol persistent states
        self.sr_states = {}   # symbol -> SR state dict
        self.tl_states = {}   # symbol -> TL state dict

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _get_sr_state(self, symbol):
        if symbol not in self.sr_states:
            self.sr_states[symbol] = _fresh_sr_state()
        return self.sr_states[symbol]

    def _get_tl_state(self, symbol):
        if symbol not in self.tl_states:
            self.tl_states[symbol] = _fresh_tl_state()
        return self.tl_states[symbol]

    def check_time_filter(self, current_utc_time):
        """Ensures trading only happens during US daytime (9:30 AM – 4:00 PM EST)."""
        if current_utc_time.tzinfo is None:
            current_utc_time = current_utc_time.replace(tzinfo=pytz.utc)
        us_time = current_utc_time.astimezone(self.eastern)
        if us_time.hour > 9 and us_time.hour < 16:
            return True
        elif us_time.hour == 9 and us_time.minute >= 30:
            return True
        return False

    def _price_distance_pct(self, price, level):
        if price is None or level is None or level == 0:
            return None
        return abs(price - level) / level * 100

    def _entry_progress_for_state(self, state, price, level):
        base_scores = {
            IDLE: 0,
            TOUCHED: 50,
            BROKEN: 60,
            LIQ_HUNT: 80,
            CHOCH: 70,
        }
        score = base_scores.get(state, 0)
        dist = self._price_distance_pct(price, level)
        if dist is None:
            return score
        
        # Increased thresholds for realistic market movement (even 0.01% is too small)
        # Now shows progress even for distant prices - proportional scaling
        if dist <= 0.01:  # Very close: within 0.01%
            score += 25
        elif dist <= 0.05:  # Close: within 0.05%
            score += 20
        elif dist <= 0.1:  # Medium: within 0.1%
            score += 15
        elif dist <= 0.5:  # Moderate: within 0.5%
            score += 10
        elif dist <= 1.0:  # Reasonable: within 1%
            score += 5
        else:
            # For prices further away, show proportional progress
            # This ensures even distant prices show SOME entry progress
            score += max(1, int(5 * (100 / dist) / 100))  # 1-5 points based on distance
        
        return min(100, score)

    def _choose_nearest_level(self, current_price, res, sup):
        if res is None and sup is None:
            return None
        if res is None:
            return sup
        if sup is None:
            return res
        return res if abs(current_price - res) < abs(current_price - sup) else sup

    def _get_sr_entry_progress(self, symbol, current_price, prev_price, res, sup):
        st = self._get_sr_state(symbol)
        if st['state'] == IDLE:
            level = self._choose_nearest_level(current_price, res, sup)
        else:
            level = st['level']
        # Return actual distance percentage, not score
        current_dist = self._price_distance_pct(current_price, level) if level else 0
        prev_dist = self._price_distance_pct(prev_price, level) if level else 0
        return (
            current_dist if current_dist is not None else 0,
            prev_dist if prev_dist is not None else 0,
            level,
        )

    def _choose_nearest_trendline(self, current_price, trendlines):
        candidates = []
        if trendlines.get('res_trendline'):
            candidates.append(trendlines['res_trendline']['current_value'])
        if trendlines.get('sup_trendline'):
            candidates.append(trendlines['sup_trendline']['current_value'])
        if not candidates:
            return None
        return min(candidates, key=lambda lvl: abs(current_price - lvl))

    def _get_tl_entry_progress(self, symbol, current_price, prev_price, trendlines):
        st = self._get_tl_state(symbol)
        if st['state'] == IDLE:
            level = self._choose_nearest_trendline(current_price, trendlines)
        else:
            tl = st['trendline']
            level = tl['current_value'] if tl else self._choose_nearest_trendline(current_price, trendlines)
        # Return actual distance percentage, not score
        current_dist = self._price_distance_pct(current_price, level) if level else 0
        prev_dist = self._price_distance_pct(prev_price, level) if level else 0
        return (
            current_dist if current_dist is not None else 0,
            prev_dist if prev_dist is not None else 0,
            level,
        )

    # ── S/R State Machine ────────────────────────────────────────────────────

    def _drive_sr_state(self, symbol, df_5m, current_price, res, sup):
        """
        Drives the S/R pipeline state machine for one symbol.
        Returns a signal string: 'BUY', 'SELL', or 'HOLD'.
        """
        from technical_analysis.support_resistance import (
            detect_level_touch, detect_break,
            detect_pullback_to_level, detect_choch,
        )

        st = self._get_sr_state(symbol)
        signal = 'HOLD'

        # ── If currently tracking a level, check for reset ──────────────────
        if st['state'] != IDLE and st['level'] is not None:
            dist_pct = abs(current_price - st['level']) / st['level']
            if dist_pct > RESET_DISTANCE_PCT and st['state'] == TOUCHED:
                # Price drifted away from touched level without confirmation → reset
                st.update(_fresh_sr_state())

        # ── IDLE: Look for a fresh level touch ──────────────────────────────
        if st['state'] == IDLE:
            for level, ltype, is_res, direction in [
                (res, 'resistance', True,  'SELL'),
                (sup, 'support',    False, 'BUY'),
            ]:
                if level is None:
                    continue
                if detect_level_touch(df_5m, level):
                    st['state']         = TOUCHED
                    st['level']         = level
                    st['level_type']    = ltype
                    st['is_resistance'] = is_res
                    st['direction']     = direction
                    break   # Track only one level at a time

        # ── TOUCHED: Check for Break or ChoCh ───────────────────────────────
        elif st['state'] == TOUCHED:
            level  = st['level']
            is_res = st['is_resistance']

            if detect_break(df_5m, level, is_res):
                # Market broke through the level → flip direction for breakout trade
                # Break above Resistance → BUY. Break below Support → SELL.
                st['direction'] = 'BUY' if is_res else 'SELL'
                st['state']     = BROKEN

            elif detect_choch(df_5m, is_res):
                # Market reversed at the level without breaking → immediate entry
                # From Resistance → SELL. From Support → BUY.
                st['direction'] = 'SELL' if is_res else 'BUY'
                st['state']     = CHOCH

        # ── BROKEN: Wait for Liq Hunt (pullback to flipped level) ────────────
        elif st['state'] == BROKEN:
            level  = st['level']
            is_res = st['is_resistance']

            if detect_pullback_to_level(df_5m, level, is_res):
                st['state'] = LIQ_HUNT

        # ── LIQ_HUNT or CHOCH: Fire entry signal, reset state ────────────────
        if st['state'] in (LIQ_HUNT, CHOCH):
            signal = st['direction']
            self.sr_states[symbol] = _fresh_sr_state()  # Reset for next cycle

        return signal

    # ── Trendline State Machine ──────────────────────────────────────────────

    def _drive_tl_state(self, symbol, df_5m, current_price, trendlines):
        """
        Drives the trendline pipeline state machine for one symbol.
        Returns a signal string: 'BUY', 'SELL', or 'HOLD'.
        """
        from technical_analysis.support_resistance import (
            detect_trendline_touch, detect_trendline_break,
            detect_trendline_pullback, detect_choch,
        )

        st     = self._get_tl_state(symbol)
        signal = 'HOLD'

        res_tl = trendlines.get('res_trendline')
        sup_tl = trendlines.get('sup_trendline')

        # ── IDLE: Look for a trendline touch ────────────────────────────────
        if st['state'] == IDLE:
            # Check descending resistance trendline (break = BUY, ChoCh = SELL)
            if detect_trendline_touch(current_price, res_tl):
                st['state']         = TOUCHED
                st['is_resistance'] = True
                st['direction']     = 'SELL'
                st['trendline']     = res_tl

            # Check ascending support trendline (break = SELL, ChoCh = BUY)
            elif detect_trendline_touch(current_price, sup_tl):
                st['state']         = TOUCHED
                st['is_resistance'] = False
                st['direction']     = 'BUY'
                st['trendline']     = sup_tl

        # ── TOUCHED: Check for TL Break or ChoCh ────────────────────────────
        elif st['state'] == TOUCHED:
            tl     = st['trendline']
            is_res = st['is_resistance']

            if detect_trendline_break(df_5m, tl, is_res):
                st['direction'] = 'BUY' if is_res else 'SELL'
                st['state']     = BROKEN

            elif detect_choch(df_5m, is_res):
                st['direction'] = 'SELL' if is_res else 'BUY'
                st['state']     = CHOCH

        # ── BROKEN: Wait for Pullback to TL ─────────────────────────────────
        elif st['state'] == BROKEN:
            tl     = st['trendline']
            is_res = st['is_resistance']

            if detect_trendline_pullback(df_5m, tl, is_res):
                st['state'] = LIQ_HUNT

        # ── LIQ_HUNT or CHOCH: Fire entry, reset ────────────────────────────
        if st['state'] in (LIQ_HUNT, CHOCH):
            signal = st['direction']
            self.tl_states[symbol] = _fresh_tl_state()

        return signal

    # ── Main Evaluation Entry Point ──────────────────────────────────────────

    def evaluate_market(self, symbol, df_macro, df_micro, current_time):
        """
        Evaluates the full SMC pipeline for a symbol using the 5m (macro) timeframe.
        Returns 'BUY', 'SELL', or 'HOLD'.
        """
        from technical_analysis.support_resistance import (
            identify_pivots, get_strongest_levels, get_trendlines,
        )

        current_price = df_macro['close'].iloc[-1]
        prev_price = df_micro['close'].iloc[-2] if len(df_micro) > 1 else current_price

        # ── Identify pivots and key levels on the 5m chart ──────────────────
        df_pivots = identify_pivots(df_macro)
        levels    = get_strongest_levels(df_pivots, current_price, lookback=100, tolerance=0.002)
        trendlines = get_trendlines(df_macro, window=5, lookback=60)

        res = levels['resistance']
        sup = levels['support']
        
        # DEBUG: Show detection status
        pivot_highs = len(df_pivots[df_pivots['pivot_high'] == True])
        pivot_lows = len(df_pivots[df_pivots['pivot_low'] == True])
        if pivot_highs == 0 or pivot_lows == 0 or res is None or sup is None:
            print(f"   [DEBUG] Pivots: {pivot_highs} highs, {pivot_lows} lows | Levels: Res={res}, Sup={sup} | TL: Res={trendlines['res_trendline'] is not None}, Sup={trendlines['sup_trendline'] is not None}")

        res_str = f"{res:.4f}" if res else "None"
        sup_str = f"{sup:.4f}" if sup else "None"

        res_tl_val = f"{trendlines['res_trendline']['current_value']:.4f}" if trendlines['res_trendline'] else "None"
        sup_tl_val = f"{trendlines['sup_trendline']['current_value']:.4f}" if trendlines['sup_trendline'] else "None"

        # ── Run both state machines ──────────────────────────────────────────
        sr_signal = self._drive_sr_state(symbol, df_macro, current_price, res, sup)
        tl_signal = self._drive_tl_state(symbol, df_macro, current_price, trendlines)

        sr_pct, sr_pct_prev, sr_level = self._get_sr_entry_progress(symbol, current_price, prev_price, res, sup)
        tl_pct, tl_pct_prev, tl_level = self._get_tl_entry_progress(symbol, current_price, prev_price, trendlines)

        # ── Prioritise an active signal (S/R first, then TL) ────────────────
        final_signal = sr_signal if sr_signal != 'HOLD' else tl_signal

        # ── Build status display lines ───────────────────────────────────────
        sr_st  = self._get_sr_state(symbol)
        tl_st  = self._get_tl_state(symbol)

        # If we just fired a signal the state was reset — show ENTRY message instead
        if final_signal != 'HOLD':
            sr_status_line = f"Status: S/R ➔ [🚀 ENTRY {final_signal} FIRED — State Reset]"
            tl_status_line = f"Status: TL  ➔ [🚀 ENTRY {final_signal} FIRED — State Reset]"
        else:
            sr_label = sr_st['level_type'].capitalize() if sr_st['level_type'] else 'S/R'
            tl_label = ('Res TL' if tl_st['is_resistance'] else 'Sup TL') if tl_st['is_resistance'] is not None else 'TL'

            sr_status_line = _pipeline_str(sr_label, sr_st['state'], sr_st['direction'] or '')
            tl_status_line = _pipeline_str(tl_label, tl_st['state'], tl_st['direction'] or '')

        # ── Print to terminal ────────────────────────────────────────────────
        print(f"\n{symbol} — [Price: {current_price:.4f} | Res: {res_str} | Sup: {sup_str} "
              f"| Res TL: {res_tl_val} | Sup TL: {sup_tl_val}]")
        print(f"   [Entry Proximity] S/R: {sr_pct:.3f}% away (1m ago {sr_pct_prev:.3f}%) | TL: {tl_pct:.3f}% away (1m ago {tl_pct_prev:.3f}%)")
        if sr_level is not None:
            print(f"   [S/R Level] {sr_level:.4f}")
        if tl_level is not None:
            print(f"   [TL Level] {tl_level:.4f}")
        print(f"   [S/R]  {sr_status_line}")
        print(f"   [TL]   {tl_status_line}")

        return final_signal
