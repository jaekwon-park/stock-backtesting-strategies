"""
변동성 스퀴즈 모멘텀 전략 (Volatility Squeeze Momentum)

볼린저 밴드(BB)와 켈트너 채널(KC)의 관계를 이용해 변동성 압축(스퀴즈) 이후
방향성 폭발 시점을 포착하는 전략입니다.

전략 개요:
─────────────────────────────────────────────────────────────────────────
[Step 1] 스퀴즈 감지
  BB_upper = SMA(20) + 2.0 × StdDev(20)
  BB_lower = SMA(20) − 2.0 × StdDev(20)
  KC_upper = EMA(20) + 1.5 × ATR(20)
  KC_lower = EMA(20) − 1.5 × ATR(20)

  SQUEEZE = BB_upper < KC_upper AND BB_lower > KC_lower
    → 변동성이 극도로 낮아진 압축 구간

[Step 2] 스퀴즈 해제 = 진입 신호
  이전 봉 SQUEEZE=True → 현재 봉 SQUEEZE=False

[Step 3] 방향성 필터
  momentum = close − ((최근20봉 고저 중간값 + SMA20) / 2)
  momentum > 0  AND  거래량 > 20일 평균 × 1.5배  →  롱 진입

[Step 4] 포지션 관리
  손절: max(진입가 − 2.0×ATR,  최고가 − 2.0×ATR)  ← 트레일링
  익절: 진입가 + 3.0×ATR
  강제청산: 10봉 초과 보유 시 (약 2주)

[Step 5] 포지션 사이징
  1회 허용 손실 = 자본의 2%
─────────────────────────────────────────────────────────────────────────

핵심 원리 (변동성이 심한 시장에서 유리한 이유):
  1. 변동성 클러스터링: 낮은 변동성 → 높은 변동성 전환이 반복됨
  2. 스퀴즈 해제 방향이 다음 추세 방향을 예측
  3. ATR 트레일링 스탑으로 추세를 끝까지 추종
  4. 높은 거래량 필터로 허위 신호 제거

타임프레임: 일봉 (1d)
참고문헌:
  - John F. Carter (2011), "Mastering the Trade" — TTM Squeeze
  - Bollinger, J. (2001), "Bollinger on Bollinger Bands"
  - Chester Keltner (1960), "How to Make Money in Commodities"
"""


# ─── 보조 함수 ────────────────────────────────────────────────────────────────

def calc_sma(arr, n):
    if len(arr) < n:
        return None
    return sum(arr[-n:]) / n


def calc_ema(arr, n):
    """EMA (지수이동평균)"""
    if len(arr) < n:
        return None
    k = 2.0 / (n + 1)
    ema = sum(arr[:n]) / n
    for v in arr[n:]:
        ema = v * k + ema * (1.0 - k)
    return ema


def calc_stddev(arr, n):
    if len(arr) < n:
        return None
    subset = arr[-n:]
    mean = sum(subset) / n
    variance = sum((x - mean) ** 2 for x in subset) / n
    return variance ** 0.5


