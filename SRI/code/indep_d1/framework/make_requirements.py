#!/usr/bin/env python3
"""
make_requirements.py -- regenerate the requirement lists and the sensitivity tables.

  out/required_inputs_D4.json   raw scalars needed through C7 (116), from the module's structural probe
  out/required_inputs_C8.json   raw scalars needed through C8 (201)
  out/sensitivities_C6_C7_D4.json
        d(C5, C6, C7, D4)/d(raw scalar), derivative convention, exact module gradients, evaluated at an
        INDEPENDENT point: the engine's own preliminary (pilot5) raw data,
        ../engine/results/e2e_pilot5_raw_flat.json (or --point FILE).  Not archive data.
  tests/archive_comparison/sensitivities_at_archive_point_COMPARISON_ONLY.json
        the same gradients at the archive-derived raw point (../spec/comparison/archive_raw_coefficients.json),
        written only for COMPARISON (it shows how much the planning numbers depend on the point).
  out/sensitivities_C8.json     (phase 3)
        d(C8, B_old, B_done, the ten new inputs)/d(raw scalar) for all 201 scalars of order C8, derivative
        convention, at OUR OWN point: the production means (116, engine/runs/prod_6digit/
        framework_input_final.json), then every further coefficient our engine has computed (production all-log
        results, poles1, kplus1, validation runs; assembly/common.extended_input), then any --c8-point FILE
        (e.g. the engine's C8 runs, highest priority); scalars still unknown are set to 0 FOR THE POINT ONLY
        and listed, and the exact dependence of every dC8/dx_i on each of them is given
        (point_dependence: d(dC8/dx_i)/dy_j, from symmetric differences; the curvature check confirms that
        dC8/dx_i is linear in each y_j), so the table can be re-evaluated at any values.  No archive data.
  out/C8_new_scalars.json       the 85 raw scalars order C8 needs beyond order D4, by new input, and which of
        them our engine has already computed

usage: python3 make_requirements.py [--point FILE] [--c8-point FILE ...] [--no-archive-comparison] [--no-c8]
Local, about 3 minutes (the C8 point-dependence scan is ~2.5 min).
"""
import argparse
import hashlib
import json
import os
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lri_framework as L  # noqa: E402

OUT = os.path.join(HERE, "out")
ENGINE_POINT = os.path.join(HERE, "..", "engine", "results", "e2e_pilot5_raw_flat.json")
# the spec agent keeps its archive-derived files in spec/comparison/ (spec/out/ in phase 1)
ARCHIVE_POINT = next((p for p in (os.path.join(HERE, "..", "spec", d, "archive_raw_coefficients.json")
                                  for d in ("comparison", "out")) if os.path.exists(p)),
                     os.path.join(HERE, "..", "spec", "comparison", "archive_raw_coefficients.json"))
SENS_OUTPUTS = ("C5", "C6", "C7", "D4")
PROD_FINAL = os.path.join(HERE, "..", "engine", "runs", "prod_6digit", "framework_input_final.json")
C8_SENS_OUTPUTS = ("C8", "B_old8", "B_done8") + tuple(L.C8_LINEAR)
# the note's structural statements about the four packages (Sec. fullpackages): exact linear coefficients
# of the leading raw scalars (derivative convention)
NOTE_STRUCTURE = {
    "J9": {"A9[eps^0 l^1]": 1, "Z8[eps^0 l^1]": -1, "A7_E[eps^0 l^0]": 2, "Z6_E[eps^0 l^0]": -2},   # l.1381
    "U": {"A7_d[eps^0 l^1]": 1, "Z6_d[eps^0 l^1]": -1, "A5_dE[eps^0 l^0]": 2, "Z4_dE[eps^0 l^0]": -2},  # l.1342
    "Kv": {"Q8_v[eps^0 l^1]": -4, "Q6_vv[eps^0 l^0]": 16, "Q6_vE[eps^0 l^0]": -8},                  # l.1361
    "Ndelta": {"Q6_vd[eps^0 l^1]": -4},                                                            # eq:NdP6
}


