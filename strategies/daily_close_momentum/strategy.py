"""
전일 마감 모멘텀 스크리닝 전략 (Daily Close Momentum Screener)

전날 1분봉 장 마감 전 패턴을 분석해 익일 오전 1% 이상 상승이
기대되는 종목을 스크리닝합니다.

전략 개요:
─────────────────────────────────────────────────────────────
[Step 1] 전일 마감 4가지 조건 (모두 충족 시 매수 신호)

  조건 A — 종가 강도 ≥ 0.65
    (종가 - 당일 저가) / (당일 고가 - 당일 저가)
    → 고가 근처에서 마감 = 매수세 유지

  조건 B — 마감 1시간 상승률 ≥ 0.3%
    마지막 60분(60봉)의 가격 변화율
    → 오후 연속 매수세 확인

  조건 C — 마감 30분 거래량 배수 ≥ 1.5×
    마지막 30봉 평균 거래량 / 당일 전체 평균 거래량
    → 세력 개입 및 거래량 집중 확인

  조건 D — 당일 양봉
    종가 > 시가
    → 수급 주도 상승 확인

[Step 2] 익일 오전 포지션 관리
  - 전일 조건 충족 → 당일 첫 봉 매수
  - 60분 경과 후 자동 청산 (스크리닝 신호 갱신)
  - 전일 조건 미충족 시 보유 포지션 즉시 청산

파라미터 (params로 조정 가능):
  min_close_strength  : 종가 강도 하한  (기본 0.65)
  min_late_momentum   : 마감 1h 상승률  (기본 0.003 = 0.3%)
  min_vol_surge       : 마감 30분 거래량 배수 (기본 1.5)
  require_bullish_day : 당일 양봉 필수   (기본 True)
  exit_bars           : 익일 청산 봉 수  (기본 60)
─────────────────────────────────────────────────────────────
"""


def initialize(context):
    context['min_close_strength'] = 0.65
    context['min_late_momentum'] = 0.003
    context['min_vol_surge'] = 1.5
    context['require_bullish_day'] = True
    context['exit_bars'] = 60


def check_conditions(bars, min_close_strength, min_late_momentum, min_vol_surge, require_bullish):
    """전일 마감 조건 4가지 검사. 모두 충족하면 True."""
    if len(bars) < 120:
        return False

    day_open = float(bars[0]['open'])
    day_close = float(bars[-1]['close'])
    day_high = max(float(b['high']) for b in bars)
    day_low = min(float(b['low']) for b in bars)

    # 조건 A: 종가 강도
    day_range = day_high - day_low
    if day_range <= 0:
        return False
    close_strength = (day_close - day_low) / day_range
    if close_strength < min_close_strength:
        return False

    # 조건 B: 마감 1시간 상승률 (마지막 60봉)
    late_bars = bars[-60:]
    late_open = float(late_bars[0]['close'])
    late_close = float(late_bars[-1]['close'])
    if late_open <= 0:
        return False
    late_momentum = (late_close - late_open) / late_open
    if late_momentum < min_late_momentum:
        return False

    # 조건 C: 마감 30분 거래량 배수
    total_vol = sum(float(b['volume']) for b in bars)
    avg_vol = total_vol / len(bars)
    if avg_vol <= 0:
        return False
    late_30 = bars[-30:]
    late_30_vol = sum(float(b['volume']) for b in late_30)
    late_avg_vol = late_30_vol / len(late_30)
    vol_surge = late_avg_vol / avg_vol
    if vol_surge < min_vol_surge:
        return False

    # 조건 D: 당일 양봉
    if require_bullish and day_close <= day_open:
        return False

    return True


def on_bar(context, bar):
    date = bar['time'][:10]
    symbol = bar.get('symbol', '')
    prev_date = context.get('cur_date', '')

    # 날짜 변경 감지 → 전일 데이터 평가
    if date != prev_date and prev_date != '':
        prev_bars = context.get('today_bars', [])
        good = check_conditions(
            prev_bars,
            context.get('min_close_strength', 0.65),
            context.get('min_late_momentum', 0.003),
            context.get('min_vol_surge', 1.5),
            context.get('require_bullish_day', True),
        )
        context['cur_date'] = date
        context['today_bars'] = [bar]
        context['hold_count'] = 0

        if good and symbol not in context.positions:
            return [{'side': 'BUY', 'quantity': 1, 'order_type': 'MARKET'}]

        if not good and symbol in context.positions:
            context['hold_count'] = -1
            return [{'side': 'SELL', 'quantity': 1, 'order_type': 'MARKET'}]

        return []

    # 최초 실행 초기화
    if prev_date == '':
        context['cur_date'] = date
        context['today_bars'] = []
        context['hold_count'] = -1

    # 봉 누적
    today_bars = context.get('today_bars', [])
    today_bars.append(bar)
    context['today_bars'] = today_bars

    # 익일 오전 60분 경과 후 청산
    hold_count = context.get('hold_count', -1)
    if hold_count >= 0:
        context['hold_count'] = hold_count + 1
        if hold_count >= context.get('exit_bars', 60) and symbol in context.positions:
            context['hold_count'] = -1
            return [{'side': 'SELL', 'quantity': 1, 'order_type': 'MARKET'}]

    return []