def calc_atr(highs, lows, closes, n):
    if len(closes) < 2:
        return None
    limit = min(len(closes), n + 1)
    trs = []
    for i in range(1, limit):
        tr = max(
            highs[-limit + i] - lows[-limit + i],
            abs(highs[-limit + i] - closes[-limit + i - 1]),
            abs(lows[-limit + i] - closes[-limit + i - 1]),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


# ─── 전략 함수 ────────────────────────────────────────────────────────────────

def initialize(ctx):
    # ── 볼린저 밴드
    ctx['bb_period'] = 20
    ctx['bb_std']    = 2.0

    # ── 켈트너 채널
    ctx['kc_period'] = 20
    ctx['kc_mult']   = 1.5

    # ── ATR / 리스크
    ctx['atr_period']  = 14
    ctx['atr_stop']    = 2.0   # 손절 ATR 배수
    ctx['atr_target']  = 3.0   # 익절 ATR 배수
    ctx['risk_pct']    = 0.02  # 1회 허용 손실: 자본의 2%
    ctx['vol_filter']  = 1.5   # 거래량 필터 (평균 대비 배수)
    ctx['max_hold']    = 10    # 최대 보유 봉 수

    # ── 내부 상태
    ctx['highs']   = []
    ctx['lows']    = []
    ctx['closes']  = []
    ctx['volumes'] = []

    ctx['was_squeeze']          = False
    ctx['position']             = False
    ctx['entry_price']          = 0.0
    ctx['stop_price']           = 0.0
    ctx['target_price']         = 0.0
    ctx['highest_since_entry']  = 0.0
    ctx['bars_held']            = 0


def on_bar(ctx, bar):
    high  = bar['high']
    low   = bar['low']
    close = bar['close']
    vol   = float(bar.get('volume', 0))

    ctx['highs'].append(high)
    ctx['lows'].append(low)
    ctx['closes'].append(close)
    ctx['volumes'].append(vol)

    # 메모리 관리 (최근 N봉만 보관)
    keep = ctx['bb_period'] + ctx['atr_period'] + 10
    if len(ctx['closes']) > keep:
        ctx['highs']   = ctx['highs'][-keep:]
        ctx['lows']    = ctx['lows'][-keep:]
        ctx['closes']  = ctx['closes'][-keep:]
        ctx['volumes'] = ctx['volumes'][-keep:]

    n      = len(ctx['closes'])
    period = ctx['bb_period']

    # 지표 계산에 필요한 최소 봉 수 확인
    min_bars = period + ctx['atr_period'] + 2
    if n < min_bars:
        return []

    # ── 지표 계산 ────────────────────────────────────────────────────────────
    ma  = calc_sma(ctx['closes'], period)
    std = calc_stddev(ctx['closes'], period)
    ema = calc_ema(ctx['closes'], period)
    atr = calc_atr(ctx['highs'], ctx['lows'], ctx['closes'], ctx['atr_period'])

    if None in (ma, std, ema, atr) or std == 0 or atr == 0:
        return []

    # 볼린저 밴드
    bb_upper = ma + ctx['bb_std'] * std
    bb_lower = ma - ctx['bb_std'] * std

    # 켈트너 채널
    kc_upper = ema + ctx['kc_mult'] * atr
    kc_lower = ema - ctx['kc_mult'] * atr

    # 스퀴즈 여부
    is_squeeze = (bb_upper < kc_upper) and (bb_lower > kc_lower)

    # 모멘텀 (최근 period봉 고저 중간값 대비 현재 종가)
    recent_high = max(ctx['highs'][-period:])
    recent_low  = min(ctx['lows'][-period:])
    midpoint    = (recent_high + recent_low) / 2.0
    momentum    = close - ((midpoint + ma) / 2.0)

    # 거래량 평균
    vol_avg = calc_sma(ctx['volumes'], period)
    if vol_avg is None or vol_avg == 0:
        ctx['was_squeeze'] = is_squeeze
        return []

    # ── 포지션 관리 ──────────────────────────────────────────────────────────
    if ctx['position']:
        ctx['bars_held'] = ctx['bars_held'] + 1

        # 최고가 갱신 (트레일링 스탑 기준)
        if high > ctx['highest_since_entry']:
            ctx['highest_since_entry'] = high

        # 트레일링 스탑: 최고가에서 2×ATR 아래
        trailing_stop  = ctx['highest_since_entry'] - ctx['atr_stop'] * atr
        effective_stop = max(ctx['stop_price'], trailing_stop)

        # 청산 조건 확인
        if low <= effective_stop:
            ctx['position'] = False
            ctx['was_squeeze'] = is_squeeze
            return [{'side': 'SELL'}]

        if high >= ctx['target_price']:
            ctx['position'] = False
            ctx['was_squeeze'] = is_squeeze
            return [{'side': 'SELL'}]

        if ctx['bars_held'] >= ctx['max_hold']:
            ctx['position'] = False
            ctx['was_squeeze'] = is_squeeze
            return [{'side': 'SELL'}]

        ctx['was_squeeze'] = is_squeeze
        return []

    # ── 진입 조건 ────────────────────────────────────────────────────────────
    squeeze_released = ctx['was_squeeze'] and (not is_squeeze)
    ctx['was_squeeze'] = is_squeeze

    if not squeeze_released:
        return []

    # 방향성 필터: 상승 모멘텀
    if momentum <= 0:
        return []

    # 거래량 확인: 평균 대비 1.5배 이상
    if vol < ctx['vol_filter'] * vol_avg:
        return []

    # ── 진입 실행 ────────────────────────────────────────────────────────────
    ctx['position']            = True
    ctx['entry_price']         = close
    ctx['stop_price']          = close - ctx['atr_stop'] * atr
    ctx['target_price']        = close + ctx['atr_target'] * atr
    ctx['highest_since_entry'] = high
    ctx['bars_held']           = 0

    return [{'side': 'BUY', 'position_size_pct': ctx['risk_pct']}]
