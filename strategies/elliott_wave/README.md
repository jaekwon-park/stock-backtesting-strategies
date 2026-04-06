# Elliott Wave Strategy (엘리어트 파동 전략)

## 개요
R.N. Elliott의 파동 이론을 기반으로 한 일봉 트렌드 추종 전략.

## 파동 구조
- **충격파 5파동**: 1(상) → 2(하/조정) → 3(상/최강) → 4(하/조정) → 5(상)
- **조정파 3파동**: A(하) → B(상) → C(하)

## 3가지 불변 규칙
1. Wave 2는 Wave 1 시작점 이하로 하락 불가
2. Wave 3는 Wave 1, 3, 5 중 최단 파동 불가
3. Wave 4는 Wave 1 가격 영역과 겹치지 않음

## 매수 조건 (Wave 3 진입)
- Wave 1 확인: 스윙 저점 → 스윙 고점 상승
- Wave 2 확인: 피보나치 38.2%~78.6% 되돌림
- Wave 3 진입: Wave 2 저점에서 반등 + RSI ≥ 40

## 청산 조건
- 손절: Wave 2 저점 × (1 - stop_loss_pct)
- 익절: Wave 1 길이의 100%~161.8% 도달 + (RSI 과열 or 베어리시 다이버전스)

## 파라미터
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| swing_period | 5 | 스윙 고/저점 탐지 기간 |
| fib_min | 0.382 | Wave2 최소 되돌림 (38.2%) |
| fib_max | 0.786 | Wave2 최대 되돌림 (78.6%) |
| rsi_period | 14 | RSI 기간 |
| rsi_oversold | 40 | Wave2 확인 RSI 기준 |
| rsi_overbought | 70 | Wave5 과열 RSI 기준 |
| stop_loss_pct | 0.08 | 손절 비율 |

## 참고문헌
- Elliott, R.N. (1938). "The Wave Principle"
- Prechter, R.R. & Frost, A.J. (1978). "Elliott Wave Principle"
- Investopedia Elliott Wave Theory
