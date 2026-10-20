#!/usr/bin/env python3
"""`make -f public.mk replay` for HT_Pert/code/lri_d1_fullblock_tail_response.

The paper quotes no number from this package. It is the cited check behind one caveat sentence of the Hamiltonian
truncation section ("a second channel with the leading power Lambda^{-1/2} enters at eps^4"). This replay recomputes the
structural facts that sentence rests on, and the package's own numbers around them, from the shipped files. Reruns
happen on a fresh copy of the package under WORK/replay_tree (the package's scripts rewrite results/); the shipped
tree is only read. Rows (ids as in results_map.md):
  fb.manifest   MANIFEST.sha256: 108 files byte-identical (files listed in public/SCRUBBED.txt are reported)
  fb.power      outer power of the J channel, Eq. (3) of docs/METHOD.md: Lambda^(3 alpha - 2) with alpha = (1 - eps)/2
                is Lambda^(-1/2) at eps = 0 (eps slope -3/2), the same leading power as the phi^6 channel
                Lambda^(alpha - 1) (slope -1/2); the J coefficient of the kernel Eq. (2), (2 - beta) B3 with
                beta = 3 alpha, equals the Eq. (3) factor Lambda^(3 alpha - 2)/[3 Gamma(3 alpha)]
  fb.onset      the channel starts at eps^4: (a) J^P (Eq. 1, reflection-even sector) annihilates every low state with
                P <= 4 and not those with P = 5, in both its Eq. (1) form and the normal-ordered form that
                code/response.py implements (the two agree); (b) exact-rational reruns (code/exact_response.py, low
                cutoff 2 and 4) reproduce results/exact_full_L{2,4}_d8.json: S_J,0..3 = 0 exactly, S_J,4 = 4375/729
                and 18571/2592; (c) all 13 shipped full-J response records (Dconn mu = 2..28, raw mu = 2..8) have
                |S_J,k| <= 1e-15 for k <= 3 and S_J,4 > 0, and float reruns of code/response.py reproduce them to
                1e-12 (scaled), at mu <= 16 here and at all 13 with --full
  fb.amplitude  arithmetic: 1/[3 Gamma(3/2)] = 2/(3 sqrt(pi)); the shipped partial assembly (mu = 8, Lambda = 1024)
                uses exactly this factor on S_J,4 and the Eq. (3) phi^6 factor on S_Phi6,2 = -40/9, and a rerun of
                code/assemble_response.py reproduces it. The J coefficient itself is UNVERIFIED (see fb.unverified)
  fb.B          code/mixing_asymptotics.py rerun: A = 32(pi-2)/(729 pi^(3/2)), 1/81 and
                B = [41+42pi+12gamma_E+24log2+48log(1+sqrt2)]/486 = 0.49138877353902566 of Eq. (6), equal to the shipped
                results/phase_overlap_asymptotics.json and to the value printed in docs/METHOD.md
  fb.annulus    tests/check_annulus.py rerun: "468 exact thresholds; 36 direct finite-annulus comparisons passed";
                the 36 fresh rows equal results/general_bath_annulus.json to 1e-8 (relative); the REPORT.md table
                (alpha = 1/2, reflection even, Lambda = 64, 256, 1024) is reproduced to its 9 decimals
  fb.caveat     INFO: what the paper uses (structure only; no number of this package is quoted)
  fb.unverified INFO: the J sign and normalisation were rated only 'plausible' by the review
Exit status 1 on any FAIL. The table is also written to WORK/replay_lri_d1_fullblock_tail_response.txt (and .json).
usage: python3 public/replay_fb.py [--work .work] [--full]"""
import argparse
import json
import math
import os
import sys
import time
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fb_common as fc  # noqa: E402

ROWS = []
QUOTED = {   # expected values (quoted_lri_d1_fullblock_tail_response.json); no macro of numbers.tex
    "fb.manifest": "108 files",
    "fb.power": "Lambda^(-1/2) at eps = 0",
    "fb.onset": "from eps^4",
    "fb.amplitude": "2/(3 sqrt(pi)) (unverified)",
    "fb.B": "0.49138877353902566",
    "fb.annulus": "36 comparisons pass",
    "fb.caveat": "structure only",
    "fb.unverified": "plausible only",
}
DCONN_MU = (2, 4, 6, 8, 12, 16, 20, 24, 28)
RAW_MU = (2, 4, 6, 8)
QUICK_MU = 16                      # float reruns of the response records up to this low cutoff (all with --full)
REPORT_TABLE = {64: ("0.511091892", "0.012191234"), 256: ("0.260162207", "0.001479356"),
                1024: ("0.130637193", "0.000183589")}
