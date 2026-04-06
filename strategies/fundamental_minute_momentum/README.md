# Fundamental Value + Daily Trend Strategy

재무제표 우량·저평가 종목을 선별하고 일봉 추세 지표로 진입 타이밍을 잡는 **포지션 트레이딩 전략**.  
목표 보유 기간: **1~3개월**.

---

## 전략 개요

| 항목 | 내용 |
|------|------|
| 타임프레임 | 1일봉 (1d) |
| 보유 기간 | 1~3개월 (최소 20거래일) |
| 재무 기준 | 연간 결산 기준 |
| 매수 조건 | 재무 필터 + 저평가 + 골든크로스 + MACD 양전환 + RSI < 65 |
| 청산 조건 | 목표수익(+15%) / 손절(-7%) / 데드크로스 / MACD 음전환 |

---

## 이론적 근거

### 1. Piotroski F-Score — 재무 건전성 점수
> Piotroski, J.D. (2000). *Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers*. Journal of Accounting Research, 38(Supplement), 1–41.

9개 항목(수익성 4개 + 레버리지 2개 + 효율 3개)으로 0~9점 채점.  
점수 ≥ 6인 종목이 점수 ≤ 2 대비 연간 **+23%p 초과수익** (원 논문 결과).  
한국 시장에서도 유효성 확인 (이상한, 2018).

| 항목 | 기준 |
|------|------|
| F1 ROA > 0 | 수익 창출 |
| F2 OCF > 0 | 현금 창출 |
| F3 ROA 증가 | 수익성 개선 |
| F4 발생주의 품질 | OCF/TA > ROA |
| F5 레버리지 감소 | 부채 관리 |
| F6 자기자본비율 증가 | 재무 안정성 |
| F7 영업이익률 개선 | 마진 확대 |
| F8 자산회전율 증가 | 운영 효율 |
| F9 EPS 증가 | 주당이익 성장 |

### 2. 내재가치 기반 저평가 필터 (Graham Number)
> Graham, B. & Dodd, D. (1934). *Security Analysis*. McGraw-Hill.  
> Buffett, W. (1992). *Berkshire Hathaway Annual Letter to Shareholders*.

3가지 내재가치 방법 중 **가장 보수적인 값** 적용:

| 방법 | 공식 | 설명 |
|------|------|------|
| P/E 기반 | EPS × 15 | KOSPI 평균 P/E 적용 |
| 순자산가치 | BPS × 1.0 | 장부가 기준 |
| Graham Number | √(22.5 × EPS × BPS) | 그레이엄의 안전마진 공식 |

**현재가 ≤ 내재가치 × 0.9** (10% 이상 저평가) 시 매수 검토.

### 3. 골든크로스 + MACD — 추세 진입 타이밍
> Appel, G. (1979). *The Moving Average Convergence-Divergence Method*. Signalert.  
> Jegadeesh, N. & Titman, S. (1993). *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency*. Journal of Finance, 48(1), 65–91.

- **20일 MA > 60일 MA** (골든크로스): 중기 상승 추세 확인
- **MACD 히스토그램 > 0**: 단기 모멘텀이 장기를 상회 → 상승 초입
- 가치주 + 모멘텀 결합 시 리스크 조정 수익률 최대화 (Asness et al., 2013)

### 4. RSI — 과열 방지
> Wilder, J.W. (1978). *New Concepts in Technical Trading Systems*. Trend Research.

- RSI < 65: 이미 과열된 종목 매수 회피 (추격매수 방지)
- 가치주는 저평가 상태이므로 RSI 65 미만에서 매수 기회 충분

---

## 매매 로직

```
[매수 진입] 모든 조건 충족 시
  1. 재무: F-Score >= 6, ROE >= 10%
  2. 가치: 현재가 <= 내재가치 × 90% (10% 이상 저평가)
  3. 추세: 20일 MA > 60일 MA (골든크로스 이후)
  4. 모멘텀: MACD 히스토그램 > 0
  5. 과열방지: RSI(14) < 65

[청산 조건] 우선순위 순
  1. 손절 (즉시): close <= 진입가 × 0.93 (-7%)
  2. 목표수익 (즉시): close >= 진입가 × 1.15 (+15%)
  3. 데드크로스 (최소 20거래일 후): 20일 MA < 60일 MA
  4. MACD 음전환 (최소 20거래일 후): MACD 히스토그램 양 → 음 전환
```

