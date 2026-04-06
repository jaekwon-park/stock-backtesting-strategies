# 이동평균 교차 전략 (Moving Average Crossover)

## 개요

단기 이동평균과 장기 이동평균의 **교차 신호**를 이용하는 가장 기본적인 트렌드 추종 전략입니다.

- **골든크로스** (단기 MA > 장기 MA): 매수 진입
- **데드크로스** (단기 MA < 장기 MA): 매도 청산

## 파라미터

| 파라미터 | 기본값 | 타입 | 설명 |
|---------|--------|------|------|
| `short_window` | 5 | int | 단기 이동평균 윈도우 (5분봉 기준) |
| `long_window` | 20 | int | 장기 이동평균 윈도우 (5분봉 기준) |
| 매수 수량 | 10 | int | 1회 매수 주식 수 |

## 전략 로직

```
prices = 종가 누적 리스트

short_ma = prices 최근 short_window개의 평균
long_ma  = prices 최근 long_window개의 평균

if short_ma > long_ma and 포지션 없음:
    → BUY 10주 (MARKET)

elif short_ma < long_ma and 포지션 있음:
    → SELL 전량 (MARKET)
```

## 사용 방법

### 플랫폼에서 직접 사용

1. 백테스팅 플랫폼 접속 → 새 전략 만들기
2. **"GitHub에서 불러오기"** 선택
3. `strategies/moving_average/strategy.py` 선택
4. 백테스트 파라미터 설정 후 실행

### 코드 복사 사용

`strategy.py` 파일의 내용을 전략 에디터에 붙여넣고 실행합니다.

## 특징

| 항목 | 내용 |
|------|------|
| 전략 유형 | 트렌드 추종 (Trend Following) |
| 적합 시장 | 강한 추세가 있는 종목 (추세 없는 횡보장에서 손실 가능) |
| 최소 데이터 | long_window 이상의 캔들 필요 (기본: 20봉) |
| 매매 방식 | 시장가 주문 (MARKET) |
| 포지션 | 단순 롱 (매수 후 보유) |

## 주의사항

- 횡보장에서는 잦은 교차 신호로 수수료 손실이 발생할 수 있습니다.
- `long_window` 값을 늘릴수록 신호가 줄고 추세 추종 강도가 높아집니다.
- 실제 운용 시 리스크 관리(손절, 최대 손실 한도) 로직 추가를 권장합니다.

## 관련 전략

- [RSI 전략](../rsi/README.md) — 과매수/과매도 기반 역추세
- [볼린저 밴드 전략](../bollinger_band/README.md) — 변동성 기반 진입
- [돌파 전략](../breakout/README.md) — 레인지 돌파 기반
