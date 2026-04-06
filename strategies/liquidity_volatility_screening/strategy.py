def initialize(context):
    context['vol_period'] = 20          # 거래대금 이동평균 기간 (일)
    context['atr_period'] = 14          # ATR 산출 기간
    context['min_tv'] = 30000000000     # 최소 거래대금: 300억 원
    context['min_atr_ratio'] = 0.015    # ATR/Close 최소 비율: 1.5%
    context['bars'] = []


def on_bar(context, bar):
    context['bars'].append(bar)

    # 필요한 만큼만 보관 (메모리 절약)
    keep = context['vol_period'] + context['atr_period'] + 5
    if len(context['bars']) > keep:
        context['bars'] = context['bars'][-keep:]

    bars = context['bars']
    needed = context['vol_period'] + context['atr_period']
    if len(bars) < needed:
        return

    close = bar['close']
    if close <= 0:
        return

    # ── 1. 일평균 거래대금 (일봉 Close × Volume 평균) ──────────────
    tv_window = bars[-context['vol_period']:]
    total_tv = 0
    for b in tv_window:
        total_tv = total_tv + b['close'] * b['volume']
    avg_tv = total_tv / context['vol_period']

    # ── 2. ATR(14) — Wilder 스무딩 ────────────────────────────────
    trs = []
    for i in range(1, len(bars)):
        h  = bars[i]['high']
        l  = bars[i]['low']
        pc = bars[i - 1]['close']
        tr = max(h - l, abs(h - pc), abs(l - pc))
        trs.append(tr)

    period = context['atr_period']
    if len(trs) < period:
        return

    atr_val = sum(trs[:period]) / period          # 초기값: 단순 평균
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period   # Wilder 평활

    atr_ratio = atr_val / close

    # ── 3. 스크리닝 조건 판단 ──────────────────────────────────────
    cond_tv  = avg_tv >= context['min_tv']            # 거래대금 300억+
    cond_atr = atr_ratio >= context['min_atr_ratio']  # ATR/Close 1.5%+

    position = context['position']

    if cond_tv and cond_atr:
        # 두 조건 충족 → 보유 아니면 전액 매수
        if position == 0:
            qty = int(context['cash'] / close)
            if qty > 0:
                context['order']('BUY', qty)
    else:
        # 조건 미달 → 보유 중이면 청산
        if position > 0:
            context['order']('SELL', position)