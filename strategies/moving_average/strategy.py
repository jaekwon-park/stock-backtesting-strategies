"""
이동평균 교차 전략 (Moving Average Crossover)

단기 이동평균과 장기 이동평균의 교차를 이용한 매수/매도 전략.
- 단기 MA > 장기 MA: 골든크로스 → 매수
- 단기 MA < 장기 MA: 데드크로스 → 매도
"""


def initialize(context):
    """전략 초기화 - 백테스트 시작 시 1회 호출"""
    context['timeframe'] = '5m'            # 5분봉 기준 전략
    context['short_window'] = 5    # 단기 이동평균 윈도우 (5분봉)
    context['long_window'] = 20    # 장기 이동평균 윈도우 (20분봉)
    context['prices'] = []
    context['position'] = 0


def on_bar(context, bar):
    """
    매 캔들(5분봉)마다 호출되는 메인 로직

    Parameters
    ----------
    context : Context
        전략 실행 컨텍스트 (포지션, 자산, 파라미터 등)
    bar : dict
        현재 캔들 데이터
        {
            'time': str,    # 캔들 시각 (ISO 8601)
            'symbol': str,  # 종목 코드 (예: '005930')
            'open': float,  # 시가
            'high': float,  # 고가
            'low': float,   # 저가
            'close': float, # 종가
            'volume': int   # 거래량
        }

    Returns
    -------
    list[dict]
        주문 목록. 빈 리스트 반환 시 주문 없음.
        주문 형식: {'side': 'BUY'|'SELL', 'quantity': int, 'order_type': 'MARKET'}
    """
    context['prices'].append(bar['close'])
    prices = context['prices']

    # 충분한 데이터가 쌓일 때까지 대기
    if len(prices) < context['long_window']:
        return []

    short_ma = sum(prices[-context['short_window']:]) / context['short_window']
    long_ma = sum(prices[-context['long_window']:]) / context['long_window']

    # 골든크로스: 매수
    if short_ma > long_ma and context.get('position', 0) == 0:
        context['position'] = 10
        return [{'side': 'BUY', 'quantity': 10, 'order_type': 'MARKET'}]

    # 데드크로스: 매도
    elif short_ma < long_ma and context.get('position', 0) > 0:
        qty = context.get('position', 0)
        context['position'] = 0
        return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

    return []
