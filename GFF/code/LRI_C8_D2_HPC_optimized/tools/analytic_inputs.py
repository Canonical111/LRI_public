#!/usr/bin/env python3
"""Regenerate the exact-function inputs required for C8(2).

The seven two-loop Taylor coefficients are obtained by polynomial arithmetic
on convergent hypergeometric series, then independently checked by two Cauchy
contours. No high-loop samples or fitted physical coefficients enter.

Requires mpmath >= 1.3. Usage:
  python tools/analytic_inputs.py --reference /path/to/C7/inputs
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import mpmath as mp


ROOT = Path(__file__).resolve().parents[1]
ORDER = 8
JET_ORDER = ORDER - 2


def mul_linear(p, a, b):
    return [a * p[j] + (b * p[j - 1] if j else 0) for j in range(len(p))]


def div_linear(p, a, b):
    q = []
    for j, x in enumerate(p):
        q.append((x - (b * q[j - 1] if j else 0)) / a)
    return q


def mul(p, q):
    return [mp.fsum(p[k] * q[j - k] for k in range(j + 1)) for j in range(len(p))]


def exponential(log_coefficients):
    """Taylor coefficients of exp(sum_{j>=1} ell_j z^j), ell_0=0."""
    p = [mp.mpf(1)]
    for n in range(1, len(log_coefficients)):
        p.append(mp.fsum(j * log_coefficients[j] * p[n - j] for j in range(1, n + 1)) / n)
    return p


def numerator(z):
    """N(z)=z^2 S2(z), with N(0)=2 and b2(z)=-6*(N(z)-2)/z."""
    a = mp.mpf(1) / 2 + z / 4
    b = mp.mpf(1) / 2 + 3 * z / 4
    f1 = mp.hyper([1, z / 2, a], [1 - z / 2, a + mp.mpf(1) / 2], mp.mpf(1) / 4)
    f2 = mp.hyper([z, 2 * a, b], [1 + z / 2, b + mp.mpf(1) / 2], mp.mpf(1) / 4)
    w = mp.gamma(1 + z) * mp.gamma(1 - z / 2) * mp.gamma(b) ** 2
    w /= mp.gamma(a) ** 2 * mp.gamma(2 * b)
    return 4 * f1 - 2 * w * f2


def two_loop_series(max_power=JET_ORDER):
    """Differentiate the defining convergent series by finite polynomial algebra.

    F2 has an exactly cancelling upper/lower parameter 1+z/2, and is
    independently summed as a 2F1. All polynomial arrays include z^(max_power+1).
    """
    size = max_power + 2
    t1 = [mp.mpf(1)] + [mp.mpf(0)] * (size - 1)
    t2 = t1.copy()
    f1, f2 = t1.copy(), t2.copy()
    threshold = mp.power(10, -mp.mp.dps + 8)
    for n in range(1, 10000):
        t1 = mul_linear(t1, mp.mpf(n - 1), mp.mpf(1) / 2)
        t1 = mul_linear(t1, mp.mpf(n) - mp.mpf(1) / 2, mp.mpf(1) / 4)
        t1 = div_linear(t1, mp.mpf(n), -mp.mpf(1) / 2)
        t1 = div_linear(t1, mp.mpf(n), mp.mpf(1) / 4)
        t1 = [x / 4 for x in t1]

        t2 = mul_linear(t2, mp.mpf(n - 1), mp.mpf(1))
        t2 = mul_linear(t2, mp.mpf(n) - mp.mpf(1) / 2, mp.mpf(3) / 4)
        t2 = div_linear(t2, mp.mpf(n), mp.mpf(3) / 4)
        t2 = [x / (4 * n) for x in t2]
        f1 = [x + y for x, y in zip(f1, t1)]
        f2 = [x + y for x, y in zip(f2, t2)]
        if max(map(abs, t1 + t2)) < threshold:
            break
    else:
        raise ArithmeticError("Hypergeometric coefficient series did not converge")

    logs = [mp.mpf(0)]
    for k in range(1, size):
        a = 1 + (-mp.mpf(1) / 2) ** k - (mp.mpf(3) / 2) ** k
        b = 2 * ((mp.mpf(3) / 4) ** k - (mp.mpf(1) / 4) ** k)
        logs.append((a * mp.polygamma(k - 1, 1) + b * mp.polygamma(k - 1, mp.mpf(1) / 2)) / mp.factorial(k))
    wf2 = mul(exponential(logs), f2)
    coeffs = [-6 * (4 * f1[j] - 2 * wf2[j]) for j in range(1, size)]
    return coeffs, n


def two_loop_cauchy(radius, nodes, max_power=JET_ORDER):
    if nodes % 2:
        raise ValueError("Even node count required")
    r = mp.mpf(radius)
    angles = [2 * mp.pi * (j + mp.mpf(1) / 2) / nodes for j in range(nodes // 2)]
    values = [numerator(r * mp.exp(1j * theta)) for theta in angles]
    # Reflection supplies the other half of the contour; the -6 is from b2.
    return [-12 * mp.fsum(mp.re(v * mp.exp(-1j * k * theta)) for v, theta in zip(values, angles)) / (nodes * r ** k)
            for k in range(1, max_power + 2)]


def gamma_logs(loop, max_power=JET_ORDER):
    """log(pi^L Gamma(1+Lz/2)/Gamma(1/2+z/4)^(2L))."""
    ans = [mp.mpf(0), loop * mp.log(2)]
    for k in range(2, max_power + 1):
        ans.append((-1) ** k * mp.zeta(k) / k * ((mp.mpf(loop) / 2) ** k - 2 * loop * (mp.mpf(2) ** k - 1) / mp.mpf(4) ** k))
    return ans


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def generate(root=ROOT, reference=None, dps=120, digits=100):
    if dps < digits + 15 or digits < 65:
        raise ValueError("Require at least 65 stored digits and 15 guard digits")
    root = Path(root)
    (root / "inputs").mkdir(parents=True, exist_ok=True)
    with mp.workdps(dps):
        b2, terms = two_loop_series()
        contours = []
        for radius, nodes in (("0.05", 128), ("0.08", 160)):
            values = two_loop_cauchy(radius, nodes)
            contours.append({"radius": radius, "nodes": nodes, "B2": [mp.nstr(v, digits) for v in values],
                             "maximum_difference_from_series": mp.nstr(max(abs(x - y) for x, y in zip(b2, values)), 20)})
        max_difference = max(mp.mpf(x["maximum_difference_from_series"]) for x in contours)
        tolerance = mp.power(10, -digits)
        if max_difference >= tolerance:
            raise ArithmeticError(f"Cauchy/series disagreement {max_difference} >= {tolerance}")
        # This also checks the normalization and first coefficient independently.
        exact_b20_error = abs(b2[0] + 24 * mp.log(2))
        if exact_b20_error >= tolerance:
            raise ArithmeticError("b2,0 differs from -24 log(2)")

        reference_check = None
        if reference is not None:
            reference = Path(reference)
            old_path = reference / "two_loop.json"
            old = json.loads(old_path.read_text())["B2"]
            if len(old) != 6:
                raise ValueError("Expected the six C7 two-loop coefficients")
            double_equal = all(float(x) == float(y) for x, y in zip(b2, old))
            difference = max(abs(x - mp.mpf(y)) for x, y in zip(b2, old))
            if not double_equal or difference > mp.mpf("1e-60"):
                raise ArithmeticError("Previously retained two-loop coefficients changed")
            reference_check = {"input_sha256": digest(old_path), "coefficients_checked": 6,
                               "binary64_identical": double_equal,
                               "maximum_absolute_difference": mp.nstr(difference, 25),
                               "legacy_coefficients": old}

        gamma_rows = []
        max_gamma_check = mp.mpf(0)
        for loop in range(2, ORDER + 1):
            logs = gamma_logs(loop)
            for k in range(1, JET_ORDER + 1):
                independent = ((mp.mpf(loop) / 2) ** k * mp.polygamma(k - 1, 1) - 2 * loop * (mp.mpf(1) / 4) ** k * mp.polygamma(k - 1, mp.mpf(1) / 2)) / mp.factorial(k)
                max_gamma_check = max(max_gamma_check, abs(logs[k] - independent))
            norm = 2 * (-1) ** (loop + 1) / mp.pi ** loop
            gamma_rows.append(" ".join([str(ORDER - loop), mp.nstr(norm, digits)] + [mp.nstr(x, digits) for x in logs]))
        if max_gamma_check >= tolerance:
            raise ArithmeticError("Gamma coefficient formulas disagree")
        if reference is not None:
            old_gamma_path = reference / "gamma_d2_7.txt"
            old_rows = [line.split() for line in old_gamma_path.read_text().splitlines() if line.strip()]
            if len(old_rows) != 6:
                raise ValueError("Expected the six C7 Gamma-normalization rows")
            old_gamma_equal = True
            for new_line, old_row in zip(gamma_rows, old_rows):
                new_row = new_line.split()
                if len(old_row) != 8 or int(new_row[0]) != int(old_row[0]) + 1:
                    raise ValueError("Unexpected C7 Gamma row format")
                old_gamma_equal &= all(mp.nstr(mp.mpf(x), 65) == mp.nstr(mp.mpf(y), 65)
                                       for x, y in zip(new_row[1:], old_row[1:]))
            if not old_gamma_equal:
                raise ArithmeticError("Previously retained Gamma coefficients changed at 65 digits")
            reference_check["gamma_input_sha256"] = digest(old_gamma_path)
            reference_check["gamma_42_values_identical_at_65_digits"] = True

        two_loop = {"B2": [mp.nstr(x, digits) for x in b2],
                    "dimension": 2, "physical_order": ORDER, "maximum_regulator_power": JET_ORDER,
                    "scheme": "finite zero-momentum, r(2,z)=1, c2(z)=b2(z)/6",
                    "method": "convergent hypergeometric Taylor series, verified on two Cauchy contours",
                    "working_decimal_digits": dps, "stored_significant_digits": digits}
        write_json(root / "inputs" / "two_loop.json", two_loop)
        (root / "inputs" / "gamma_d2_8.txt").write_text("\n".join(gamma_rows) + "\n")
        report = {"status": "passed", "dimension": 2, "physical_order": ORDER,
                  "working_decimal_digits": dps, "stored_significant_digits": digits,
                  "series_terms": terms, "series_method": "finite Taylor arithmetic on 3F2 and independently simplified 2F1 series at 1/4",
                  "contours": contours, "maximum_contour_series_difference": mp.nstr(max_difference, 25),
                  "b20_plus_24log2": mp.nstr(exact_b20_error, 25),
                  "normalization_formula_difference": mp.nstr(max_gamma_check, 25),
                  "C7_reference": reference_check,
                  "new_b2_z6": mp.nstr(b2[6], digits),
                  "outputs_sha256": {name: digest(root / "inputs" / name) for name in ("two_loop.json", "gamma_d2_8.txt")}}
        write_json(root / "verification" / "analytic_inputs.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--reference", type=Path, help="C7 inputs directory, for preservation checks")
    parser.add_argument("--dps", type=int, default=120)
    parser.add_argument("--digits", type=int, default=100)
    args = parser.parse_args()
    report = generate(args.root, args.reference, args.dps, args.digits)
    print(json.dumps({key: report[key] for key in ("status", "new_b2_z6", "maximum_contour_series_difference", "series_terms")}))


if __name__ == "__main__":
    main()
