#!/usr/bin/env python3
"""
derive_C8.py -- symbolic derivation of everything the eighth coefficient C8 = 8 T4 needs
(phase 3, 2026-10-03).  Note sections 14-15 (lines 1100-1170) and appendix app:C8polynomial (l.2781).

  A  J0 beta = R1 through g^9 (derive_rg.part_1B, the phase-1 derivation from the regulated responses):
     read the Jacobian coefficients j_n, lambda_n off J0 and compare j7, lambda6 with the note's
     definitions (eq:b9, l.1156-1157); h8 and b9 against the note's recurrence (l.1149-1155).
  B  vacuum normalization: K8 and C9 from the series division sum A g^odd / sum Z g^even and
     sum Q g^even / sum Z g^even, against eq:K8norm and eq:C9norm (l.1141-1147).
  C  the full delta^4 trace: generic (u,z,delta) jets -> fixed point through delta^4 -> T4; the power
     counting of T4 (which jet coefficients enter); the prescription (eq:C8F, eq:C8H) -> C8 = 8 T4 as a
     polynomial in the 35 dictionary inputs; C8 is affine in the ten new inputs with constant
     coefficients; those coefficients against eq:C8assembly; the remainder B_old against the appendix
     polynomial, which is PARSED HERE FROM THE NOTE'S TeX SOURCE (no hand transcription), and against the
     table embedded in lri_framework.py (B_OLD_C8_TERMS); B_done = B_old + the six inherited-record terms.
  D  the derivative dictionary of the ten new inputs (derive_rg Part 1E) and their explicit formulas in
     normalized-response coefficients (out/beta_input_formulas.json), term counts.

Writes out/C8_trace.json (T4, C8 decomposition, B_old term table, checks) and out/derive_C8.log.
Imports only the project's own symbolic scripts (derive_rg.py, derive_invariants.py) and, for the
table comparison in C, lri_framework.B_OLD_C8_TERMS.  Reads the note's TeX (definitions only).
Run: python3 derive_C8.py      (local, about 2 minutes)
"""
import json
import os
import re
import sys
import time
from fractions import Fraction

import sympy as sp
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
NOTE = os.path.normpath(os.path.join(HERE, "..", "..", "LRI_SRI_research_compendium", "note",
                                     "LRI_perturbation_compendium.tex"))
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


OLD = ["a", "p", "A", "E", "V", "alpha", "beta", "gamma", "b", "G", "R", "Phi", "Psi", "J", "Omega",
       "c", "f", "q", "L", "M", "Q", "k", "N", "P", "K"]
NEW = ["W", "S", "U", "J9", "L3", "M21", "M12", "N2", "Ndelta", "Kv"]
INHERITED = ["W", "S", "L3", "M21", "M12", "N2"]
SYM = {n: sp.Symbol(n) for n in OLD + NEW}


# ------------------------------------------------------------------------------------------------
# TeX parsing (note = definitions only)
# ------------------------------------------------------------------------------------------------
def tex_to_sympy(s):
    """the subset of LaTeX used in eq:C8assembly and app:C8polynomial -> sympy (names as in SYM)"""
    s = s.replace("\\notag", " ").replace("\\\\", " ").replace("&", " ").replace("{}", " ")
    s = " ".join(s.split())
    s = s.replace("\\left", "").replace("\\right", "")
    # names with sub/superscripts first
    for pat, rep in ((r"B_\{\\rm old\}", " Bold "), (r"J_9", " J9 "), (r"L_3", " L3 "), (r"M_\{21\}", " M21 "),
                     (r"M_\{12\}", " M12 "), (r"N_2", " N2 "), (r"N_\\delta", " Ndelta "), (r"K_v", " Kv ")):
        s = re.sub(pat, rep, s)
    for g in ("alpha", "beta", "gamma", "Omega", "Psi", "Phi"):
        s = s.replace("\\" + g, f" {g} ")
    s = re.sub(r"\^\{(\d+)\}", r"**\1", s)
    s = s.strip().rstrip(".")
    # \frac{x}{y}, \frac3{32}, \frac34
    for _ in range(3):
        s = re.sub(r"\\frac\{([^{}]*)\}\{([^{}]*)\}", r" ((\1)/(\2)) ", s)
        s = re.sub(r"\\frac(\d)\{([^{}]*)\}", r" ((\1)/(\2)) ", s)
        s = re.sub(r"\\frac(\d)(\d)", r" ((\1)/(\2)) ", s)
    s = re.sub(r"\^\{(\d+)\}", r"**\1", s)
    s = re.sub(r"\^(\d)", r"**\1", s)
    if "\\" in s or "{" in s or "}" in s:
        raise ValueError(f"unparsed TeX left: {s!r}")
    loc = dict(SYM)
    loc["Bold"] = sp.Symbol("Bold")
    # explicit '*' between adjacent operands (then sympy's implicit multiplication is not needed for names)
    s = re.sub(r"(?<=[\w\)])\s+(?=[\w\(])", "*", s.strip())
    return sp.expand(parse_expr(s, local_dict=loc, transformations=standard_transformations
                                + (implicit_multiplication,)))


