#!/usr/bin/env python3
"""
Write the deliverables from the raw solver outputs (raw_out/<tag>_L<L>.json, reconstructed exact rationals):
  results/complete_L<L>.json          scheme W of WINDOW_SPEC.md (primary) + labelled alternatives, window tables,
                                      checks, comparison with raw / consistent / zeromode
  results/descendant_<scheme>_L<L>.json   descendant energies and identity residuals, order by order
usage: python3 export_results.py [--tag main] [--L 0,2,...]
"""
import argparse, csv, glob, json, math, os, re
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
ORD = 8
RL = os.path.join(HERE, "..", "residual_log")

SCHEME_DOC = {
    "W": "WINDOW_SPEC.md scheme W (definition as of the 2026-10-09 changelog): D_l = D^zm + D^M; h(l) = X Lambda X^-1 "
         "from the auxiliary channels with the degenerate partners of z >= 5 removed from the resolvent (sec. 2.10), "
         "D^M = (1/4){Delta c_1(l, N), M'}; all orders, self-consistent",
    "W+V": "WINDOW_SPEC.md scheme W+V: W + D^V = (1/2){Delta c_2(l, N), V'}",
    "WB": "earlier literal reading of WINDOW_SPEC 2.3/2.10 (before the 2026-10-09 change): h from the branch "
          "eigenvectors with the B-equation in the auxiliary channels (partner components included)",
    "W+VB": "W+V with the earlier literal reading (B-equation in the auxiliary channels)",
    "W2B": "WB with windows of order eps^2 only", "WnoMB": "WB without D^M",
    "Wn": "legacy: B-equation in the auxiliary channels, but h^(2) from the explicit second-order sum",
    "W+Vn": "legacy: W+V with the Wn convention",
    "W2": "W with windows of order eps^2 only (D^(k>=3) = 0; WINDOW_SPEC sec. 5.2; reproduces the sec. 8 values)",
    "W2n": "legacy: Wn with windows of order eps^2 only (= W2 at eps^4)",
    "WnoM": "W without D^M (check: equals consistent through eps^3)",
    "WM2": "diagnostic: W with D^M truncated at eps^2 (D^zm at all orders)",
    "WM3": "diagnostic: W with D^M truncated at eps^3 (D^zm at all orders)",
    "raw": "D = 0", "consistent": "D_l(N) = E_v(l) - E_v(l - N), self-consistent vacua",
    "zeromode": "D_l(z, N) = E_z(l) - E_z(l - N) (../zeromode_exact)",
    "complete2": "residual_log README eps^2 window: D = eps^2 [D^zm(naive h^(2)) - (1/(27 pi)) {N, M'_0}]; "
                 "exact polynomials in t = 1/pi",
}


def frs(x):
    return None if x is None else Fr(x)


def flt(x):
    return None if x is None else float(x)


def series(v, key, n=ORD + 1):
    return [v.get(f"{key}|{i}") for i in range(n)]


def load(tag, L):
    fn = os.path.join(HERE, "raw_out", f"{tag}_L{L}.json")
    return json.load(open(fn)) if os.path.exists(fn) else None


