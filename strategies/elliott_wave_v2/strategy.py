"""
Elliott Wave Strategy v2.0 (손실 최소화 버전)

개선사항 (v1 → v2):
    1. ATR 기반 동적 손절 (8% 고정 → ATR × 2.0)
    2. Break-even + Trailing Stop (수익 +3% → BEP, +6% → +3% 잠금)
    3. 피보나치 되돌림 범위 축소 (0.236~0.886 → 0.382~0.618 황금구간)
    4. 고정 리스크 포지션 사이징 (자본의 2% 리스크 기반)
    5. 목표가 도달 즉시 청산 (RSI/다이버전스 조건 불필요)
    6. 20MA 추세 필터 (하락 추세 진입 금지)
    7. RSI 진입 기준 상향 (35 → 45)
    8. Wave1 최소 상승률 상향 (3% → 5%)
    9. RestrictedPython 호환 수정 완료
"""


def initialize(context):
    context['timeframe'] = '1d'

    # 파동 탐지 파라미터
    context['swing_period'] = 3

    # Wave1 최소 조건 (v1: 3% → v2: 5%)
    context['min_wave1_pct'] = 0.05

    # 피보나치 (v1: 0.236~0.886 → v2: 0.382~0.618 황금구간)
    context['fib_min'] = 0.382
    context['fib_max'] = 0.618
    context['fib_target'] = 1.618   # 목표가 161.8%
    context['fib_stop'] = 2.0       # 강제 청산 200%

    # RSI 파라미터 (v1: entry=35 → v2: entry=45)
    context['rsi_period'] = 14
    context['rsi_entry'] = 45
    context['rsi_overbought'] = 70

    # 리스크 관리 (v2 신규)
    context['risk_pct'] = 0.02      # 손실 허용 자본 비율 2%
    context['atr_period'] = 14      # ATR 기간
    context['atr_multiplier'] = 2.0 # 손절 = ATR × 2.0
    context['bep_trigger'] = 0.03   # +3% 달성 시 BEP로 손절 이동
    context['trail_trigger'] = 0.06 # +6% 달성 시 +3% 잠금

    # 추세 필터
    context['ma_period'] = 20       # 20MA 위에서만 매수

    # 내부 상태
    context['closes'] = []
    context['highs'] = []
    context['lows'] = []
    context['swing_highs'] = []
    context['swing_lows'] = []
    context['wave_state'] = 'IDLE'
    context['wave1_start'] = None
    context['wave1_end'] = None
    context['wave2_end'] = None
    context['entry_price'] = None
    context['stop_price'] = None
    context['bar_idx'] = 0
    context['rsi_values'] = []
    context['price_peaks'] = []


# ---------------------------------------------------------------------------
# 보조 지표 계산
# ---------------------------------------------------------------------------

def calc_rsi(prices, period):
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    recent = deltas[-(period):]
    gains = [d if d > 0 else 0.0 for d in recent]
    losses = [-d if d < 0 else 0.0 for d in recent]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_atr(highs, lows, closes, period):
    """ATR(Average True Range) 계산"""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def calc_ma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def find_swing_high(highs, period, idx):
    if idx < period or idx >= len(highs) - period:
        return False
    pivot = highs[idx]
    for i in range(idx - period, idx + period + 1):
        if i != idx and highs[i] >= pivot:
            return False
    return True


def find_swing_low(lows, period, idx):
    if idx < period or idx >= len(lows) - period:
        return False
    pivot = lows[idx]
    for i in range(idx - period, idx + period + 1):
        if i != idx and lows[i] <= pivot:
            return False
    return True


def validate_wave2(w1_start, w1_end, w2_end, fib_min, fib_max):
    w1_range = w1_end - w1_start
    if w1_range <= 0:
        return False
    retracement = (w1_end - w2_end) / w1_range
    if w2_end <= w1_start:
        return False
    return fib_min <= retracement <= fib_max


def reset_wave(context):
    context['wave_state'] = 'IDLE'
    context['wave1_start'] = None
    context['wave1_end'] = None
    context['wave2_end'] = None
    context['entry_price'] = None
    context['stop_price'] = None
    context['rsi_values'] = []
    context['price_peaks'] = []


# ---------------------------------------------------------------------------
# 메인 on_bar
# ---------------------------------------------------------------------------

