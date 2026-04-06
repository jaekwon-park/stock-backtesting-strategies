#!/usr/bin/env python3
"""
전략 파일 검증 스크립트.
CI/CD 파이프라인에서 PR 생성 시 자동 실행됩니다.

사용법:
    python scripts/validate_strategy.py
    python scripts/validate_strategy.py strategies/moving_average/strategy.py
"""

import ast
import re
import sys
from pathlib import Path

STRATEGIES_ROOT = Path(__file__).parent.parent / "strategies"
REQUIRED_FUNCTIONS = ("def initialize", "def on_bar")

# 금지 모듈 / 코드 패턴
FORBIDDEN_PATTERNS = [
    "import os",
    "import sys",
    "import subprocess",
    "import socket",
    "__import__",
    "eval(",
    "exec(",
]

# 허용된 import (플랫폼이 주입하는 모듈)
ALLOWED_IMPORTS = {"math", "json"}


def check_restricted_python(code: str, filepath: str) -> list[str]:
    """RestrictedPython 제약 사항 위반 검사."""
    errors = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []  # 문법 오류는 다른 검사에서 처리

    for node in ast.walk(tree):

        # 1. 밑줄로 시작하는 함수/변수 정의 금지 (_func, _var)
        #    단 __dunder__ 와 일반 dunder 도 금지
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                errors.append(
                    f"Line {node.lineno}: 밑줄로 시작하는 함수명 금지 → `{node.name}` "
                    f"(RestrictedPython이 private 접근으로 간주해 차단)"
                )

        # 2. import 문 금지 (허용 모듈 제외)
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod not in ALLOWED_IMPORTS:
                    errors.append(
                        f"Line {node.lineno}: import 금지 → `import {alias.name}` "
                        f"(허용 모듈: {', '.join(sorted(ALLOWED_IMPORTS))})"
                    )

        if isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod not in ALLOWED_IMPORTS:
                errors.append(
                    f"Line {node.lineno}: import 금지 → `from {node.module} import ...` "
                    f"(허용 모듈: {', '.join(sorted(ALLOWED_IMPORTS))})"
                )

        # 3. subscript augmented assignment 금지
        #    dict['key'] += value 형태
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Subscript):
            op_name = type(node.op).__name__
            op_symbol = {
                "Add": "+=", "Sub": "-=", "Mult": "*=", "Div": "/=",
                "FloorDiv": "//=", "Mod": "%=", "Pow": "**=",
            }.get(op_name, f"{op_name}=")
            errors.append(
                f"Line {node.lineno}: subscript augmented assignment 금지 → `[...] {op_symbol}` "
                f"(대신 `x = x {op_symbol[:-1]} val` 형태 사용)"
            )

        # 4. __dunder__ 속성 직접 접근 금지
        if isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                errors.append(
                    f"Line {node.lineno}: dunder 속성 접근 금지 → `.{node.attr}` "
                    f"(safer_getattr에 의해 차단됨)"
                )

        # 5. open() 호출 금지
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open":
                errors.append(
                    f"Line {node.lineno}: `open()` 금지 (파일 접근 차단)"
                )

    return errors


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

    # 4. 금지 패턴 (문자열 기반)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code:
            errors.append(f"금지된 코드 사용: `{pattern}`")

    # 5. RestrictedPython 제약 사항 (AST 기반)
    errors.extend(check_restricted_python(code, str(strategy_file)))

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
        rel_path = (
            target.relative_to(STRATEGIES_ROOT.parent)
            if target.is_relative_to(STRATEGIES_ROOT.parent)
            else target
        )

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