def note_appendix_Bold():
    tex = open(NOTE).read()
    i = tex.index("\\section{Complete old-input polynomial for the eighth-order trace}")
    j = tex.index("\\begin{align}", i)
    k = tex.index("\\end{align}", j)
    body = tex[j + len("\\begin{align}"):k]
    lhs, rhs = body.split("=", 1)
    assert "B_{\\rm old}" in lhs, lhs
    line0 = tex[:j].count("\n") + 1
    return tex_to_sympy(rhs), line0


def note_C8assembly():
    tex = open(NOTE).read()
    k = tex.index("\\label{eq:C8assembly}")
    j = tex.rindex("\\begin{aligned}", 0, k)
    body = tex[j + len("\\begin{aligned}"):tex.rindex("\\end{aligned}", 0, k)]
    lhs, rhs = body.split("=", 1)
    assert "C_8" in lhs, lhs
    return tex_to_sympy(rhs.rstrip().rstrip(".")), tex[:j].count("\n") + 1


# ------------------------------------------------------------------------------------------------
# A: J0 beta = R1 through g^9
# ------------------------------------------------------------------------------------------------
def part_A(res):
    import derive_rg as R
    log("=" * 96)
    log("A. J0 beta = R1 through g^9 (derive_rg.part_1B, phase-1 derivation from the regulated responses)")
    log("=" * 96)
    t0 = time.time()
    out = R.part_1B(order=9)
    ok_rec = R.compare_with_note(out)
    J0, R1 = R.LAST_J0R1["J0"], R.LAST_J0R1["R1"]
    g, b0 = R.g, R.b0
    s = sp.Symbol
    v = b0 ** 2
    # J0[GH] = sqrt2 b0 sum_n j_n g^n ;  J0[HH] = 1 + sum_n lambda_n g^n
    jn = {n: sp.expand(J0[0, 1].coeff(g, n) / (sp.sqrt(2) * b0)) for n in (1, 3, 5, 7, 9)}
    lam = {n: sp.expand(J0[1, 1].coeff(g, n)) for n in (2, 4, 6, 8)}
    note_j = {1: s("C10_E")}
    for n in (3, 5, 7, 9):
        note_j[n] = -2 * s(f"C{n}0_v") + s(f"C{n}0_E")           # j_n = -2 d_v C_{n,0} + (EE C_n)_0
    note_lam = {n: -2 * s(f"K{n}0") - 4 * v * s(f"K{n}0_v") + 2 * v * s(f"K{n}0_E") for n in (2, 4, 6, 8)}
    ok_j = all(sp.expand(jn[n] - note_j[n]) == 0 for n in jn)
    ok_l = all(sp.expand(lam[n] - note_lam[n]) == 0 for n in lam)
    for n in (1, 3, 5, 7):
        log(f"  j{n}      = {jn[n]}      (note: {note_j[n]})")
    for n in (2, 4, 6):
        log(f"  lambda{n} = {lam[n]}      (note: {note_lam[n]})")
    log(f"  j7 = -2 d_v C7_0 + (EE C7)_0 as in note eq:b9 (l.1157): {ok_j};  "
        f"lambda6 = -2 K6_0 - 4 v d_v K6_0 + 2 v (EE K6)_0: {ok_l}")
    # J0[GG] and J0[HG], and R1, for the record
    ok_gg = sp.expand(J0[0, 0] - 1 - sum(n * s(f"C{n}0") * g ** (n - 1) for n in (3, 5, 7, 9))) == 0
    ok_hg = sp.expand(J0[1, 0] - sp.sqrt(2) * b0 * sum(n * s(f"K{n}0") * g ** (n - 1) for n in (2, 4, 6, 8))) == 0
    ok_r1 = (sp.expand(R1[0] - sum(s(f"C{n}1") * g ** n for n in (3, 5, 7, 9))) == 0 and
             sp.expand(R1[1] - sp.sqrt(2) * b0 * sum(s(f"K{n}1") * g ** n for n in (2, 4, 6, 8))) == 0)
    log(f"  J0[GG] = 1 + sum n C_n0 g^(n-1): {ok_gg};  J0[HG] = sqrt2 b0 sum n K_n0 g^(n-1): {ok_hg};  "
        f"R1 = (sum C_n1 g^n, sqrt2 b0 sum K_n1 g^n): {ok_r1}")
    # which j's and lambda's enter h8, b9 (structure): differentiate the note recurrence with symbols
    log(f"  h8: {len(sp.Add.make_args(out['h8']))} terms, b9: {len(sp.Add.make_args(out['b9']))} terms "
        f"(fully expanded in the response coefficients); derived = note recurrence: {ok_rec}")
    log(f"  [part A {time.time() - t0:.1f} s]")
    res["A"] = {"recurrence_b3_to_b9_h4_to_h8_equals_note": bool(ok_rec), "j_n_equal_note": bool(ok_j),
                "lambda_n_equal_note": bool(ok_l), "J0_GG_HG_R1_structure": bool(ok_gg and ok_hg and ok_r1),
                "j7": str(jn[7]), "lambda6": str(lam[6]),
                "n_terms": {"h8": len(sp.Add.make_args(out["h8"])), "b9": len(sp.Add.make_args(out["b9"]))}}
    return ok_rec and ok_j and ok_l and ok_gg and ok_hg and ok_r1


