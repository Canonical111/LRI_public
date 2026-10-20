#!/usr/bin/env python3
"""Markdown tables for README.md from results/complete_L<L>.json and results/descendant_<scheme>_L<L>.json:
  1. C_2..C_8 of W next to consistent and zeromode (and W+V, Wn);
  2. descendant identity residuals per scheme, order and L, with the effective exponent
     p_eff(L) = d ln|R| / d ln L between consecutive L (-1: decays like 1/L; 0: constant; > 0: grows);
  3. the first order whose residual does not decay (classification rule below).
usage: python3 make_tables.py > results/tables.md"""
import glob, json, math, os, re
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")


def Ls_of(pattern):
    return sorted(int(re.search(r"_L(\d+)\.json", f).group(1)) for f in glob.glob(os.path.join(R, pattern)))


def g(x, n=10):
    return "—" if x is None else f"{x:.{n}g}"


def main():
    Ls = Ls_of("complete_L*.json")
    comp = {L: json.load(open(os.path.join(R, f"complete_L{L}.json"))) for L in Ls}
    print("## C_n per L (13 significant digits; exact rationals in results/complete_L<L>.json)\n")
    for n in range(2, 9):
        print(f"### C_{n}\n")
        print("| L | W | W+V | WB (earlier reading) | consistent | zeromode | raw |")
        print("|---|---|---|---|---|---|---|")
        for L in Ls:
            c = comp[L]
            alt = c["alternatives"]
            oth = c["other_schemes_C"]
            print(f"| {L} | {g(c['C_float'][n], 13)} | {g(alt.get('W+V', {}).get('C_float', [None]*9)[n], 13)} | "
                  f"{g(alt.get('WB', {}).get('C_float', [None]*9)[n], 13)} | {g(oth['consistent']['C_float'][n], 13)} | "
                  f"{g(oth['zeromode']['C_float'][n], 13)} | {g(oth['raw']['C_float'][n], 13)} |")
        print()
    # descendants
    schemes = ["raw", "consistent", "zeromode", "complete2", "W", "WB", "W+V", "WnoM", "WM2", "WM3"]
    print("## Descendant identity residuals R_n(L) = [E_desc - E_prim - 2a]^(n)\n")
    print("p_eff = d ln|R_n| / d ln L between consecutive L (shown after the value, for the last pairs).\n")
    for s in schemes:
        Lsd = Ls_of(f"descendant_{s}_L*.json")
        if not Lsd:
            continue
        D = {L: json.load(open(os.path.join(R, f"descendant_{s}_L{L}.json")))["descendants"] for L in Lsd}
        names = sorted({k for L in Lsd for k in D[L]}, key=lambda k: (k[:3] != "odd", int(re.sub(r"\D", "", k))))
        for dn in names:
            if dn not in ("odd1", "odd2", "odd3", "even1", "even2"):
                continue
            Lh = [L for L in Lsd if dn in D[L]]
            print(f"### {s}: {dn} ({D[Lh[0]][dn]['state']}; {D[Lh[0]][dn]['identity']})\n")
            print("| n | " + " | ".join(f"L={L}" for L in Lh) + " | p_eff (last two pairs) |")
            print("|---|" + "---|" * len(Lh) + "---|")
            for n in range(1, 9):
                vals = [D[L][dn]["residual_float"][n] for L in Lh]
                pe = []
                for i in range(max(1, len(Lh) - 2), len(Lh)):
                    a, b = vals[i - 1], vals[i]
                    if a and b and a * b > 0 and Lh[i - 1] > 0:
                        pe.append(f"{math.log(abs(b / a)) / math.log(Lh[i] / Lh[i - 1]):+.2f}")
                    else:
                        pe.append("sign" if (a and b) else "—")
                print(f"| {n} | " + " | ".join(g(v, 4) for v in vals) + f" | {', '.join(pe)} |")
            print()


if __name__ == "__main__":
    main()
