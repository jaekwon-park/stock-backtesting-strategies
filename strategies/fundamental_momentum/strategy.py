"""
Fundamental Momentum Strategy (재무-모멘텀 복합 전략)

전략 근거:
  - Piotroski (2000) "Value Investing: The Use of Historical Financial Statement
    Information to Separate Winners from Losers", Journal of Accounting Research.
    → F-Score: 9개 재무지표 점수합 (수익성 3 + 레버리지 3 + 효율성 3)
  - 한국 KOSPI 적용 연구 (이상한, 2018): F-Score 고점 종목이 초과수익 유의
  - 기술적 필터: 단기 RSI 과매도 + 이동평균 상향 돌파로 매수 타이밍 정밀화

전략 로직:
  1. context['fundamentals'] 에서 F-Score 계산 (3점 이상 = 양호 종목 필터)
  2. 캔들 데이터로 RSI(14) + MA(20) 기술 신호 생성
  3. F-Score >= min_fscore AND RSI < rsi_buy AND close > MA(20) → 매수
  4. RSI > rsi_sell OR close < MA(20) * (1 - stop_loss) → 매도

context['fundamentals'] 구조 (백테스트 워커가 주입):
  {
    "2022-12-31": {
      "revenue":          302231360000000,
      "operating_profit":  43376630000000,
      "net_income":        55654077000000,
      "total_assets":     448424507000000,
      "total_equity":     354749604000000,
      "total_debt":        93674903000000,
      "operating_cf":      62181346000000,
      "eps":               8057.0
    },
    ...
  }
"""


# ─────────────────────────────────────────────────────────────
# 지표 계산 함수
# ─────────────────────────────────────────────────────────────

def calc_rsi(prices, period=14):
    """Wilder's Smoothing RSI"""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains  = [d if d > 0 else 0.0 for d in deltas]
    losses = [-d if d < 0 else 0.0 for d in deltas]
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def calc_ma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def piotroski_fscore(fund_now, fund_prev):
    """
    Piotroski F-Score 계산 (0 ~ 9점).
    fund_now / fund_prev: fundamentals dict (period_end 기준 최신 / 전년도)
    반환: (score, detail_dict)
    """
    score = 0
    detail = {}

    # ── 수익성 (Profitability) ──────────────────────────────
    assets_now  = fund_now.get('total_assets') or 1
    assets_prev = fund_prev.get('total_assets') or 1
    avg_assets  = (assets_now + assets_prev) / 2

    # F1: ROA > 0
    net_income = fund_now.get('net_income') or 0
    roa = net_income / avg_assets
    f1 = 1 if roa > 0 else 0
    score += f1
    detail['F1_ROA_positive'] = f1

    # F2: 영업현금흐름 > 0
    op_cf = fund_now.get('operating_cf') or 0
    f2 = 1 if op_cf > 0 else 0
    score += f2
    detail['F2_CFO_positive'] = f2

    # F3: ROA 증가 (전년 대비)
    net_income_prev = fund_prev.get('net_income') or 0
    roa_prev = net_income_prev / avg_assets
    f3 = 1 if roa > roa_prev else 0
    score += f3
    detail['F3_ROA_increased'] = f3

    # F4: 발생주의 = CFO/avg_assets > ROA (현금이익 > 회계이익)
    accrual = op_cf / avg_assets
    f4 = 1 if accrual > roa else 0
    score += f4
    detail['F4_Accrual_quality'] = f4

    # ── 레버리지/유동성 (Leverage/Liquidity) ───────────────
    equity_now  = fund_now.get('total_equity') or 1
    equity_prev = fund_prev.get('total_equity') or 1
    debt_now    = fund_now.get('total_debt') or 0
    debt_prev   = fund_prev.get('total_debt') or 0

    # F5: 장기부채비율 감소
    lev_now  = debt_now / assets_now
    lev_prev = debt_prev / (assets_prev or 1)
    f5 = 1 if lev_now < lev_prev else 0
    score += f5
    detail['F5_Leverage_down'] = f5

    # F6: 자기자본비율 개선 (단순화: 자본/자산 증가)
    eq_ratio_now  = equity_now / assets_now
    eq_ratio_prev = equity_prev / (assets_prev or 1)
    f6 = 1 if eq_ratio_now > eq_ratio_prev else 0
    score += f6
    detail['F6_Equity_ratio_up'] = f6

    # ── 효율성 (Operating Efficiency) ─────────────────────
    rev_now  = fund_now.get('revenue') or 0
    rev_prev = fund_prev.get('revenue') or 1
    op_now   = fund_now.get('operating_profit') or 0
    op_prev  = fund_prev.get('operating_profit') or 0

    # F7: 영업이익률 개선
    margin_now  = op_now / (rev_now or 1)
    margin_prev = op_prev / (rev_prev or 1)
    f7 = 1 if margin_now > margin_prev else 0
    score += f7
    detail['F7_Margin_improved'] = f7

    # F8: 자산회전율 개선
    turnover_now  = rev_now / assets_now
    turnover_prev = rev_prev / (assets_prev or 1)
    f8 = 1 if turnover_now > turnover_prev else 0
    score += f8
    detail['F8_Asset_turnover_up'] = f8

    # F9: EPS 개선
    eps_now  = fund_now.get('eps') or 0
    eps_prev = fund_prev.get('eps') or 0
    f9 = 1 if eps_now > eps_prev else 0
    score += f9
    detail['F9_EPS_improved'] = f9

    return score, detail