def rel(p):
    return os.path.relpath(os.path.abspath(p), HERE)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def requirements(order):
    fw = L.Framework(order, dps=30)
    by_out = fw.required_inputs()
    names = fw.required_names()
    spec_atoms = {}
    for nm in names:
        M, n, i, j, e, p, k = L.parse_raw_name(nm)
        atom = L.prefix_to_spec_atom(M, n, i, j, e)
        spec_atoms.setdefault(atom, {}).setdefault(str(p), []).append(k)
    for atom in spec_atoms:
        for p in spec_atoms[atom]:
            spec_atoms[atom][p] = sorted(spec_atoms[atom][p])
    prefixes = {L.parse_raw_name(nm)[:5] for nm in names}
    return {
        "note": ("raw coefficients [eps^p l^k] needed by lri_framework (exact two-kink sector A1,Z2,Q2 built in); "
                 "derivative convention; minimal set (coefficients multiplying exact zeros omitted)"),
        "generated_by": "framework/make_requirements.py (Framework.required_inputs, structural probe)",
        "order": order,
        "outputs": "all beta inputs and C3..C7" + ("/C8" if order == "C8" else ""),
        "mandatory": ("EVERY listed scalar must be supplied (strict mode raises MissingInputError otherwise), "
                      "including positive-eps coefficients of A3, Q4, Z4 and structural zeros, which are "
                      "given explicitly as value 0, sigma 0, exact true. See INPUT_FORMAT.md."),
        "conventions": ("d = plain d/ddelta at 0; v = d/dv at 1; E = EE = d/deta at 0, two-sided source "
                        "(U^odd + for A, U^even - for Z, Q); d on an E atom also differentiates the f_delta "
                        "inside the source"),
        "count": len(names),
        "n_atoms": len(prefixes),
        "flat_names": names,
        "spec_atoms": spec_atoms,
        "by_output": by_out,
    }


def evaluation_point(path, need):
    data = L.load_inputs(path)
    scal = data["scalars"]
    point, zeroed = {}, []
    for nm in need:
        ent = L._entry(nm, scal.get(nm))
        if ent is None:
            point[nm] = 0          # absent from the point file: set to 0 for the EVALUATION POINT only
            zeroed.append(nm)
        else:
            point[nm] = (sum(ent["reps"]) / len(ent["reps"])) if "reps" in ent else ent["value"]
    return point, zeroed, data


def sensitivities(point):
    fw = L.Framework("D4", dps=40)
    res = fw.from_raw(point)
    sens, signed = {}, {}
    for o in SENS_OUTPUTS:
        g = res.gradient(o)
        items = sorted(g.items(), key=lambda kv: -abs(kv[1]))
        sens[o] = {k: mp.nstr(abs(v), 4) for k, v in items}
        signed[o] = {k: mp.nstr(v, 10) for k, v in items}
    return sens, signed, res


def own_c8_point(need8, extra_files=()):
    """our own evaluation point for the C8 gradients: {name: value} for every scalar we have, by priority
    extra_files (later first) > production canonical means > every other coefficient our engine computed"""
    sys.path.insert(0, os.path.join(HERE, "..", "assembly"))
    import common as CM
    sources = []
    vals = {}

    def add(scal, label, path):
        n = 0
        for nm, ent in scal.items():
            cn = L.canonical_raw_name(nm)
            if cn in vals or cn not in need8:
                continue
            e = L._entry(cn, ent)
            if e is None:
                continue
            vals[cn] = (sum(e["reps"]) / len(e["reps"])) if "reps" in e else e["value"]
            n += 1
        sources.append({"source": label, "path": rel(path) if path else None,
                        "sha256": sha256(path) if path and os.path.isfile(path) else None, "n_used": n})
    for f in reversed(list(extra_files)):
        add(L.load_inputs(f)["scalars"], "--c8-point", f)
    add(L.load_inputs(PROD_FINAL)["scalars"], "production (canonical, 116)", PROD_FINAL)
    ext, info = CM.extended_input(1, with_validation=True, with_poles=True)
    add(ext["scalars"], "own engine: production all-log results, poles1, validation runs", CM.FINAL_RESULTS)
    add(L.load_inputs(CM.KPLUS1_RESULTS)["scalars"], "own engine: kplus1", CM.KPLUS1_RESULTS)
    zeroed = sorted(set(need8) - set(vals))
    return vals, zeroed, sources


