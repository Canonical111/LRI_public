#!/usr/bin/env python3
"""Verify the D3 period certificate using Python's standard library only.

No numerical constants, modular arithmetic, fitted values, or third-party
packages are used.  Each source relation is regenerated from its mathematical
label, then every coefficient of the resulting word vector is checked over Q.

This checks the period-identity layer. Run verify_integral_reduction.py to
check the separate exact map from the regulated integrals to the target vector.
"""
from __future__ import annotations
from collections import Counter
from fractions import Fraction as F
from functools import lru_cache
from pathlib import Path
import argparse
import json

Word = tuple[int, ...]
Vector = dict[Word, F]


def nonzero(v: dict) -> dict:
    return {w: c for w, c in v.items() if c}


@lru_cache(None)
def shuffle(left: Word, right: Word) -> dict[Word, int]:
    if not left:
        return {right: 1}
    if not right:
        return {left: 1}
    out: Counter = Counter()
    for tail, multiplicity in shuffle(left[1:], right).items():
        out[(left[0],) + tail] += multiplicity
    for tail, multiplicity in shuffle(left, right[1:]).items():
        out[(right[0],) + tail] += multiplicity
    return dict(out)


@lru_cache(None)
def fixed_letter_expansion(affine_word: tuple[tuple[int, int], ...]) -> dict[Word, int]:
    """Expand G(s_i*T+c_i;T) by the exact total-differential recurrence."""
    if not affine_word:
        return {(): 1}
    extended = ((1, 0),) + affine_word + ((0, 0),)
    out: Counter = Counter()
    for i, (si, ci) in enumerate(affine_word):
        smaller = fixed_letter_expansion(affine_word[:i] + affine_word[i + 1:])
        for sign, (sj, cj) in ((1, extended[i]), (-1, extended[i + 2])):
            slope, intercept = sj - si, cj - ci
            if slope == 0:
                # Constant dlog vanishes; adjacent equal-letter terms cancel.
                continue
            root = F(-intercept, slope)
            if root.denominator != 1 or root >= 0:
                raise ValueError(f"Invalid confluence pole: {root}")
            for word, coefficient in smaller.items():
                out[(-root.numerator,) + word] += sign * coefficient
    return nonzero(out)


MZV_MULTIPLIER = {
    (0, 1): F(-1),
    (0, 0, 1): F(-1), (0, 1, 1): F(1),
    (0, 0, 0, 1): F(-1), (0, 0, 1, 1): F(1, 4),
    (0, 1, 0, 1): F(3, 4), (0, 1, 1, 1): F(-1),
}
ZETA_IN_WORDS = {2: F(-2), 3: F(-4, 3), 4: F(-8, 7)}


def relation(label: dict) -> Vector:
    kind = label["kind"]
    row: Counter = Counter()
    if kind == "confluence":
        bits, intercepts = tuple(label["bits"]), tuple(label["a"])
        if bits not in MZV_MULTIPLIER or len(bits) != len(intercepts):
            raise ValueError("Invalid convergent binary word")
        if any(not isinstance(a, int) or a <= 0 for a in intercepts):
            raise ValueError("Intercepts must be positive integers")
        affine = tuple((b, a if b else -a) for b, a in zip(bits, intercepts))
        row.update({w: F(c) for w, c in fixed_letter_expansion(affine).items()})
        n = len(bits)
        row[(2,) + (1,) * (n - 1)] -= MZV_MULTIPLIER[bits] * ZETA_IN_WORDS[n]
    elif kind == "R1zero":
        row[(1,)] += F(1)
    elif kind == "logproduct":
        a, b = int(label["a"]), int(label["b"])
        if min(a, b) <= 0:
            raise ValueError("Invalid logarithm indices")
        row[(a * b,)] += F(1)
        row[(a,)] -= F(1)
        row[(b,)] -= F(1)
    elif kind == "scaling":
        d, word = int(label["d"]), tuple(label["word"])
        if d <= 0 or any(a <= 0 for a in word):
            raise ValueError("Invalid rescaling")
        row[tuple(d * a for a in word)] += F(1)
        for j in range(len(word) + 1):
            for w, c in shuffle((d,) * j, word[j:]).items():
                row[w] -= F(c)
    else:
        raise ValueError(f"Unknown relation type: {kind}")
    out: Counter = Counter()
    multiplier = tuple(label.get("times", ()))
    if any(not isinstance(a, int) or a <= 0 for a in multiplier):
        raise ValueError("Invalid shuffle-multiplier word")
    for w, c in nonzero(row).items():
        for u, m in shuffle(w, multiplier).items():
            out[u] += c * m
    return nonzero(out)


def read_vector(rows: list) -> Vector:
    out: Counter = Counter()
    for word, coefficient in rows:
        if not all(isinstance(a, int) and a > 0 for a in word):
            raise ValueError("Period indices must be positive integers")
        out[tuple(word)] += F(coefficient)
    return nonzero(out)


def verify(root: Path) -> dict:
    target = read_vector(json.loads((root / "D3_linear_words.json").read_text()))
    if set(map(len, target)) != {2, 3, 4}:
        raise AssertionError("Unexpected target weights")
    report = {"arithmetic": "exact rational (fractions.Fraction)", "weights": []}
    total = 0
    for n in (2, 3, 4):
        data = json.loads((root / f"confluence_certificate_w{n}.json").read_text())
        expected = {w: c for w, c in target.items() if len(w) == n}
        if read_vector(data["target"]) != expected:
            raise AssertionError(f"Weight-{n} certificate is for a different target")
        residual: Counter = Counter(expected)
        counts: Counter = Counter()
        for entry in data["certificate"]:
            coefficient = F(entry["coefficient"])
            row = relation(entry["relation"])
            if any(len(w) != n for w in row):
                raise AssertionError("Inhomogeneous source relation")
            for w, c in row.items():
                residual[w] -= coefficient * c
            counts[entry["relation"]["kind"]] += 1
        residual = nonzero(residual)
        if residual:
            raise AssertionError(f"Exact residual at weight {n}: {residual}")
        count = len(data["certificate"])
        total += count
        result = {"weight": n, "target_words": len(expected),
                  "certificate_relations": count, "types": dict(counts),
                  "exact_residual": 0}
        report["weights"].append(result)
        print(f"Weight {n}: {len(expected)} target words, {count} proved relations; EXACT RESIDUAL = 0")
    report["total_relations"] = total
    report["status"] = "All exact rational word identities verified"
    print(f"PASS: all {total} relations verified; no numerical period values used.")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.directory)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
