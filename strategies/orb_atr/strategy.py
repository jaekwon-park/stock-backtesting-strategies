"""
ORB-ATR 전략 (Opening Range Breakout + ATR Stop)

5분봉 기준 개장 초기 30분(6봉)의 고가·저가 돌파를 진입 신호로 사용하며,
ATR 기반 동적 손절·익절과 포지션 사이징으로 일일 1% 수익을 목표로 합니다.

전략 개요:
- Opening Range: 당일 첫 6봉(30분)의 최고가·최저가 구간 설정
- 진입: 구간 상단 돌파 → 매수, 구간 하단 이탈 → 숏(롱 청산)
- 손절: 진입가 기준 1.5 × ATR
- 익절: 진입가 기준 2.0 × ATR (손익비 1:2)
- 포지션 사이징: 1회 손실 허용 = 자본의 0.5%
- 강제 청산: 당일 마지막 봉(일일 종료 시)
"""


def initialize(context):
    """전략 초기화"""
    context['timeframe'] = '5m'            # 5분봉 기준 전략 (ORB)
    # ----- OR 파라미터 -----
    context['or_bars'] = 6          # Opening Range 봉 수 (5분봉 × 6 = 30분)

    # ----- ATR 파라미터 -----
    context['atr_period'] = 14      # ATR 계산 기간
    context['atr_stop_mult'] = 1.5  # 손절 배수
    context['atr_target_mult'] = 2.0  # 익절 배수

    # ----- 리스크 관리 -----
    context['risk_per_trade'] = 0.005   # 1회 허용 손실: 자본의 0.5%
    context['max_daily_loss'] = 0.005   # 일일 최대 허용 손실: 자본의 0.5%
    context['equity'] = None            # 초기 자본 (첫 봉에서 설정)

    # ----- 내부 상태 -----
    context['bar_count'] = 0        # 당일 봉 누적 수
    context['or_high'] = None       # Opening Range 고가
    context['or_low'] = None        # Opening Range 저가
    context['or_bars_buf'] = []     # OR 계산용 버퍼 (high/low 리스트)
    context['highs'] = []           # ATR 계산용 고가 히스토리
    context['lows'] = []            # ATR 계산용 저가 히스토리
    context['closes'] = []          # ATR 계산용 종가 히스토리
    context['position'] = 0         # 현재 포지션 수량 (양수=롱)
    context['entry_price'] = None   # 진입가
    context['stop_price'] = None    # 손절가
    context['target_price'] = None  # 익절가
    context['daily_entry_done'] = False  # 당일 진입 여부 (1일 1회)
    context['daily_loss'] = 0.0     # 당일 누적 손실
    context['last_date'] = None     # 날짜 변경 감지용


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------

def calc_atr(highs, lows, closes, period):
    """ATR (Average True Range) 계산"""
    if len(closes) < 2:
        return None
    n = min(len(closes), period + 1)
    trs = []
    for i in range(1, n):
        tr = max(
            highs[-n + i] - lows[-n + i],
            abs(highs[-n + i] - closes[-n + i - 1]),
            abs(lows[-n + i] - closes[-n + i - 1]),
        )
        trs.append(tr)
    if len(trs) == 0:
        return None
    return sum(trs) / len(trs)


def position_size(equity, risk_pct, stop_dist, close):
    """
    1회 손실 한도 내 최대 수량 계산.
    stop_dist: 진입가 대비 손절 거리 (원 단위)
    반환값은 정수 수량 (최소 1주)
    """
    if stop_dist <= 0:
        return 1
    risk_amount = equity * risk_pct
    qty = int(risk_amount / stop_dist)
    return max(qty, 1)


# ---------------------------------------------------------------------------
# 메인 로직
# ---------------------------------------------------------------------------

def on_bar(context, bar):
    """
    매 5분봉마다 호출되는 메인 로직.

    Parameters
    ----------
    context : Context
        전략 실행 컨텍스트
    bar : dict
        현재 캔들 {'time', 'symbol', 'open', 'high', 'low', 'close', 'volume'}
    """
    high = bar['high']
    low = bar['low']
    close = bar['close']
    date_str = bar['time'][:10]   # "YYYY-MM-DD"

    # ----- 초기 자본 설정 -----
    if context['equity'] is None:
        context['equity'] = 10_000_000   # 기본 1,000만원 (백테스트 엔진이 주입하지 않는 경우)

    # ----- 날짜 변경 감지: 일별 상태 초기화 -----
    if context['last_date'] != date_str:
        context['last_date'] = date_str
        context['bar_count'] = 0
        context['or_high'] = None
        context['or_low'] = None
        context['or_bars_buf'] = []
        context['daily_entry_done'] = False
        context['daily_loss'] = 0.0

        # 미청산 포지션 강제 청산 (전일 잔여)
        if context['position'] > 0:
            orders = [{'side': 'SELL', 'quantity': context['position'], 'order_type': 'MARKET'}]
            context['position'] = 0
            context['entry_price'] = None
            context['stop_price'] = None
            context['target_price'] = None
            return orders

    context['bar_count'] = context['bar_count'] + 1

    # ----- 히스토리 누적 -----
    context['highs'].append(high)
    context['lows'].append(low)
    context['closes'].append(close)

    # ----- Opening Range 수집 (첫 6봉) -----
    if context['bar_count'] <= context['or_bars']:
        context['or_bars_buf'].append({'high': high, 'low': low})
        if context['bar_count'] == context['or_bars']:
            context['or_high'] = max(b['high'] for b in context['or_bars_buf'])
            context['or_low'] = min(b['low'] for b in context['or_bars_buf'])
        return []

    # OR 구간이 아직 설정되지 않은 경우 스킵
    if context['or_high'] is None or context['or_low'] is None:
        return []

    # ----- ATR 계산 -----
    atr = calc_atr(context['highs'], context['lows'], context['closes'], context['atr_period'])
    if atr is None or atr <= 0:
        return []

    orders = []

    # ----- 진입 중인 포지션 손절·익절 체크 -----
    if context['position'] > 0:
        stop = context['stop_price']
        target = context['target_price']
        qty = context['position']

        # 손절
        if low <= stop:
            loss = (stop - context['entry_price']) * qty
            context['daily_loss'] = context['daily_loss'] + loss
            context['position'] = 0
            context['entry_price'] = None
            context['stop_price'] = None
            context['target_price'] = None
            return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

        # 익절
        if high >= target:
            context['position'] = 0
            context['entry_price'] = None
            context['stop_price'] = None
            context['target_price'] = None
            return [{'side': 'SELL', 'quantity': qty, 'order_type': 'MARKET'}]

        return []

    # ----- 신규 진입 (1일 1회, 일일 손실 한도 체크) -----
    if context['daily_entry_done']:
        return []

    if context['daily_loss'] >= context['equity'] * context['max_daily_loss']:
        return []

    stop_dist = atr * context['atr_stop_mult']
    qty = position_size(context['equity'], context['risk_per_trade'], stop_dist, close)

    # 상단 돌파 → 롱 진입
    if close > context['or_high']:
        entry = close
        stop = entry - stop_dist
        target = entry + atr * context['atr_target_mult']

        context['position'] = qty
        context['entry_price'] = entry
        context['stop_price'] = stop
        context['target_price'] = target
        context['daily_entry_done'] = True

        orders.append({'side': 'BUY', 'quantity': qty, 'order_type': 'MARKET'})

    return orders