def c8_sensitivities(extra_files=()):
    with mp.workdps(40):     # gradients, differences and the curvature check at 40 digits
        return _c8_sensitivities(extra_files)


def _c8_sensitivities(extra_files):
    fw = L.Framework("C8", dps=40)
    need8 = fw.required_names()
    need4 = set(L.Framework("D4", dps=30).required_names())
    vals, zeroed, sources = own_c8_point(set(need8), extra_files)
    point = dict(vals)
    for nm in zeroed:
        point[nm] = 0
    res = fw.from_raw(point)
    signed = {}
    for o in C8_SENS_OUTPUTS:
        g = res.gradient(o)
        signed[o] = {k: mp.nstr(v, 12) for k, v in sorted(g.items(), key=lambda kv: -abs(kv[1]))}
    g0 = res.gradient("C8")
    # dependence of dC8/dx on each unknown scalar y_j (exact: symmetric difference; curvature check)
    dep, curv = {}, mp.mpf(0)
    for y in zeroed:
        gp = fw.from_raw(dict(point, **{y: 1}), keep_normalized=False).gradient("C8")
        gm = fw.from_raw(dict(point, **{y: -1}), keep_normalized=False).gradient("C8")
        for x in set(gp) | set(gm) | set(g0):
            d = (gp.get(x, 0) - gm.get(x, 0)) / 2
            c = gp.get(x, 0) + gm.get(x, 0) - 2 * g0.get(x, 0)
            curv = max(curv, abs(c))
            if abs(d) > mp.mpf(10) ** -30:
                dep.setdefault(x, {})[y] = mp.nstr(d, 12)
    const = sorted(x for x in need8 if x not in dep)
    # note structure (exact coefficients of the leading raw scalars of the four packages)
    struct = {}
    for o, coefs in NOTE_STRUCTURE.items():
        g = res.gradient(o)
        struct[o] = {x: {"note": c, "framework": mp.nstr(g.get(x, 0), 15),
                         "independent_of_zeroed_scalars": x not in dep,
                         "agree": abs(g.get(x, 0) - c) < mp.mpf(10) ** -25} for x, c in coefs.items()}
    # precision plan: equal sharing of a target sigma(C8) among the new (beyond-D4) scalars
    new_names = [x for x in need8 if x not in need4]
    plan = {}
    for tgt in ("0.025", "0.0025"):
        T = mp.mpf(tgt)
        n = len(new_names)
        rows = {}
        for x in sorted(new_names, key=lambda k: -abs(g0.get(k, 0))):
            gx = abs(g0.get(x, 0))
            if gx == 0:
                continue
            sx = T / (gx * mp.sqrt(n))
            rows[x] = {"abs_dC8_dx": mp.nstr(gx, 4), "sigma_needed": mp.nstr(sx, 3),
                       "value_at_point": None if x in zeroed else mp.nstr(mp.mpf(vals[x]), 8),
                       "relative_needed": None if x in zeroed or vals[x] == 0 else mp.nstr(sx / abs(mp.mpf(vals[x])), 3)}
        plan[tgt] = {"rule": f"sigma_i = T / (|dC8/dx_i| sqrt(n)), n = {n} new scalars, T = {tgt} "
                             f"(= {mp.nstr(T / mp.mpf('247.38'), 2)} relative)", "rows": rows}
    newdoc = {}
    by = fw.required_inputs()
    for o in L.C8_LINEAR:
        lst = [x for x in by[o] if x not in need4]
        newdoc[o] = {"n_required": len(by[o]), "beyond_D4": lst,
                     "beyond_D4_computed_by_our_engine": [x for x in lst if x not in zeroed],
                     "beyond_D4_not_yet_computed": [x for x in lst if x in zeroed]}
    doc = {
        "note": ("d(output)/d(raw scalar), DERIVATIVE convention, exact lri_framework gradients at order C8 "
                 "(201 scalars). Outputs: C8 = 8 T4, B_old8 (old-input part; depends only on the 116 order-D4 "
                 "scalars), B_done8, and the ten new inputs. 'sens_C8' = |dC8/dx| sorted. The gradients are "
                 "polynomials in the other scalars: see point_dependence."),
        "generated_by": "framework/make_requirements.py",
        "evaluation_point": {"sources_by_priority": sources, "n_scalars": len(need8), "n_known": len(vals),
                             "set_to_zero_for_this_point": zeroed,
                             "why_zero": ("not yet computed by our engine; 0 places the evaluation point only. "
                                          "point_dependence gives d(dC8/dx_i)/dy_j for each of them"),
                             "C8_at_point": mp.nstr(res.C[8].v, 12) + " (meaningless while scalars are zeroed)",
                             "B_old8_at_point": mp.nstr(res.c8["B_old8"].v, 15)},
        "sens_C8": {k: mp.nstr(abs(mp.mpf(v)), 4) for k, v in signed["C8"].items()},
        "signed": signed,
        "point_dependence": {
            "dC8dx_independent_of_the_zeroed_scalars": const,
            "d_dC8dx_d_zeroed": dep,
            "max_curvature": mp.nstr(curv, 3),
            "use": "dC8/dx_i(y) = signed['C8'][x_i] + sum_j d_dC8dx_d_zeroed[x_i][y_j] * y_j (exactly linear in each "
                   "y_j: max_curvature ~ 0; products y_j y_k are not included)"},
        "note_structure_checks": struct,
        "precision_plan_C8": plan,
    }
    newfile = {"note": "raw scalars order C8 needs beyond order D4, by new input (derivative convention)",
               "generated_by": "framework/make_requirements.py", "n_beyond_D4": len(new_names),
               "all_beyond_D4": sorted(new_names),
               "computed_by_our_engine": sorted(x for x in new_names if x not in zeroed),
               "not_yet_computed": sorted(x for x in new_names if x in zeroed), "by_new_input": newdoc}
    return doc, newfile, res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--point", default=ENGINE_POINT, help="raw data file used as the evaluation point")
    ap.add_argument("--c8-point", action="append", default=[],
                    help="further raw file(s) for the C8 evaluation point (highest priority), e.g. C8 engine runs")
    ap.add_argument("--no-archive-comparison", action="store_true")
    ap.add_argument("--no-c8", action="store_true", help="skip the C8 sensitivities")
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    req = {}
    for order in ("D4", "C8"):
        req[order] = requirements(order)
        with open(os.path.join(OUT, f"required_inputs_{order}.json"), "w") as f:
            json.dump(req[order], f, indent=1)
        print(f"required_inputs_{order}.json: {req[order]['count']} scalars in {req[order]['n_atoms']} atoms")
    need = req["D4"]["flat_names"]
    if not os.path.exists(a.point):
        print(f"evaluation point {a.point} not found: sensitivities NOT regenerated")
        return 1
    point, zeroed, _ = evaluation_point(a.point, need)
    sens, signed, res = sensitivities(point)
    doc = {
        "note": ("d(output)/d(raw scalar) for C5, C6, C7, D4: exact gradients of lri_framework, DERIVATIVE "
                 "convention (d output / d [eps^p l^k] of the plain derivative). 'sens' = |value| sorted by "
                 "size (planning: precision targets); 'signed' = signed values. Most entries are exact "
                 "constants; the others depend weakly on the evaluation point."),
        "generated_by": "framework/make_requirements.py",
        "evaluation_point": {
            "source": rel(a.point), "sha256": sha256(a.point),
            "description": ("the engine's own preliminary raw data (pilot5, modest N): an independent point, "
                            "NOT archive data"),
            "set_to_zero_for_this_point": zeroed,
            "why_zero": ("absent from the engine file (the engine's pole analysis finds no such term); "
                         "used only to place the evaluation point, never as a result"),
            "C6_C7_D4_at_point": {o: mp.nstr(res.get(o).v, 12) for o in ("C6", "C7", "D4")},
        },
        "sens": sens,
        "signed": signed,
    }
    with open(os.path.join(OUT, "sensitivities_C6_C7_D4.json"), "w") as f:
        json.dump(doc, f, indent=1)
    print(f"sensitivities_C6_C7_D4.json at {rel(a.point)} ({len(zeroed)} absent scalars set to 0 for the point: "
          f"{zeroed})")
    for o in ("C6", "C7"):
        top = list(sens[o].items())[:4]
        print(f"   largest |d{o}/dx|: {top}")
    if not a.no_archive_comparison and os.path.exists(ARCHIVE_POINT):
        apoint, azero, _ = evaluation_point(ARCHIVE_POINT, need)
        asens, asigned, _ = sensitivities(apoint)
        worst, wname = mp.mpf(0), None
        for o in SENS_OUTPUTS:
            for k, v in signed[o].items():
                w = mp.mpf(asigned[o].get(k, "0"))
                d = abs(mp.mpf(v) - w) / max(abs(mp.mpf(v)), abs(w), mp.mpf(10) ** -30)
                if d > worst:
                    worst, wname = d, f"d{o}/d{k}"
        cdoc = {"note": ("COMPARISON ONLY: the same gradients evaluated at the ARCHIVE-derived raw point "
                         "(spec agent's archive_raw_coefficients.json). Not used for planning or results."),
                "evaluation_point": {"source": rel(ARCHIVE_POINT), "sha256": sha256(ARCHIVE_POINT),
                                     "set_to_zero_for_this_point": azero},
                "max_rel_difference_vs_independent_point": {"value": mp.nstr(worst, 3), "where": wname},
                "sens": asens, "signed": asigned}
        dst = os.path.join(HERE, "tests", "archive_comparison", "sensitivities_at_archive_point_COMPARISON_ONLY.json")
        with open(dst, "w") as f:
            json.dump(cdoc, f, indent=1)
        print(f"comparison only: archive-point sensitivities written; max rel. difference from the independent "
              f"point {mp.nstr(worst, 3)} ({wname})")
    if not a.no_c8:
        doc8, newfile, res8 = c8_sensitivities(a.c8_point)
        with open(os.path.join(OUT, "sensitivities_C8.json"), "w") as f:
            json.dump(doc8, f, indent=1)
        with open(os.path.join(OUT, "C8_new_scalars.json"), "w") as f:
            json.dump(newfile, f, indent=1)
        ep = doc8["evaluation_point"]
        print(f"sensitivities_C8.json: {ep['n_known']} of {ep['n_scalars']} scalars known at our point, "
              f"{len(ep['set_to_zero_for_this_point'])} set to 0 (point dependence given); max curvature "
              f"{doc8['point_dependence']['max_curvature']}; "
              f"{len(doc8['point_dependence']['dC8dx_independent_of_the_zeroed_scalars'])} gradients independent of them")
        top = list(doc8["sens_C8"].items())[:5]
        print(f"   largest |dC8/dx|: {top}")
        ok = all(v["agree"] for o in doc8["note_structure_checks"].values() for v in o.values())
        print(f"   note structure of J9, U, Kv, Ndelta (leading raw scalars): {'AGREE' if ok else 'DISAGREE'}")
        print(f"C8_new_scalars.json: {newfile['n_beyond_D4']} beyond D4, {len(newfile['computed_by_our_engine'])} "
              f"computed by our engine, {len(newfile['not_yet_computed'])} not yet")
    print("REQUIREMENTS AND SENSITIVITIES REGENERATED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
