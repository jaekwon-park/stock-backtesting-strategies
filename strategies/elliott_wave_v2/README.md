# Elliott Wave Strategy v2.0 (손실 최소화 버전)

## 개요
v1 엘리어트 파동 전략의 손실을 줄이기 위한 개선 버전.
ATR 동적 손절, Break-even/Trailing Stop, 황금 피보나치 구간, 고정 리스크 포지션 사이징을 적용.

## v1 → v2 주요 개선사항

| 항목 | v1 | v2 |
|------|----|----|
| 손절 | 고정 8% | ATR × 2.0 동적 손절 |
| 피보나치 되돌림 | 23.6%~88.6% | 38.2%~61.8% (황금구간) |
| Wave1 최소 상승률 | 3% | 5% |
| RSI 진입 기준 | 35 | 45 |
| 포지션 사이징 | 고정 비율 | 고정 리스크 (자본 2%) |
| 목표가 청산 | RSI + 다이버전스 조건 | 도달 즉시 청산 |
| 추세 필터 | 없음 | 20MA 필터 (하락추세 진입 금지) |
| Break-even Stop | 없음 | +3% 도달 시 진입가로 손절 이동 |
| Trailing Stop | 없음 | +6% 도달 시 +3% 잠금 |

## 매수 조건 (Wave 3 진입)
- Wave 1 확인: 스윙 저점 → 스윙 고점 상승 (≥ 5%)
- Wave 2 확인: 피보나치 38.2%~61.8% 되돌림 (황금구간)
- 20MA 위에서만 진입 (상승 추세 확인)
- RSI ≥ 45 (강한 모멘텀 확인)
- Wave 1 시작점 위에서 진입 (파동 유효성)

## 청산 조건
1. **손절**: ATR × 2.0 아래 (또는 Wave2 저점 -8% 하한선)
2. **Break-even**: 진입가 +3% 달성 시 손절을 진입가로 이동
3. **Trailing Stop**: 진입가 +6% 달성 시 +3% 수익 잠금
4. **목표가**: Wave1 길이의 161.8% 도달 시 즉시 청산
5. **강제청산**: Wave1 길이의 200% 도달 시 청산

## 파라미터
| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| swing_period | 3 | 스윙 고/저점 탐지 기간 |
| min_wave1_pct | 0.05 | Wave1 최소 상승률 (5%) |
| fib_min | 0.382 | Wave2 최소 되돌림 (38.2%) |
| fib_max | 0.618 | Wave2 최대 되돌림 (61.8%) |
| fib_target | 1.618 | 목표가 (161.8%) |
| rsi_period | 14 | RSI 기간 |
| rsi_entry | 45 | 진입 RSI 기준 |
| risk_pct | 0.02 | 손실 허용 자본 비율 (2%) |
| atr_period | 14 | ATR 기간 |
| atr_multiplier | 2.0 | 손절 = ATR × 배수 |
| bep_trigger | 0.03 | Break-even 발동 기준 (+3%) |
| trail_trigger | 0.06 | Trailing Stop 발동 기준 (+6%) |
| ma_period | 20 | 추세 필터 MA 기간 |

## 참고문헌
- Elliott, R.N. (1938). "The Wave Principle"
- Prechter, R.R. & Frost, A.J. (1978). "Elliott Wave Principle"
