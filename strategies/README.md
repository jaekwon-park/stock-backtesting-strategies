# 전략 목록

백테스팅 플랫폼에서 사용할 수 있는 전략 모음입니다.

## 전략 디렉터리 구조

```
strategies/
├── moving_average/    # 이동평균 교차 전략
│   ├── strategy.py
│   └── README.md
├── rsi/               # RSI 과매수/과매도 전략
│   ├── strategy.py
│   └── README.md
├── bollinger_band/    # 볼린저 밴드 변동성 전략
│   ├── strategy.py
│   └── README.md
└── breakout/          # 레인지 돌파 전략
    ├── strategy.py
    └── README.md
```

## 전략 목록

| 전략 | 유형 | 설명 | 적합 시장 |
|------|------|------|----------|
| [이동평균 교차](./moving_average/README.md) | 트렌드 추종 | 단기/장기 MA 교차 신호 | 추세장 |
| [RSI](./rsi/README.md) | 역추세 | 과매수/과매도 기반 | 횡보장 |
| [볼린저 밴드](./bollinger_band/README.md) | 역추세/변동성 | 밴드 이탈 기반 | 횡보장 |
| [돌파](./breakout/README.md) | 모멘텀 | N봉 레인지 돌파 | 변동성 높은 추세장 |

## 전략 파일 규격

각 전략 파일은 다음 두 함수를 **반드시** 포함해야 합니다:

```python
def initialize(context):
    """
    백테스트 시작 시 1회 호출.
    context['key'] = value 형태로 초기 파라미터 저장.
    """
    context['my_param'] = 10

def on_bar(context, bar):
    """
    매 캔들(5분봉)마다 호출.

    bar 구조:
    {
        'time': str,    # ISO 8601 시각
        'symbol': str,  # 종목 코드
        'open': float,
        'high': float,
        'low': float,
        'close': float,
        'volume': int
    }

    Returns: list[dict] — 주문 목록
    주문 형식: {'side': 'BUY'|'SELL', 'quantity': int, 'order_type': 'MARKET'}
    """
    return []
```

## 새 전략 기여하기

1. `strategies/<strategy_name>/` 디렉터리 생성
2. `strategy.py` 작성 (위 규격 준수)
3. `README.md` 작성 (파라미터 표, 로직 설명 포함)
4. PR 생성 — 자동 검증 스크립트가 실행됩니다
