"""
RSI (Relative Strength Index) 전략

RSI 지표를 이용한 과매수/과매도 역추세 전략.
- RSI < oversold_level: 과매도 → 매수
- RSI > overbought_level: 과매수 → 매도
"""


def initialize(context):
    """전략 초기화"""
    context['timeframe'] = '1d'           # 일봉 기준 전략
    context['rsi_period'] = 14           # RSI 계산 기간
    context['oversold_level'] = 30       # 과매도 기준 (이하 시 매수)
    context['overbought_level'] = 70     # 과매수 기준 (이상 시 매도)
    context['prices'] = []
    context['position'] = 0


def calc_rsi(prices, period):
    """RSI 계산 (Wilder's smoothing 방식)"""
    if len(prices) < period + 1:
        return None

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


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
    context['prices'].append(bar['close'])
    prices = context['prices']

    rsi = calc_rsi(prices, context['rsi_period'])
    if rsi is None:
        return []

    # 과매도: 매수
    if rsi < context['oversold_level'] and context.get('position', 0) == 0:
        context['position'] = 10
        return [{'side': 'BUY', 'quantity': 10, 'order_type': 'MARKET'}]

    # 과매수: 매도
    elif rsi > context['overbought_level'] and context.get('position', 0) > 0:
        qty = context.get('position', 0)
        context['position'] = 0
        return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

    return []
