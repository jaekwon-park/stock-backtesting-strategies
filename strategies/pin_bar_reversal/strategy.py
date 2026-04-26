"""
핀바 반전 매수 전략 (Bullish Pin Bar Reversal)

캔들의 긴 아래 꼬리(Pin Bar / Hammer)를 포착해 단기 반등 수익을 추구합니다.

전략 개요:
─────────────────────────────────────────────────────────────────────────
[Step 1] 하락 추세 확인 (진입 후보 필터)
  조건 A: 현재 종가가 20일 이동평균선 아래  (하락 구간)
  조건 B: 최근 5봉 수익률 ≤ -3%  (단기 눌림 확인)

[Step 2] 핀바 패턴 감지 (당일 봉)
  조건 C: 아래 꼬리 ≥ 전체 범위의 60%  (긴 아래 꼬리)
  조건 D: 아래 꼬리 ≥ 몸통의 2배  (꼬리가 몸통보다 충분히 김)
  조건 E: 위 꼬리 ≤ 전체 범위의 20%  (위 꼬리는 짧아야 함)
  조건 F: 종가 ≥ 시가  (양봉 핀바)

[Step 3] 거래량 확인
  조건 G: 거래량 ≥ 20일 평균 × 1.2배  (거래량 동반 반전)

[Step 4] 포지션 관리
  진입: 핀바 봉 종가에 매수
  손절: 핀바 저가 − 0.3 × ATR
  익절: 진입가 + 2.0 × ATR  (2:1 리스크:리워드)
  강제 청산: 8봉 보유 후

─────────────────────────────────────────────────────────────────────────

핵심 원리:
  1. 핀바 = 매도 압력이 소진된 증거  (저가까지 밀렸다가 종가 회복)
  2. 거래량 동반 반전 = 기관/세력 개입 신호
  3. 하락 추세 중 핀바 = 단기 과매도 반등

타임프레임: 일봉 (1d)
"""


def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr = sum(trs[-period:]) / period
    return atr if atr > 0 else None


def calc_sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def initialize(ctx):
    ctx['timeframe'] = '1d'

    # 추세 필터
    ctx['trend_ma_period']  = 20     # 추세 판단 이동평균 기간
    ctx['pullback_window']  = 5      # 눌림 확인 봉 수
    ctx['pullback_pct']     = 0.03   # 최소 눌림폭 (3%)

    # 핀바 판별 기준
    ctx['wick_ratio']       = 0.60   # 아래 꼬리 / 전체 범위 최소 비율
    ctx['body_wick_ratio']  = 2.0    # 아래 꼬리 / 몸통 최소 배수
    ctx['upper_wick_ratio'] = 0.20   # 위 꼬리 / 전체 범위 최대 비율

    # 거래량
    ctx['vol_period']       = 20
    ctx['vol_min_mult']     = 1.2    # 거래량 최소 배수

    # 리스크 관리
    ctx['atr_period']       = 14
    ctx['atr_stop_mult']    = 0.3    # 손절 ATR 배수
    ctx['atr_target_mult']  = 2.0    # 익절 ATR 배수 (2:1)
    ctx['max_hold']         = 8      # 최대 보유 봉 수
    ctx['risk_pct']         = 0.01   # 1회 허용 손실: 자본의 1%
    ctx['max_pos_pct']      = 0.20   # 종목당 최대 자본 비율

    # 내부 상태
    ctx['opens']    = []
    ctx['highs']    = []
    ctx['lows']     = []
    ctx['closes']   = []
    ctx['volumes']  = []
    ctx['pos_meta'] = {}    # symbol → {entry, stop, target, hold}


def on_bar(ctx, bar):
    o     = bar['open']
    high  = bar['high']
    low   = bar['low']
    close = bar['close']
    vol   = float(bar.get('volume', 0))

    ctx['opens'].append(o)
    ctx['highs'].append(high)
    ctx['lows'].append(low)
    ctx['closes'].append(close)
    ctx['volumes'].append(vol)

    keep = ctx['trend_ma_period'] + ctx['atr_period'] + ctx['pullback_window'] + 10
    if len(ctx['closes']) > keep:
        ctx['opens']   = ctx['opens'][-keep:]
        ctx['highs']   = ctx['highs'][-keep:]
        ctx['lows']    = ctx['lows'][-keep:]
        ctx['closes']  = ctx['closes'][-keep:]
        ctx['volumes'] = ctx['volumes'][-keep:]

    n = len(ctx['closes'])
    if n < ctx['trend_ma_period'] + ctx['atr_period'] + 2:
        return []

    symbol = bar.get('symbol', 'UNKNOWN')
    orders = []

    atr = calc_atr(ctx['highs'], ctx['lows'], ctx['closes'], ctx['atr_period'])
    if atr is None:
        return []

    # 포지션 관리 (청산 우선)
    meta = ctx['pos_meta'].get(symbol)
    if meta:
        meta['hold'] += 1

        if close >= meta['target']:
            orders.append({'side': 'SELL', 'symbol': symbol, 'qty': 9999999})
            ctx['pos_meta'].pop(symbol, None)
            return orders

        if low <= meta['stop']:
            orders.append({'side': 'SELL', 'symbol': symbol, 'qty': 9999999})
            ctx['pos_meta'].pop(symbol, None)
            return orders

        if meta['hold'] >= ctx['max_hold']:
            orders.append({'side': 'SELL', 'symbol': symbol, 'qty': 9999999})
            ctx['pos_meta'].pop(symbol, None)
            return orders

        return []

    # 진입 신호

    # [조건 A] 20일 이동평균 아래
    ma20 = calc_sma(ctx['closes'], ctx['trend_ma_period'])
    if ma20 is None or close >= ma20:
        return []

    # [조건 B] 최근 5봉 눌림 확인
    if n > ctx['pullback_window']:
        past_close = ctx['closes'][-(ctx['pullback_window'] + 1)]
        if past_close > 0 and (close - past_close) / past_close > -ctx['pullback_pct']:
            return []

    # [조건 C~F] 핀바 패턴
    candle_range = high - low
    if candle_range <= 0:
        return []

    body       = abs(close - o)
    lower_wick = min(o, close) - low
    upper_wick = high - max(o, close)

    if lower_wick / candle_range < ctx['wick_ratio']:
        return []
    if body > 0 and lower_wick / body < ctx['body_wick_ratio']:
        return []
    if upper_wick / candle_range > ctx['upper_wick_ratio']:
        return []
    if close < o:
        return []

    # [조건 G] 거래량
    vol_ma = calc_sma(ctx['volumes'], ctx['vol_period'])
    if vol_ma is None or vol_ma == 0 or vol < vol_ma * ctx['vol_min_mult']:
        return []

    # 수량 계산 (리스크 기반)
    stop_dist = atr * ctx['atr_stop_mult']
    if stop_dist <= 0:
        return []

    capital  = ctx.get('cash', 0)
    risk_amt = capital * ctx['risk_pct']
    qty      = int(risk_amt / stop_dist)

    max_qty = int(capital * ctx['max_pos_pct'] / close)
    qty = min(qty, max_qty)
    if qty <= 0:
        return []

    stop   = low - atr * ctx['atr_stop_mult']
    target = close + atr * ctx['atr_target_mult']

    ctx['pos_meta'][symbol] = {
        'entry':  close,
        'stop':   stop,
        'target': target,
        'hold':   0,
    }
    orders.append({'side': 'BUY', 'symbol': symbol, 'qty': qty})
    return orders
