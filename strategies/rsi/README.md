# RSI 전략 (Relative Strength Index)

## 개요

RSI(상대강도지수) 지표를 활용한 **과매수/과매도 역추세** 전략입니다.

- **RSI < 30** (과매도): 매수 진입
- **RSI > 70** (과매수): 매도 청산

## 파라미터

| 파라미터 | 기본값 | 타입 | 설명 |
|---------|--------|------|------|
| `rsi_period` | 14 | int | RSI 계산 기간 |
| `oversold_level` | 30 | float | 과매도 기준 (이하 시 매수) |
| `overbought_level` | 70 | float | 과매수 기준 (이상 시 매도) |

## 전략 로직

```
RSI = 100 - (100 / (1 + RS))
RS  = 평균 상승폭 / 평균 하락폭 (최근 rsi_period 봉)

if RSI < oversold_level and 포지션 없음:
    → BUY 10주 (MARKET)

elif RSI > overbought_level and 포지션 있음:
    → SELL 전량 (MARKET)
```

## 특징

| 항목 | 내용 |
|------|------|
| 전략 유형 | 역추세 (Mean Reversion) |
| 적합 시장 | 횡보장, 과매수·과매도 반복 종목 |
| 최소 데이터 | `rsi_period + 1` 이상의 캔들 필요 (기본: 15봉) |

## 주의사항

- 강한 추세장에서는 과매도/과매수 상태가 지속되어 큰 손실이 발생할 수 있습니다.
- `oversold_level`을 낮추고 `overbought_level`을 높이면 신호가 줄어 안정성이 높아집니다.

## 관련 전략

- [이동평균 교차 전략](../moving_average/README.md)
- [볼린저 밴드 전략](../bollinger_band/README.md)
