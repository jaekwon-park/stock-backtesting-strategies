# ─── Korean Opening Range Momentum (장초 돌파 전략) ──────────────────────────
#
# Academic Foundation:
# - Market Intraday Momentum: Gao, Han, Li, Zhou (JFE 2018)
#   → KOSPI replication confirmed: MDPI JRFM 2022
#   → First 30-min return positively predicts last 30-min return
# - Opening Range Breakout: Zarattini et al. (Concretum Group, 2025)
#   → 10-year CAGR 41.9%, Sharpe 1.067 on US equities
# - VWAP trend filter: Zarattini & Aziz (SSRN 2023)
#   → Sharpe 2.1 vs 0.7 for buy-and-hold
#
# Strategy Logic:
# 1. Build opening range during first 30 minutes (09:00–09:30)
# 2. Enter LONG when:
#    - Close breaks above OR high (momentum breakout)
#    - Price is above VWAP (trend confirmation)
#    - Relative volume >= 1.5x (activity confirmation)
# 3. Stop loss: entry price - ATR × 1.5
# 4. Exit: stop hit | 15:00 EOD | max 4-hour hold
#
# Recommended timeframe: 5m
# ─────────────────────────────────────────────────────────────────────────────


def initialize(context):
    context['or_bars'] = 6        # Opening range: 6 × 5m = 30 minutes
    context['atr_period'] = 14    # ATR lookback bars
    context['atr_mul'] = 1.5      # Stop = entry - ATR × atr_mul
    context['min_rvol'] = 1.5     # Minimum relative volume multiplier
    context['max_hold'] = 48      # Max hold: 48 × 5m = 4 hours

    context['bars'] = []
    context['session_bars'] = []
    context['or_high'] = None
    context['or_low'] = None
    context['or_ready'] = False
    context['vwap_tp_vol'] = 0.0
    context['vwap_vol'] = 0.0
    context['stop_price'] = None
    context['hold_count'] = 0
    context['prev_date'] = None


def bar_date(bar):
    t = bar.get('time', '')
    return t[:10] if len(t) >= 10 else ''


def bar_hour(bar):
    t = bar.get('time', '')
    if len(t) >= 13 and t[11:13].isdigit():
        return int(t[11:13])
    return -1


def compute_atr(bars, period):
    if len(bars) < 2:
        return 0.0
    recent = bars[-(period + 1):]
    trs = []
    for i in range(1, len(recent)):
        b = recent[i]
        pb = recent[i - 1]
        tr = max(
            b['high'] - b['low'],
            abs(b['high'] - pb['close']),
            abs(b['low'] - pb['close']),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0


def on_bar(context, bar):
    close = bar['close']
    high = bar['high']
    low = bar['low']
    volume = bar.get('volume', 0)
    hour = bar_hour(bar)
    today = bar_date(bar)

    # ── New session reset ─────────────────────────────────────
    if today and today != context.get('prev_date'):
        context['prev_date'] = today
        context['session_bars'] = []
        context['or_high'] = None
        context['or_low'] = None
        context['or_ready'] = False
        context['vwap_tp_vol'] = 0.0
        context['vwap_vol'] = 0.0

    context['session_bars'].append(bar)
    context['bars'].append(bar)
    keep = context['atr_period'] + 10
    if len(context['bars']) > keep:
        context['bars'] = context['bars'][-keep:]

    # ── Running VWAP ──────────────────────────────────────────
    typical = (high + low + close) / 3.0
    context['vwap_tp_vol'] = context['vwap_tp_vol'] + typical * volume
    context['vwap_vol'] = context['vwap_vol'] + volume
    vwap = (
        context['vwap_tp_vol'] / context['vwap_vol']
        if context['vwap_vol'] > 0 else close
    )

    # ── Opening range construction ────────────────────────────
    session_len = len(context['session_bars'])
    or_bars = context['or_bars']

    if session_len <= or_bars:
        if context['or_high'] is None:
            context['or_high'] = high
            context['or_low'] = low
        else:
            if high > context['or_high']:
                context['or_high'] = high
            if low < context['or_low']:
                context['or_low'] = low
        return []

    if not context['or_ready']:
        context['or_ready'] = True

    or_high = context['or_high']

    # ── ATR & relative volume ─────────────────────────────────
    atr = compute_atr(context['bars'], context['atr_period'])
    vol_window = [b.get('volume', 0) for b in context['bars'][-context['atr_period']:]]
    avg_vol = sum(vol_window) / len(vol_window) if vol_window else 1
    rvol = volume / avg_vol if avg_vol > 0 else 1.0

    position = context.get('position', 0)
    signals = []

    # ── Exit ──────────────────────────────────────────────────
    if position > 0:
        context['hold_count'] = context.get('hold_count', 0) + 1
        stop_hit = context['stop_price'] is not None and close <= context['stop_price']
        eod = hour >= 15
        max_hold = context['hold_count'] >= context['max_hold']

        if stop_hit or eod or max_hold:
            signals.append({'side': 'SELL', 'quantity': position, 'order_type': 'MARKET'})
            context['stop_price'] = None
            context['hold_count'] = 0
            return signals

    # ── Entry ─────────────────────────────────────────────────
    if position == 0 and context['or_ready']:
        if hour >= 14:
            return []

        if (
            close > or_high and
            close > vwap and
            rvol >= context['min_rvol'] and
            atr > 0
        ):
            context['stop_price'] = close - atr * context['atr_mul']
            context['hold_count'] = 0
            signals.append({'side': 'BUY', 'quantity': 1, 'order_type': 'MARKET'})

    return signals
