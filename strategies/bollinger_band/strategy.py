"""
볼린저 밴드 전략 (Bollinger Band)

볼린저 밴드를 이용한 변동성 기반 전략.
- 가격이 하단 밴드 이하: 매수
- 가격이 상단 밴드 이상: 매도
"""


def initialize(context):
    """전략 초기화"""
    context['timeframe'] = '1d'           # 일봉 기준 전략
    context['bb_period'] = 20       # 볼린저 밴드 기간
    context['bb_std'] = 2.0         # 표준편차 배수
    context['prices'] = []
    context['position'] = 0


def calc_bollinger(prices, period, std_mult):
    """볼린저 밴드 계산"""
    if len(prices) < period:
        return None, None, None

    window = prices[-period:]
    sma = sum(window) / period
    variance = sum((p - sma) ** 2 for p in window) / period
    std = variance ** 0.5

    upper = sma + std_mult * std
    lower = sma - std_mult * std
    return upper, sma, lower


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
    close = bar['close']
    context['prices'].append(close)

    upper, mid, lower = calc_bollinger(
        context['prices'],
        context['bb_period'],
        context['bb_std']
    )

    if upper is None:
        return []

    # 하단 밴드 터치: 매수
    if close <= lower and context.get('position', 0) == 0:
        context['position'] = 10
        return [{'side': 'BUY', 'quantity': 10, 'order_type': 'MARKET'}]

    # 상단 밴드 터치: 매도
    elif close >= upper and context.get('position', 0) > 0:
        qty = context.get('position', 0)
        context['position'] = 0
        return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

    return []
