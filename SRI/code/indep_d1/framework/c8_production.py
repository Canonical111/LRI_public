#!/usr/bin/env python3
"""
c8_production.py -- the old-input part of C8 on our own phase-2 production data (phase 3, 2026-10-03).

  B_old (appendix polynomial in the 25 old inputs, eq:C8assembly) from the engine's production replicates
  engine/runs/prod_6digit/framework_input_final.json, strict, per-replicate assembly (order D4: the 116
  required scalars), with the three error estimators of the assembly phase:
      sigma_cov   linear propagation with the per-job replicate covariance (+ precision floors),
      sigma_rep   standard error of the R = 6 per-replicate assemblies (+ floors),
      sigma_pool  sector-pooled projection of every job on dB_old/dx (assembly/pooled_errors.py) (+ floors);
  quoted sigma = the largest.  Tier 1 alone (framework_input.json) is assembled as a cross-check.
  Then the 'partial C8' with what we have: B_old + 4 W, where W is the framework's own semi-analytic
  three-kink value (validate_low_order.three_kink_single_log, recomputed here at 50 digits); the other nine
  new inputs are MISSING (never zero) and are listed with the raw scalars they still need, split into those
  our engine already has (production all-log results, poles1, kplus1, validation runs) and those it lacks.

Archive-free: reads only our own engine output and the framework.  Writes out/C8_production.json (+ .sha256)
and out/c8_production.log.  The comparison with the archive is a separate step (compare_c8_production.py),
which refuses to run before this file exists and records its SHA-256.
Run: python3 c8_production.py      (local, about 1 minute)
"""
import hashlib
import json
import os
import sys
import time

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "assembly"))
import lri_framework as L  # noqa: E402

OUT = os.path.join(HERE, "out")
PROD = os.path.join(ROOT, "engine", "runs", "prod_6digit")
TOPUP = os.path.join(ROOT, "engine", "runs", "prod_6digit_topup1")
FINAL = os.path.join(PROD, "framework_input_final.json")
TIER1 = os.path.join(PROD, "framework_input.json")
REPLACED = ["Q6_E", "A7_v", "A7_base", "A5_vE"]       # top-up groups (assembly/run_assembly.py)
DPS = 50
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def nstr(x, d=30):
    return None if x is None else mp.nstr(x, d)


def semi_analytic_W(dps):
    prev = mp.mp.dps
    import validate_low_order as V          # (its import sets the global mpmath precision: restored below)
    old = V.DPS
    try:
        V.DPS = dps
        mp.mp.dps = dps
        c31 = V.three_kink_single_log(0, 3)[0]
        return +(c31 / 6 + 4)
    finally:
        V.DPS = old
        mp.mp.dps = prev


def own_extended_data():
    """every raw coefficient our engine has computed (production all logs, poles1, kplus1, validation runs),
    for the status of the new C8 scalars only (never an input of B_old)"""
    import common as CM
    d, _ = CM.extended_input(1, with_validation=True, with_poles=True)
    have = {L.canonical_raw_name(k) for k in d["scalars"]}
    kp = L.load_inputs(CM.KPLUS1_RESULTS)["scalars"]
    have |= {L.canonical_raw_name(k) for k in kp}
    return have


