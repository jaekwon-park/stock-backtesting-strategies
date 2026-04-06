"""
돌파 전략 (Breakout)

최근 N봉의 최고가/최저가 레인지를 이용한 돌파 전략.
- 현재 가격이 최근 N봉 최고가 돌파: 매수
- 현재 가격이 최근 N봉 최저가 이탈: 매도
"""


def initialize(context):
    """전략 초기화"""
    context['timeframe'] = '1d'           # 일봉 기준 전략
    context['breakout_period'] = 20   # 레인지 계산 기간
    context['prices_high'] = []
    context['prices_low'] = []
    context['prices_close'] = []
    context['position'] = 0


def on_bar(context, bar):
    """
    매 캔들마다 호출되는 메인 로직

    Parameters
    ----------
    context : Context
        전략 실행 컨텍스트
    bar : dict
        현재 캔들 데이터 {'time', 'symbol', 'open', 'high', 'low', 'close', 'volume'}
    """
    context['prices_high'].append(bar['high'])
    context['prices_low'].append(bar['low'])
    context['prices_close'].append(bar['close'])

    period = context['breakout_period']
    highs = context['prices_high']
    lows = context['prices_low']
    close = bar['close']

    if len(highs) <= period:
        return []

    # 이전 N봉 기준 레인지 (현재 봉 제외)
    prev_highs = highs[-(period + 1):-1]
    prev_lows = lows[-(period + 1):-1]

    range_high = max(prev_highs)
    range_low = min(prev_lows)

    # 상단 돌파: 매수
    if close > range_high and context.get('position', 0) == 0:
        context['position'] = 10
        return [{'side': 'BUY', 'quantity': 10, 'order_type': 'MARKET'}]

    # 하단 이탈: 매도
    elif close < range_low and context.get('position', 0) > 0:
        qty = context.get('position', 0)
        context['position'] = 0
        return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

    return []
