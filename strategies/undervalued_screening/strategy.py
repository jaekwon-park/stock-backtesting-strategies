# 저평가 종목 스크리닝 전략 (Undervalued Stock Screener)
# ─────────────────────────────────────────────────────────────
# 재무 지표 기반 저평가 종목을 선별하는 전략입니다.
# KIS 재무데이터 수집 후 종목 스크리닝에서 사용하세요.
#
# 저평가 판단 기준:
#   PER  ≤ max_per  : 낮을수록 이익 대비 저평가
#   PBR  ≤ max_pbr  : 1 미만이면 자산 대비 저평가 (청산가치 이하)
#   ROE  ≥ min_roe  : 자기자본이익률 — 수익성 기준
#   EPS  ≥ min_eps  : 적자 기업 제외 (EPS 양수)
#
# context['fundamentals'] 구조 (KIS 수집 또는 DART 수집 후 자동 주입):
#   { "YYYY-MM-DD": { "eps": float, "bps": float, "per": float, "pbr": float, "roe": float } }
#
# 신호 의미:
#   BUY  = 저평가 기준 충족 → 매수 고려
#   SELL = 기준 미충족 (보유 포지션 있을 때)
#   HOLD = 조건 충족하지 못함 / 재무 데이터 없음
# ─────────────────────────────────────────────────────────────

def initialize(context):
    # 저평가 판단 기준 파라미터 (백테스트/스크리닝 시 조정 가능)
    context['max_per'] = 15.0   # PER 상한 (0이면 체크 안함)
    context['max_pbr'] = 1.2    # PBR 상한 (0이면 체크 안함)
    context['min_roe'] = 8.0    # ROE 하한 % (0이면 체크 안함)
    context['min_eps'] = 1.0    # EPS 최솟값

def on_bar(context, bar):
    fd_all = context.get('fundamentals', {})
    if not fd_all:
        return []

    # 가장 최신 기간의 재무 데이터 사용
    latest_key = sorted(fd_all.keys())[-1]
    fd = fd_all[latest_key]

    eps = float(fd.get('eps') or 0)
    bps = float(fd.get('bps') or 0)
    per = float(fd.get('per') or 0)
    pbr = float(fd.get('pbr') or 0)
    roe = float(fd.get('roe') or 0)

    price = bar['close']

    # PER: 직접 제공되지 않으면 현재가 / EPS 로 계산
    if per <= 0 and eps > 0 and price > 0:
        per = price / eps

    # PBR: 직접 제공되지 않으면 현재가 / BPS 로 계산
    if pbr <= 0 and bps > 0 and price > 0:
        pbr = price / bps

    # ROE: 직접 제공되지 않으면 EPS / BPS * 100 으로 근사
    if roe <= 0 and bps > 0 and eps > 0:
        roe = (eps / bps) * 100

    max_per = context.get('max_per', 15.0)
    max_pbr = context.get('max_pbr', 1.2)
    min_roe = context.get('min_roe', 8.0)
    min_eps = context.get('min_eps', 1.0)

    undervalued = True

    # PER 조건
    if max_per > 0 and (per <= 0 or per > max_per):
        undervalued = False

    # PBR 조건
    if max_pbr > 0 and (pbr <= 0 or pbr > max_pbr):
        undervalued = False

    # ROE 조건
    if min_roe > 0 and roe < min_roe:
        undervalued = False

    # EPS 조건 (적자 기업 제외)
    if eps < min_eps:
        undervalued = False

    # 실제 포지션은 context.positions에서 확인 (context['position']은 항상 0이므로 사용 금지)
    symbol = bar.get('symbol', '')
    has_position = symbol in context.positions

    if undervalued and not has_position:
        return [{'side': 'BUY', 'quantity': 1, 'order_type': 'MARKET'}]
    elif not undervalued and has_position:
        return [{'side': 'SELL', 'quantity': 1, 'order_type': 'MARKET'}]

    return []