def main():
    t0 = time.time()
    with mp.workdps(DPS):
        log("=" * 100)
        log("B_old (old-input part of C8 = 8 T4, eq:C8assembly) on the phase-2 production replicates")
        log("=" * 100)
        fw = L.Framework("D4", dps=DPS)
        rr = fw.from_replicates(FINAL)
        rr1 = fw.from_replicates(TIER1)
        assert rr.meta["strict"] and rr.meta["n_required"] == 116 and rr.meta["n_inputs"] == 116
        st, st1 = rr.stats["B_old8"], rr1.stats["B_old8"]
        cen = rr.central
        x = cen.get("B_old8")
        # sector-pooled
        import pooled_errors as PE
        inp, _ = fw._parse(FINAL, "raw", None, None, None)
        grad = PE.input_gradient(x, inp)
        jobs = PE.final_jobs(PROD, TOPUP, REPLACED)
        r_stat, p_stat, per_job = PE.pooled_projection(jobs, grad)
        floor = st["sigma_extra"]
        s_pool = mp.sqrt(mp.mpf(p_stat) ** 2 + floor ** 2)
        s_cov, s_rep = st["sigma_linear"], st["sigma_rep_total"]
        quoted = max(s_cov, s_rep, s_pool)
        # tier 1 vs final (difference only through the four replaced groups, independent seeds)
        inp1, _ = fw._parse(TIER1, "raw", None, None, None)

        def repl(ii):
            out = set()
            for nm in ii.values:
                pref = nm.split("[")[0]
                if (pref if "_" in pref else pref + "_base") in REPLACED:
                    out.add(nm)
            return out
        rf, r1n = repl(inp), repl(inp1)
        emf = inp.errmodel.restricted(keep_sig=rf, keep_blocks=rf, keep_reps=rf)
        em1 = inp1.errmodel.restricted(keep_sig=r1n, keep_blocks=r1n, keep_reps=r1n)
        x1 = rr1.central.get("B_old8")
        sd = mp.sqrt(emf.variance(x.g) + em1.variance(x1.g))
        log(f"  B_old = {nstr(st['value'], 25)}   (replicate mean {nstr(st['rep_mean'], 25)}, "
            f"nonlinearity {nstr(st['nonlinearity'], 3)})")
        log(f"  sigma_cov {nstr(s_cov, 3)}   sigma_rep {nstr(s_rep, 3)} (R = {st['n_rep']}, 5 dof)   "
            f"sigma_pool {nstr(s_pool, 3)}   floor {nstr(floor, 3)}   ->  quoted sigma {nstr(quoted, 3)}")
        log(f"  tier 1 alone: {nstr(st1['value'], 20)};  final - tier1 = {nstr(x.v - x1.v, 3)} "
            f"+- {nstr(sd, 3)} (pull {nstr((x.v - x1.v) / sd, 3)})")
        log("  largest sector-pooled job contributions: "
            + ", ".join(f"{j['job']} {j['pool']:.2e}" for j in per_job[:6]))
        # beta-level gradient of B_old at our point and the error budget by input (linear, own covariance)
        bgrad = {}
        bres = L.Framework("D4", dps=DPS).from_beta({nm: cen.beta[nm].v for nm in L.BETA_NAMES_D4})
        for nm, gv in bres.c8["B_old8"].g.items():
            bgrad[nm] = gv
        contrib = {}
        for nm in L.BETA_NAMES_D4:
            sb = cen.beta[nm].sigma(cen.sig)
            contrib[nm] = abs(bgrad.get(nm, 0)) * sb
        top = sorted(contrib.items(), key=lambda kv: -kv[1])[:8]
        log("  |dB_old/d beta| * sigma(beta) (largest): " + ", ".join(f"{k} {mp.nstr(v, 2)}" for k, v in top))
        # ------------------------------------------------------------------ partial C8
        log("=" * 100)
        log("partial C8 with our own data: B_old + 4 W (W semi-analytic); the other nine new inputs MISSING")
        log("=" * 100)
        W40, W50 = semi_analytic_W(40), semi_analytic_W(50)
        W = W50
        log(f"  W (three-kink boundary integral, framework) = {nstr(W, 40)}   (40 vs 50 digits: "
            f"{nstr(W50 - W40, 3)})")
        comb = L.c8_combine(rr, {"W": [mp.nstr(W, 45), "1e-38"]}, dps=DPS)
        cp = comb["parts"]["C8_partial"]
        log(f"  C8_partial = B_old + 4 W = {nstr(cp['value'], 25)} +- {nstr(max(cp['sigma_linear'], cp['sigma_rep_total']), 3)}"
            f"   (missing terms, NOT included: {comb['partial_missing']})")
        for k in ("B_done8", "C8_asm"):
            log(f"  {k}: MISSING (needs {', '.join(sorted({m.split(' ')[0].strip('<') for m in comb['parts'][k]['missing']}))})")
        # ------------------------------------------------------------------ status of the new inputs
        fw8 = L.Framework("C8", dps=30)
        need8 = fw8.required_inputs()
        old_req = set(fw.required_names())
        have = own_extended_data()
        status = {}
        log("  what each new input still needs (raw scalars beyond the 116 production ones):")
        for nm in L.C8_LINEAR:
            req = need8[nm]
            new_req = [r for r in req if r not in old_req]
            avail = [r for r in new_req if r in have]
            lack = [r for r in new_req if r not in have]
            status[nm] = {"required": req, "n_required": len(req), "beyond_production": new_req,
                          "available_in_own_engine_runs": avail, "not_yet_computed": lack,
                          "source_now": comb["terms"][nm]["source"]}
            log(f"    {nm:7s} {len(req):3d} scalars, {len(new_req):3d} beyond production: {len(avail):3d} in our "
                f"engine runs, {len(lack):3d} not yet computed  {lack}")
        all_new = sorted({r for v in status.values() for r in v["beyond_production"]})
        lack_all = sorted({r for v in status.values() for r in v["not_yet_computed"]})
        log(f"  all ten: {len(all_new)} raw scalars beyond production, {len(lack_all)} not yet computed by our engine")
        out = {
            "generated_by": "framework/c8_production.py", "date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "archive_free": True,
            "inputs": {"final": {"path": os.path.relpath(FINAL, ROOT), "sha256": sha256(FINAL)},
                       "tier1": {"path": os.path.relpath(TIER1, ROOT), "sha256": sha256(TIER1)}},
            "B_old": {"value": nstr(st["value"]), "rep_mean": nstr(st["rep_mean"]),
                      "sigma_cov": nstr(s_cov, 4), "sigma_rep": nstr(s_rep, 4), "rep_se_stat": nstr(st["rep_se"], 4),
                      "sigma_pool": nstr(s_pool, 4), "sigma_pool_stat": p_stat, "sigma_floor": nstr(floor, 4),
                      "sigma": nstr(quoted, 4), "nonlinearity": nstr(st["nonlinearity"], 4), "n_rep": st["n_rep"],
                      "per_replicate": [nstr(v, 25) for v in rr.per_rep["B_old8"]],
                      "top_jobs_pooled": per_job[:8],
                      "tier1": {"value": nstr(st1["value"]), "final_minus_tier1": nstr(x.v - x1.v, 4),
                                "sigma_diff_replaced_groups": nstr(sd, 4), "pull": nstr((x.v - x1.v) / sd, 3)},
                      "gradient_wrt_beta_inputs": {k: nstr(v, 20) for k, v in sorted(bgrad.items())},
                      "error_budget_abs_grad_times_sigma_beta": {k: nstr(v, 3) for k, v in top}},
            "W_semi_analytic": {"value": nstr(W, 40), "diff_40_vs_50_digits": nstr(W50 - W40, 3),
                                "source": "validate_low_order.three_kink_single_log(0, 3)/6 + 4 (framework, phase 1)"},
            "C8_partial": {"value": nstr(cp["value"]), "sigma_linear": nstr(cp["sigma_linear"], 4),
                           "sigma_rep_total": nstr(cp["sigma_rep_total"], 4),
                           "definition": "B_old + 4 W", "missing_terms_not_included": comb["partial_missing"],
                           "doc": L.C8_PARTS_DOC["C8_partial"]},
            "B_done": {"status": "MISSING", "needs": [n for n in L.C8_INHERITED if n != "W"]},
            "C8": {"status": "MISSING", "needs": comb["partial_missing"]},
            "new_input_status": status,
            "n_new_raw_beyond_production": len(all_new), "new_raw_not_yet_computed": lack_all,
            "framework_warnings": rr.warnings,
        }
        path = os.path.join(OUT, "C8_production.json")
        with open(path, "w") as f:
            json.dump(out, f, indent=1, default=str)
        h = sha256(path)
        with open(path + ".sha256", "w") as f:
            f.write(f"{h}  C8_production.json  {out['date']}\n")
        log(f"  wrote out/C8_production.json  sha256 {h}  [{time.time() - t0:.0f} s]")
        with open(os.path.join(OUT, "c8_production.log"), "w") as f:
            f.write("\n".join(LOG) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
