#!/usr/bin/env python3
"""Write results/zeromode_L<L>.json from the raw outputs, running every exact cross-check.

Inputs (raw_out/):  zm_L<L>.json      zeromode_modular, variants zeromode (+ garbage)       [production]
                    capx2_L<L>.json   every channel cap raised by 2                          [cap check]
                    ext_L<L>.json     extended z range / orders (0-6:8, 7-10:6, 11-14:4, 15-18:2) [closure check]
                    frac_L<L>.json    zeromode_fraction (independent exact code)              [code check]
                    test_L<L>.json    local modular run with the 'consistent' variant (L <= 6)
           ../rs_exact/results/consistent_L<L>.json   (consistent scheme, for the comparison)
           np_check/results/np_L<L>_<variant>.json    (non-perturbative Cauchy comparison summaries)
usage: python3 export_results.py --Ls 0,2,...,18
"""
import argparse, json, os, sys
from fractions import Fraction as Fr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import closed_form_dC4 as CF        # noqa: E402
from zeromode_modular import default_tiers   # noqa: E402

ORD = 8


def load(fn):
    return json.load(open(fn)) if os.path.exists(fn) else None


def vals(d, v="zeromode"):
    return {k: Fr(x) for k, x in d["variants"][v]["values"].items() if x is not None}