# ------------------------------------------------------------------------------------------------
# B: normalization K8, C9
# ------------------------------------------------------------------------------------------------
def part_B(res):
    log("=" * 96)
    log("B. vacuum normalization: C_n = [sum A g^odd / sum Z g^even]_n, K_n = [sum Q g^even / sum Z g^even]_n")
    log("=" * 96)
    g = sp.Symbol("g")
    A = {n: sp.Symbol(f"A{n}") for n in (1, 3, 5, 7, 9)}
    Z = {n: sp.Symbol(f"Z{n}") for n in (2, 4, 6, 8)}
    Q = {n: sp.Symbol(f"Q{n}") for n in (2, 4, 6, 8)}
    Zs = 1 + sum(Z[n] * g ** n for n in Z)
    inv = sp.series(1 / Zs, g, 0, 10).removeO()
    Cs = sp.expand(sum(A[n] * g ** n for n in A) * inv)
    Ks = sp.expand(sum(Q[n] * g ** n for n in Q) * inv)
    C9 = Cs.coeff(g, 9)
    K8 = Ks.coeff(g, 8)
    A3, A5, A7, A9 = A[3], A[5], A[7], A[9]
    Z2, Z4, Z6, Z8 = Z[2], Z[4], Z[6], Z[8]
    Q2, Q4, Q6, Q8 = Q[2], Q[4], Q[6], Q[8]
    note_K8 = Q8 - Q6 * Z2 + Q4 * (Z2 ** 2 - Z4) + Q2 * (-Z2 ** 3 + 2 * Z2 * Z4 - Z6)
    note_C9 = (A9 - A7 * Z2 + A5 * (Z2 ** 2 - Z4) + A3 * (-Z2 ** 3 + 2 * Z2 * Z4 - Z6)
               + Z2 ** 4 - 3 * Z2 ** 2 * Z4 + Z4 ** 2 + 2 * Z2 * Z6 - Z8)
    dK8 = sp.expand(K8 - note_K8)
    dC9 = sp.expand(C9.subs(A[1], 1) - note_C9)
    a1part = sp.expand(C9.coeff(A[1]))
    log(f"  K8 derived - eq:K8norm = {dK8}")
    log(f"  C9 derived (A1 = 1) - eq:C9norm = {dC9}")
    log(f"  A1 term of C9: A1 * ({a1part})  (A1 = 1 at eta = 0; the EE derivative also acts on A1, "
        "which the module's jets keep: E A1 = j1)")
    res["B"] = {"K8_equals_eq_K8norm": dK8 == 0, "C9_equals_eq_C9norm_at_A1_1": dC9 == 0,
                "C9_A1_coefficient": str(a1part)}
    return dK8 == 0 and dC9 == 0