def get_fscore_from_context(context, current_date_str):
    """
    context['fundamentals'] 에서 current_date 이전 최신 2개 연도 데이터로
    F-Score 계산. fundamentals 없으면 None 반환.
    """
    fundamentals = context.get('fundamentals') or {}
    if len(fundamentals) < 2:
        return None, None

    # period_end 기준으로 current_date 이전 날짜만 사용
    valid_keys = sorted([
        k for k in fundamentals.keys()
        if k <= current_date_str[:10]
    ], reverse=True)

    if len(valid_keys) < 2:
        return None, None

    fund_now  = fundamentals[valid_keys[0]]
    fund_prev = fundamentals[valid_keys[1]]

    score, detail = piotroski_fscore(fund_now, fund_prev)
    return score, detail


# ─────────────────────────────────────────────────────────────
# 전략 진입점
# ─────────────────────────────────────────────────────────────

def initialize(context):
    """전략 파라미터 초기화"""
    context['timeframe'] = '1d'           # 일봉 기준 전략 (재무+기술)
    # 기술 지표 파라미터
    context['rsi_period']    = 14
    context['rsi_buy']       = 40      # RSI < 40: 과매도 영역 진입
    context['rsi_sell']      = 70      # RSI > 70: 과매수 영역 이탈
    context['ma_period']     = 20      # 20일 이동평균
    context['stop_loss']     = 0.08    # 8% 손절 (MA 기준 아닌 진입가 대비)

    # 재무 필터 파라미터
    context['min_fscore']    = 5       # F-Score 5점 이상만 매수
    context['use_fscore']    = True    # False 로 하면 순수 기술 전략으로 동작

    # 내부 상태
    context['prices']        = []
    context['position']      = 0
    context['entry_price']   = 0.0
    context['fscore']        = None
    context['fscore_detail'] = {}
    context['fscore_cached_date'] = ''


def on_bar(context, bar):
    """매 캔들마다 호출"""
    close = bar['close']
    date_str = bar['time'][:10]    # "2026-01-02T09:00:00Z" → "2026-01-02"

    context['prices'].append(close)
    prices = context['prices']

    # ── 기술 지표 계산 ─────────────────────────────────────
    rsi = calc_rsi(prices, context['rsi_period'])
    ma  = calc_ma(prices, context['ma_period'])

    if rsi is None or ma is None:
        return []

    # ── F-Score: 월 1회만 재계산 (성능) ───────────────────
    cached_month = context['fscore_cached_date'][:7] if context['fscore_cached_date'] else ''
    current_month = date_str[:7]
    if context['use_fscore'] and current_month != cached_month:
        score, detail = get_fscore_from_context(context, date_str)
        context['fscore'] = score
        context['fscore_detail'] = detail or {}
        context['fscore_cached_date'] = date_str

    fscore = context['fscore']
    min_f  = context['min_fscore']

    # ── 재무 필터 통과 여부 ────────────────────────────────
    if context['use_fscore']:
        fundamental_ok = (fscore is not None and fscore >= min_f)
    else:
        fundamental_ok = True

    position = context['position']
    orders   = []

    # ── 매수 조건 ──────────────────────────────────────────
    # 1) F-Score >= min_fscore (재무 건전성)
    # 2) RSI < rsi_buy (과매도 — 단기 저평가)
    # 3) close > MA (상승 추세 확인)
    if position == 0 and fundamental_ok and rsi < context['rsi_buy'] and close > ma:
        # 매수 수량: 전체 현금의 95% 투입
        available_cash = context.get('cash', 0)
        if available_cash <= 0:
            available_cash = context.get('initial_capital', 10000000)
        qty = int(available_cash * 0.95 / close)
        if qty > 0:
            context['position'] = qty
            context['entry_price'] = close
            orders.append({'side': 'BUY', 'quantity': qty})

    # ── 매도 조건 ──────────────────────────────────────────
    # 1) RSI > rsi_sell (과매수 — 단기 고평가)
    # 2) 손절: 진입가 대비 stop_loss% 이하
    # 3) F-Score 악화: 재무 필터 미통과 상태에서 MA 하향 이탈
    elif position > 0:
        entry_p  = context['entry_price']
        stop_hit = entry_p > 0 and close < entry_p * (1 - context['stop_loss'])
        fund_exit = context['use_fscore'] and not fundamental_ok and close < ma

        if rsi > context['rsi_sell'] or stop_hit or fund_exit:
            qty = context['position']
            context['position'] = 0
            context['entry_price'] = 0.0
            orders.append({'side': 'SELL', 'quantity': qty})

    return orders