def same(a, b, keys=None):
    keys = keys if keys is not None else [k for k in a if k in b]
    bad = [k for k in keys if a[k] != b.get(k)]
    return len(keys), bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--Ls", default="0,2,4,6,8,10,12,14,16,18")
    a = ap.parse_args()
    tiers = default_tiers()
    global DEG
    DEG = json.load(open(os.path.join(HERE, "results", "degeneracy.json")))["blocks"]
    summary = []
    for L in [int(x) for x in a.Ls.split(",")]:
        zm = load(os.path.join(HERE, "raw_out", f"zm_L{L}.json"))
        if zm is None:
            print(f"L={L}: no production file, skipped")
            continue
        V = vals(zm)
        assert not zm["variants"]["zeromode"]["bad"], f"L={L}: reconstruction failures"
        checks = {}
        C = [V[f"C|{i}"] for i in range(ORD + 1)]
        r = [V[f"r|{i}"] for i in range(ORD + 1)]
        g = [V[f"g|{i}"] for i in range(ORD + 1)]
        E = [[V[f"E|{p}|{i}"] for i in range(ORD + 1)] for p in range(4)]
        Ez = {}
        for k, x in V.items():
            if k.startswith("Ez|"):
                _, zl, i = k.split("|")
                Ez.setdefault(zl, {})[int(i)] = x
        Ez = {zl: [d[i] for i in range(len(d))] for zl, d in Ez.items()}
        Ez = dict(sorted(Ez.items(), key=lambda kv: tuple(map(int, kv[0].split(",")))))
        # --- basic identities
        x = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
        checks["C0==1, C1==-1/6"] = C[0] == 1 and C[1] == Fr(-1, 6)
        checks["r1==0, g1==1/3"] = r[1] == 0 and g[1] == Fr(1, 3)
        checks["tuning E1-E0=x, E3-E0=2-x (all orders)"] = all(
            E[1][n] - E[0][n] == x[n] and E[3][n] - E[0][n] == (2 - x[0] if n == 0 else -x[n]) for n in range(ORD + 1))
        checks["C == E2-E0"] = all(C[n] == E[2][n] - E[0][n] for n in range(ORD + 1))
        checks["E_p(L) == E_z(L) table entry for z = p"] = all(
            Ez[f"{p},{L}"][:ORD + 1] == E[p] for p in range(4))
        # --- garbage (closure) check
        if "garbage" in zm["variants"]:
            G = vals(zm, "garbage")
            n, bad = same(V, G)
            checks["D outside the needed (z,k) set replaced by random residues: all numbers identical"] = (
                not bad, n)
        zg = load(os.path.join(HERE, "raw_out", f"zmg_L{L}.json"))
        if zg is not None:
            n, bad = same(V, vals(zg, "garbage"))
            checks["D outside the needed (z,k) set replaced by random residues: all numbers identical"] = (
                not bad, n)
        # --- cap check
        cx = load(os.path.join(HERE, "raw_out", f"capx2_L{L}.json"))
        if cx is not None:
            n, bad = same(V, vals(cx))
            checks["every channel cap raised by 2: all numbers identical"] = (not bad, n)
        ext = load(os.path.join(HERE, "raw_out", f"ext_L{L}.json"))
        if ext is not None:
            X = vals(ext)
            n, bad = same(V, X, [k for k in V])
            checks["extended table (z<=6: k<=8, z<=10: 6, z<=14: 4, z<=18: 2; caps up to 22): all numbers identical"] = (
                not bad, n)
            if "garbage" in ext["variants"]:
                n2, bad2 = same(V, vals(ext, "garbage"), [k for k in V])
                checks["extended table + random D outside it: identical"] = (not bad2, n2)
        fr = load(os.path.join(HERE, "raw_out", f"frac_L{L}.json"))
        if fr is not None:
            F = {}
            for k in ("C", "r", "g"):
                for i, s in enumerate(fr[k]):
                    F[f"{k}|{i}"] = Fr(s)
            for p, row in enumerate(fr["E"]):
                for i, s in enumerate(row):
                    F[f"E|{p}|{i}"] = Fr(s)
            for zl, row in fr["Ez"].items():
                for i, s in enumerate(row):
                    F[f"Ez|{zl}|{i}"] = Fr(s)
            n, bad = same(F, V, list(F))
            checks["identical to the independent Fraction implementation (all C, r, g, E_p, E_z)"] = (not bad, n)
        # --- consistent comparison and closed form
        cons = load(os.path.join(HERE, "..", "rs_exact", "results", f"consistent_L{L}.json"))
        Cc = [Fr(s) for s in cons["C"]]
        rc = [Fr(s) for s in cons["r"]]
        gc = [Fr(s) for s in cons["g"]]
        Ec = [[Fr(s) for s in row] for row in cons["E"]]
        first = lambda A, B: next((i for i in range(ORD + 1) if A[i] != B[i]), None)
        fd = {"C": first(C, Cc), "r": first(r, rc), "g": first(g, gc)}
        for p in range(4):
            fd[f"E{p}"] = first(E[p], Ec[p])
        checks["first order differing from consistent (C, r, g, E_0..E_3)"] = fd
        checks["identical to consistent through eps^3"] = all(
            C[i] == Cc[i] and r[i] == rc[i] and g[i] == gc[i] and all(E[p][i] == Ec[p][i] for p in range(4))
            for i in range(4))
        cf = CF.dC4(L)
        checks["C4 - C4(consistent) == closed-form order-eps^2 zero-mode window term"] = (C[4] - Cc[4] == cf["dC4"])
        checks["r4, g4 differences == closed form"] = (r[4] - rc[4] == cf["dr4"] and g[4] - gc[4] == cf["dg4"])
        checks["C2 == closed form"] = C[2] == cf["C2"]
        # vacuum: E_0(l) must equal the consistent vacuum through order 3 (and differs from 4 on)
        vac_eq = all(Ez[f"0,{l}"][i] == Fr(cons["vacua"][str(l)][i]) for l in range(0, L + 1, 2) for i in range(4))
        checks["E_0(l) == consistent vacuum E_v(l) through eps^3"] = vac_eq
        test = load(os.path.join(HERE, "raw_out", f"test_L{L}.json"))
        if test is not None and "consistent" in test["variants"]:
            T = vals(test, "consistent")
            ok = all(T[f"C|{i}"] == Cc[i] and T[f"r|{i}"] == rc[i] and T[f"g|{i}"] == gc[i]
                     and all(T[f"E|{p}|{i}"] == Ec[p][i] for p in range(4)) for i in range(ORD + 1))
            ok = ok and all(T[f"Ez|0,{l}|{i}"] == Fr(cons["vacua"][str(l)][i])
                            for l in range(0, L + 1, 2) for i in range(7 if l < L else ORD + 1))
            checks["this code in 'consistent' mode reproduces ../rs_exact consistent (C, r, g, E_p, vacua)"] = ok
        # --- non-perturbative summaries
        npres = {}
        for var in ("base", "zh14", "rhoK", "prec", "path", "cap21"):
            s = load(os.path.join(HERE, "np_check", "results", f"np_L{L}_{var}.json"))
            if s is not None:
                npres[var] = {"n_coefficients_compared": s["n_numbers_compared"],
                              "worst_rel_diff_vs_exact": s["worst_rel_diff"],
                              "setup": {k: s["meta"][k] for k in ("Zh", "rho", "K", "prec", "cap", "tsteps")}}
        if npres:
            checks["non-perturbative Cauchy (np_check)"] = npres
        # --- output
        kmax = {z: tiers[z] for z in tiers}
        out = {
            "scheme": "zeromode", "L": L, "exact": True, "digits": "exact",
            "definition": ("D_l(z_s, N_s) = E_{z_s}(l) - E_{z_s}(l - N_s) on every state of level N_s >= 2 with z_s (0,0) "
                           "quanta, D = 0 at level 0; E_z(l) = eigenvalue branch through |z> of "
                           "P_l(H0 + r M + g V)P_l + D_l (self-consistent); one r(eps), g(eps) tuned at cutoff L on "
                           "p = 0..3; observable E_2(L) - E_0(L). See README.md"),
            "precision_note": (f"exact rationals: modulo {zm['meta']['nprimes_used'] + zm['meta']['ncheck']} primes "
                               f"< 2^23, CRT over {zm['meta']['nprimes_used']} + rational reconstruction, every value "
                               f"verified on {zm['meta']['ncheck']} held-out primes; *_float = the rational rounded "
                               "to double"),
            "method": ("Rayleigh-Schroedinger with full wavefunction corrections, degenerate partners (z >= 5) treated by "
                       "the first-order-lifted degenerate RS (psi_{n-1}^B fixed by the B-projection of the order-n "
                       "equation), all channels (z, l) in lock step, reflection-even J=0 sector"),
            "C": [str(v) for v in C], "C_float": [float(v) for v in C],
            "r": [str(v) for v in r], "r_float": [float(v) for v in r],
            "g": [str(v) for v in g], "g_float": [float(v) for v in g],
            "E": [[str(v) for v in row] for row in E], "E_float": [[float(v) for v in row] for row in E],
            "E_z": {zl: [str(v) for v in row] for zl, row in Ez.items()},
            "E_z_float": {zl: [float(v) for v in row] for zl, row in Ez.items()},
            "E_z_key": ("'z,l' -> [E_z^(0)(l), ..., E_z^(k_max)(l)]; k_max = 6 (z <= 6), 4 (7 <= z <= 10), 2 "
                        "(11 <= z <= 14): exactly what D needs through eps^8 (README sec. 3); the primaries "
                        "(p,L), p <= 3, to order 8"),
            "k_max_of_z": {str(z): k for z, k in kmax.items()},
            "channel_cap": "P <= z + 4*floor(k_max/2) in channel (z,l); P <= p + 16 for the primaries (p, L)",
            "degenerate_partners": {
                "rule": "|z> is degenerate with the J=0 states of level N >= 2 and P = z - 2N (z >= 5); in channel (z,l) "
                        "those with N <= l are present; lifted at first order (degeneracy.py)",
                "reflection_even_dim_by_z_and_N": {str(z): {str(b["N"]): b["n_even"] for b in DEG
                                                            if b["z"] == z and b["N"] <= L} for z in range(5, 15)},
                "min_first_order_gap_by_z": {str(z): min(b["min_gap_even"] for b in DEG if b["z"] == z)
                                             for z in range(5, 15)}},
            "consistent": {"C": [str(v) for v in Cc], "C_float": [float(v) for v in Cc]},
            "C_minus_consistent_float": [float(C[i] - Cc[i]) for i in range(ORD + 1)],
            "closed_form_dC4": {"dC4": str(cf["dC4"]), "dr4": str(cf["dr4"]), "dg4": str(cf["dg4"])},
            "n_states_reflection_even": zm["meta"]["n_states"],
            "max_num_plus_den_digits": zm["variants"]["zeromode"]["max_digits"],
            "modulus_digits": zm["variants"]["zeromode"]["modulus_digits"],
            "checks": checks,
        }
        os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
        with open(os.path.join(HERE, "results", f"zeromode_L{L}.json"), "w") as f:
            json.dump(out, f, indent=1)
        flat = []
        for k, v in checks.items():
            if isinstance(v, bool):
                flat.append(v)
            elif isinstance(v, tuple):
                flat.append(v[0])
        print(f"L={L:2d}: wrote results/zeromode_L{L}.json; boolean checks {sum(flat)}/{len(flat)} pass; "
              f"first diff vs consistent {fd}; C8 = {float(C[8]):.10g} (cons {float(Cc[8]):.10g})")
        for k, v in checks.items():
            if (isinstance(v, bool) and not v) or (isinstance(v, tuple) and not v[0]):
                print("   FAILED:", k, v)
        summary.append(L)


if __name__ == "__main__":
    main()