---

## 파라미터

백테스트 실행 시 `params` 필드로 원하는 값만 선택적으로 오버라이드 가능합니다.

```json
{
  "params": {
    "undervalue_pct": 0.05,
    "min_fscore": 5,
    "stop_pct": 0.07,
    "target_pct": 0.20
  }
}
```

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `min_fscore` | 6 | 최소 Piotroski F-Score (낮출수록 진입 빈도 증가) |
| `min_roe` | 0.10 | 최소 ROE 10% |
| `undervalue_pct` | 0.10 | **저평가 기준 (0.05 = 5%, 0.10 = 10%)** |
| `target_pe` | 15.0 | EPS 기반 내재가치 P/E 배수 |
| `rsi_period` | 14 | RSI 계산 기간 |
| `rsi_max_buy` | 65 | 매수 허용 최대 RSI (과열 방지) |
| `ma_fast` | 20 | 단기 이동평균 기간 (일) |
| `ma_slow` | 60 | 장기 이동평균 기간 (일) |
| `macd_fast` | 12 | MACD 빠른 EMA |
| `macd_slow` | 26 | MACD 느린 EMA |
| `macd_signal` | 9 | MACD 시그널 EMA |
| `stop_pct` | 0.07 | **손절 비율** (0.05 = 5%, 0.10 = 10%) |
| `target_pct` | 0.15 | **목표수익 비율** (0.15 = 15%, 0.20 = 20%) |
| `min_hold_bars` | 20 | 최소 보유 거래일 (~1개월) |
| `max_position_pct` | 0.10 | 최대 포지션 비율 (0.10 = 자본의 10%) |

---

## 데이터 요구사항

### OHLCV (일봉)
- 타임프레임: `1d`
- MA(60) 계산을 위해 최소 **60거래일** 이상 데이터 필요

### Fundamentals (`context['fundamentals']` 자동 주입)
```json
{
  "2023-12-31": {
    "revenue": 258940000000000,
    "operating_profit": 6566670000000,
    "net_income": 15487480000000,
    "total_assets": 455905200000000,
    "total_equity": 360980700000000,
    "total_debt": 94924500000000,
    "operating_cf": 44800420000000,
    "eps": 2131.0,
    "bps": 48218.0
  }
}
```

---

## 주의사항

- **최소 데이터**: MA(60) 계산을 위해 백테스트 시작일 기준 60거래일 이전 데이터 필요
- **재무 데이터 없는 경우**: 재무 필터 비활성화, 기술 지표만으로 매매
- **저평가 기준**: EPS/BPS 데이터가 없으면 내재가치 계산 불가 → 저평가 필터 자동 생략
- **수수료**: 1개월 이상 보유이므로 수수료 영향 적음 (commission_rate 0.015% 권장)

---

## 참고 문헌

1. Piotroski, J.D. (2000). Value Investing. *Journal of Accounting Research*, 38, 1–41.
2. Graham, B. & Dodd, D. (1934). *Security Analysis*. McGraw-Hill.
3. Jegadeesh, N. & Titman, S. (1993). Returns to Buying Winners. *Journal of Finance*, 48(1), 65–91.
4. Asness, C., Moskowitz, T., Pedersen, L. (2013). Value and Momentum Everywhere. *Journal of Finance*, 68(3), 929–985.
5. Appel, G. (1979). *The Moving Average Convergence-Divergence Method*. Signalert.
6. Wilder, J.W. (1978). *New Concepts in Technical Trading Systems*. Trend Research.
7. 이상한 (2018). 한국 주식시장에서의 Piotroski F-Score 유효성 연구. 한국증권학회지.
