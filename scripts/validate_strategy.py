#!/usr/bin/env python3
"""
전략 파일 검증 스크립트.
CI/CD 파이프라인에서 PR 생성 시 자동 실행됩니다.

사용법:
    python scripts/validate_strategy.py
    python scripts/validate_strategy.py strategies/moving_average/strategy.py
"""

import sys
from pathlib import Path

STRATEGIES_ROOT = Path(__file__).parent.parent / "strategies"
REQUIRED_FUNCTIONS = ("def initialize", "def on_bar")


def validate_file(strategy_file: Path) -> list[str]:
    """전략 파일 검증. 오류 목록 반환."""
    errors = []
    try:
        code = strategy_file.read_text(encoding="utf-8")
    except Exception as e:
        return [f"파일 읽기 실패: {e}"]

    # 1. 문법 검사
    try:
        compile(code, str(strategy_file), "exec")
    except SyntaxError as e:
        errors.append(f"문법 오류: {e}")

    # 2. 필수 함수 존재 여부
    for fn in REQUIRED_FUNCTIONS:
        if fn not in code:
            errors.append(f"필수 함수 누락: {fn}()")

    # 3. README 존재 여부
    readme = strategy_file.parent / "README.md"
    if not readme.exists():
        errors.append("README.md 파일이 없습니다")

    # 4. 금지 모듈 사용 여부
    forbidden = ["import os", "import sys", "import subprocess", "import socket",
                 "open(", "__import__", "eval(", "exec("]
    for f in forbidden:
        if f in code:
            errors.append(f"금지된 코드 사용: {f}")

    return errors


def main():
    # 대상 파일 결정
    if len(sys.argv) > 1:
        targets = [Path(p) for p in sys.argv[1:]]
    else:
        targets = list(STRATEGIES_ROOT.rglob("strategy.py"))

    if not targets:
        print("검증할 전략 파일이 없습니다.")
        sys.exit(0)

    total = 0
    failed = 0

    for target in targets:
        total += 1
        errors = validate_file(target)
        rel_path = target.relative_to(STRATEGIES_ROOT.parent) if target.is_relative_to(STRATEGIES_ROOT.parent) else target

        if errors:
            failed += 1
            print(f"[FAIL] {rel_path}")
            for err in errors:
                print(f"       ❌ {err}")
        else:
            print(f"[PASS] {rel_path}")

    print(f"\n결과: {total - failed}/{total} 통과")

    if failed:
        sys.exit(1)
    else:
        print("✅ 모든 전략이 검증을 통과했습니다.")
        sys.exit(0)


if __name__ == "__main__":
    main()
