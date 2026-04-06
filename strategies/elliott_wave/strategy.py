"""
Elliott Wave Strategy (엘리어트 파동 전략)

이론적 근거:
    R.N. Elliott (1938): "The Wave Principle"
    - 시장 가격은 충격파(Impulse Wave) 5개 + 조정파(Corrective Wave) 3개의
      반복적 프랙탈 구조로 움직인다.
    - 피보나치 비율(38.2%, 61.8%, 161.8%)이 각 파동의 목표가와 지지/저항 역할.

파동 구조:
    상승 5파동 (충격): 1(상) → 2(하/조정) → 3(상/최강) → 4(하/조정) → 5(상)
    조정 3파동: A(하) → B(상) → C(하)

파동 규칙 (3가지 불변 규칙):
    1. Wave 2는 Wave 1의 시작점 이하로 내려가지 않는다 (100% 이상 되돌림 금지)
    2. Wave 3은 Wave 1, 3, 5 중 가장 짧은 파동이 될 수 없다
    3. Wave 4는 Wave 1의 가격 영역과 겹치지 않는다

매수 조건 (Wave 2 완료 후 Wave 3 진입):
    - Wave 1 확인: 스윙 저점 → 스윙 고점 (최소 3% 상승)
    - Wave 2 확인: Wave 1 고점 이후 되돌림 (38.2%~78.6%)
    - 진입: Wave 2 저점에서 반등 시작 (close > wave2_low) + RSI >= 35

매도 조건:
    - 손절: Wave 2 저점 아래 8%
    - 익절: Wave 2 저점 기준 Wave 1 길이의 161.8% 도달
    - 추가 청산: RSI 과매수(70) + 베어리시 다이버전스

수정 이력:
    v1.0 — 최초 작성
    v1.1 — 버그 수정:
        - Wave1 탐지 인덱스 비교 방향 오류 수정 (> → <)
        - swing_period 5→3으로 축소 (탐지 지연 감소)
        - WAVE2_CONFIRMED 즉각 진입 가능하도록 상태 머신 개선
        - Wave1 최소 상승률 조건 추가 (3%)
        - 피보나치 되돌림 범위 완화 (0.382~0.786 → 0.236~0.886)
        - 진입 조건 RSI 기준 완화 (40 → 35)
        - 봉 배열 500봉 → 300봉 (메모리 최적화)
    v1.2 — 버그 수정:
        - closes[-300:] 트리밍 후 check_idx가 296에 고정되어 swing 항목이
          동일 인덱스 누적 → 시간순 정렬 실패 → 약 300봉(약 1년) 이후 진입 불가
        - 수정: abs_check_idx = bar_idx - sp 사용 (절대 봉 번호로 단조 증가 보장)
        - sl_a_price == 0 종목에서 float division by zero 방지 가드 추가

참고문헌:
    - Elliott, R.N. (1938). "The Wave Principle"
    - Prechter, R.R. & Frost, A.J. (1978). "Elliott Wave Principle"
    - Investopedia: https://www.investopedia.com/terms/e/elliottwavetheory.asp
"""


def initialize(context):
    """전략 파라미터 및 상태 초기화"""
    context['timeframe'] = '1d'          # 일봉 기준 전략

    # 파동 탐지 파라미터
    # v1.1: sp=5→3으로 축소 (Wave2 저점 탐지 지연 감소: 5봉→3봉)
    context['swing_period'] = 3

    # Wave1 최소 조건
    context['min_wave1_pct'] = 0.03      # Wave1 최소 상승률 3%

    # 피보나치 파라미터
    # v1.1: 범위 완화 (실제 시장에서 되돌림이 정확히 피보나치에 맞지 않음)
    context['fib_min'] = 0.236           # Wave2 최소 되돌림 (23.6%)
    context['fib_max'] = 0.886           # Wave2 최대 되돌림 (88.6%) — 규칙 1 경계
    context['fib_target'] = 1.618        # Wave5 목표 (Wave1 길이의 161.8%)
    context['fib_stop'] = 2.0            # 강제 청산 (Wave1 길이의 200%)

    # RSI 파라미터
    context['rsi_period'] = 14
    # v1.1: 기준 완화 (40→35), Wave2 조정에서 RSI가 항상 40 이상이 아닐 수 있음
    context['rsi_entry'] = 35            # 진입 최소 RSI
    context['rsi_overbought'] = 70       # Wave5 과열 감지

    # 리스크 관리
    context['stop_loss_pct'] = 0.08      # 손절 8%
    context['position_ratio'] = 0.95     # 자본 사용 비율

    # 내부 상태
    context['closes'] = []
    context['highs'] = []
    context['lows'] = []
    context['swing_highs'] = []          # [(index, price), ...]
    context['swing_lows'] = []           # [(index, price), ...]
    context['wave_state'] = 'IDLE'
    context['wave1_start'] = None        # Wave1 시작 저점 가격
    context['wave1_end'] = None          # Wave1 끝 고점 가격
    context['wave2_end'] = None          # Wave2 끝 저점 가격
    context['entry_price'] = None
    context['stop_price'] = None
    context['bar_idx'] = 0
    context['rsi_values'] = []           # 최근 RSI 값 추적 (다이버전스)
    context['price_peaks'] = []          # 최근 가격 고점 추적 (다이버전스)


