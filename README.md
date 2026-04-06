# 📈 Stock Backtesting Strategies

주식 백테스팅 플랫폼에서 사용할 수 있는 **매매 전략 저장소**입니다.

## 디렉터리 구조

```
stock-backtesting-strategies/
├── strategies/                # 전략 파일 모음
│   ├── moving_average/        # 이동평균 교차
│   │   ├── strategy.py
│   │   └── README.md
│   ├── rsi/                   # RSI 과매수/과매도
│   │   ├── strategy.py
│   │   └── README.md
│   ├── bollinger_band/        # 볼린저 밴드
│   │   ├── strategy.py
│   │   └── README.md
│   ├── breakout/              # 레인지 돌파
│   │   ├── strategy.py
│   │   └── README.md
│   └── README.md              # 전략 목록 및 규격
├── scripts/
│   └── validate_strategy.py   # 검증 스크립트
├── .github/
│   └── workflows/
│       └── validate.yml       # CI 자동 검증
└── README.md
```

## 전략 목록

| 전략 | 유형 | 파일 |
|------|------|------|
| 이동평균 교차 | 트렌드 추종 | [moving_average/strategy.py](strategies/moving_average/strategy.py) |
| RSI | 역추세 | [rsi/strategy.py](strategies/rsi/strategy.py) |
| 볼린저 밴드 | 역추세/변동성 | [bollinger_band/strategy.py](strategies/bollinger_band/strategy.py) |
| 돌파 | 모멘텀 | [breakout/strategy.py](strategies/breakout/strategy.py) |

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

# 3. 전략 파일 작성 (규격: strategies/README.md 참고)
vim strategies/my_strategy/strategy.py
vim strategies/my_strategy/README.md

# 4. 로컬 검증
python scripts/validate_strategy.py strategies/my_strategy/strategy.py

# 5. PR 생성
git add -A && git commit -m "feat: add my_strategy"
git push origin main
```

## 전략 파일 규격

```python
def initialize(context):
    context['param'] = value  # 파라미터 초기화

def on_bar(context, bar):
    # bar: {'time', 'symbol', 'open', 'high', 'low', 'close', 'volume'}
    return []  # 주문: [{'side': 'BUY'|'SELL', 'quantity': int, 'order_type': 'MARKET'}]
```

## ⚠️ 전략 코드 작성 시 반드시 지켜야 할 규칙

전략 코드는 **RestrictedPython** 샌드박스 환경에서 실행됩니다. 일반 Python과 다른 제약이 있으니 반드시 확인하세요.

### 🚫 사용 금지

| 항목 | 이유 | 대안 |
|------|------|------|
| `_`로 시작하는 이름 | RestrictedPython이 private 접근으로 간주해 차단 | `calc_rsi`, `sma` 등 밑줄 없는 이름 사용 |
| `import` 문 | 모듈 임포트 불가 | `math`, `json`은 이미 주입되어 있음 |
| `open()` | 파일 접근 차단 | 사용 불가 |
| `exec()` / `eval()` | 동적 코드 실행 차단 | 사용 불가 |
| `os`, `sys`, `subprocess` 등 시스템 모듈 | 주입되지 않음 | 사용 불가 |
| `__dunder__` 속성 접근 (`__class__`, `__dict__` 등) | `safer_getattr`에 의해 차단 | 직접 속성 접근 불가 |

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
- `for a, b in list_of_tuples:` 반복 언패킹
- 증감 연산 (`x += 1`, `x -= 1`, `x *= 2`, `x //= 2`)
- 딕셔너리 항목 접근 및 수정 (`ctx['key'] = value`)

### 📝 올바른 예시

```python
# ✅ 올바름: 밑줄 없는 함수 이름
def calc_sma(arr, n):
    if len(arr) < n:
        return None
    return sum(arr[-n:]) / n

# ✅ 올바름: math 모듈 사용
result = math.sqrt(value)

# ✅ 올바름: 리스트 컴프리헨션
gains = [d for d in deltas if d > 0]

# ❌ 잘못됨: 밑줄 시작 함수
def _calc_sma(arr, n):   # 실행 시 오류 발생!
    ...

# ❌ 잘못됨: import 문
import numpy as np       # 실행 시 오류 발생!
```
