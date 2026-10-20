#!/usr/bin/env python3
"""Condensed tables for README.md (from results/complete_L<L>.json, results/descendant_<scheme>_L<L>.json).
usage: python3 readme_tables.py > results/readme_tables.md"""
import glob, json, math, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
R = os.path.join(HERE, "results")


def Ls_of(pattern):
    return sorted(int(re.search(r"_L(\d+)\.json", f).group(1)) for f in glob.glob(os.path.join(R, pattern)))


def f(x, n=10):
    return "—" if x is None else f"{x:.{n}g}"


def main():
    Ls = Ls_of("complete_L*.json")
    comp = {L: json.load(open(os.path.join(R, f"complete_L{L}.json"))) for L in Ls}
    print("### C_4 .. C_8: W next to consistent and zeromode (10 significant digits)\n")
    print("| L | n | W | consistent | zeromode | W+V | WB (earlier reading) |")
    print("|---|---|---|---|---|---|---|")
    for L in Ls:
        c = comp[L]
        for n in range(4, 9):
            print(f"| {L} | {n} | {f(c['C_float'][n])} | {f(c['other_schemes_C']['consistent']['C_float'][n])} | "
                  f"{f(c['other_schemes_C']['zeromode']['C_float'][n])} | {f(c['alternatives'].get('W+V', {}).get('C_float', [None]*9)[n])} | "
                  f"{f(c['alternatives'].get('WB', {}).get('C_float', [None]*9)[n])} |")
    print()
    print("### C_4 of the variants (check b)\n")
    print("| L | W (= brute_W Sec. 8 for L <= 12) | WB (earlier reading) | WB - W | complete2 (slope form, t = 1/pi) | "
          "C4W_by_L.csv | W+V |")
    print("|---|---|---|---|---|---|---|")
    import csv
    c4w = {int(r["L"]): float(r["C4_W"]) for r in csv.DictReader(open(os.path.join(HERE, "..", "residual_log",
                                                                                      "C4W_by_L.csv")))}
    for L in Ls:
        c = comp[L]
        w = c["C_float"][4]
        wb = c["alternatives"].get("WB", {}).get("C_float", [None] * 9)[4]
        c2 = c["alternatives"].get("complete2", {}).get("C_float_at_t=1/pi", [None] * 9)[4]
        print(f"| {L} | {f(w, 13)} | {f(wb, 13)} | {(wb - w) if wb is not None else float('nan'):+.3e} | "
              f"{f(c2, 13)} | {f(c4w.get(L), 13)} | {f(c['alternatives'].get('W+V', {}).get('C_float', [None] * 9)[4], 13)} |")
    print()
    schemes = ["raw", "consistent", "zeromode", "complete2", "W", "WB", "W+V", "WnoM", "WM2"]
    for dn, lab in (("odd1", "chi_11 = d dbar phi: E - E_1 - 2"), ("odd2", "chi_22 = d^2 dbar^2 phi: E - E_1 - 4"),
                    ("even1", "L_-1 Lbar_-1 phi^2: E - E_2 - 2")):
        print(f"### Descendant residual {lab}, orders 2..8\n")
        for s in schemes:
            Lsd = [L for L in Ls_of(f"descendant_{s}_L*.json") if L >= 2]
            D = {L: json.load(open(os.path.join(R, f"descendant_{s}_L{L}.json")))["descendants"] for L in Lsd}
            Lh = [L for L in Lsd if dn in D[L]]
            if not Lh:
                continue
            print(f"**{s}**\n")
            print("| n | " + " | ".join(f"L={L}" for L in Lh) + " | L*R (last) | p_eff (last pair) |")
            print("|---|" + "---|" * len(Lh) + "---|---|")
            for n in range(2, 9):
                vals = [D[L][dn]["residual_float"][n] for L in Lh]
                a, b = vals[-2], vals[-1]
                pe = (f"{math.log(abs(b / a)) / math.log(Lh[-1] / Lh[-2]):+.2f}" if (a and b and a * b > 0)
                      else "sign change")
                print(f"| {n} | " + " | ".join(f(v, 4) for v in vals) + f" | {f(Lh[-1] * b, 4)} | {pe} |")
            print()


if __name__ == "__main__":
    main()
