#!/usr/bin/env python3
"""README sec. 8.2 overview: first failing order per scheme and descendant, with R_2, R_3 at the largest L and
their effective exponents.  Classification of an order: restored if p_eff(last pair) <= -0.7 (1/L decay),
constant if |p_eff| < 0.15, grows if p_eff > 0.15, slow decrease otherwise.  usage: python3 desc_overview.py"""
import glob, json, math, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")


def cls(pe):
    if pe is None:
        return "sign change"
    if pe <= -0.7:
        return "restored (1/L)"
    if abs(pe) < 0.15:
        return "constant"
    return "grows" if pe > 0 else "slow decrease"


def main():
    print("| scheme | descendant | R_2 at L_max (L R_2; p_eff) | eps^2 | R_3 at L_max (p_eff) | eps^3 | first failing order |")
    print("|---|---|---|---|---|---|---|")
    for s in ("raw", "consistent", "zeromode", "complete2", "W", "WB", "W+V", "WnoM", "WM2"):
        Ls = sorted(int(re.search(r"_L(\d+)\.json", f).group(1))
                    for f in glob.glob(os.path.join(R, f"descendant_{s}_L*.json")))
        if not Ls:
            continue
        D = {L: json.load(open(os.path.join(R, f"descendant_{s}_L{L}.json")))["descendants"] for L in Ls}
        for dn, lab in (("odd1", "chi_11"), ("odd2", "chi_22"), ("even1", "L Lbar phi^2")):
            Lh = [L for L in Ls if dn in D[L] and L >= 4]
            out, first = [], None
            for n in range(2, 9):
                v = [D[L][dn]["residual_float"][n] for L in Lh]
                a, b = v[-2], v[-1]
                pe = math.log(abs(b / a)) / math.log(Lh[-1] / Lh[-2]) if a * b > 0 else None
                c = cls(pe)
                if n <= 3:
                    out.append((b, Lh[-1] * b, pe, c))
                if first is None and not c.startswith("restored"):
                    first = f"eps^{n} ({c})"
            (b2, lb2, p2, c2), (b3, _, p3, c3) = out
            f = lambda p: "sign" if p is None else f"{p:+.2f}"
            print(f"| {s} | {lab} | {b2:+.4g} ({lb2:+.3g}; {f(p2)}) | {c2} | {b3:+.4g} ({f(p3)}) | {c3} | {first} |")


if __name__ == "__main__":
    main()