# ---------------------------------------------------------------------------
# 보조 지표 계산 함수
# ---------------------------------------------------------------------------

def calc_rsi(prices, period):
    """RSI 계산 (단순 평균 방식)"""
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


def find_swing_high(highs, period, idx):
    """idx가 좌우 period봉 대비 최고점인지 확인"""
    if idx < period or idx >= len(highs) - period:
        return False
    pivot = highs[idx]
    for i in range(idx - period, idx + period + 1):
        if i != idx and highs[i] >= pivot:
            return False
    return True


def find_swing_low(lows, period, idx):
    """idx가 좌우 period봉 대비 최저점인지 확인"""
    if idx < period or idx >= len(lows) - period:
        return False
    pivot = lows[idx]
    for i in range(idx - period, idx + period + 1):
        if i != idx and lows[i] <= pivot:
            return False
    return True


def detect_bearish_divergence(price_peaks, rsi_values):
    """베어리시 다이버전스: 가격 신고점 + RSI 하락"""
    if len(price_peaks) < 2 or len(rsi_values) < 2:
        return False
    return price_peaks[-1] > price_peaks[-2] and rsi_values[-1] < rsi_values[-2]


# ---------------------------------------------------------------------------
# 파동 검증 함수
# ---------------------------------------------------------------------------

def validate_wave2(w1_start, w1_end, w2_end, fib_min, fib_max):
    """
    Wave2 되돌림 비율 검증.
    - fib_min ~ fib_max 범위
    - w2_end > w1_start (규칙 1: Wave2가 Wave1 시작점을 침범하지 않음)
    """
    w1_range = w1_end - w1_start
    if w1_range <= 0:
        return False
    retracement = (w1_end - w2_end) / w1_range
    if w2_end <= w1_start:          # 규칙 1 위반
        return False
    return fib_min <= retracement <= fib_max


