# Fundamental Momentum Strategy (재무-모멘텀 복합 전략)

## 전략 개요

재무제표 건전성 점수(Piotroski F-Score)와 기술적 지표(RSI + 이동평균)를 결합하여
**양질의 종목을 선별하고, 최적 매매 타이밍을 포착**하는 복합 전략입니다.

## 학술적 근거

| 논문 | 핵심 내용 |
|------|-----------|
| Piotroski (2000) "Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers" | 9개 재무지표로 F-Score 산출. 고득점 종목의 연평균 초과수익 7.5% 입증 |
| Asness, Moskowitz & Pedersen (2013) "Value and Momentum Everywhere" | 가치 지표와 모멘텀 결합 시 각각 단독 사용 대비 샤프 비율 현저히 향상 |
| 이상한 (2018) "한국 주식시장에서 Piotroski F-Score 전략의 유효성" | KOSPI 적용 결과 F-Score ≥ 6 포트폴리오가 벤치마크 대비 초과수익 유의적 |

## Piotroski F-Score 구성 (9점 만점)

### 수익성 (Profitability, 4점)
| 항목 | 조건 | 점수 |
|------|------|------|
| F1 | ROA > 0 | 1 |
| F2 | 영업현금흐름 > 0 | 1 |
| F3 | ROA 전년 대비 증가 | 1 |
| F4 | 발생주의 품질 (CFO/Assets > ROA) | 1 |

### 레버리지/유동성 (Leverage, 2점)
| 항목 | 조건 | 점수 |
|------|------|------|
| F5 | 부채비율 감소 | 1 |
| F6 | 자기자본비율 개선 | 1 |

### 효율성 (Operating Efficiency, 3점)
| 항목 | 조건 | 점수 |
|------|------|------|
| F7 | 영업이익률 개선 | 1 |
| F8 | 자산회전율 개선 | 1 |
| F9 | EPS 개선 | 1 |

## 매매 규칙

### 매수 조건 (AND)
1. **F-Score ≥ 5** — 재무 건전성 기준 통과
2. **RSI(14) < 40** — 단기 과매도 (저평가 진입 타이밍)
3. **종가 > MA(20)** — 상승 추세 확인

### 매도 조건 (OR)
1. **RSI(14) > 70** — 단기 과매수 (차익실현)
2. **손절: 진입가 대비 -8%** — 리스크 관리
3. **F-Score 기준 미충족 + 종가 < MA(20)** — 재무 악화 + 추세 이탈

## 파라미터

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `rsi_period` | 14 | RSI 계산 기간 |
| `rsi_buy` | 40 | 매수 기준 RSI |
| `rsi_sell` | 70 | 매도 기준 RSI |
| `ma_period` | 20 | 이동평균 기간 |
| `stop_loss` | 0.08 | 손절 비율 (8%) |
| `min_fscore` | 5 | 최소 F-Score |
| `use_fscore` | True | False 시 순수 기술 전략 |

## context['fundamentals'] 데이터 구조

백테스트 워커가 전략 실행 시 자동으로 주입합니다.

```python
context['fundamentals'] = {
    "2022-12-31": {
        "revenue":          302231360000000,
        "operating_profit":  43376630000000,
        "net_income":        55654077000000,
        "total_assets":     448424507000000,
        "total_equity":     354749604000000,
        "total_debt":        93674903000000,
        "operating_cf":      62181346000000,
        "eps":               8057.0
    },
    "2023-12-31": { ... }
}
```

## 백테스트 권장 설정

- **종목**: 삼성전자 (005930), SK하이닉스 (000660), POSCO홀딩스 (005490)
- **기간**: 2022-01-01 ~ 현재 (최소 2개 연도 재무 데이터 필요)
- **타임프레임**: 1d
- **초기자본**: 10,000,000원
- **수수료**: 0.015%
- **세금**: 0.2%

## 주의사항

- F-Score 계산을 위해 최소 **2개 연도**의 재무제표 데이터가 DB에 있어야 합니다.
- `use_fscore = False` 설정 시 F-Score 조건 없이 순수 RSI + MA 전략으로 동작합니다.
- 재무 데이터가 없는 경우 F-Score 필터를 자동으로 무시하고 기술 신호만 사용합니다.
