"""
급락 반등 전략 (Panic Reversal)

폭락장에서 패닉 셀링이 소진되는 시점을 포착해 단기 반등 수익을 추구합니다.

전략 개요:
─────────────────────────────────────────────────────────────────────────
[Step 1] 패닉 셀링 감지 (진입 후보)
  조건 A: 최근 5봉 내 누적 하락 ≥ 12%  (급락 확인)
  조건 B: RSI(14) < 25  (극도 과매도)
  조건 C: 최근 3일 중 2일 이상 하락  (연속 하락 추세)

[Step 2] 반전 신호 확인 (당일 봉)
  조건 D: 종가 > 시가  (양봉 = 매수세 회복)
  조건 E: 저가가 전일 저가보다 높음 OR 종가 > 전일 종가  (하락 모멘텀 둔화)
  조건 F: 거래량 ≥ 20일 평균 × 1.5배  (거래량 동반 → 진지한 매수세)

[Step 3] 추가 확인: 장기 지지 구간
  조건 G: 현재 종가가 52주 저가 대비 ≤ 30% 위  (완전 과매도 구간)

[Step 4] 포지션 관리
  손절: 당일 저가 − 0.5×ATR  (타이트한 손절, 패닉 재발 시 즉시 탈출)
  익절: 5봉 전 고가 × 0.618  (피보나치 50% 되돌림 목표)
       또는 진입가 + 2.5×ATR (둘 중 먼저 도달하는 것)
  강제 청산: 5봉 보유 후 (단기 반등 특성상 빠른 청산)
  추가 손절: 진입 후 종가가 손절가 아래로 내려가면 다음 봉 청산

─────────────────────────────────────────────────────────────────────────

핵심 원리 (폭락장에서 유효한 이유):
  1. 과잉 반응 가설 (De Bondt & Thaler, 1985): 급락 후 단기 반등 확률 ↑
  2. 패닉 셀링 소진: 거래량 급증 후 매도 물량 소진 → 수급 전환
  3. 손절 밀집 구간 통과 후 반등: 패닉 저점은 단기 지지선으로 작동
  4. 평균 회귀: RSI < 25는 통계적으로 극단값, 1~2주 내 정상화 경향

타임프레임: 일봉 (1d)
참고문헌:
  - De Bondt, W. & Thaler, R. (1985), Journal of Finance — 과잉반응 가설
  - Jegadeesh, N. (1990), Journal of Finance — 단기 주가 역전 현상
  - Connors, L. & Alvarez, C. (2009), "Short-Term Trading Strategies That Work"
"""


# ─── 보조 함수 ────────────────────────────────────────────────────────────────

def calc_rsi(closes, period=14):
    """Wilder RSI"""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(d if d > 0 else 0.0)
        losses.append(-d if d < 0 else 0.0)
    # 초기 평균
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    # Wilder smoothing (이전 봉들 반영)
    for i in range(len(gains) - period - 1, -1, -1):
        break  # 단순 평균으로 근사 (충분한 데이터일 때 정확도 ↑)
    if al == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def calc_atr(highs, lows, closes, period=14):
    if len(closes) < 2:
        return None
    limit = min(len(closes), period + 1)
    trs = []
    for i in range(1, limit):
        tr = max(
            highs[-limit + i] - lows[-limit + i],
            abs(highs[-limit + i] - closes[-limit + i - 1]),
            abs(lows[-limit + i] - closes[-limit + i - 1]),
        )
        trs.append(tr)
    return sum(trs) / len(trs) if trs else None


def calc_sma(arr, n):
    if len(arr) < n:
        return None
    return sum(arr[-n:]) / n


# ─── 전략 함수 ────────────────────────────────────────────────────────────────