def on_bar(context, bar):
    close = bar['close']
    high  = bar['high']
    low   = bar['low']

    context['closes'].append(close)
    context['highs'].append(high)
    context['lows'].append(low)
    context['bar_idx'] = context['bar_idx'] + 1

    if len(context['closes']) > 300:
        context['closes'] = context['closes'][-300:]
        context['highs'] = context['highs'][-300:]
        context['lows'] = context['lows'][-300:]

    closes = context['closes']
    highs  = context['highs']
    lows   = context['lows']
    idx    = len(closes) - 1
    sp     = context['swing_period']

    if idx < sp * 2 + 1:
        return None

    # 스윙 고/저점 업데이트 (abs_check_idx: 트리밍 후에도 단조 증가)
    check_idx = idx - sp
    abs_check_idx = context['bar_idx'] - sp
    if check_idx >= sp:
        if find_swing_high(highs, sp, check_idx):
            context['swing_highs'].append((abs_check_idx, highs[check_idx]))
        if find_swing_low(lows, sp, check_idx):
            context['swing_lows'].append((abs_check_idx, lows[check_idx]))

    if len(context['swing_highs']) > 60:
        context['swing_highs'] = context['swing_highs'][-60:]
    if len(context['swing_lows']) > 60:
        context['swing_lows'] = context['swing_lows'][-60:]

    # RSI
    rsi = calc_rsi(closes, context['rsi_period'])
    if rsi is None:
        return None

    # ATR
    atr = calc_atr(highs, lows, closes, context['atr_period'])

    # 20MA 추세 필터
    ma20 = calc_ma(closes, context['ma_period'])

    sh = context['swing_highs']
    sl = context['swing_lows']
    state = context['wave_state']
    symbol = bar['symbol']
    position = context.positions.get(symbol)

    # =========================================================
    # 포지션 보유 중: 청산 조건
    # =========================================================
    if position:
        entry = context['entry_price']
        stop  = context['stop_price']
        w2_end = context['wave2_end']
        w1_len = 0
        if context['wave1_start'] and context['wave1_end']:
            w1_len = context['wave1_end'] - context['wave1_start']

        qty = int(position.quantity)
        if qty <= 0:
            return None

        # --- Trailing Stop / Break-even 업데이트 ---
        if entry:
            bep_trigger   = context['bep_trigger']    # 0.03
            trail_trigger = context['trail_trigger']   # 0.06
            if close >= entry * (1 + trail_trigger):
                # +6% 이상: 수익의 절반 보호 (+3% 잠금)
                new_stop = entry * (1 + bep_trigger)
                if stop is None or new_stop > stop:
                    context['stop_price'] = new_stop
                    stop = new_stop
            elif close >= entry * (1 + bep_trigger):
                # +3% 이상: 진입가(BEP)로 손절 이동
                new_stop = entry
                if stop is None or new_stop > stop:
                    context['stop_price'] = new_stop
                    stop = new_stop

        # 1) 손절
        if stop and close <= stop:
            reset_wave(context)
            return [{'side': 'SELL', 'quantity': qty}]

        # 2) 목표가 도달 즉시 청산 (v2: RSI/다이버전스 조건 제거)
        if w2_end and w1_len > 0:
            target = w2_end + w1_len * context['fib_target']
            forced = w2_end + w1_len * context['fib_stop']
            if close >= target or close >= forced:
                reset_wave(context)
                return [{'side': 'SELL', 'quantity': qty}]

        return None

    # =========================================================
    # 포지션 없음: 파동 탐지 및 진입
    # =========================================================

    # IDLE: Wave1 + Wave2 패턴 탐지
    if state == 'IDLE':
        if len(sh) < 1 or len(sl) < 2:
            return None

        recent_sl = sl[-3:]
        recent_sh = sh[-3:]

        best = None
        for sh_b_idx, sh_b_price in recent_sh:
            for sl_a_idx, sl_a_price in recent_sl:
                for sl_c_idx, sl_c_price in recent_sl:
                    if not (sl_a_idx < sh_b_idx < sl_c_idx):
                        continue
                    if sh_b_price <= sl_a_price:
                        continue
                    if sl_a_price == 0:
                        continue
                    w1_pct = (sh_b_price - sl_a_price) / sl_a_price
                    if w1_pct < context['min_wave1_pct']:
                        continue
                    if sl_c_price <= sl_a_price:
                        continue
                    if not validate_wave2(sl_a_price, sh_b_price, sl_c_price,
                                          context['fib_min'], context['fib_max']):
                        continue
                    if best is None or sl_c_idx > best[2]:
                        best = (sl_a_price, sh_b_price, sl_c_idx, sl_c_price)

        if best:
            w1_start, w1_end, w2_idx, w2_end = best
            context['wave_state'] = 'WAVE2_CONFIRMED'
            context['wave1_start'] = w1_start
            context['wave1_end'] = w1_end
            context['wave2_end'] = w2_end
            state = 'WAVE2_CONFIRMED'

    # WAVE2_CONFIRMED: 진입 조건
    if state == 'WAVE2_CONFIRMED':
        w2_low   = context['wave2_end']
        w1_start = context['wave1_start']
        w1_end   = context['wave1_end']

        if w2_low is None or w1_start is None or w1_end is None:
            context['wave_state'] = 'IDLE'
            return None

        # 20MA 추세 필터: 20MA 아래면 진입 금지
        if ma20 and close < ma20:
            # Wave2가 Wave1 침범하면 패턴 초기화
            if close < w1_start * 0.99:
                reset_wave(context)
            return None

        # 진입 조건: Wave2 저점 위 + RSI >= 45 + Wave1 시작점 위
        if close > w2_low and rsi >= context['rsi_entry'] and close > w1_start:
            capital = float(context.cash)

            # ATR 기반 손절가 계산
            if atr and atr > 0:
                stop_price = close - atr * context['atr_multiplier']
            else:
                # ATR 없으면 Wave2 저점 아래 5%로 fallback
                stop_price = w2_low * 0.95
            stop_price = max(stop_price, w2_low * 0.92)  # Wave2 저점 -8% 하한선

            stop_dist_pct = (close - stop_price) / close
            if stop_dist_pct <= 0:
                return None

            # 고정 리스크 포지션 사이징 (자본의 2% 리스크)
            risk_amount = capital * context['risk_pct']
            position_value = risk_amount / stop_dist_pct
            position_value = min(position_value, capital * 0.30)  # 최대 자본의 30%
            qty = int(position_value / close)

            if qty <= 0:
                return None

            context['wave_state'] = 'IN_WAVE3_5'
            context['entry_price'] = close
            context['stop_price'] = stop_price
            context['rsi_values'] = [rsi]
            context['price_peaks'] = [close]
            return [{'side': 'BUY', 'quantity': qty}]

        # Wave2가 Wave1 침범 → 패턴 무효
        if close < w1_start * 0.99:
            reset_wave(context)

        # Wave2가 추가 하락 → w2_end 업데이트
        if low < w2_low and low > w1_start:
            context['wave2_end'] = low

    return None
