#!/usr/bin/env python3
"""
Turn the output of fast_modular.py (all schemes, one L) into results/<scheme>_L<L>.json, and
cross-check against (i) the Fraction reference outputs ref_<scheme>_L<L>_K<K>.json if present,
(ii) closed forms (C_0 = 1, C_1 = -1/6, C_2(L), E_v^(2)(l)), (iii) internal consistency of the tuning.

usage: export_results.py FAST_JSON [--refdir DIR] [--outdir results] [--capcheck FAST_JSON_K2 ...]
"""
import argparse, json, os, sys
from fractions import Fraction as Fr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closed_forms as cf

ORD = 8


def unpack(vals, L, scheme):
    get = lambda *k: Fr(vals["|".join(map(str, k))])
    C = [get("C", i) for i in range(ORD + 1)]
    r = [get("r", i) for i in range(ORD + 1)]
    g = [get("g", i) for i in range(ORD + 1)]
    E = [[get("E", p, i) for i in range(ORD + 1)] for p in range(4)]
    ls = [L] if scheme == "raw" else list(range(0, L + 1, 2))
    vac = {l: [get("vac", l, i) for i in range(ORD + 1)] for l in ls}
    return C, r, g, E, vac


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fast_json")
    ap.add_argument("--refdir", default=None)
    ap.add_argument("--outdir", default="results")
    ap.add_argument("--capcheck", nargs="*", default=[])
    a = ap.parse_args()
    D = json.load(open(a.fast_json))
    meta = D["meta"]
    L, K = meta["L"], meta["K"]
    report = {"L": L, "K": K, "checks": {}}
    ok_all = True
    for scheme, S in D["schemes"].items():
        assert not S["bad"], f"unverified reconstruction in {scheme}: {S['bad'][:3]}"
        C, r, g, E, vac = unpack(S["values"], L, scheme)
        chk = {}
        chk["C0==1"] = C[0] == 1
        chk["C1==-1/6"] = C[1] == Fr(-1, 6)
        c2, Sp = cf.C2(L)
        chk["C2==closed form"] = C[2] == c2
        chk["E_v^(2)(l)==-(l+2)(l+4)/864 for all l"] = all(vac[l][2] == cf.Ev2(l) for l in vac)
        chk["E_p^(2) - 2p r2 - p(p-1)/2 g2 == S_p(closed)"] = all(
            E[p][2] - 2 * p * r[2] - Fr(p * (p - 1), 2) * g[2] == Sp[p] for p in range(4))
        x = [Fr(1, 2), Fr(-1, 4)] + [Fr(0)] * (ORD - 1)
        chk["tuning E1-E0=x, E3-E0=2-x (all orders)"] = all(
            E[1][n] - E[0][n] == x[n] and E[3][n] - E[0][n] == (2 if n == 0 else 0) - x[n] for n in range(ORD + 1))
        chk["C == E2-E0"] = all(C[n] == E[2][n] - E[0][n] for n in range(ORD + 1))
        chk["r1==0, g1==1/3"] = r[1] == 0 and g[1] == Fr(1, 3)
        if scheme == "consistent":
            chk["E_0 == E_v(L)"] = E[0] == vac[L]
        if scheme == "raw":
            chk["E_0 == vacua[L]"] = E[0] == vac[L]
        # reference comparison
        if a.refdir:
            import glob as _g
            for fn in sorted(_g.glob(os.path.join(a.refdir, f"ref_{scheme}_L{L}_K*.json"))):
                Kref = int(fn.rsplit("_K", 1)[1].split(".")[0])
                R = json.load(open(fn))
                same = (all(Fr(R["C"][i]) == C[i] for i in range(ORD + 1)) and
                        all(Fr(R["r"][i]) == r[i] and Fr(R["g"][i]) == g[i] for i in range(ORD + 1)) and
                        all(Fr(R["E"][p][i]) == E[p][i] for p in range(4) for i in range(ORD + 1)) and
                        all(Fr(R["vacua"][str(l)][i]) == vac[l][i] for l in vac for i in range(ORD + 1)))
                if Kref == K:
                    chk["identical to Fraction reference (all C, r, g, E, vacua)"] = same
                else:
                    chk[f"identical to Fraction reference with cap K={Kref}"] = same
        # particle-cap check against other K runs
        for fn in a.capcheck:
            D2 = json.load(open(fn))
            if scheme not in D2["schemes"] or D2["meta"]["L"] != L:
                continue
            K2 = D2["meta"]["K"]
            C2_, r2_, g2_, E2_, vac2_ = unpack(D2["schemes"][scheme]["values"], L, scheme)
            same = C2_ == C and r2_ == r and g2_ == g and E2_ == E and vac2_ == vac
            first = next((n for n in range(ORD + 1) if C2_[n] != C[n]), None)
            if K2 > K:
                chk[f"identical with raised cap K={K2}"] = same
            else:
                # a LOWER cap must miss the height-16 paths at order 8 (demonstrates that K=16 is needed)
                chk[f"lower cap K={K2} differs, first at order 8 (expected)"] = (not same) and first == 8
        report["checks"][scheme] = chk
        res_cap_verified = sorted(int(k.split("K=")[1].split()[0]) for k in chk if k.startswith("identical with raised cap"))
        res_cap_lower = sorted(int(k.split("K=")[1].split()[0]) for k in chk if k.startswith("lower cap"))
        for k, v in chk.items():
            if v is False:
                ok_all = False
        # write result file
        res = {
            "scheme": scheme, "L": L, "exact": True,
            "digits": "exact",
            "precision_note": "exact rationals: computed modulo "
                              f"{meta['nprimes_used'] + meta['ncheck']} primes < 2^23, Chinese remaindering over "
                              f"{meta['nprimes_used']} primes + rational reconstruction, every value verified on the "
                              f"{meta['ncheck']} held-out primes; *_float fields are these rationals rounded to double",
            "method": "Rayleigh-Schroedinger to eps^8 with full wavefunction corrections psi_1..psi_7, "
                      "reflection-even J=0 sector, exact modular arithmetic",
            "C": [str(c) for c in C], "C_float": [float(c) for c in C],
            "r": [str(c) for c in r], "r_float": [float(c) for c in r],
            "g": [str(c) for c in g], "g_float": [float(c) for c in g],
            "E": [[str(c) for c in row] for row in E], "E_float": [[float(c) for c in row] for row in E],
            "vacua": {str(l): [str(c) for c in vac[l]] for l in vac},
            "vacua_float": {str(l): [float(c) for c in vac[l]] for l in vac},
            "particle_cap": {"relative_cap_K": K,
                             "rule": "states with P <= p + K kept in the channel of reference |p>; "
                                     "vacuum channels p = 0",
                             "exactness_argument": "a contribution to E^(n) is a closed path of <= n vertices, "
                                                   "each changing P by at most 4, so it never exceeds "
                                                   "p + 4*floor(n/2) = p + 16 at n = 8",
                             "identical_results_with_K": res_cap_verified,
                             "lower_K_differs_first_at_order_8": res_cap_lower},
            "n_states_reflection_even": meta["n_states"],
            "n_states_full_J0": meta["n_states_full_J0"],
            "checks": {k: v for k, v in chk.items()},
        }
        os.makedirs(a.outdir, exist_ok=True)
        with open(os.path.join(a.outdir, f"{scheme}_L{L}.json"), "w") as f:
            json.dump(res, f, indent=1)
    print(json.dumps(report, indent=1))
    if not ok_all:
        print("SOME CHECK FAILED", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