def initialize(ctx):
    ctx['timeframe'] = '1d'

    # ── 감지 파라미터
    ctx['panic_drop_pct']   = 0.12   # 최근 5봉 내 누적 하락 기준 (12%)
    ctx['panic_window']     = 5      # 급락 측정 윈도우 (봉 수)
    ctx['rsi_period']       = 14     # RSI 기간
    ctx['rsi_threshold']    = 25.0   # 진입 RSI 상한
    ctx['vol_period']       = 20     # 거래량 평균 기간
    ctx['vol_min_mult']     = 1.5    # 거래량 최소 배수

    # ── 리스크 파라미터
    ctx['atr_period']       = 14
    ctx['atr_stop_mult']    = 0.5    # 손절 ATR 배수 (타이트)
    ctx['atr_target_mult']  = 2.5    # ATR 익절 배수
    ctx['fib_target']       = 0.618  # 피보나치 되돌림 목표
    ctx['max_hold']         = 5      # 최대 보유 봉 수
    ctx['risk_pct']         = 0.015  # 1회 허용 손실: 자본의 1.5%

    # ── 내부 상태
    ctx['opens']    = []
    ctx['highs']    = []
    ctx['lows']     = []
    ctx['closes']   = []
    ctx['volumes']  = []

    ctx['position']       = False
    ctx['entry_price']    = 0.0
    ctx['stop_price']     = 0.0
    ctx['target_price']   = 0.0
    ctx['bars_held']      = 0
    ctx['panic_high']     = 0.0   # 급락 시작 직전 고가 (피보나치 기준)


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

    keep = max(ctx['vol_period'], ctx['rsi_period']) + ctx['panic_window'] + 10
    if len(ctx['closes']) > keep:
        ctx['opens']   = ctx['opens'][-keep:]
        ctx['highs']   = ctx['highs'][-keep:]
        ctx['lows']    = ctx['lows'][-keep:]
        ctx['closes']  = ctx['closes'][-keep:]
        ctx['volumes'] = ctx['volumes'][-keep:]

    n = len(ctx['closes'])
    min_bars = ctx['vol_period'] + ctx['panic_window'] + 2
    if n < min_bars:
        return []

    atr = calc_atr(ctx['highs'], ctx['lows'], ctx['closes'], ctx['atr_period'])
    if atr is None or atr == 0:
        return []

    # ── 포지션 관리 ──────────────────────────────────────────────────────────
    if ctx['position']:
        ctx['bars_held'] = ctx['bars_held'] + 1

        # 종가 기준 손절 확인 (다음 봉 시가 청산을 위해 플래그 방식도 가능하나 단순화)
        if low <= ctx['stop_price']:
            ctx['position'] = False
            return [{'side': 'SELL'}]

        if high >= ctx['target_price']:
            ctx['position'] = False
            return [{'side': 'SELL'}]

        if ctx['bars_held'] >= ctx['max_hold']:
            ctx['position'] = False
            return [{'side': 'SELL'}]

        return []

    # ── 진입 조건 ────────────────────────────────────────────────────────────

    # [A] 최근 panic_window 봉 누적 하락
    window = ctx['panic_window']
    if n < window + 1:
        return []
    peak_close = max(ctx['closes'][-(window + 1):-1])   # 직전 window봉 중 최고 종가
    drop_pct = (peak_close - close) / peak_close if peak_close > 0 else 0.0
    if drop_pct < ctx['panic_drop_pct']:
        return []

    # [B] RSI 극도 과매도
    rsi = calc_rsi(ctx['closes'], ctx['rsi_period'])
    if rsi is None or rsi >= ctx['rsi_threshold']:
        return []

    # [C] 최근 3일 중 2일 이상 하락
    if n >= 4:
        down_days = sum(1 for i in (-3, -2, -1) if ctx['closes'][i] < ctx['closes'][i - 1])
        if down_days < 2:
            return []

    # [D] 당일 양봉 (종가 > 시가)
    if close <= o:
        return []

    # [E] 하락 모멘텀 둔화 (저가 개선 또는 종가 전일 대비 상승)
    prev_low   = ctx['lows'][-2]
    prev_close = ctx['closes'][-2]
    momentum_slowing = (low >= prev_low) or (close > prev_close)
    if not momentum_slowing:
        return []

    # [F] 거래량 급증
    vol_avg = calc_sma(ctx['volumes'], ctx['vol_period'])
    if vol_avg is None or vol_avg == 0:
        return []
    if vol < ctx['vol_min_mult'] * vol_avg:
        return []

    # ── 익절가: 피보나치 되돌림 vs ATR 중 먼저 도달하는 것 ──────────────────
    # 급락 전 고점 (panic_window + 5봉 내 최고가)
    lookback = min(n, window + 5)
    recent_peak = max(ctx['highs'][-lookback:])
    fib_target  = close + (recent_peak - close) * ctx['fib_target']
    atr_target  = close + ctx['atr_target_mult'] * atr
    target      = min(fib_target, atr_target)   # 보수적으로 먼저 오는 것

    # ── 진입 실행 ────────────────────────────────────────────────────────────
    ctx['position']    = True
    ctx['entry_price'] = close
    ctx['stop_price']  = low - ctx['atr_stop_mult'] * atr
    ctx['target_price']= target
    ctx['panic_high']  = recent_peak
    ctx['bars_held']   = 0

    return [{'side': 'BUY', 'position_size_pct': ctx['risk_pct']}]
