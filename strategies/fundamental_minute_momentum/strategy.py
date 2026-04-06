"""
Fundamental Value + Daily Trend Strategy (재무가치 + 일봉 추세 전략)

전략 개요:
    재무제표로 우량 저평가 종목을 선별하고, 일봉 추세 지표로 매수 타이밍을 잡는
    포지션 트레이딩 전략. 목표 보유 기간 1~3개월.

이론적 근거:
    - Piotroski (2000): F-Score로 재무 우량주 선별 → 초과수익 검증.
    - Graham & Dodd (1934): Graham Number로 내재가치 산출, 10% 이상 안전마진.
    - Asness et al. (2013): 가치+모멘텀 결합 시 안정적 초과수익.
    - Jegadeesh & Titman (1993): 3~12개월 가격 모멘텀 유효성 검증.

매수 조건 (모두 충족):
    1. 재무 필터: Piotroski F-Score >= 6, ROE >= 10%
    2. 저평가 필터: 내재가치(Graham Number / EPS×P/E / BPS 중 최솟값) 대비
                   현재가 <= 90% (10% 이상 저평가)
    3. 추세 진입: 20일 MA > 60일 MA (골든크로스 이후 유지)
    4. 모멘텀 확인: MACD 히스토그램 > 0 (상승 추세 초입)
    5. 과열 방지: RSI(14) < 65 (과매수 직전)

매도 조건 (하나라도 충족):
    1. 목표수익 달성: 진입가 대비 +15%
    2. 손절: 진입가 대비 -7%
    3. 추세 이탈: 20일 MA < 60일 MA (데드크로스)
    4. 최소 보유기간(20거래일) 경과 후 MACD 히스토그램 음전환

파라미터:
    min_fscore       (int)   기본 6    — 최소 F-Score
    min_roe          (float) 기본 0.10 — 최소 ROE 10%
    undervalue_pct   (float) 기본 0.10 — 저평가 기준 10%
    target_pe        (float) 기본 15.0 — EPS 기반 P/E 배수
    rsi_period       (int)   기본 14   — RSI 기간
    rsi_max_buy      (float) 기본 65   — 과열 방지 상한선
    ma_fast          (int)   기본 20   — 단기 이동평균 기간
    ma_slow          (int)   기본 60   — 장기 이동평균 기간
    macd_fast        (int)   기본 12   — MACD 빠른 EMA
    macd_slow        (int)   기본 26   — MACD 느린 EMA
    macd_signal      (int)   기본 9    — MACD 시그널 EMA
    stop_pct         (float) 기본 0.07 — 손절 7%
    target_pct       (float) 기본 0.15 — 목표수익 15%
    min_hold_bars    (int)   기본 20   — 최소 보유 거래일
    max_position_pct (float) 기본 0.10 — 최대 포지션 10%
"""


# ====================== 지표 계산 ======================

def calc_sma(prices, period):
    """단순 이동평균."""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def calc_ema(prices, period):
    """지수 이동평균 (EMA)."""
    if len(prices) < period:
        return None
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for p in prices[period:]:
        ema = p * k + ema * (1 - k)
    return ema