# ------------------------------------------------------------------------------------------------
# C: the delta^4 trace
# ------------------------------------------------------------------------------------------------
def part_C(res):
    import derive_invariants as DI
    log("=" * 96)
    log("C. the full delta^4 trace T4 and C8 = 8 T4")
    log("=" * 96)
    t0 = time.time()
    # ---- power counting of T4 with exact rationals (generic jets of degree <= 5)
    import random
    random.seed(271828)
    F, H, Fc, Hc = DI.generic_jets()
    keys = sorted(Fc)
    base = {("F",) + kk: Fraction(random.randint(-9, 9), random.randint(1, 5)) for kk in keys}
    base.update({("H",) + kk: Fraction(random.randint(-9, 9), random.randint(1, 5)) for kk in keys})
    base[("F", 1, 0, 0)] = Fraction(1)
    base[("H", 1, 0, 0)] = Fraction(4)
    for kk in keys:
        if kk[0] == 1 and kk != (1, 0, 0):
            base[("H",) + kk] = Fraction(0)          # H_1jk = -4 h2 = 4 exactly: no z, delta dependence
    T0, _ = DI.rational_TD(base, 4)
    enter = []
    for key in sorted(base):
        if key[0] == "H" and key[1] == 1:
            continue
        pert = dict(base)
        pert[key] = base[key] + Fraction(7, 3)
        T1, _ = DI.rational_TD(pert, 4)
        if T1[4] != T0[4]:
            enter.append(key)
    named = {("F",) + k: v for k, v in DI.FNAMES.items()}
    named.update({("H",) + k: v for k, v in DI.HNAMES.items()})
    unnamed = [k for k in enter if k not in named]
    names_in = sorted(named[k] for k in enter if k in named and isinstance(named[k], str))
    log(f"  power counting: {len(enter)} generic jet coefficients enter T4; unnamed ones: {unnamed}")
    log(f"  named inputs entering T4 ({len(names_in)}): {names_in}")
    missing_names = sorted(set(OLD + NEW) - set(names_in))
    log(f"  dictionary inputs that do NOT enter T4: {missing_names}")
    # also: the one-pair sector H_1jk (= 4 delta_j0 delta_k0 because h2 = -1 identically) -- does T4 see it?
    seen_h1 = []
    for kk in keys:
        if kk[0] == 1 and kk != (1, 0, 0):
            pert = dict(base)
            pert[("H",) + kk] = Fraction(5, 7)
            T1, _ = DI.rational_TD(pert, 4)
            if T1[4] != T0[4]:
                seen_h1.append(kk)
    log(f"  H_1jk (u^1 z^j delta^k of H) that WOULD enter T4 if nonzero: {seen_h1}")
    log("    they vanish because h2 = [eps^0 l^1]Q2 = -1 identically in (v, delta) (phase 1, derive_rg Part 1B);"
        " the module checks it at run time (c8_info['tree_data_hold'], with b3(0,0) = 1)")
    # ---- prescription and T4
    rep = DI.prescription_subs(Fc, Hc)
    Fp, Hp = sp.expand(F.subs(rep)), sp.expand(H.subs(rep))
    us, zs, Ts, Ds = DI.invariants(Fp, Hp, 4)
    T = {m: sp.expand(Ts.coeff(DI.d, m)) for m in range(1, 5)}
    C8 = sp.expand(8 * T[4])
    log(f"  T1 = {T[1]};  T4: {len(sp.Add.make_args(T[4]))} terms;  [sympy {time.time() - t0:.1f} s]")
    new = [SYM[n] for n in NEW]
    # affine in the new inputs with CONSTANT coefficients
    P = sp.Poly(C8, *new)
    deg_new = P.total_degree()
    lin = {n: sp.expand(sp.diff(C8, SYM[n])) for n in NEW}
    const_coef = all(not c.free_symbols for c in lin.values())
    Bold = sp.expand(C8.subs({x: 0 for x in new}))
    recon = sp.expand(Bold + sum(lin[n] * SYM[n] for n in NEW) - C8)
    log(f"  C8 = 8 T4: total degree in the ten new inputs = {deg_new}; their coefficients are constants: "
        f"{const_coef}; C8 - (B_old + sum coef*X) = {recon}")
    note_lin, l_asm = note_C8assembly()
    Bsym = sp.Symbol("Bold")
    dlin = {n: sp.nsimplify(lin[n] - note_lin.coeff(SYM[n])) for n in NEW}
    ok_lin = all(v == 0 for v in dlin.values()) and note_lin.coeff(Bsym) == 1 and \
        sp.expand(note_lin - Bsym - sum(note_lin.coeff(SYM[n]) * SYM[n] for n in NEW)) == 0
    log(f"  linear coefficients (derived): {', '.join(f'{n}: {lin[n]}' for n in NEW)}")
    log(f"  eq:C8assembly parsed from the note TeX (l.{l_asm}): {note_lin}")
    log(f"  derived - eq:C8assembly: {dlin}  ==> {'AGREE' if ok_lin else 'DISAGREE'}")
    # ---- B_old against the appendix (parsed from TeX) and the module table
    Bnote, l_app = note_appendix_Bold()
    dB = sp.expand(Bold - Bnote)
    log(f"  appendix app:C8polynomial parsed from the note TeX (l.{l_app}): {len(sp.Add.make_args(Bnote))} terms")
    log(f"  B_old derived ({len(sp.Add.make_args(Bold))} terms) - appendix = {dB}  ==> "
        f"{'AGREE' if dB == 0 else 'DISAGREE'}")
    assert not (Bold.free_symbols - {SYM[n] for n in OLD}), "B_old contains a new input"
    import lri_framework as LF
    mod = sum(sp.Rational(c.numerator, c.denominator) * sp.Mul(*[SYM[nm] ** pw for nm, pw in mon])
              for c, mon in LF.B_OLD_C8_TERMS)
    dmod = sp.expand(Bold - mod)
    mod_lin = {n: sp.Rational(LF.C8_LINEAR[n].numerator, LF.C8_LINEAR[n].denominator) for n in NEW}
    ok_modlin = all(mod_lin[n] == lin[n] for n in NEW) and tuple(LF.C8_INHERITED) == tuple(INHERITED)
    log(f"  lri_framework.B_OLD_C8_TERMS ({len(LF.B_OLD_C8_TERMS)} terms) - derived = {dmod};  "
        f"C8_LINEAR, C8_INHERITED = derived: {ok_modlin}")
    # B_done
    Bdone = sp.expand(Bold + sum(lin[n] * SYM[n] for n in INHERITED))
    rest = sp.expand(C8 - Bdone)
    log(f"  B_done = B_old + {' + '.join(f'({lin[n]}) {n}' for n in INHERITED)}")
    log(f"  C8 - B_done = {rest}   (the four packages F1..F4: Ndelta, U, Kv, J9; note l.1404)")
    # degree structure of B_old
    degs = {}
    for t in sp.Add.make_args(Bold):
        dg = sp.Poly(t, *[SYM[n] for n in OLD]).total_degree()
        degs[dg] = degs.get(dg, 0) + 1
    log(f"  B_old: {len(sp.Add.make_args(Bold))} terms by total degree {dict(sorted(degs.items()))}; "
        f"old inputs absent from B_old: {sorted(set(OLD) - {str(x) for x in Bold.free_symbols})}")
    table = []
    for t in sorted(sp.Add.make_args(Bold), key=lambda e: (sp.Poly(e, *[SYM[n] for n in OLD]).total_degree(), str(e))):
        c, mon = t.as_coeff_Mul()
        pw = mon.as_powers_dict()
        table.append([str(sp.Rational(c)), [[str(k), int(v)] for k, v in sorted(pw.items(), key=lambda kv: OLD.index(str(kv[0])))]])
    ok = (deg_new == 1 and const_coef and recon == 0 and ok_lin and dB == 0 and dmod == 0 and ok_modlin
          and not unnamed and names_in == sorted(OLD + NEW))
    res["C"] = {
        "power_counting": {"n_generic_coefficients_entering_T4": len(enter), "unnamed": [str(x) for x in unnamed],
                           "named_inputs_entering_T4": names_in, "inputs_not_entering_T4": missing_names,
                           "one_pair_H1jk_entering_T4": [str(x) for x in seen_h1]},
        "T1_to_T4": {f"T{m}": str(T[m]) for m in range(1, 5)},
        "u_star": str(us), "z_star": str(zs),
        "C8_equals_8T4": str(C8),
        "C8_total_degree_in_new_inputs": deg_new, "C8_new_coefficients_constant": const_coef,
        "C8_linear_coefficients": {n: str(lin[n]) for n in NEW},
        "eq_C8assembly_line": l_asm, "linear_part_equals_eq_C8assembly": ok_lin,
        "B_old": str(Bold), "B_old_n_terms": len(sp.Add.make_args(Bold)), "B_old_terms_by_degree": degs,
        "B_old_term_table": table,
        "appendix_line": l_app, "B_old_equals_appendix_parsed_from_TeX": dB == 0,
        "B_old_equals_module_table": dmod == 0, "module_C8_LINEAR_and_C8_INHERITED_equal_derived": ok_modlin,
        "inherited_record_inputs": INHERITED,
        "B_done": str(Bdone), "C8_minus_B_done": str(rest),
        "all_ok": ok,
    }
    log(f"  [part C {time.time() - t0:.1f} s]")
    return ok