def reset_wave(context):
    """파동 상태 초기화"""
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
    """매 일봉마다 호출."""
    close = bar['close']
    high  = bar['high']
    low   = bar['low']

    context['closes'].append(close)
    context['highs'].append(high)
    context['lows'].append(low)
    context['bar_idx'] = context['bar_idx'] + 1

    # 최대 300봉 유지 (v1.1: 500→300)
    if len(context['closes']) > 300:
        context['closes'] = context['closes'][-300:]
        context['highs'] = context['highs'][-300:]
        context['lows'] = context['lows'][-300:]

    closes = context['closes']
    highs  = context['highs']
    lows   = context['lows']
    idx    = len(closes) - 1
    sp     = context['swing_period']

    # 최소 봉 수 확인
    if idx < sp * 2 + 1:
        return None

    # --- 스윙 고/저점 업데이트 ---
    # check_idx: 현재봉에서 sp봉 이전 (미래 봉이 확정된 위치)
    # abs_check_idx: 절대 봉 번호 — closes 배열 트리밍 후에도 단조 증가 보장
    #   버그 수정 v1.2: closes[-300:] 트리밍 후 check_idx가 296에 고정되어
    #   모든 swing 항목이 동일 인덱스를 가져 시간순 정렬 검증 실패 → 진입 불가
    check_idx = idx - sp
    abs_check_idx = context['bar_idx'] - sp
    if check_idx >= sp:
        if find_swing_high(highs, sp, check_idx):
            context['swing_highs'].append((abs_check_idx, highs[check_idx]))
        if find_swing_low(lows, sp, check_idx):
            context['swing_lows'].append((abs_check_idx, lows[check_idx]))

    # 최대 60개 유지
    if len(context['swing_highs']) > 60:
        context['swing_highs'] = context['swing_highs'][-60:]
    if len(context['swing_lows']) > 60:
        context['swing_lows'] = context['swing_lows'][-60:]

    # RSI 계산
    rsi = calc_rsi(closes, context['rsi_period'])
    if rsi is None:
        return None

    sh = context['swing_highs']
    sl = context['swing_lows']
    state = context['wave_state']
    symbol = bar['symbol']
    position = context.positions.get(symbol)

    # =====================================================================
    # 포지션 보유 중: 청산 조건 체크
    # =====================================================================
    if position:
        stop = context['stop_price']
        w2_end = context['wave2_end']
        w1_len = 0
        if context['wave1_start'] and context['wave1_end']:
            w1_len = context['wave1_end'] - context['wave1_start']

        # RSI 고점 추적 (다이버전스용)
        if len(sh) >= 1:
            last_sh_idx, last_sh_price = sh[-1]
            if w2_end and last_sh_price > w2_end:
                context['price_peaks'].append(last_sh_price)
                context['rsi_values'].append(rsi)
                if len(context['price_peaks']) > 6:
                    context['price_peaks'] = context['price_peaks'][-6:]
                    context['rsi_values'] = context['rsi_values'][-6:]

        # 1) 손절
        if stop and close <= stop:
            qty = int(position.quantity)
            if qty > 0:
                reset_wave(context)
                return [{'side': 'SELL', 'quantity': qty}]

        # 2) 목표가 도달 청산 (Wave2 저점 기준 Wave1 길이 × 161.8%)
        if w2_end and w1_len > 0:
            target = w2_end + w1_len * context['fib_target']
            forced = w2_end + w1_len * context['fib_stop']

            bearish_div = detect_bearish_divergence(
                context['price_peaks'],
                context['rsi_values']
            )

            # 목표가 도달 + (RSI 과열 or 다이버전스)
            if close >= target and (rsi >= context['rsi_overbought'] or bearish_div):
                qty = int(position.quantity)
                if qty > 0:
                    reset_wave(context)
                    return [{'side': 'SELL', 'quantity': qty}]

            # 강제 청산 (과연장 방지)
            if close >= forced:
                qty = int(position.quantity)
                if qty > 0:
                    reset_wave(context)
                    return [{'side': 'SELL', 'quantity': qty}]

        return None

    # =====================================================================
    # 포지션 없음: 파동 탐지 및 진입
    # =====================================================================

    # --- IDLE: Wave1+Wave2 패턴 탐지 ---
    if state == 'IDLE':
        # 스윙 포인트 최소 2개 이상 필요
        if len(sh) < 1 or len(sl) < 2:
            return None

        # 최근 스윙 포인트 조합 순회 (최근 3개씩)
        # 구조: sl_a (Wave1 시작) → sh_b (Wave1 끝) → sl_c (Wave2 끝)
        # 조건: sl_a.idx < sh_b.idx < sl_c.idx (시간 순서)
        recent_sl = sl[-3:]   # 최근 저점 3개
        recent_sh = sh[-3:]   # 최근 고점 3개

        best = None
        for sh_b_idx, sh_b_price in recent_sh:
            for sl_a_idx, sl_a_price in recent_sl:
                for sl_c_idx, sl_c_price in recent_sl:
                    # 시간 순서 체크
                    if not (sl_a_idx < sh_b_idx < sl_c_idx):
                        continue
                    # Wave1 상승 확인
                    if sh_b_price <= sl_a_price:
                        continue
                    # Wave1 최소 상승률 확인 (3%) — sl_a_price == 0 가드 (v1.2)
                    if sl_a_price == 0:
                        continue
                    w1_pct = (sh_b_price - sl_a_price) / sl_a_price
                    if w1_pct < context['min_wave1_pct']:
                        continue
                    # Wave2가 Wave1 시작점 이상 (규칙 1)
                    if sl_c_price <= sl_a_price:
                        continue
                    # Wave2 피보나치 되돌림 검증
                    if not validate_wave2(sl_a_price, sh_b_price, sl_c_price,
                                          context['fib_min'], context['fib_max']):
                        continue
                    # 가장 최근 패턴 선택 (sl_c_idx 기준 최대값)
                    if best is None or sl_c_idx > best[2]:
                        best = (sl_a_price, sh_b_price, sl_c_idx, sl_c_price)

        if best:
            w1_start, w1_end, w2_idx, w2_end = best
            context['wave_state'] = 'WAVE2_CONFIRMED'
            context['wave1_start'] = w1_start
            context['wave1_end'] = w1_end
            context['wave2_end'] = w2_end
            state = 'WAVE2_CONFIRMED'   # 즉각 WAVE2_CONFIRMED 블록으로 진입 (v1.1 수정)

    # --- WAVE2_CONFIRMED: 진입 조건 체크 ---
    if state == 'WAVE2_CONFIRMED':
        w2_low   = context['wave2_end']
        w1_start = context['wave1_start']
        w1_end   = context['wave1_end']

        if w2_low is None or w1_start is None or w1_end is None:
            context['wave_state'] = 'IDLE'
            return None

        # 진입 조건:
        # 1) 현재가 Wave2 저점 이상 (반등 확인)
        # 2) RSI >= 35 (과매도 이탈)
        # 3) 현재가 Wave1 시작점 이상 (Wave2가 Wave1을 완전히 되돌리지 않음)
        if close > w2_low and rsi >= context['rsi_entry'] and close > w1_start:
            capital = float(context.cash)
            qty = int(capital * context['position_ratio'] // close)
            if qty <= 0:
                return None

            stop_price = w2_low * (1 - context['stop_loss_pct'])
            context['wave_state'] = 'IN_WAVE3_5'
            context['entry_price'] = close
            context['stop_price'] = stop_price
            context['rsi_values'] = [rsi]
            context['price_peaks'] = [close]
            return [{'side': 'BUY', 'quantity': qty}]

        # Wave2가 Wave1 시작점 침범 → 패턴 무효
        if close < w1_start * 0.99:
            reset_wave(context)

        # Wave2가 추가 하락하여 w1_start에 근접 → 새 저점으로 w2_end 업데이트
        if low < w2_low and low > w1_start:
            context['wave2_end'] = low

    return None