EXACT_S4 = {2: "4375/729", 4: "18571/2592"}
ANNULUS_OUT = "468 exact thresholds; 36 direct finite-annulus comparisons passed"


def row(rid, verdict, what, computed):
    ROWS.append((rid, verdict, what, QUOTED[rid], computed))


def jload(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def guarded(rid, what, fn):
    """Run one row's computation; an exception is a FAIL of that row, not of the whole replay."""
    try:
        ok, computed = fn()
        row(rid, "PASS" if ok else "FAIL", what, computed)
    except Exception as e:  # noqa: BLE001
        row(rid, "FAIL", what, f"error: {type(e).__name__}: {str(e)[:300]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(fc.PKG, ".work"))
    ap.add_argument("--full", action="store_true", help="float reruns of all 13 full-J response records (about 3.5 min)")
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    t0 = time.perf_counter()
    SHIP = fc.PKG
    RES = os.path.join(SHIP, "results")
    method = open(os.path.join(SHIP, "docs", "METHOD.md"), encoding="utf-8").read()
    report = open(os.path.join(SHIP, "REPORT.md"), encoding="utf-8").read()
    tree = fc.copy_tree(os.path.join(work, "replay_tree"))
    sys.path[:0] = [os.path.join(tree, "code"), os.path.join(tree, "vendor")]

    # fb.manifest
    def manifest():
        n, ok, sc, bad = fc.verify_manifest()
        return (not bad and n == 108), f"{ok}/{n} byte-identical, {len(sc)} scrubbed {sc}, failures {bad}"
    guarded("fb.manifest", "MANIFEST.sha256 of the shipped package (sha256)", manifest)

    # fb.power
    def power():
        import sympy as s
        need = ["epsilon=2s-1, x=(1-epsilon)/4, alpha=2x,", "beta=3alpha.",
                "B3=Lambda^(beta-2)/[3(2-beta)Gamma(beta)].", "-(2-beta) J_nu^bath],",
                "delta Delta_E = -Lambda^(alpha-1) S_Phi6/[18(1-alpha)Gamma(alpha)]",
                "+Lambda^(3alpha-2) S_J/[3Gamma(3alpha)] + ... ."]
        missing = [x for x in need if x not in method]
        eps, lam = s.symbols("epsilon Lambda", positive=True)
        alpha = (1 - eps) / 2
        beta = 3 * alpha
        pj, p6 = 3 * alpha - 2, alpha - 1
        vals = (pj.subs(eps, 0), s.diff(pj, eps), p6.subs(eps, 0), s.diff(p6, eps))
        b3 = lam ** (beta - 2) / (3 * (2 - beta) * s.gamma(beta))
        ident = s.simplify((2 - beta) * b3 - lam ** pj / (3 * s.gamma(3 * alpha))) == 0
        ok = (not missing and vals == (s.Rational(-1, 2), s.Rational(-3, 2), s.Rational(-1, 2), s.Rational(-1, 2))
              and ident)
        return ok, (f"J: 3alpha-2 = {vals[0]} at eps=0, slope {vals[1]}; phi6: alpha-1 = {vals[2]}, slope {vals[3]}; "
                    f"(2-beta)B3 = Lambda^(3alpha-2)/[3Gamma(3alpha)]: {ident}; METHOD.md text missing {missing}")
    guarded("fb.power", "outer power of the J channel, METHOD Eqs. (2)-(3)", power)

    # fb.onset
    def onset():
        import numpy as np
        from annulus import basis
        from exact_response import solve as exact_solve
        from response import solve
        notes, ok = [], True
        # (a) operator check on the low basis of code/annulus.py (modes 0..3, up to 8 particles)
        K, pmax = 3, 8
        states, index = basis(K, pmax)
        P = np.array([len(x) for x in states])
        D = len(states)
        d0 = lambda p: 2 - 2 * np.ceil(p / 8)   # d_nu(p) of METHOD Sec. 2 at nu = 0 (reflection even)
        worst_low, min_p5, worst_eq = 0.0, np.inf, 0.0
        for alpha in (0.49, 0.5, 0.51):
            ws = np.ones(K + 1)
            for n in range(1, K + 1):
                ws[n] = ws[n - 1] * (alpha + n - 1) / n
            B = np.zeros((D, D))
            for i, st in enumerate(states):
                for n in set(st):
                    z = list(st)
                    z.remove(n)
                    B[index[tuple(z)], i] = math.sqrt(st.count(n) * ws[n])
            C, q, A = B.T, B + B.T, ws.sum()
            jp = q @ (d0(P + 3)[:, None] * q) - np.diag(A * d0(P + 4))          # Eq. (1) form, J_0^P
            jn = ((C @ C) * d0(P + 4)[None, :] + C @ ((d0(P + 3) + d0(P + 5))[:, None] * B)
                  + d0(P + 4)[:, None] * (B @ B))                                # response.py normal-ordered form
            worst_low = max(worst_low, float(np.abs(jp[:, P <= 4]).max()), float(np.abs(jn[:, P <= 4]).max()))
            min_p5 = min(min_p5, float(np.abs(jp[:, P == 5]).max()), float(np.abs(jn[:, P == 5]).max()))
            inner = P <= pmax - 2
            worst_eq = max(worst_eq, float(np.abs((jp - jn)[:, inner]).max()))
        ok_a = worst_low == 0.0 and min_p5 > 0.5 and worst_eq < 1e-12
        ok &= ok_a
        notes.append(f"(a) J^P on P<=4: max|.| = {worst_low:g}, on P=5: {min_p5:.3g}; Eq.(1) vs normal-ordered "
                     f"{worst_eq:.1e} ({D} states, alpha 0.49/0.5/0.51)")
        # (b) exact-rational reruns
        got = []
        for L in (2, 4):
            e = exact_solve(L, 8, "dconn", "full")
            sv = jload(os.path.join(RES, f"exact_full_L{L}_d8.json"))
            same = e["response"] == sv["response"] and e["C"] == sv["C"]
            zero = all(Fraction(x) == 0 for x in e["response"][:4])
            ok &= same and zero and e["response"][4] == EXACT_S4[L] and Fraction(e["response"][4]) > 0
            got.append(f"mu={L}: S_J,0..3 = 0 {zero}, S_J,4 = {e['response'][4]}, record equal {same}")
        notes.append("(b) " + "; ".join(got))
        # (c) float records and reruns
        recs = [("dconn", L) for L in DCONN_MU] + [("raw", L) for L in RAW_MU]
        low3, s4min, drift, nre = 0.0, np.inf, 0.0, 0
        for sch, L in recs:
            sv = jload(os.path.join(RES, f"{sch}_full_L{L}_d8.json"))
            r = np.array(sv["response"], dtype=float)
            low3 = max(low3, float(np.abs(r[:4]).max()))
            s4min = min(s4min, float(r[4]))
            if a.full or L <= QUICK_MU:
                fr = np.array(solve(L, 8, sch, "full")["response"], dtype=float)
                drift = max(drift, float(np.max(np.abs(fr - r) / np.maximum(1, np.abs(r)))))
                nre += 1
        ok &= low3 <= 1e-15 and s4min > 0 and drift <= 1e-12
        notes.append(f"(c) 13 records: max|S_J,0..3| = {low3:.1e}, min S_J,4 = {s4min:.6f}; "
                     f"{nre} reruns, max scaled diff {drift:.1e}")
        return ok, " | ".join(notes)
    guarded("fb.onset", "J channel starts at eps^4 (J^P kills P <= 4; response records)", onset)

    # fb.amplitude
    def amplitude():
        import mpmath as mp
        mp.mp.dps = 40
        amp = 1 / (3 * mp.gamma(mp.mpf(3) / 2))
        tgt = 2 / (3 * mp.sqrt(mp.pi))
        ok = abs(amp - tgt) < mp.mpf(10) ** -35
        f6 = -1 / (18 * (1 - mp.mpf(1) / 2) * mp.gamma(mp.mpf(1) / 2))     # Eq. (3) phi6 factor at alpha = 1/2
        ok &= abs(f6 + 1 / (9 * mp.sqrt(mp.pi))) < mp.mpf(10) ** -35
        pa = jload(os.path.join(RES, "partial_assembly_example.json"))
        mu, lam = pa["low_mu"], pa["outer_Lambda"]
        sj = jload(os.path.join(RES, f"dconn_full_L{mu}_d8.json"))["response"]
        s6 = jload(os.path.join(RES, f"dconn_phi6_L{mu}_d8.json"))["response"]
        rows = {r["order"]: r for r in pa["rows"]}
        bath4 = float(rows[4]["bath_phase_component"])
        phi2 = float(rows[2]["phi6_component"])
        e_b = rel(bath4, float(tgt) * sj[4] / math.sqrt(lam))
        e_6 = rel(phi2, float(f6) * s6[2] / math.sqrt(lam))
        e_40 = rel(s6[2], -40 / 9)
        ok &= e_b < 1e-14 and e_6 < 1e-14 and e_40 < 1e-14
        from assemble_response import evaluate
        ev = evaluate(mu, lam)
        mp.mp.dps = 40
        worst = 0.0
        for x, y in zip(ev["rows"], pa["rows"]):
            for k in ("phi6_component", "bath_phase_component", "sum"):
                X, Y = mp.mpf(x[k]), mp.mpf(y[k])
                worst = max(worst, float(abs(X - Y) / max(abs(Y), mp.mpf(10) ** -30)))
        ok &= len(ev["rows"]) == len(pa["rows"]) and worst < 1e-30
        return ok, (f"1/[3Gamma(3/2)] = 2/(3sqrt(pi)) = {mp.nstr(tgt, 17)}; record mu={mu}, Lambda={lam:g}: "
                    f"bath eps^4 term = 2/(3sqrt(pi Lambda)) S_J,4 (rel {e_b:.1e}); phi6 eps^2 term = "
                    f"-S_Phi6,2/(9sqrt(pi Lambda)) with S_Phi6,2 = -40/9 (rel {e_6:.1e}, {e_40:.1e}); "
                    f"assemble_response rerun max rel {worst:.1e}. Arithmetic only: J coefficient UNVERIFIED")
    guarded("fb.amplitude", "J-channel prefactor at eps = 0, Eq. (3) (arithmetic; coefficient unverified)", amplitude)

    # fb.B
    def bcoef():
        import mpmath as mp
        rc, out, err, s = fc.run_py(["code/mixing_asymptotics.py"], tree)
        if rc:
            return False, "code/mixing_asymptotics.py failed: " + err.strip()[-300:]
        f = jload(os.path.join(tree, "results", "phase_overlap_asymptotics.json"))
        g = jload(os.path.join(RES, "phase_overlap_asymptotics.json"))
        A, Q, B = f["numeric"]
        mp.mp.dps = 40
        Bx = (41 + 42 * mp.pi + 12 * mp.euler + 24 * mp.log(2) + 48 * mp.log(1 + mp.sqrt(2))) / 486
        Ax = 32 * (mp.pi - 2) / (729 * mp.pi ** mp.mpf(1.5))
        same = all(rel(x, y) <= 1e-15 for x, y in zip(f["numeric"], g["numeric"]))
        rows_same = ([(r["edges"], r["left_shift"], r["right_shift"], r["weight"]) for r in f["group_rows"]] ==
                     [(r["edges"], r["left_shift"], r["right_shift"], r["weight"]) for r in g["group_rows"]])
        ok = (same and rows_same and f["log_squared"] == "1/81" and abs(B - float(Bx)) <= 1e-16
              and rel(A, float(Ax)) <= 1e-15 and f["finite_part_estimate"] == g["finite_part_estimate"]
              and "B=0.49138877353902566" in method and f"{B!r}" == "0.49138877353902566")
        return ok, (f"A = {A!r}, Q = {f['log_squared']}, B = {B!r} (closed form {mp.nstr(Bx, 20)}); "
                    f"{len(f['group_rows'])} topology rows equal: {rows_same}; equal to the shipped JSON: {same}; "
                    f"rerun {s:.1f} s")
    guarded("fb.B", "log coefficient B of the phase response S_phase,4(mu), Eq. (6)", bcoef)

    # fb.annulus
    def annulus_row():
        rc, out, err, s = fc.run_py(["tests/check_annulus.py"], tree)
        if rc:
            return False, "tests/check_annulus.py failed: " + err.strip()[-300:]
        f = jload(os.path.join(tree, "results", "general_bath_annulus.json"))
        g = jload(os.path.join(RES, "general_bath_annulus.json"))
        v_f = jload(os.path.join(tree, "results", "annulus_validation.json"))
        v_g = jload(os.path.join(RES, "annulus_validation.json"))
        worst, struct = 0.0, len(f) == len(g) == 36
        for x, y in zip(f, g):
            for k in y:
                if isinstance(y[k], float) and k != "alpha":
                    worst = max(worst, rel(x[k], y[k]))
                elif x[k] != y[k]:
                    struct = False
        tab = {r["L"]: r for r in f if r["alpha"] == 0.5 and r["reflection"] == 0}
        tab_ok = all((f"{tab[L]['phase_only_error']:.9f}", f"{tab[L]['error']:.9f}") == v and
                     f"| {L} | {v[0]} | {v[1]} |" in report for L, v in REPORT_TABLE.items())
        pw = math.log2(tab[512]["error"] / tab[1024]["error"])
        pw_bad = math.log2(tab[512]["phase_only_error"] / tab[1024]["phase_only_error"])
        ok = (out.strip() == ANNULUS_OUT and v_f == v_g and struct and worst <= 1e-8 and tab_ok)
        return ok, (f"'{out.strip()}'; 36 rows vs shipped: max rel {worst:.1e}; REPORT table (Lambda 64/256/1024) "
                    f"reproduced: {tab_ok}; error ~ Lambda^-{pw:.2f} with -{{N,M}}/2, ~ Lambda^-{pw_bad:.2f} without "
                    f"(alpha = 1/2, Lambda 512 -> 1024)")
    guarded("fb.annulus", "direct finite-annulus test of the low-bath kernel, Eq. (2)", annulus_row)

    # INFO rows
    row("fb.caveat", "INFO", "paper caveat (ht_section.tex): 'a second channel with the leading power "
        "Lambda^{-1/2} enters at eps^4'",
        "rests on fb.power (power) and fb.onset (onset) only; the phi^6 channel has the same leading power; no "
        "number of this package is quoted in the paper")
    row("fb.unverified", "INFO", "status of the J coefficient (review 2026-10-07)",
        "J sign and normalisation (hence the amplitude 2/(3 sqrt(pi)) and any use of B in a C4 tail) rated "
        "'plausible' only; the K3 J coefficient was not re-derived; fb.annulus checks Eq. (2) against the "
        "package's own direct sums, not their derivation from the Hamiltonian")

    w = max(len(r[0]) for r in ROWS)
    lines = [f"# replay {fc.NAME} ({'full' if a.full else 'quick reruns'}); python {sys.version.split()[0]}, "
             f"long double mantissa {fc.longdouble_bits()} bits",
             f"{'id':{w}s}  verdict  what | quoted | computed"]
    for rid, v, what, q, comp in ROWS:
        lines.append(f"{rid:{w}s}  {v:7s}  {what} | {q} | {comp}")
    npass = sum(r[1] == "PASS" for r in ROWS)
    nfail = sum(r[1] == "FAIL" for r in ROWS)
    ninfo = sum(r[1] == "INFO" for r in ROWS)
    lines.append(f"{npass} PASS, {nfail} FAIL, {ninfo} INFO  ({time.perf_counter() - t0:.1f} s)")
    text = "\n".join(lines)
    print(text)
    with open(os.path.join(work, f"replay_{fc.NAME}.txt"), "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    with open(os.path.join(work, f"replay_{fc.NAME}.json"), "w", encoding="utf-8") as fh:
        json.dump([dict(id=r[0], verdict=r[1], what=r[2], quoted=r[3], computed=r[4]) for r in ROWS], fh, indent=1)
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