# ------------------------------------------------------------------------------------------------
# D: dictionary and explicit formulas of the ten new inputs
# ------------------------------------------------------------------------------------------------
def part_D(res):
    import derive_rg as R
    log("=" * 96)
    log("D. dictionary of the ten new inputs and their explicit formulas")
    log("=" * 96)
    ok = R.part_1E_dictionary()
    fpath = os.path.join(OUT, "beta_input_formulas.json")
    if not os.path.exists(fpath):
        R.explicit_input_formulas()
    form = json.load(open(fpath))
    nterms = {n: len(sp.Add.make_args(sp.sympify(form[n]))) for n in NEW}
    log(f"  explicit formulas (normalized-response coefficients, out/beta_input_formulas.json), terms: {nterms}")
    for n in ("W", "L3", "M21", "M12"):
        log(f"  {n} = {form[n]}")
    res["D"] = {"dictionary_equals_note": bool(ok), "formula_terms": nterms}
    return ok


def main():
    t0 = time.time()
    res = {"generated_by": "framework/derive_C8.py", "note": os.path.relpath(NOTE, HERE)}
    okA = part_A(res)
    okB = part_B(res)
    okC = part_C(res)
    okD = part_D(res)
    res["all_ok"] = bool(okA and okB and okC and okD)
    log("=" * 96)
    log("SUMMARY: A (J0 beta = R1 through g^9; h8, b9, j7, lambda6) %s | B (K8, C9 normalization) %s | "
        "C (T4, C8 = 8T4 = B_old + eq:C8assembly) %s | D (dictionary) %s"
        % tuple("OK" if x else "FAIL" for x in (okA, okB, okC, okD)))
    log("==> C8 DERIVATION AGREES WITH THE NOTE" if res["all_ok"] else "==> C8 DERIVATION: DISCREPANCY (see above)")
    log(f"[{time.time() - t0:.0f} s]")
    with open(os.path.join(OUT, "C8_trace.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)
    with open(os.path.join(OUT, "derive_C8.log"), "w") as f:
        f.write("\n".join(LOG) + "\n")
    return 0 if res["all_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
