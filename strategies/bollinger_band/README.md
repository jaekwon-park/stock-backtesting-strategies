# 볼린저 밴드 전략 (Bollinger Band)

## 개요

볼린저 밴드를 활용한 **변동성 기반 역추세** 전략입니다.

- 가격이 **하단 밴드(SMA - 2σ) 이하**: 매수 진입
- 가격이 **상단 밴드(SMA + 2σ) 이상**: 매도 청산

## 파라미터

| 파라미터 | 기본값 | 타입 | 설명 |
|---------|--------|------|------|
| `bb_period` | 20 | int | 볼린저 밴드 기간 (이동평균 기간) |
| `bb_std` | 2.0 | float | 표준편차 배수 (밴드 폭 조절) |

## 전략 로직

```
SMA   = 최근 bb_period 봉의 종가 단순 평균
σ     = 최근 bb_period 봉의 표준편차

Upper Band = SMA + bb_std * σ
Lower Band = SMA - bb_std * σ

if 종가 <= Lower Band and 포지션 없음:
    → BUY 10주 (MARKET)

elif 종가 >= Upper Band and 포지션 있음:
    → SELL 전량 (MARKET)
```

## 특징

| 항목 | 내용 |
|------|------|
| 전략 유형 | 역추세 / 변동성 기반 |
| 적합 시장 | 횡보장, 변동성이 일정한 종목 |
| 최소 데이터 | `bb_period` 이상의 캔들 필요 (기본: 20봉) |

## 주의사항

- `bb_std` 값이 작을수록 밴드가 좁아져 신호가 잦아집니다.
- 강한 하락 추세에서 하단 밴드 돌파 후 반등이 오지 않을 수 있습니다.

## 관련 전략

- [이동평균 교차 전략](../moving_average/README.md)
- [RSI 전략](../rsi/README.md)
- [돌파 전략](../breakout/README.md)
