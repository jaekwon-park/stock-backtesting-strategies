# 📈 Stock Backtesting Strategies

주식 백테스팅 플랫폼에서 사용할 수 있는 **매매 전략 저장소**입니다.

## 디렉터리 구조

```
stock-backtesting-strategies/
├── strategies/                    # 전략 파일 모음
│   ├── moving_average/            # 이동평균 교차
│   ├── rsi/                       # RSI 과매수/과매도
│   ├── bollinger_band/            # 볼린저 밴드
│   ├── breakout/                  # 레인지 돌파
│   ├── panic_reversal/            # 급락 반등
│   ├── pin_bar_reversal/          # 핀바 반전 매수
│   └── ...
├── scripts/
│   └── validate_strategy.py       # 검증 스크립트
└── README.md
```

## 전략 목록

| 전략 | 유형 | 타임프레임 | 파일 |
|------|------|-----------|------|
| 이동평균 교차 | 트렌드 추종 | 일봉 | [moving_average](strategies/moving_average/strategy.py) |
| RSI | 역추세 | 일봉 | [rsi](strategies/rsi/strategy.py) |
| 볼린저 밴드 | 역추세/변동성 | 일봉 | [bollinger_band](strategies/bollinger_band/strategy.py) |
| 레인지 돌파 | 모멘텀 | 일봉 | [breakout](strategies/breakout/strategy.py) |
| 급락 반등 | 역추세 | 일봉 | [panic_reversal](strategies/panic_reversal/strategy.py) |
| **핀바 반전 매수** | **역추세** | **일봉** | [**pin_bar_reversal**](strategies/pin_bar_reversal/strategy.py) |

## 플랫폼 연동

이 레포지토리의 전략은 **백테스팅 플랫폼**에서 직접 불러올 수 있습니다.

1. 플랫폼 접속 → 전략 에디터 → **"GitHub에서 불러오기"**
2. 전략 선택 → 백테스트 설정 후 실행

## 새 전략 추가하기

```bash
# 1. 레포 클론
git clone https://github.com/jaekwon-park/stock-backtesting-strategies.git
cd stock-backtesting-strategies

# 2. 새 전략 디렉터리 생성
mkdir strategies/my_strategy

# 3. 전략 파일 작성 (아래 규격 참고)
vim strategies/my_strategy/strategy.py

# 4. 로컬 검증
python scripts/validate_strategy.py strategies/my_strategy/strategy.py

# 5. PR 생성
git add -A && git commit -m "feat: add my_strategy"
git push origin main
```

---

## 전략 파일 규격

### 기본 구조

```python
def initialize(ctx):
    ctx['timeframe'] = '1d'   # 기본 타임프레임 설정
    ctx['param'] = value       # 파라미터 초기화

def on_bar(ctx, bar):
    # bar: 현재 봉 데이터 (아래 상세 참조)
    # ctx: 전략 상태 + 계좌 정보
    return [{'side': 'BUY', 'symbol': '005930', 'qty': 10}]
```

### `bar` 필드

**기본 필드 (항상 제공):**

| 필드 | 타입 | 설명 |
|------|------|------|
| `bar['time']` | str | 봉 시각 (`"2024-01-15 09:00:00"`) |
| `bar['symbol']` | str | 종목코드 (`"A005930"`) |
| `bar['open']` | float | 시가 |
| `bar['high']` | float | 고가 |
| `bar['low']` | float | 저가 |
| `bar['close']` | float | 종가 |
| `bar['volume']` | int | 거래량 |

**멀티 타임프레임 (유니버스 백테스트, `extra_data_sources` 지정 시):**

```python
# 추가 분봉 캔들 — bar['5m'], bar['15m'], bar['30m'] 등
if bar.get('5m'):
    m5 = bar['5m']   # {'time', 'open', 'high', 'low', 'close', 'volume', 'symbol'}
```

**기술지표 (`extra_data_sources: ["technical"]`):**

```python
if bar.get('technical'):
    ti = bar['technical']
    ma20      = float(ti.get('ma20') or 0)
    rsi14     = float(ti.get('rsi14') or 0)
    macd      = float(ti.get('macd') or 0)
    bb_upper  = float(ti.get('bb_upper') or 0)
    bb_lower  = float(ti.get('bb_lower') or 0)
    atr14     = float(ti.get('atr14') or 0)
    obv       = float(ti.get('obv') or 0)
    # 전체 필드: ma5, ma10, ma20, ma60, ma120, ma200, rsi14, macd, macd_signal,
    #            bb_upper, bb_lower, bb_width, atr14, adx14, obv, stoch_k, stoch_d, volume_ratio
```

**투자자 동향 (`extra_data_sources: ["investor"]`):**

```python
if bar.get('investor'):
    inv = bar['investor']
    foreign_net = float(inv.get('foreign_net') or 0)   # 외국인 순매수
    inst_net    = float(inv.get('inst_net') or 0)       # 기관 순매수
    indiv_net   = float(inv.get('indiv_net') or 0)      # 개인 순매수
```