def calc_macd(prices, fast=12, slow=26, signal=9):
    """
    MACD 계산.
    Returns (macd_line, signal_line, histogram) or (None, None, None).
    """
    if len(prices) < slow + signal:
        return None, None, None
    ema_fast = calc_ema(prices, fast)
    ema_slow = calc_ema(prices, slow)
    if ema_fast is None or ema_slow is None:
        return None, None, None
    macd_line = ema_fast - ema_slow

    # 시그널 라인: 최근 signal 기간의 MACD 값 EMA
    # 근사치: 마지막 signal 개 MACD 값으로 EMA 계산
    macd_history = []
    step = max(1, len(prices) // (signal * 2))
    for i in range(signal + 1, 0, -1):
        window = prices[:-i] if i > 0 else prices
        ef = calc_ema(window, fast)
        es = calc_ema(window, slow)
        if ef is not None and es is not None:
            macd_history.append(ef - es)
    if len(macd_history) < signal:
        return macd_line, macd_line, 0.0
    signal_line = calc_ema(macd_history, signal) if len(macd_history) >= signal else macd_line
    if signal_line is None:
        signal_line = macd_line
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_rsi(prices, period=14):
    """Wilder's smoothing RSI."""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ====================== 재무 분석 ======================

def calc_piotroski(fund_now, fund_prev):
    """Piotroski F-Score (0~9점). Returns (score, detail)."""
    score = 0
    detail = {}

    ni = fund_now.get("net_income") or 0
    ocf = fund_now.get("operating_cf") or 0
    ta = fund_now.get("total_assets") or 1
    te = fund_now.get("total_equity") or 0
    td = fund_now.get("total_debt") or 0
    rev = fund_now.get("revenue") or 0
    op = fund_now.get("operating_profit") or 0
    eps = fund_now.get("eps") or 0

    ta_p = fund_prev.get("total_assets") or 1
    te_p = fund_prev.get("total_equity") or 1
    td_p = fund_prev.get("total_debt") or 0
    rev_p = fund_prev.get("revenue") or 1
    op_p = fund_prev.get("operating_profit") or 0
    ni_p = fund_prev.get("net_income") or 0
    eps_p = fund_prev.get("eps") or 0

    roa = ni / ta
    roa_p = ni_p / ta_p

    if roa > 0:
        score = score + 1
        detail["F1"] = "ROA>0"
    if ocf > 0:
        score = score + 1
        detail["F2"] = "OCF>0"
    if roa > roa_p:
        score = score + 1
        detail["F3"] = "ROA증가"
    if ta > 0 and (ocf / ta) > roa:
        score = score + 1
        detail["F4"] = "발생주의품질"
    lev = td / ta
    lev_p = td_p / ta_p
    if lev < lev_p:
        score = score + 1
        detail["F5"] = "레버리지감소"
    eq = te / ta
    eq_p = te_p / ta_p
    if eq > eq_p:
        score = score + 1
        detail["F6"] = "자기자본비율증가"
    margin = op / rev if rev else 0
    margin_p = op_p / rev_p if rev_p else 0
    if margin > margin_p:
        score = score + 1
        detail["F7"] = "영업이익률개선"
    turn = rev / ta
    turn_p = rev_p / ta_p
    if turn > turn_p:
        score = score + 1
        detail["F8"] = "자산회전율증가"
    if eps > eps_p:
        score = score + 1
        detail["F9"] = "EPS증가"

    return score, detail


def calc_intrinsic_value(fund_now, target_pe=15.0):
    """
    내재가치 = min(EPS×PE, BPS, GrahamNumber).
    BPS 없으면 총자산으로 추정.
    """
    eps = fund_now.get("eps") or 0
    bps = fund_now.get("bps") or 0

    if bps == 0:
        te = fund_now.get("total_equity") or 0
        ni = fund_now.get("net_income") or 0
        if eps > 0 and ni > 0 and te > 0:
            shares = ni / eps
            bps = te / shares if shares > 0 else 0

    candidates = []
    if eps > 0:
        candidates.append(eps * target_pe)
    if bps > 0:
        candidates.append(bps)
    if eps > 0 and bps > 0:
        # Newton-Raphson sqrt (math 미사용)
        val = 22.5 * eps * bps
        x = val
        for _ in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19]:
            x = (x + val / x) / 2
        candidates.append(x)

    return min(candidates) if candidates else None


def get_latest_fundamentals(context, date_str):
    """현재 날짜 이전 가장 최신 재무 데이터 2개 반환."""
    fundamentals = context.get("fundamentals") or {}
    if not fundamentals:
        return None, None
    valid = sorted([k for k in fundamentals.keys() if k <= date_str], reverse=True)
    if not valid:
        return None, None
    fund_now = fundamentals[valid[0]]
    fund_prev = fundamentals[valid[1]] if len(valid) >= 2 else fund_now
    return fund_now, fund_prev


def check_fundamental(context, date_str, price):
    """
    재무 필터 + 저평가 필터.
    Returns (passed, intrinsic_value).
    """
    fund_now, fund_prev = get_latest_fundamentals(context, date_str)
    if fund_now is None:
        return True, None  # 데이터 없으면 필터 통과

    min_fscore = context.get("min_fscore", 6)
    min_roe = context.get("min_roe", 0.10)
    undervalue_pct = context.get("undervalue_pct", 0.10)
    target_pe = context.get("target_pe", 15.0)

    # F-Score
    score, detail = calc_piotroski(fund_now, fund_prev)
    if score < min_fscore:
        return False, None

    # ROE
    ni = fund_now.get("net_income") or 0
    te = fund_now.get("total_equity") or 1
    te_p = fund_prev.get("total_equity") or te
    avg_eq = (te + te_p) / 2
    roe = ni / avg_eq if avg_eq else 0
    if roe < min_roe:
        return False, None

    # 저평가
    intrinsic = calc_intrinsic_value(fund_now, target_pe)
    if intrinsic and intrinsic > 0:
        threshold = intrinsic * (1.0 - undervalue_pct)
        if price > threshold:
            return False, intrinsic  # 저평가 기준 미달

    return True, intrinsic


# ====================== 전략 엔트리포인트 ======================