def tpoly_float(v, key):
    """value at t = 1/pi of a t-polynomial stored as key|t0, key|t1, ..."""
    tot, j, ok = 0.0, 0, False
    while f"{key}|t{j}" in v:
        x = v[f"{key}|t{j}"]
        if x is None:
            return None
        tot += float(Fr(x)) / math.pi ** j
        j += 1
        ok = True
    return tot if ok else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="prod")
    ap.add_argument("--ext", default="ext", help="tag of the closure-test runs")
    ap.add_argument("--c2", default="c2t10", help="tag of the complete2 runs")
    a = ap.parse_args()
    Ls = sorted(int(m.group(1)) for m in (re.search(rf"/{re.escape(a.tag)}_L(\d+)\.json$", f) for f in
                                             glob.glob(os.path.join(HERE, "raw_out", f"{a.tag}_L*.json"))) if m)
    w_spec = {}
    fn = os.path.join(RL, "results", "w_spec_small_L.txt")
    if os.path.exists(fn):
        for row in open(fn):
            if row.strip() and row[0].isdigit():
                parts = [x.strip() for x in row.split(",")]
                w_spec[int(parts[0])] = float(parts[1])
    c4w = {int(r["L"]): float(r["C4_W"]) for r in csv.DictReader(open(os.path.join(RL, "C4W_by_L.csv")))}
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    summary = {}
    for L in Ls:
        d = load(a.tag, L)
        S = d["schemes"]
        meta = d["meta"]
        ext = load(a.ext, L)
        c2 = load(a.c2, L) or load("c2", L)
        checks = {}
        # reconstruction
        for s, blk in S.items():
            if s.startswith("_"):
                continue
            bad = [k for k in blk["bad"] if not k.startswith(("Ez|", "H|"))]
            checks[f"reconstruction failures ({s}; C, r, g, E_p, descendants)"] = bad
        W = S["W"]["values"]

        def block(s):
            v = S[s]["values"]
            return {"C": series(v, "C"), "C_float": [flt(frs(x)) for x in series(v, "C")],
                    "r": series(v, "r"), "r_float": [flt(frs(x)) for x in series(v, "r")],
                    "g": series(v, "g"), "g_float": [flt(frs(x)) for x in series(v, "g")],
                    "E": [series(v, f"E|{p}") for p in range(4)],
                    "E_float": [[flt(frs(x)) for x in series(v, f"E|{p}")] for p in range(4)]}
        out = {"scheme": "W", "L": L, "exact": True, "definition": SCHEME_DOC["W"],
               "precision_note": "exact rationals: RS modulo %d primes < 2^23, CRT over %d + rational reconstruction, "
                                 "every value verified on %d held-out primes; *_float = the rational rounded to double"
                                 % (len(meta["primes"]), len(meta["primes"]) - meta["args"]["ncheck"],
                                    meta["args"]["ncheck"]),
               "window_spec": "../residual_log/WINDOW_SPEC.md (READY 2026-10-08 23:09 EDT; changelog checked)"}
        out.update(block("W"))
        out["alternatives"] = {s: dict(doc=SCHEME_DOC[s], **block(s)) for s in ("W+V", "WB", "W+VB", "W2", "WnoM",
                                                                                  "WM2", "WM3", "W2B", "WnoMB",
                                                                                  "Wn", "W+Vn", "W2n") if s in S}
        out["other_schemes_C"] = {s: {"C": series(S[s]["values"], "C"),
                                      "C_float": [flt(frs(x)) for x in series(S[s]["values"], "C")]}
                                  for s in ("raw", "consistent", "zeromode") if s in S}
        if c2 is not None and "complete2" in c2["schemes"]:
            v = c2["schemes"]["complete2"]["values"]
            out["alternatives"]["complete2"] = {
                "doc": SCHEME_DOC["complete2"],
                "C_tpoly": [[v.get(f"C|{n}|t{j}") for j in range(8) if f"C|{n}|t{j}" in v] for n in range(ORD + 1)],
                "C_float_at_t=1/pi": [tpoly_float(v, f"C|{n}") for n in range(ORD + 1)]}
        # window tables (claimed entries; every l)
        tabs = {"h": {}, "c1": {}, "c2": {}, "E_z": {}}
        for k_, x in W.items():
            if k_.startswith("H|"):
                _, k, zp, z, l = k_.split("|")
                tabs["h"].setdefault(f"{k}|{zp}|{z}", {})[l] = x
            elif k_.startswith("c1|") or k_.startswith("c2|"):
                nm, k, l = k_.split("|")
                tabs[nm].setdefault(k, {})[l] = x
        book = json.load(open(os.path.join(HERE, "results", os.path.basename(meta["book"]))))
        eclaim = {int(z): j for z, j in book["E"].items()}
        for k_, x in W.items():
            if k_.startswith("Ez|"):
                _, zl, n = k_.split("|")
                z, l = map(int, zl.split(","))
                if int(n) <= eclaim.get(z, -1):
                    tabs["E_z"].setdefault(zl, {})[n] = x
        out["window_tables"] = {"doc": "h: 'k|z'|z' -> {l: h^(k)_{z'z}(l)} (monomial frame, claimed entries of "
                                       "results/book_W_V_desc.json); c1, c2: k -> {l: c^(k)(l)}; E_z: 'z,l' -> "
                                       "{order: E_z^(order)(l)} (claimed orders)", **tabs}
        # ---------------------------------------------------------------- checks
        SS = [s for s in S if not s.startswith("_")]
        C = {s: [frs(x) for x in series(S[s]["values"], "C")] for s in SS}
        rr = {s: [frs(x) for x in series(S[s]["values"], "r")] for s in SS}
        gg = {s: [frs(x) for x in series(S[s]["values"], "g")] for s in SS}
        EE = {s: [[frs(x) for x in series(S[s]["values"], f"E|{p}")] for p in range(4)] for s in SS}
        checks["C0 = 1, C1 = -1/6 (W, W+V)"] = all(C[s][0] == 1 and C[s][1] == Fr(-1, 6) for s in ("W", "W+V"))
        checks["(a) W: C_0..C_3 == consistent == zeromode"] = all(C["W"][n] == C["consistent"][n] == C["zeromode"][n]
                                                                  for n in range(4))
        checks["(a) W: r, g, E_p through eps^2 == consistent"] = all(
            rr["W"][n] == rr["consistent"][n] and gg["W"][n] == gg["consistent"][n] and
            all(EE["W"][p][n] == EE["consistent"][p][n] for p in range(4)) for n in range(3))
        checks["(a) W: r_3, g_3 differ from consistent (D^M,(2) through <V R D^M>)"] = (
            rr["W"][3] != rr["consistent"][3] and gg["W"][3] != gg["consistent"][3]) if L > 0 else "L=0: no window"
        if "WnoM" in C:
            checks["(a) W without D^M == consistent through eps^3 (C, r, g, E_p)"] = all(
                C["WnoM"][n] == C["consistent"][n] and rr["WnoM"][n] == rr["consistent"][n] and
                gg["WnoM"][n] == gg["consistent"][n] and all(EE["WnoM"][p][n] == EE["consistent"][p][n]
                                                             for p in range(4)) for n in range(4))
        if "W+V" in C:
            checks["(a) W+V: C_3 differs from consistent (D^V,(2) survives Pi; WINDOW_SPEC 2.8)"] = (
                C["W+V"][3] != C["consistent"][3]) if L > 0 else "L=0: no window"
        vc, vz = S["consistent"]["values"], S["zeromode"]["values"]
        odds = sorted({k.split("|")[1] for k in vc if k.startswith("Ed|odd")})
        checks["(a) chi_aa energies: consistent == zeromode through eps^3 (z = 0 reference)"] = all(
            vc[f"Ed|{dn}|{n}"] == vz[f"Ed|{dn}|{n}"] for dn in odds for n in range(4)) if odds else "no chi_aa"
        checks["(a) descendant identities exact at eps^0, eps^1 (all schemes)"] = all(
            Fr(S[s]["values"][f"Ed|{dn}|{n}"]) - Fr(S[s]["values"][f"E|{1 if dn.startswith('odd') else 2}|{n}"])
            - (2 * int(dn[3:] if dn.startswith("odd") else dn[4:]) if n == 0 else 0) == 0
            for s in SS for dn in sorted({k.split("|")[1] for k in S[s]["values"] if k.startswith("Ed|")})
            for n in range(2))
        checks["(a) first order where C(W) differs from zeromode"] = next(
            (n for n in range(ORD + 1) if C["W"][n] != C["zeromode"][n]), None)
        if "W2" in C:
            checks["W2 (eps^2 windows only) C_0..C_4 == W"] = all(C["W2"][n] == C["W"][n] for n in range(5))
        if "WB" in C:
            checks["WB == W through eps^3 (C, r, g, E_p): partners enter windows from h^(2) of z >= 5"] = all(
                C["WB"][n] == C["W"][n] and rr["WB"][n] == rr["W"][n] and gg["WB"][n] == gg["W"][n]
                for n in range(4))
        b5 = os.path.join(RL, "brute", f"brute_W5_L{L}.json")
        if os.path.exists(b5) and "W" in C:
            b = json.load(open(b5))["Wb"]
            checks["(b) W: C_0..C_5, r_0..r_4, g_0..g_4 == brute_W5.py variant Wb (spec changelog 2026-10-09)"] = (
                all(C["W"][n] == Fr(b["C"][n]) for n in range(6)) and
                all(rr["W"][n] == Fr(b["r"][n]) and gg["W"][n] == Fr(b["g"][n]) for n in range(5)))
        bfn = os.path.join(RL, "brute", f"brute_W_L{L}.json")
        if os.path.exists(bfn):
            b = json.load(open(bfn))
            ref4 = Fr(b["C4_W_spec_exact"])
            checks["(b) W and W2: C_4 == WINDOW_SPEC sec. 8 brute_W exact; r_0..3, g_0..3 == brute_W"] = (
                C["W"][4] == ref4 and C["W2"][4] == ref4 and
                all(rr["W"][n] == Fr(b["r_W_spec"][n]) and gg["W"][n] == Fr(b["g_W_spec"][n]) for n in range(4)))
            if "WB" in C:
                checks["(b) WB (earlier reading) C_4 - brute_W reference (partner terms of h^(2), z >= 5)"] = float(
                    C["WB"][4] - ref4)
        if L in w_spec:
            checks["(b) W C_4 - w_spec_small_L.txt (large-L codes, c1 form, floats)"] = float(C["W"][4]) - w_spec[L]
            if "WB" in C:
                checks["(b) WB C_4 - w_spec_small_L.txt (partner terms of h^(2))"] = float(C["WB"][4]) - w_spec[L]
        if c2 is not None and "complete2" in c2["schemes"] and L in c4w:
            v = c2["schemes"]["complete2"]["values"]
            checks["(b) complete2 C_4(t=1/pi) - C4W_by_L.csv C4_W (slope form)"] = tpoly_float(v, "C|4") - c4w[L]
        for s, e in S.get("_garbage_report", {}).items():
            checks[f"(d) garbage outside the claimed set: {s} unchanged ({e['primes']} primes x "
                   f"{e['compared_per_prime']} residues of C, r, g, E_p, descendants)"] = (len(e["differ"]) == 0)
        for s in ("W", "W+V", "Wn", "W+Vn", "W2", "W2n", "WnoM", "WB", "W+VB", "W2B", "WnoMB", "consistent",
                  "zeromode"):
            gk = s + "_garbage"
            if gk in S:
                v, g = S[s]["values"], S[gk]["values"]
                bad = set(S[s]["bad"]) | set(S[gk]["bad"])
                keys = [k for k in v if k.split("|")[0] in ("C", "r", "g", "E", "Ed") and k not in bad]
                checks[f"(d) garbage outside the claimed set: {s} unchanged ({len(keys)} reconstructed C, r, g, "
                       f"E_p, descendant values)"] = all(v[k] == g.get(k) for k in keys)
        if ext is not None:
            for s, blk in ext["schemes"].items():
                if s in S:
                    v, e = S[s]["values"], blk["values"]
                    bad = set(S[s]["bad"]) | set(blk["bad"])
                    keys = [k for k in v if k.split("|")[0] in ("C", "r", "g", "E", "Ed") and k not in bad]
                    checks[f"(d) caps + 2, z range + 2, one more order per channel: {s} unchanged "
                           f"({len(keys)} reconstructed values)"] = all(v[k] == e.get(k) for k in keys)
        out["checks"] = checks
        out["meta"] = {k: meta[k] for k in ("Pmax", "n_states", "tiers", "ctiers", "book", "aux_partner_blocks")
                       if k in meta}
        out["meta"]["nprimes"] = len(meta["primes"])
        with open(os.path.join(HERE, "results", f"complete_L{L}.json"), "w") as f:
            json.dump(out, f, indent=1)
        # ---------------------------------------------------------------- descendants
        dsrc = [(s, S[s]["values"]) for s in S if not s.endswith("_garbage") and not s.startswith("_")]
        if c2 is not None and "complete2" in c2["schemes"]:
            dsrc.append(("complete2", c2["schemes"]["complete2"]["values"]))
        dg = load("diagB", L)
        if dg is not None:
            dsrc += [(s_ + "B", b_["values"]) for s_, b_ in dg["schemes"].items() if not s_.startswith("_")]
        for s, v in dsrc:
            if s == "complete2":
                # t-polynomials (t = 1/pi): residual coefficients per power of t + float at t = 1/pi
                descs = sorted({k.split("|")[1] for k in v if k.startswith("Ed|")})
                dd = {}
                for dn in descs:
                    kind, aa = re.match(r"(odd|even)(\d+)", dn).groups()
                    aa = int(aa)
                    prim = 1 if kind == "odd" else 2
                    tp, fl = [], []
                    for n in range(ORD + 1):
                        co = []
                        j = 0
                        while f"Ed|{dn}|{n}|t{j}" in v:
                            x, y = v[f"Ed|{dn}|{n}|t{j}"], v.get(f"E|{prim}|{n}|t{j}")
                            co.append(None if x is None or y is None else
                                      str(Fr(x) - Fr(y) - (2 * aa if (n == 0 and j == 0) else 0)))
                            j += 1
                        tp.append(co)
                        fl.append(None if any(c is None for c in co) else
                                  sum(float(Fr(c)) / math.pi ** jj for jj, c in enumerate(co)))
                    dd[dn] = {"state": (f"d^{aa} dbar^{aa} phi" if kind == "odd" else f"(L_-1 Lbar_-1)^{aa} phi^2"),
                              "identity": f"E - E_{prim} - {2 * aa} = 0",
                              "residual_tpoly (coefficients of t^0, t^1, ...; t = 1/pi)": tp,
                              "residual_float": fl}
                with open(os.path.join(HERE, "results", f"descendant_{s}_L{L}.json"), "w") as f:
                    json.dump({"scheme": s, "L": L, "definition": SCHEME_DOC.get(s, s), "descendants": dd}, f,
                              indent=1)
                continue
            descs = sorted({k.split("|")[1] for k in v if k.startswith("Ed|")})
            if not descs:
                continue
            dd = {}
            for dn in descs:
                kind, aa = re.match(r"(odd|even)(\d+)", dn).groups()
                aa = int(aa)
                prim = 1 if kind == "odd" else 2
                E = series(v, f"Ed|{dn}")
                Ep = series(v, f"E|{prim}")
                res = [None if (x is None or y is None) else str(Fr(x) - Fr(y) - (2 * aa if n == 0 else 0))
                       for n, (x, y) in enumerate(zip(E, Ep))]
                info = meta["desc_info"].get(dn, {})
                dd[dn] = {"state": (f"d^{aa} dbar^{aa} phi" if kind == "odd" else f"(L_-1 Lbar_-1)^{aa} phi^2"),
                          "identity": f"E - E_{prim} - {2 * aa} = 0", "E": E, "E_float": [flt(frs(x)) for x in E],
                          "residual": res, "residual_float": [flt(frs(x)) for x in res],
                          "eps0_degenerate_space": info}
            with open(os.path.join(HERE, "results", f"descendant_{s}_L{L}.json"), "w") as f:
                json.dump({"scheme": s, "L": L, "definition": SCHEME_DOC.get(s, s), "descendants": dd}, f, indent=1)
        summary[L] = checks
        print(f"L={L}: wrote complete_L{L}.json and descendant files; checks:")
        for k, x in checks.items():
            print(f"    {k}: {x}")
    json.dump(summary, open(os.path.join(HERE, "results", "checks_summary.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