**공매도 (`extra_data_sources: ["shorting"]`):**

```python
if bar.get('shorting'):
    sh = bar['shorting']
    short_ratio = float(sh.get('short_ratio') or 0)    # 공매도 비율 (%)
    short_volume = float(sh.get('short_volume') or 0)  # 공매도 수량
```

**분기 재무 (`extra_data_sources: ["quarterly"]`):**

```python
if bar.get('quarterly'):
    q = bar['quarterly']    # 가장 최근 분기 데이터 (look-ahead bias 방지)
    revenue = float(q.get('revenue') or 0)
    net_income = float(q.get('net_income') or 0)
    operating_income = float(q.get('operating_income') or 0)
```

**재무지표 (`extra_data_sources: ["fundamentals"]`):**

```python
if bar.get('fundamentals'):
    f = bar['fundamentals']
    per    = float(f.get('per') or 0)
    pbr    = float(f.get('pbr') or 0)
    roe    = float(f.get('roe') or 0)
    market_cap = float(f.get('market_cap') or 0)
```

**GICS 섹터 (`extra_data_sources: ["sector"]`):**

```python
sector = ctx.get('sector', {}).get('gics_sector', '')   # context에서 접근
```

### `ctx` (context) 필드

| 필드 | 설명 |
|------|------|
| `ctx['cash']` | 현재 가용 현금 |
| `ctx.get('positions', {})` | 보유 포지션 `{symbol: position}` |

---

## ⚠️ 전략 코드 작성 시 반드시 지켜야 할 규칙

전략 코드는 **RestrictedPython** 샌드박스 환경에서 실행됩니다.

### 🚫 사용 금지

| 항목 | 이유 | 대안 |
|------|------|------|
| `_`로 시작하는 이름 | RestrictedPython이 private 접근으로 간주해 차단 | `calc_rsi`, `sma` 등 밑줄 없는 이름 사용 |
| `import` 문 | 모듈 임포트 불가 | `math`, `json`은 이미 주입되어 있음 |
| `open()` | 파일 접근 차단 | 사용 불가 |
| `exec()` / `eval()` | 동적 코드 실행 차단 | 사용 불가 |
| `os`, `sys`, `subprocess` 등 시스템 모듈 | 주입되지 않음 | 사용 불가 |
| `__dunder__` 속성 접근 | `safer_getattr`에 의해 차단 | 직접 속성 접근 불가 |

### ✅ 사용 가능한 기능

**내장 함수:**
`abs`, `bool`, `callable`, `chr`, `divmod`, `float`, `frozenset`, `hash`, `hex`, `int`,
`isinstance`, `issubclass`, `iter`, `len`, `list`, `min`, `max`, `next`, `oct`, `ord`,
`pow`, `range`, `repr`, `reversed`, `round`, `slice`, `sorted`, `str`, `sum`, `tuple`,
`zip`, `enumerate`, `map`, `filter`, `any`, `all`, `print`, `getattr`, `hasattr`,
`type`, `dict`, `set`, `object`

**모듈:** `math`, `json`

**문법:**
- 일반 함수 정의 (`def my_func():`)
- 클래스 정의
- 리스트 컴프리헨션 (`[x for x in items]`)
- 제너레이터 표현식 (`sum(x for x in items)`)
- 튜플 언패킹 (`a, b = func()`)
- 증감 연산 (`x += 1`, `x -= 1`, `x *= 2`, `x //= 2`)
- 딕셔너리 항목 접근 및 수정 (`ctx['key'] = value`)

### 📝 주문 형식

```python
# 매수
return [{'side': 'BUY', 'symbol': symbol, 'qty': qty}]

# 매도 (전량 청산)
return [{'side': 'SELL', 'symbol': symbol, 'qty': 9999999}]

# 복수 주문
return [
    {'side': 'BUY', 'symbol': 'A005930', 'qty': 10},
    {'side': 'BUY', 'symbol': 'A000660', 'qty': 5},
]
```

### 📝 예시 — 멀티 데이터소스 전략

```python
def initialize(ctx):
    ctx['timeframe'] = '1d'
    ctx['closes'] = []

def on_bar(ctx, bar):
    ctx['closes'].append(bar['close'])
    if len(ctx['closes']) < 20:
        return []

    symbol = bar['symbol']

    # 기술지표 활용
    if bar.get('technical'):
        rsi = float(bar['technical'].get('rsi14') or 50)
        if rsi > 70:
            return [{'side': 'SELL', 'symbol': symbol, 'qty': 9999999}]

    # 투자자 동향 활용
    if bar.get('investor'):
        foreign_net = float(bar['investor'].get('foreign_net') or 0)
        inst_net    = float(bar['investor'].get('inst_net') or 0)
        if foreign_net > 0 and inst_net > 0:
            qty = int(ctx['cash'] * 0.1 / bar['close'])
            if qty > 0:
                return [{'side': 'BUY', 'symbol': symbol, 'qty': qty}]

    return []
```
