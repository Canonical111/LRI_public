#!/usr/bin/env python3
"""Verify the D3 period certificate using Python's standard library only.

No numerical constants, modular arithmetic, fitted values, or third-party
packages are used.  Each source relation is regenerated from its mathematical
label, then every coefficient of the resulting word vector is checked over Q.

The complete rational target and certificate are embedded below as plain JSON.
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


def verify(root: Path | None = None) -> dict:
    target = read_vector(EMBEDDED["target"] if root is None else json.loads((root / "D3_linear_words.json").read_text()))
    if set(map(len, target)) != {2, 3, 4}:
        raise AssertionError("Unexpected target weights")
    report = {"arithmetic": "exact rational (fractions.Fraction)", "weights": []}
    total = 0
    for n in (2, 3, 4):
        data = EMBEDDED["certificates"][str(n)] if root is None else json.loads((root / f"confluence_certificate_w{n}.json").read_text())
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
    parser.add_argument("--directory", type=Path, default=None)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = verify(args.directory)
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n")


EMBEDDED = json.loads(r'''
{
  "target": [
    [
      [
        1,
        1
      ],
      "67/4"
    ],
    [
      [
        1,
        1,
        2
      ],
      "24"
    ],
    [
      [
        1,
        1,
        3
      ],
      "14"
    ],
    [
      [
        1,
        2,
        1
      ],
      "24"
    ],
    [
      [
        1,
        2,
        2
      ],
      "-4"
    ],
    [
      [
        1,
        2,
        2,
        2
      ],
      "8"
    ],
    [
      [
        1,
        2,
        3
      ],
      "2"
    ],
    [
      [
        1,
        3
      ],
      "-55/4"
    ],
    [
      [
        1,
        3,
        1
      ],
      "14"
    ],
    [
      [
        1,
        3,
        2
      ],
      "2"
    ],
    [
      [
        1,
        3,
        3
      ],
      "-38"
    ],
    [
      [
        1,
        4
      ],
      "-17"
    ],
    [
      [
        2,
        1
      ],
      "-24"
    ],
    [
      [
        2,
        1,
        1
      ],
      "346/9"
    ],
    [
      [
        2,
        1,
        1,
        1
      ],
      "244/7"
    ],
    [
      [
        2,
        1,
        1,
        2
      ],
      "28/3"
    ],
    [
      [
        2,
        1,
        2
      ],
      "138"
    ],
    [
      [
        2,
        1,
        2,
        1
      ],
      "28/3"
    ],
    [
      [
        2,
        1,
        2,
        2
      ],
      "4"
    ],
    [
      [
        2,
        1,
        3
      ],
      "-30"
    ],
    [
      [
        2,
        1,
        4
      ],
      "-35"
    ],
    [
      [
        2,
        2
      ],
      "-20"
    ],
    [
      [
        2,
        2,
        1
      ],
      "192"
    ],
    [
      [
        2,
        2,
        1,
        1
      ],
      "224/3"
    ],
    [
      [
        2,
        2,
        1,
        2
      ],
      "8"
    ],
    [
      [
        2,
        2,
        2,
        1
      ],
      "120"
    ],
    [
      [
        2,
        2,
        3,
        1
      ],
      "8"
    ],
    [
      [
        2,
        2,
        3,
        2
      ],
      "8"
    ],
    [
      [
        2,
        3
      ],
      "-22"
    ],
    [
      [
        2,
        3,
        1
      ],
      "-68"
    ],
    [
      [
        2,
        3,
        1,
        2
      ],
      "4"
    ],
    [
      [
        2,
        3,
        2
      ],
      "-26"
    ],
    [
      [
        2,
        3,
        2,
        1
      ],
      "-68"
    ],
    [
      [
        2,
        3,
        2,
        2
      ],
      "4"
    ],
    [
      [
        2,
        3,
        3,
        1
      ],
      "16"
    ],
    [
      [
        2,
        3,
        3,
        2
      ],
      "-4"
    ],
    [
      [
        2,
        4,
        1
      ],
      "-17"
    ],
    [
      [
        2,
        4,
        3
      ],
      "18"
    ],
    [
      [
        2,
        5,
        3,
        1
      ],
      "-20"
    ],
    [
      [
        2,
        5,
        3,
        3
      ],
      "20"
    ],
    [
      [
        2,
        5,
        6,
        3
      ],
      "-20"
    ],
    [
      [
        3,
        1
      ],
      "37/4"
    ],
    [
      [
        3,
        1,
        1
      ],
      "14"
    ],
    [
      [
        3,
        1,
        3
      ],
      "-38"
    ],
    [
      [
        3,
        1,
        4
      ],
      "-2"
    ],
    [
      [
        3,
        2
      ],
      "1"
    ],
    [
      [
        3,
        2,
        1
      ],
      "98"
    ],
    [
      [
        3,
        2,
        1,
        1
      ],
      "-4"
    ],
    [
      [
        3,
        2,
        1,
        2
      ],
      "-62"
    ],
    [
      [
        3,
        2,
        1,
        3
      ],
      "10"
    ],
    [
      [
        3,
        2,
        1,
        4
      ],
      "20"
    ],
    [
      [
        3,
        2,
        2
      ],
      "-8"
    ],
    [
      [
        3,
        2,
        2,
        1
      ],
      "-152"
    ],
    [
      [
        3,
        2,
        3
      ],
      "1"
    ],
    [
      [
        3,
        2,
        3,
        1
      ],
      "50"
    ],
    [
      [
        3,
        2,
        3,
        2
      ],
      "10"
    ],
    [
      [
        3,
        2,
        4,
        1
      ],
      "10"
    ],
    [
      [
        3,
        2,
        4,
        3
      ],
      "-10"
    ],
    [
      [
        3,
        3,
        1
      ],
      "-76"
    ],
    [
      [
        3,
        3,
        1,
        1
      ],
      "4"
    ],
    [
      [
        3,
        3,
        1,
        2
      ],
      "12"
    ],
    [
      [
        3,
        3,
        1,
        4
      ],
      "-4"
    ],
    [
      [
        3,
        3,
        2
      ],
      "17"
    ],
    [
      [
        3,
        3,
        2,
        1
      ],
      "76"
    ],
    [
      [
        3,
        3,
        2,
        3
      ],
      "-2"
    ],
    [
      [
        3,
        3,
        3
      ],
      "-23"
    ],
    [
      [
        3,
        3,
        3,
        1
      ],
      "-18"
    ],
    [
      [
        3,
        3,
        3,
        2
      ],
      "-6"
    ],
    [
      [
        3,
        3,
        4
      ],
      "7"
    ],
    [
      [
        3,
        3,
        4,
        1
      ],
      "-4"
    ],
    [
      [
        3,
        3,
        5,
        2
      ],
      "2"
    ],
    [
      [
        3,
        3,
        5,
        3
      ],
      "2"
    ],
    [
      [
        3,
        4
      ],
      "12"
    ],
    [
      [
        3,
        4,
        1
      ],
      "-8"
    ],
    [
      [
        3,
        4,
        2,
        1
      ],
      "18"
    ],
    [
      [
        3,
        4,
        2,
        3
      ],
      "2"
    ],
    [
      [
        3,
        4,
        3
      ],
      "1"
    ],
    [
      [
        3,
        4,
        3,
        2
      ],
      "14"
    ],
    [
      [
        3,
        4,
        5,
        2
      ],
      "-2"
    ],
    [
      [
        3,
        4,
        5,
        3
      ],
      "-2"
    ],
    [
      [
        3,
        5,
        2
      ],
      "6"
    ],
    [
      [
        3,
        5,
        3
      ],
      "6"
    ],
    [
      [
        3,
        5,
        3,
        1
      ],
      "8"
    ],
    [
      [
        3,
        5,
        3,
        3
      ],
      "-8"
    ],
    [
      [
        3,
        5,
        6,
        3
      ],
      "8"
    ],
    [
      [
        4,
        1
      ],
      "-26"
    ],
    [
      [
        4,
        2,
        1
      ],
      "-14"
    ],
    [
      [
        4,
        3
      ],
      "3"
    ],
    [
      [
        4,
        3,
        1
      ],
      "-7"
    ],
    [
      [
        4,
        3,
        2
      ],
      "-26"
    ],
    [
      [
        4,
        3,
        2,
        1
      ],
      "-64"
    ],
    [
      [
        4,
        3,
        2,
        3
      ],
      "4"
    ],
    [
      [
        4,
        3,
        3
      ],
      "-6"
    ],
    [
      [
        4,
        3,
        3,
        1
      ],
      "16"
    ],
    [
      [
        4,
        3,
        3,
        2
      ],
      "8"
    ],
    [
      [
        4,
        3,
        5,
        2
      ],
      "-4"
    ],
    [
      [
        4,
        3,
        5,
        3
      ],
      "-4"
    ],
    [
      [
        4,
        4
      ],
      "5"
    ],
    [
      [
        4,
        4,
        1
      ],
      "-8"
    ],
    [
      [
        4,
        4,
        2,
        1
      ],
      "8"
    ],
    [
      [
        4,
        4,
        3
      ],
      "-8"
    ],
    [
      [
        4,
        4,
        3,
        1
      ],
      "4"
    ],
    [
      [
        4,
        5,
        3,
        1
      ],
      "-12"
    ],
    [
      [
        4,
        5,
        3,
        2
      ],
      "-4"
    ],
    [
      [
        4,
        5,
        3,
        3
      ],
      "4"
    ],
    [
      [
        4,
        5,
        6,
        3
      ],
      "-4"
    ],
    [
      [
        4,
        6,
        3
      ],
      "-2"
    ],
    [
      [
        5,
        2
      ],
      "-2"
    ],
    [
      [
        5,
        2,
        3,
        1
      ],
      "-20"
    ],
    [
      [
        5,
        2,
        3,
        3
      ],
      "20"
    ],
    [
      [
        5,
        2,
        6,
        3
      ],
      "-20"
    ],
    [
      [
        5,
        3
      ],
      "-2"
    ],
    [
      [
        5,
        3,
        1
      ],
      "42"
    ],
    [
      [
        5,
        3,
        1,
        1
      ],
      "-4"
    ],
    [
      [
        5,
        3,
        1,
        2
      ],
      "-12"
    ],
    [
      [
        5,
        3,
        1,
        4
      ],
      "4"
    ],
    [
      [
        5,
        3,
        2
      ],
      "4"
    ],
    [
      [
        5,
        3,
        2,
        1
      ],
      "-26"
    ],
    [
      [
        5,
        3,
        2,
        3
      ],
      "18"
    ],
    [
      [
        5,
        3,
        3
      ],
      "-34"
    ],
    [
      [
        5,
        3,
        3,
        1
      ],
      "18"
    ],
    [
      [
        5,
        3,
        3,
        2
      ],
      "14"
    ],
    [
      [
        5,
        3,
        3,
        3
      ],
      "-12"
    ],
    [
      [
        5,
        3,
        3,
        4
      ],
      "-4"
    ],
    [
      [
        5,
        3,
        4,
        1
      ],
      "8"
    ],
    [
      [
        5,
        3,
        5,
        2
      ],
      "-2"
    ],
    [
      [
        5,
        3,
        5,
        3
      ],
      "-2"
    ],
    [
      [
        5,
        3,
        6,
        3
      ],
      "8"
    ],
    [
      [
        5,
        4,
        2,
        1
      ],
      "-6"
    ],
    [
      [
        5,
        4,
        2,
        3
      ],
      "-2"
    ],
    [
      [
        5,
        4,
        3,
        1
      ],
      "6"
    ],
    [
      [
        5,
        4,
        3,
        2
      ],
      "2"
    ],
    [
      [
        5,
        4,
        5,
        2
      ],
      "2"
    ],
    [
      [
        5,
        4,
        5,
        3
      ],
      "2"
    ],
    [
      [
        5,
        5,
        3,
        1
      ],
      "-8"
    ],
    [
      [
        5,
        5,
        3,
        3
      ],
      "8"
    ],
    [
      [
        5,
        5,
        6,
        3
      ],
      "-8"
    ],
    [
      [
        5,
        6,
        2,
        3
      ],
      "-20"
    ],
    [
      [
        5,
        6,
        3
      ],
      "34"
    ],
    [
      [
        5,
        6,
        3,
        1
      ],
      "-4"
    ],
    [
      [
        5,
        6,
        3,
        2
      ],
      "-16"
    ],
    [
      [
        5,
        6,
        3,
        3
      ],
      "12"
    ],
    [
      [
        5,
        6,
        3,
        4
      ],
      "4"
    ],
    [
      [
        5,
        6,
        4,
        1
      ],
      "-4"
    ],
    [
      [
        5,
        6,
        5,
        2
      ],
      "4"
    ],
    [
      [
        5,
        6,
        5,
        3
      ],
      "4"
    ],
    [
      [
        5,
        6,
        6,
        3
      ],
      "-8"
    ],
    [
      [
        6,
        3,
        1
      ],
      "6"
    ],
    [
      [
        6,
        3,
        2
      ],
      "-7"
    ],
    [
      [
        6,
        3,
        3
      ],
      "9"
    ],
    [
      [
        6,
        3,
        4
      ],
      "-7"
    ],
    [
      [
        6,
        4,
        1
      ],
      "6"
    ],
    [
      [
        6,
        4,
        2,
        1
      ],
      "-8"
    ],
    [
      [
        6,
        4,
        3
      ],
      "-1"
    ],
    [
      [
        6,
        4,
        3,
        1
      ],
      "-4"
    ],
    [
      [
        6,
        4,
        3,
        3
      ],
      "4"
    ],
    [
      [
        6,
        4,
        4,
        1
      ],
      "4"
    ],
    [
      [
        6,
        4,
        4,
        3
      ],
      "4"
    ],
    [
      [
        6,
        5,
        2
      ],
      "-7"
    ],
    [
      [
        6,
        5,
        3
      ],
      "-7"
    ],
    [
      [
        6,
        5,
        3,
        1
      ],
      "-4"
    ],
    [
      [
        6,
        5,
        3,
        3
      ],
      "4"
    ],
    [
      [
        6,
        5,
        6,
        3
      ],
      "-4"
    ],
    [
      [
        6,
        6,
        3
      ],
      "14"
    ],
    [
      [
        6,
        7,
        4,
        1
      ],
      "-4"
    ],
    [
      [
        6,
        7,
        4,
        3
      ],
      "-4"
    ],
    [
      [
        6,
        7,
        6,
        3
      ],
      "-4"
    ],
    [
      [
        7,
        4,
        1
      ],
      "8"
    ],
    [
      [
        7,
        4,
        3
      ],
      "8"
    ],
    [
      [
        7,
        6,
        3
      ],
      "8"
    ]
  ],
  "certificates": {
    "2": {
      "weight": 2,
      "status": "exact rational identity verified",
      "period_convention": "R_w = constant as T -> infinity of G(-w;T)",
      "certificate": [
        {
          "coefficient": "67/8",
          "relation": {
            "kind": "R1zero",
            "times": [
              1
            ]
          }
        },
        {
          "coefficient": "23",
          "relation": {
            "kind": "R1zero",
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-91/4",
          "relation": {
            "kind": "R1zero",
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-17",
          "relation": {
            "kind": "R1zero",
            "times": [
              4
            ]
          }
        },
        {
          "coefficient": "5",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "5/2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              4
            ]
          }
        },
        {
          "coefficient": "23",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-9",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": []
          }
        }
      ],
      "source_count": 59,
      "rank_mod_prime": 30,
      "discovery_prime": "2305843009213693951",
      "target": [
        [
          [
            1,
            1
          ],
          "67/4"
        ],
        [
          [
            1,
            3
          ],
          "-55/4"
        ],
        [
          [
            1,
            4
          ],
          "-17"
        ],
        [
          [
            2,
            1
          ],
          "-24"
        ],
        [
          [
            2,
            2
          ],
          "-20"
        ],
        [
          [
            2,
            3
          ],
          "-22"
        ],
        [
          [
            3,
            1
          ],
          "37/4"
        ],
        [
          [
            3,
            2
          ],
          "1"
        ],
        [
          [
            3,
            4
          ],
          "12"
        ],
        [
          [
            4,
            1
          ],
          "-26"
        ],
        [
          [
            4,
            3
          ],
          "3"
        ],
        [
          [
            4,
            4
          ],
          "5"
        ],
        [
          [
            5,
            2
          ],
          "-2"
        ],
        [
          [
            5,
            3
          ],
          "-2"
        ]
      ]
    },
    "3": {
      "weight": 3,
      "status": "exact rational identity verified",
      "period_convention": "R_w = constant as T -> infinity of G(-w;T)",
      "certificate": [
        {
          "coefficient": "62",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              1
            ]
          }
        },
        {
          "coefficient": "-109/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-33/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-95",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1
            ]
          }
        },
        {
          "coefficient": "180",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-13",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-35",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4
            ]
          }
        },
        {
          "coefficient": "115/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1
            ]
          }
        },
        {
          "coefficient": "239/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-50",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4
            ]
          }
        },
        {
          "coefficient": "47/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              1
            ]
          }
        },
        {
          "coefficient": "-87",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2
            ]
          }
        },
        {
          "coefficient": "35/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3
            ]
          }
        },
        {
          "coefficient": "21",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2
            ]
          }
        },
        {
          "coefficient": "21",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              7,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              7,
              4
            ]
          }
        },
        {
          "coefficient": "35",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "7",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-7",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              6,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-14",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              4
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "62",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-148/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "26",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-47/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-21",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "18",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "7",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-18",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-23",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-5/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "7/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-17",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-7",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              4,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "scaling",
            "d": 3,
            "word": [
              1,
              1,
              2
            ],
            "times": []
          }
        }
      ],
      "source_count": 634,
      "rank_mod_prime": 254,
      "discovery_prime": "2305843009213693951",
      "target": [
        [
          [
            1,
            1,
            2
          ],
          "24"
        ],
        [
          [
            1,
            1,
            3
          ],
          "14"
        ],
        [
          [
            1,
            2,
            1
          ],
          "24"
        ],
        [
          [
            1,
            2,
            2
          ],
          "-4"
        ],
        [
          [
            1,
            2,
            3
          ],
          "2"
        ],
        [
          [
            1,
            3,
            1
          ],
          "14"
        ],
        [
          [
            1,
            3,
            2
          ],
          "2"
        ],
        [
          [
            1,
            3,
            3
          ],
          "-38"
        ],
        [
          [
            2,
            1,
            1
          ],
          "346/9"
        ],
        [
          [
            2,
            1,
            2
          ],
          "138"
        ],
        [
          [
            2,
            1,
            3
          ],
          "-30"
        ],
        [
          [
            2,
            1,
            4
          ],
          "-35"
        ],
        [
          [
            2,
            2,
            1
          ],
          "192"
        ],
        [
          [
            2,
            3,
            1
          ],
          "-68"
        ],
        [
          [
            2,
            3,
            2
          ],
          "-26"
        ],
        [
          [
            2,
            4,
            1
          ],
          "-17"
        ],
        [
          [
            2,
            4,
            3
          ],
          "18"
        ],
        [
          [
            3,
            1,
            1
          ],
          "14"
        ],
        [
          [
            3,
            1,
            3
          ],
          "-38"
        ],
        [
          [
            3,
            1,
            4
          ],
          "-2"
        ],
        [
          [
            3,
            2,
            1
          ],
          "98"
        ],
        [
          [
            3,
            2,
            2
          ],
          "-8"
        ],
        [
          [
            3,
            2,
            3
          ],
          "1"
        ],
        [
          [
            3,
            3,
            1
          ],
          "-76"
        ],
        [
          [
            3,
            3,
            2
          ],
          "17"
        ],
        [
          [
            3,
            3,
            3
          ],
          "-23"
        ],
        [
          [
            3,
            3,
            4
          ],
          "7"
        ],
        [
          [
            3,
            4,
            1
          ],
          "-8"
        ],
        [
          [
            3,
            4,
            3
          ],
          "1"
        ],
        [
          [
            3,
            5,
            2
          ],
          "6"
        ],
        [
          [
            3,
            5,
            3
          ],
          "6"
        ],
        [
          [
            4,
            2,
            1
          ],
          "-14"
        ],
        [
          [
            4,
            3,
            1
          ],
          "-7"
        ],
        [
          [
            4,
            3,
            2
          ],
          "-26"
        ],
        [
          [
            4,
            3,
            3
          ],
          "-6"
        ],
        [
          [
            4,
            4,
            1
          ],
          "-8"
        ],
        [
          [
            4,
            4,
            3
          ],
          "-8"
        ],
        [
          [
            4,
            6,
            3
          ],
          "-2"
        ],
        [
          [
            5,
            3,
            1
          ],
          "42"
        ],
        [
          [
            5,
            3,
            2
          ],
          "4"
        ],
        [
          [
            5,
            3,
            3
          ],
          "-34"
        ],
        [
          [
            5,
            6,
            3
          ],
          "34"
        ],
        [
          [
            6,
            3,
            1
          ],
          "6"
        ],
        [
          [
            6,
            3,
            2
          ],
          "-7"
        ],
        [
          [
            6,
            3,
            3
          ],
          "9"
        ],
        [
          [
            6,
            3,
            4
          ],
          "-7"
        ],
        [
          [
            6,
            4,
            1
          ],
          "6"
        ],
        [
          [
            6,
            4,
            3
          ],
          "-1"
        ],
        [
          [
            6,
            5,
            2
          ],
          "-7"
        ],
        [
          [
            6,
            5,
            3
          ],
          "-7"
        ],
        [
          [
            6,
            6,
            3
          ],
          "14"
        ],
        [
          [
            7,
            4,
            1
          ],
          "8"
        ],
        [
          [
            7,
            4,
            3
          ],
          "8"
        ],
        [
          [
            7,
            6,
            3
          ],
          "8"
        ]
      ]
    },
    "4": {
      "weight": 4,
      "status": "exact rational identity verified",
      "period_convention": "R_w = constant as T -> infinity of G(-w;T)",
      "certificate": [
        {
          "coefficient": "56",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              1,
              1
            ]
          }
        },
        {
          "coefficient": "33",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "22/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-21",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "-48",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "431/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-5/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "-25/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-17/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "86",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-20",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "-35/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "44/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              5,
              1
            ]
          }
        },
        {
          "coefficient": "-34/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "5",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              5,
              4
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              1,
              6,
              4
            ]
          }
        },
        {
          "coefficient": "-164/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1,
              1
            ]
          }
        },
        {
          "coefficient": "43/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "337/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "57",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-25",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              1,
              5
            ]
          }
        },
        {
          "coefficient": "104",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "148",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-220",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-158/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "86",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              2,
              6
            ]
          }
        },
        {
          "coefficient": "40",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "-591/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "88",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "250/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "-19",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "-88/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              3,
              6
            ]
          }
        },
        {
          "coefficient": "-83/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "30",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "-34/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "-28/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              4
            ]
          }
        },
        {
          "coefficient": "-61/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              5
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              4,
              6
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              5,
              1
            ]
          }
        },
        {
          "coefficient": "245/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-94/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              5,
              4
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              2,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "-89/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1,
              1
            ]
          }
        },
        {
          "coefficient": "250/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-26/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-18",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "25/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              1,
              5
            ]
          }
        },
        {
          "coefficient": "187/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "-346",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "623/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "78",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "-32/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-88/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              2,
              6
            ]
          }
        },
        {
          "coefficient": "76/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "400/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-96",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-26",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "32",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              3,
              6
            ]
          }
        },
        {
          "coefficient": "-15/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "373/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "-35/2",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              4
            ]
          }
        },
        {
          "coefficient": "25/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              5
            ]
          }
        },
        {
          "coefficient": "-16/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              4,
              6
            ]
          }
        },
        {
          "coefficient": "3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              5,
              1
            ]
          }
        },
        {
          "coefficient": "-44/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "3",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              5,
              4
            ]
          }
        },
        {
          "coefficient": "-38",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "32",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "-14",
          "relation": {
            "kind": "R1zero",
            "times": [
              3,
              6,
              4
            ]
          }
        },
        {
          "coefficient": "-46/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              1,
              1
            ]
          }
        },
        {
          "coefficient": "-72",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "37/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-22/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "314/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "-25",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              2,
              6
            ]
          }
        },
        {
          "coefficient": "-161/6",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "-34",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "25/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "-16/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              3,
              6
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "-16",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              5,
              1
            ]
          }
        },
        {
          "coefficient": "-94/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "6",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              5,
              4
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              4,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              1,
              1
            ]
          }
        },
        {
          "coefficient": "41/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-11",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "244/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-106/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-5",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "-71/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "29/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "-17/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "43/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "-5/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "R1zero",
            "times": [
              5,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              2,
              1
            ]
          }
        },
        {
          "coefficient": "-10",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              3,
              1
            ]
          }
        },
        {
          "coefficient": "-14",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "32",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-12",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              4,
              1
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              4,
              2
            ]
          }
        },
        {
          "coefficient": "-12",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              7,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "R1zero",
            "times": [
              6,
              7,
              4
            ]
          }
        },
        {
          "coefficient": "56",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-142/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-8/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              2,
              6
            ]
          }
        },
        {
          "coefficient": "-202/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "38",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "-25/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              3,
              6
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-37/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "-8/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              1,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "28",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-28/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              1,
              5
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              2,
              5,
              4
            ]
          }
        },
        {
          "coefficient": "-58",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "21",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "56/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-9",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "6",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              2,
              6
            ]
          }
        },
        {
          "coefficient": "-26",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "24",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              3,
              6
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "6",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              6,
              2
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              3,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              4,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              4,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              4,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "50/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-37/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              2,
              4
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              2,
              5
            ]
          }
        },
        {
          "coefficient": "6",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              3,
              5
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              5,
              2
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              5,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              5,
              6,
              3
            ]
          }
        },
        {
          "coefficient": "-8/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              6,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              6,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              6,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 2,
            "times": [
              6,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-16",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "20",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "20",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-24",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              1,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              2,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              2,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              2,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "-16",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              2,
              3,
              3
            ]
          }
        },
        {
          "coefficient": "16",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-12",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              1,
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              2,
              3
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              3,
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              3,
              4
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "logproduct",
            "a": 2,
            "b": 3,
            "times": [
              3,
              4,
              3
            ]
          }
        },
        {
          "coefficient": "-35/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "31/6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "17",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-25/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              1,
              5
            ]
          }
        },
        {
          "coefficient": "92/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-32",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              2,
              4
            ]
          }
        },
        {
          "coefficient": "50/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              2,
              5
            ]
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              2,
              6
            ]
          }
        },
        {
          "coefficient": "-75/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              3,
              2
            ]
          }
        },
        {
          "coefficient": "20",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "17",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              3,
              4
            ]
          }
        },
        {
          "coefficient": "-12",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              3,
              6
            ]
          }
        },
        {
          "coefficient": "-25/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              4,
              5
            ]
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              4,
              6
            ]
          }
        },
        {
          "coefficient": "13",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-11/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              2
            ],
            "times": [
              5,
              3
            ]
          }
        },
        {
          "coefficient": "165/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-16",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              1,
              4
            ]
          }
        },
        {
          "coefficient": "-22",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "-10",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              3,
              4
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              3
            ],
            "times": [
              3,
              6
            ]
          }
        },
        {
          "coefficient": "-22/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "10",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              2,
              4
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              5,
              2
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              4
            ],
            "times": [
              5,
              3
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              5
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              5
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              1,
              5
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-52/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-2/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              1,
              5
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              2,
              5
            ]
          }
        },
        {
          "coefficient": "7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              4,
              5
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              2
            ],
            "times": [
              5,
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-1",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              1,
              5
            ]
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "5/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              2,
              5
            ]
          }
        },
        {
          "coefficient": "-7/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              4,
              5
            ]
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              3
            ],
            "times": [
              5,
              3
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              4
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              4
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              4
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              2,
              4
            ],
            "times": [
              3,
              3
            ]
          }
        },
        {
          "coefficient": "-10",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              1,
              2
            ]
          }
        },
        {
          "coefficient": "6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              1,
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              2,
              2
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              1
            ],
            "a": [
              3,
              3
            ],
            "times": [
              2,
              3
            ]
          }
        },
        {
          "coefficient": "30",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-25/6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-5",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-28",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "10/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "10/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-12",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-10/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "59/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-16/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "2/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "56/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-5/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-2/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              4,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              5,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              2,
              5,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-25/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "20/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              3
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              4
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "25/6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              3
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              4
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              1,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              1,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              1,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              1,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-56/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              2,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "5",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              2,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              4,
              3,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              5,
              2,
              1
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              5,
              2,
              1
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              5,
              3,
              2
            ],
            "times": [
              2
            ]
          }
        },
        {
          "coefficient": "14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1
            ],
            "a": [
              5,
              3,
              2
            ],
            "times": [
              3
            ]
          }
        },
        {
          "coefficient": "56",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-46/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "46/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              1,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "9",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              1,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "44/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-103/6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "34/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              2,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "1",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-3/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "12",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-29/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              3,
              5,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-5",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              1,
              4,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-116/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-32/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              1,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "97/6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-34/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "58/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "26/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "10/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              1,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-98/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "70/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "56/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              2,
              5,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "9",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-7/2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              3,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              4,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              4,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              4,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "28/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              4,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              5,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              2,
              5,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-56/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "5/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              1,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "8/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              1,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              2,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "40/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-6",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              2,
              5,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              1,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              2,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "-8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              4,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "8",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              3,
              4,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-4",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              4,
              1,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-5",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              4,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              4,
              3,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              4,
              3,
              3
            ],
            "times": []
          }
        },
        {
          "coefficient": "2",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              5,
              2,
              1
            ],
            "times": []
          }
        },
        {
          "coefficient": "-14/3",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              0,
              1
            ],
            "a": [
              3,
              5,
              3,
              2
            ],
            "times": []
          }
        },
        {
          "coefficient": "-10",
          "relation": {
            "kind": "confluence",
            "bits": [
              0,
              0,
              1,
              1
            ],
            "a": [
              1,
              1,
              1,
              2
            ],
            "times": []
          }
        }
      ],
      "source_count": 6023,
      "rank_mod_prime": 1974,
      "discovery_prime": "2305843009213693951",
      "target": [
        [
          [
            1,
            2,
            2,
            2
          ],
          "8"
        ],
        [
          [
            2,
            1,
            1,
            1
          ],
          "244/7"
        ],
        [
          [
            2,
            1,
            1,
            2
          ],
          "28/3"
        ],
        [
          [
            2,
            1,
            2,
            1
          ],
          "28/3"
        ],
        [
          [
            2,
            1,
            2,
            2
          ],
          "4"
        ],
        [
          [
            2,
            2,
            1,
            1
          ],
          "224/3"
        ],
        [
          [
            2,
            2,
            1,
            2
          ],
          "8"
        ],
        [
          [
            2,
            2,
            2,
            1
          ],
          "120"
        ],
        [
          [
            2,
            2,
            3,
            1
          ],
          "8"
        ],
        [
          [
            2,
            2,
            3,
            2
          ],
          "8"
        ],
        [
          [
            2,
            3,
            1,
            2
          ],
          "4"
        ],
        [
          [
            2,
            3,
            2,
            1
          ],
          "-68"
        ],
        [
          [
            2,
            3,
            2,
            2
          ],
          "4"
        ],
        [
          [
            2,
            3,
            3,
            1
          ],
          "16"
        ],
        [
          [
            2,
            3,
            3,
            2
          ],
          "-4"
        ],
        [
          [
            2,
            5,
            3,
            1
          ],
          "-20"
        ],
        [
          [
            2,
            5,
            3,
            3
          ],
          "20"
        ],
        [
          [
            2,
            5,
            6,
            3
          ],
          "-20"
        ],
        [
          [
            3,
            2,
            1,
            1
          ],
          "-4"
        ],
        [
          [
            3,
            2,
            1,
            2
          ],
          "-62"
        ],
        [
          [
            3,
            2,
            1,
            3
          ],
          "10"
        ],
        [
          [
            3,
            2,
            1,
            4
          ],
          "20"
        ],
        [
          [
            3,
            2,
            2,
            1
          ],
          "-152"
        ],
        [
          [
            3,
            2,
            3,
            1
          ],
          "50"
        ],
        [
          [
            3,
            2,
            3,
            2
          ],
          "10"
        ],
        [
          [
            3,
            2,
            4,
            1
          ],
          "10"
        ],
        [
          [
            3,
            2,
            4,
            3
          ],
          "-10"
        ],
        [
          [
            3,
            3,
            1,
            1
          ],
          "4"
        ],
        [
          [
            3,
            3,
            1,
            2
          ],
          "12"
        ],
        [
          [
            3,
            3,
            1,
            4
          ],
          "-4"
        ],
        [
          [
            3,
            3,
            2,
            1
          ],
          "76"
        ],
        [
          [
            3,
            3,
            2,
            3
          ],
          "-2"
        ],
        [
          [
            3,
            3,
            3,
            1
          ],
          "-18"
        ],
        [
          [
            3,
            3,
            3,
            2
          ],
          "-6"
        ],
        [
          [
            3,
            3,
            4,
            1
          ],
          "-4"
        ],
        [
          [
            3,
            3,
            5,
            2
          ],
          "2"
        ],
        [
          [
            3,
            3,
            5,
            3
          ],
          "2"
        ],
        [
          [
            3,
            4,
            2,
            1
          ],
          "18"
        ],
        [
          [
            3,
            4,
            2,
            3
          ],
          "2"
        ],
        [
          [
            3,
            4,
            3,
            2
          ],
          "14"
        ],
        [
          [
            3,
            4,
            5,
            2
          ],
          "-2"
        ],
        [
          [
            3,
            4,
            5,
            3
          ],
          "-2"
        ],
        [
          [
            3,
            5,
            3,
            1
          ],
          "8"
        ],
        [
          [
            3,
            5,
            3,
            3
          ],
          "-8"
        ],
        [
          [
            3,
            5,
            6,
            3
          ],
          "8"
        ],
        [
          [
            4,
            3,
            2,
            1
          ],
          "-64"
        ],
        [
          [
            4,
            3,
            2,
            3
          ],
          "4"
        ],
        [
          [
            4,
            3,
            3,
            1
          ],
          "16"
        ],
        [
          [
            4,
            3,
            3,
            2
          ],
          "8"
        ],
        [
          [
            4,
            3,
            5,
            2
          ],
          "-4"
        ],
        [
          [
            4,
            3,
            5,
            3
          ],
          "-4"
        ],
        [
          [
            4,
            4,
            2,
            1
          ],
          "8"
        ],
        [
          [
            4,
            4,
            3,
            1
          ],
          "4"
        ],
        [
          [
            4,
            5,
            3,
            1
          ],
          "-12"
        ],
        [
          [
            4,
            5,
            3,
            2
          ],
          "-4"
        ],
        [
          [
            4,
            5,
            3,
            3
          ],
          "4"
        ],
        [
          [
            4,
            5,
            6,
            3
          ],
          "-4"
        ],
        [
          [
            5,
            2,
            3,
            1
          ],
          "-20"
        ],
        [
          [
            5,
            2,
            3,
            3
          ],
          "20"
        ],
        [
          [
            5,
            2,
            6,
            3
          ],
          "-20"
        ],
        [
          [
            5,
            3,
            1,
            1
          ],
          "-4"
        ],
        [
          [
            5,
            3,
            1,
            2
          ],
          "-12"
        ],
        [
          [
            5,
            3,
            1,
            4
          ],
          "4"
        ],
        [
          [
            5,
            3,
            2,
            1
          ],
          "-26"
        ],
        [
          [
            5,
            3,
            2,
            3
          ],
          "18"
        ],
        [
          [
            5,
            3,
            3,
            1
          ],
          "18"
        ],
        [
          [
            5,
            3,
            3,
            2
          ],
          "14"
        ],
        [
          [
            5,
            3,
            3,
            3
          ],
          "-12"
        ],
        [
          [
            5,
            3,
            3,
            4
          ],
          "-4"
        ],
        [
          [
            5,
            3,
            4,
            1
          ],
          "8"
        ],
        [
          [
            5,
            3,
            5,
            2
          ],
          "-2"
        ],
        [
          [
            5,
            3,
            5,
            3
          ],
          "-2"
        ],
        [
          [
            5,
            3,
            6,
            3
          ],
          "8"
        ],
        [
          [
            5,
            4,
            2,
            1
          ],
          "-6"
        ],
        [
          [
            5,
            4,
            2,
            3
          ],
          "-2"
        ],
        [
          [
            5,
            4,
            3,
            1
          ],
          "6"
        ],
        [
          [
            5,
            4,
            3,
            2
          ],
          "2"
        ],
        [
          [
            5,
            4,
            5,
            2
          ],
          "2"
        ],
        [
          [
            5,
            4,
            5,
            3
          ],
          "2"
        ],
        [
          [
            5,
            5,
            3,
            1
          ],
          "-8"
        ],
        [
          [
            5,
            5,
            3,
            3
          ],
          "8"
        ],
        [
          [
            5,
            5,
            6,
            3
          ],
          "-8"
        ],
        [
          [
            5,
            6,
            2,
            3
          ],
          "-20"
        ],
        [
          [
            5,
            6,
            3,
            1
          ],
          "-4"
        ],
        [
          [
            5,
            6,
            3,
            2
          ],
          "-16"
        ],
        [
          [
            5,
            6,
            3,
            3
          ],
          "12"
        ],
        [
          [
            5,
            6,
            3,
            4
          ],
          "4"
        ],
        [
          [
            5,
            6,
            4,
            1
          ],
          "-4"
        ],
        [
          [
            5,
            6,
            5,
            2
          ],
          "4"
        ],
        [
          [
            5,
            6,
            5,
            3
          ],
          "4"
        ],
        [
          [
            5,
            6,
            6,
            3
          ],
          "-8"
        ],
        [
          [
            6,
            4,
            2,
            1
          ],
          "-8"
        ],
        [
          [
            6,
            4,
            3,
            1
          ],
          "-4"
        ],
        [
          [
            6,
            4,
            3,
            3
          ],
          "4"
        ],
        [
          [
            6,
            4,
            4,
            1
          ],
          "4"
        ],
        [
          [
            6,
            4,
            4,
            3
          ],
          "4"
        ],
        [
          [
            6,
            5,
            3,
            1
          ],
          "-4"
        ],
        [
          [
            6,
            5,
            3,
            3
          ],
          "4"
        ],
        [
          [
            6,
            5,
            6,
            3
          ],
          "-4"
        ],
        [
          [
            6,
            7,
            4,
            1
          ],
          "-4"
        ],
        [
          [
            6,
            7,
            4,
            3
          ],
          "-4"
        ],
        [
          [
            6,
            7,
            6,
            3
          ],
          "-4"
        ]
      ]
    }
  }
}
''')

if __name__ == "__main__":
    main()
