#!/usr/bin/env python3
"""Compact descendant summary (markdown): for each scheme and descendant, R_n at the largest L, L*R_n, and
p_eff = d ln|R|/d ln L over the last two L pairs, n = 2..5.  usage: python3 desc_summary.py"""
import glob, json, math, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")


def main():
    print("| scheme | desc. | n | L_max | R_n(L_max) | L R_n | p_eff (last two pairs) |")
    print("|---|---|---|---|---|---|---|")
    for s in ("raw", "consistent", "zeromode", "complete2", "W", "WB", "W+V", "WnoM", "WM2", "WM3"):
        Ls = sorted(int(re.search(r"_L(\d+)\.json", f).group(1))
                    for f in glob.glob(os.path.join(R, f"descendant_{s}_L*.json")))
        if not Ls:
            continue
        D = {L: json.load(open(os.path.join(R, f"descendant_{s}_L{L}.json")))["descendants"] for L in Ls}
        for dn in ("odd1", "odd2", "even1"):
            Lh = [L for L in Ls if dn in D[L] and L >= 4]
            for n in (2, 3, 4, 5):
                v = [D[L][dn]["residual_float"][n] for L in Lh]
                pe = []
                for i in (len(Lh) - 2, len(Lh) - 1):
                    a, b = v[i - 1], v[i]
                    pe.append(f"{math.log(abs(b / a)) / math.log(Lh[i] / Lh[i - 1]):+.2f}" if a * b > 0 else "sign")
                print(f"| {s} | {dn} | {n} | {Lh[-1]} | {v[-1]:+.4g} | {Lh[-1] * v[-1]:+.4g} | {', '.join(pe)} |")


if __name__ == "__main__":
    main()
