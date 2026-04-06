# 한국 장초 돌파 모멘텀 전략 (Korean Opening Range Momentum)

## 학술적 근거

| 논문 | 핵심 발견 | 성과 |
|------|----------|------|
| Gao et al. (JFE 2018) — Market Intraday Momentum | 장초 30분 수익률이 장마감 30분 수익률 방향을 예측 | Sharpe 1.08 (S&P 500) |
| MDPI JRFM (2022) — KOSPI MIM | KOSPI에서도 동일 패턴 검증됨 | 거래비용 차감 후 수익 |
| Zarattini et al. (Concretum Group, 2025) — ORB | 장초 5분 돌파 전략 백테스트 | CAGR 41.9%, Sharpe 1.07 |
| Zarattini & Aziz (SSRN 2023) — VWAP | VWAP 기반 필터 효과 | Sharpe 2.1 |

## 전략 로직

1. **장초 30분 (09:00–09:30)**: 고점·저점 기록 → Opening Range 형성
2. **진입 조건** (3가지 모두 충족):
   - 종가가 OR 고점 상향 돌파 (모멘텀)
   - 종가 > VWAP (추세 방향 확인)
   - 상대거래량 ≥ 1.5x (거래 활성도 확인)
3. **손절**: 진입가 - ATR(14) × 1.5
4. **청산**: 손절 도달 | 15:00 장마감 | 최대 4시간 보유

## 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `or_bars` | 6 | Opening range 봉 수 (5m × 6 = 30분) |
| `atr_period` | 14 | ATR 계산 기간 |
| `atr_mul` | 1.5 | 손절 거리 배율 |
| `min_rvol` | 1.5 | 최소 상대거래량 |
| `max_hold` | 48 | 최대 보유 봉 수 (5m × 48 = 4시간) |

## 권장 설정

- **타임프레임**: 5분봉
- **대상 종목**: 당일 거래량 상위, 갭 상승 종목에 효과적
- **주의**: 수익률 3%/일은 학술적 근거 상 어렵습니다. 이 전략은 **일관된 양의 기댓값**을 목표로 합니다.

## 현실적인 기대 성과 (학술 연구 기준)

- 일평균 수익률: **0.1–0.4%** (비용 차감 후)
- 연환산 수익률: 25–100%
- Sharpe Ratio: 1.0–2.1

> 3%/일 = 연 1,000%+ 는 어떤 전략으로도 지속 불가능합니다.
> 이 전략의 목표는 **장기적으로 시장을 이기는 일관된 알파**입니다.

## 참고 논문

- [Market Intraday Momentum (JFE 2018)](https://www.sciencedirect.com/science/article/pii/S0304405X18300120)
- [KOSPI MIM (MDPI 2022)](https://www.mdpi.com/1911-8074/15/11/523)
- [Opening Range Breakout Backtest (Concretum 2025)](https://concretumgroup.com/backtesting-the-opening-range-breakout-orb-strategy-using-polygon-io/)
- [VWAP Holy Grail (SSRN 2023)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4631351)