def initialize(context):
    """파라미터 및 내부 상태 초기화."""
    context["timeframe"] = "1d"           # 일봉 기준 전략 (재무가치 + 일봉추세)
    # 재무 파라미터
    context["min_fscore"] = 6
    context["min_roe"] = 0.10
    context["undervalue_pct"] = 0.10
    context["target_pe"] = 15.0

    # 기술 파라미터 (일봉)
    context["rsi_period"] = 14
    context["rsi_max_buy"] = 65        # 과열 방지 상한
    context["ma_fast"] = 20            # 단기 MA 기간
    context["ma_slow"] = 60            # 장기 MA 기간
    context["macd_fast"] = 12
    context["macd_slow"] = 26
    context["macd_signal"] = 9
    context["stop_pct"] = 0.07         # 손절 7%
    context["target_pct"] = 0.15       # 목표수익 15%
    context["min_hold_bars"] = 20      # 최소 보유 거래일 (약 1개월)
    context["max_position_pct"] = 0.10 # 최대 포지션 10%

    # 내부 상태
    context["prices"] = []             # 일봉 종가 시계열
    context["position"] = 0
    context["entry_price"] = 0.0
    context["stop_price"] = 0.0
    context["target_price"] = 0.0
    context["hold_bars"] = 0           # 보유 거래일 수
    context["fund_cache_month"] = ""
    context["fund_ok"] = True
    context["intrinsic_value"] = None
    context["prev_macd_hist"] = None   # 직전 MACD 히스토그램


def on_bar(context, bar):
    """매 일봉마다 호출되는 메인 로직."""
    close = bar["close"]
    date_str = bar["time"][:10]        # YYYY-MM-DD

    # --- 종가 시계열 누적 ---
    context["prices"].append(close)
    if len(context["prices"]) > 200:
        context["prices"] = context["prices"][-200:]

    prices = context["prices"]
    ma_fast = context["ma_fast"]
    ma_slow = context["ma_slow"]

    # --- 지표 계산 ---
    sma20 = calc_sma(prices, ma_fast)
    sma60 = calc_sma(prices, ma_slow)
    rsi = calc_rsi(prices, context["rsi_period"])
    _, _, macd_hist = calc_macd(
        prices,
        context["macd_fast"],
        context["macd_slow"],
        context["macd_signal"],
    )

    orders = []
    position = context.get("position", 0)

    # =================== 매수 로직 ===================
    if position == 0:
        # 재무 캐시: 월 1회 갱신
        current_month = date_str[:7]
        if context.get("fund_cache_month") != current_month:
            passed, intrinsic = check_fundamental(context, date_str, close)
            context["fund_ok"] = passed
            context["intrinsic_value"] = intrinsic
            context["fund_cache_month"] = current_month

        # 기술 조건
        golden_cross = (sma20 is not None and sma60 is not None and sma20 > sma60)
        macd_positive = (macd_hist is not None and macd_hist > 0)
        rsi_ok = (rsi is not None and rsi < context["rsi_max_buy"])

        if context["fund_ok"] and golden_cross and macd_positive and rsi_ok:
            capital = context.get("initial_capital", 10000000)
            qty = int(capital * context["max_position_pct"] / close)
            if qty > 0:
                context["position"] = qty
                context["entry_price"] = close
                context["stop_price"] = close * (1.0 - context["stop_pct"])
                context["target_price"] = close * (1.0 + context["target_pct"])
                context["hold_bars"] = 0
                context["prev_macd_hist"] = macd_hist
                orders.append({"side": "BUY", "quantity": qty})

    # =================== 매도 로직 ===================
    elif position > 0:
        context["hold_bars"] = context.get("hold_bars", 0) + 1
        hold = context["hold_bars"]
        entry = context["entry_price"]
        stop = context["stop_price"]
        target = context["target_price"]
        prev_hist = context.get("prev_macd_hist")

        sell = False
        reason = ""

        # 1. 손절 (즉시)
        if close <= stop:
            sell = True
            reason = "손절"

        # 2. 목표수익 달성 (즉시)
        elif target > 0 and close >= target:
            sell = True
            reason = "목표수익"

        # 3. 골든크로스 붕괴 (데드크로스) — 최소 보유 후
        elif hold >= context["min_hold_bars"]:
            dead_cross = (sma20 is not None and sma60 is not None and sma20 < sma60)
            if dead_cross:
                sell = True
                reason = "데드크로스"

            # 4. 최소 보유 후 MACD 히스토그램 음전환
            elif (macd_hist is not None and prev_hist is not None
                  and prev_hist > 0 and macd_hist <= 0):
                sell = True
                reason = "MACD음전환"

        if sell:
            orders.append({"side": "SELL", "quantity": position})
            context["position"] = 0
            context["hold_bars"] = 0
            context["entry_price"] = 0.0
        else:
            context["prev_macd_hist"] = macd_hist

    return orders
