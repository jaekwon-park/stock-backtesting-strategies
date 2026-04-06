# 돌파 전략 (Breakout)

## 개요

최근 N봉의 최고가/최저가 **레인지 돌파**를 이용하는 모멘텀 전략입니다.

- 현재 가격이 **최근 N봉 최고가 돌파**: 매수 진입
- 현재 가격이 **최근 N봉 최저가 이탈**: 매도 청산

## 파라미터

| 파라미터 | 기본값 | 타입 | 설명 |
|---------|--------|------|------|
| `breakout_period` | 20 | int | 레인지 계산 기간 (봉 수) |

## 전략 로직

```
range_high = 이전 breakout_period 봉의 최고가 중 최대값
range_low  = 이전 breakout_period 봉의 최저가 중 최소값

if 종가 > range_high and 포지션 없음:
    → BUY 10주 (MARKET)

elif 종가 < range_low and 포지션 있음:
    → SELL 전량 (MARKET)
```

## 특징

| 항목 | 내용 |
|------|------|
| 전략 유형 | 모멘텀 / 추세 추종 |
| 적합 시장 | 변동성 높은 강한 추세 종목 |
| 최소 데이터 | `breakout_period + 1` 이상의 캔들 필요 (기본: 21봉) |

## 주의사항

- 횡보장에서 잦은 돌파 신호로 수수료 손실이 발생할 수 있습니다.
- `breakout_period`를 늘릴수록 더 큰 움직임에서만 신호가 발생합니다.

## 관련 전략

- [이동평균 교차 전략](../moving_average/README.md)
- [RSI 전략](../rsi/README.md)
- [볼린저 밴드 전략](../bollinger_band/README.md)
