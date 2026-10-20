#!/usr/bin/env python3
"""The Python environment check (G0's venv check; first step of `make test-python`, so J-VAL-1 and J-EXP-1 stop at once,
naming the package, when a requirement is missing): every package of requirements.txt is importable, and its version
is reported next to the requirement's minimum.

F2 (Stage 5): tests/vendored_isolated.py runs the vendored assembly tests with pytest, which requirements.txt did not
list and the symmetry venv did not hold; requirements.txt now lists pytest, and this check imports it.
A missing package always fails. A version below the minimum is reported, and fails only with --strict, the G0 form on a
compute node (`python3 -B tests/check_venv.py --strict`): the Mac suite runs on an older interpreter stack.
Usage: python3 -B tests/check_venv.py [--strict] [--output FILE]"""
from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def requirements(path: Path = ROOT / 'requirements.txt') -> list[tuple[str, str | None]]:
    """(name, minimum or None) for every line 'name' or 'name>=x.y' of requirements.txt; anything else is refused."""
    out = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        line = line.split('#', 1)[0].strip()
        if not line:
            continue
        m = re.fullmatch(r'([A-Za-z0-9_.\-]+)\s*(?:>=\s*([0-9][0-9A-Za-z.]*))?', line)
        if not m:
            raise SystemExit(f'{path}:{n}: unsupported requirement {line!r} (name or name>=version)')
        out.append((m.group(1), m.group(2)))
    return out


def version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', v)[:3])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--strict', action='store_true', help='a version below its minimum fails (G0 on a compute node)')
    ap.add_argument('--output', type=Path)
    a = ap.parse_args()
    rows, missing, old = [], [], []
    for name, minimum in requirements():
        try:
            mod = importlib.import_module(name)
            v = str(getattr(mod, '__version__', 'unknown'))
        except ImportError as e:
            rows.append(dict(package=name, minimum=minimum, version=None, error=str(e)))
            missing.append(name)
            continue
        below = minimum is not None and v != 'unknown' and version_tuple(v) < version_tuple(minimum)
        rows.append(dict(package=name, minimum=minimum, version=v, below_minimum=below))
        if below:
            old.append(f'{name} {v} < {minimum}')
    ok = not missing and not (a.strict and old)
    rec = dict(schema='c8-d2-venv-check-1', python=sys.version.split()[0], executable=sys.executable, strict=a.strict,
               packages=rows, missing=missing, below_minimum=old, passed=ok)
    if a.output:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_text(json.dumps(rec, indent=1) + '\n')
    for r in rows:
        print(f"{r['package']:8s} {r['version'] or 'MISSING':12s} (requirement {'>=' + r['minimum'] if r['minimum'] else 'any'})"
              + (' BELOW MINIMUM' if r.get('below_minimum') else ''))
    if missing:
        print(f'check_venv: missing {", ".join(missing)} in {sys.executable}; install requirements.txt '
              f'(python3 -m pip install -r requirements.txt)', file=sys.stderr)
    if old:
        print(('check_venv: ' if a.strict else 'check_venv (warning): ') + '; '.join(old), file=sys.stderr)
    print(f'check_venv: {"passed" if ok else "FAILED"}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
