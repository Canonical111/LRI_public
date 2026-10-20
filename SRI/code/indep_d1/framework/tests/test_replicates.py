#!/usr/bin/env python3
"""
Regression test for the per-replicate assembly, the canonical input format and the engine adapters.
Synthetic data (random point + random replicate noise); the engine's own phase-1 pilot data are used
in [6] only through the adapter (our own numbers, no archive data).

  1. one replicate block (shared shift index): the central value equals from_raw at the means, each
     replicate's assembly equals a direct from_raw of that replicate, rep_se equals the linear sample-
     covariance propagation (the per-replicate scatter is the same linear functional), and the
     nonlinearity is negligible;
  2. sigma_extra is the linear propagation of the fixed sigmas and systematic floors only, and
     sigma_rep_total = sqrt(rep_se^2 + sigma_extra^2);
  3. several independent replicate blocks: the per-block linear variance equals the hand formula;
     with equal R the per-replicate assembly runs; with different R it is refused and from_raw gives
     the linear errors;
  4. the canonical file through the CLI (replicate table, JSON with replicate_stats);
  5. a synthetic engine v2 collect output (results/replicates/errors/structural_zeros) through
     load_engine_results gives the same assembly as the canonical file;
  6. the engine's phase-1 results.json (pilot5) through the adapter: strict mode names the 3 scalars the
     engine omits; with them declared zero (--zero) the CLI reproduces the engine's e2e numbers;
  7. malformed inputs are rejected (R mismatch inside a block, wrong mean, sigma= on a replicated scalar).
"""
import json
import os
import random
import subprocess
import sys
import tempfile

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import lri_framework as L  # noqa: E402

random.seed(314)
FAIL = []
R = 8


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def raises(f, text=""):
    try:
        f()
    except ValueError as e:
        return text in str(e)
    return False


def synthetic(need, blocks="one", Rmap=None):
    """canonical dict: A3 family fixed (sigma 1e-12, some exact); everything else replicated with
    correlated noise ~1e-6, systematic floors on the Q atoms"""
    base = {nm: mp.mpf(random.uniform(-3, 3)) for nm in need}
    scal = {}
    common = {}
    for nm in need:
        M, n, i, j, e, p, k = L.parse_raw_name(nm)
        if M == "A" and n == 3:
            scal[nm] = {"value": mp.nstr(base[nm], 40), "exact": True} if (i + j + e == 0 and p < 0) else \
                [mp.nstr(base[nm], 40), "1e-12"]
            continue
        bid = "one" if blocks == "one" else f"{M}{n}_{L.deriv_str(i, j, e)}|k={p}"
        Rb = (Rmap or {}).get(M, R)
        if bid not in common:
            common[bid] = [random.gauss(0, 1) for _ in range(Rb)]
        sc = mp.mpf("1e-6") * (1 + abs(base[nm]))
        reps = [base[nm] + sc * (random.gauss(0, 1) + 0.7 * common[bid][r]) for r in range(Rb)]
        ent = {"reps": [mp.nstr(x, 40) for x in reps], "block": bid}
        if M == "Q":
            ent["sys"] = mp.nstr(sc / 3, 10)
        scal[nm] = ent
    return {"format": L.CANONICAL_FORMAT, "convention": "derivative", "producer": {"component": "test"},
            "scalars": scal}


def main():
    mp.mp.dps = 40
    fw = L.Framework("D4", dps=40)
    need = fw.required_names()
    outs = ("C5", "C6", "C7", "D4", "Omega", "K", "J")

    print("[1] one replicate block")
    data = synthetic(need, "one")
    rr = fw.from_replicates(data)
    means = {nm: (sum(mp.mpf(x) for x in v["reps"]) / R if isinstance(v, dict) and "reps" in v else
                  (mp.mpf(v["value"]) if isinstance(v, dict) else mp.mpf(v[0]))) for nm, v in data["scalars"].items()}
    r0 = fw.from_raw(means)
    check(all(rr.stats[o]["value"] == r0.get(o).v for o in outs), "central value == from_raw at the means (exact)")
    rep2 = {nm: (mp.mpf(v["reps"][2]) if isinstance(v, dict) and "reps" in v else means[nm])
            for nm, v in data["scalars"].items()}
    d2 = fw.from_raw(rep2, track=False)
    check(all(rr.per_rep[o][2] == d2.get(o).v for o in outs), "replicate 2 == direct from_raw of replicate 2 (exact)")
    inp = L.InputSet("raw", "derivative").parse(data["scalars"])
    stat_only = inp.errmodel.restricted(keep_reps=inp.reps)
    worst_lin = max(abs(rr.stats[o]["rep_se"] / mp.sqrt(stat_only.variance(r0.get(o).g)) - 1) for o in outs)
    worst_nl = max(abs(rr.stats[o]["nonlinearity"]) / rr.stats[o]["rep_se"] for o in outs)
    check(worst_lin < 1e-4, f"rep_se == linear sample-covariance sigma (worst rel. diff {mp.nstr(worst_lin, 3)})")
    check(worst_nl < 1e-3, f"nonlinearity / rep_se <= {mp.nstr(worst_nl, 3)}")
    check(rr.meta["n_replicates"] == R and rr.meta["dof"] == R - 1, "meta: R and degrees of freedom")

    print("[2] sigma_extra and sigma_rep_total")
    ok = True
    for o in outs:
        g = r0.get(o).g
        hand = mp.sqrt(sum((g.get(k, 0) * s) ** 2 for k, s in inp.sig.items()))
        st = rr.stats[o]
        ok &= abs(st["sigma_extra"] - hand) <= mp.mpf(10) ** -25 * (1 + hand)
        ok &= abs(st["sigma_rep_total"] ** 2 - st["rep_se"] ** 2 - st["sigma_extra"] ** 2) <= mp.mpf(10) ** -25
        lin = st["sigma_linear"] ** 2
        ok &= abs(lin - stat_only.variance(g) - hand ** 2) <= mp.mpf(10) ** -20 * lin
    check(ok and len(inp.sys) > 0, f"sigma_extra = fixed sigmas + {len(inp.sys)} systematic floors; totals consistent")

    print("[3] independent replicate blocks")
    data_b = synthetic(need, "blocks")
    inpb = L.InputSet("raw", "derivative").parse(data_b["scalars"])
    rb0 = fw.from_raw(data_b)
    g = rb0.get("C7").g
    var = mp.mpf(0)
    for bid, (Rb, devs) in inpb.errmodel.rep_blocks.items():
        for r in range(Rb):
            var += sum(g.get(k, 0) * d[r] for k, d in devs.items()) ** 2 / (Rb * (Rb - 1))
    var += sum((g.get(k, 0) * s) ** 2 for k, s in inpb.sig.items())
    check(len(inpb.errmodel.rep_blocks) > 20 and abs(rb0.sigma("C7") ** 2 / var - 1) < 1e-25,
          f"{len(inpb.errmodel.rep_blocks)} blocks: sigma(C7)^2 == sum over blocks (hand formula)")
    rrb = fw.from_replicates(data_b)
    ratio = rrb.stats["C7"]["sigma_rep_total"] / rrb.stats["C7"]["sigma_linear"]
    check(0.3 < ratio < 3, f"equal R: per-replicate assembly runs; sigma_rep_total/sigma_linear = {mp.nstr(ratio, 3)} "
                           "(statistical agreement only: cross-block sample covariance)")
    data_c = synthetic(need, "blocks", {"Q": 6})
    check(raises(lambda: fw.from_replicates(data_c), "different numbers of replicates"),
          "different R across blocks: per-replicate assembly refused")
    rc = fw.from_raw(data_c)
    check(rc.sigma("C7") > 0 and rc.meta["replicates_per_block"] == [6, 8], "... and from_raw gives the linear errors")

    print("[4] canonical file through the CLI")
    tmp = tempfile.mkdtemp(prefix="fwrep_")
    fin, fout = os.path.join(tmp, "canon.json"), os.path.join(tmp, "out.json")
    json.dump(data, open(fin, "w"), default=str)
    p = subprocess.run([sys.executable, os.path.join(ROOT, "run_framework.py"), "--raw", fin, "--dps", "40",
                        "--out", fout], capture_output=True, text=True)
    ok = p.returncode == 0 and "per-replicate assembly: R = 8" in p.stdout
    if ok:
        out = json.load(open(fout))
        st = out["replicate_stats"]["C7"]
        ok = (abs(mp.mpf(st["rep_mean"]) - rr.stats["C7"]["rep_mean"]) < mp.mpf(10) ** -25
              and len(out["replicate_values"]["C7"]) == R and out["meta"]["n_replicates"] == R)
    check(ok, "CLI: replicate table printed; JSON replicate_stats/replicate_values match the module")

    print("[5] synthetic engine v2 collect output")
    res, reps, errs, zeros = {}, {}, {}, []
    names3 = ["A3[eps^-1 l^1]", "A3[eps^2 l^1]", "Z4[eps^-2 l^1]"]
    for nm, v in data["scalars"].items():
        M, n, i, j, e, p, k = L.parse_raw_name(nm)
        ds = L.deriv_str(i, j, e)
        grp = f"{M}{n}_{ds or 'base'}"
        key = f"{p},{k}"
        if nm in names3:     # engine v2 (2026-10-03): zero flag, no replicates, listed in 'zeros' by flat name
            res.setdefault(grp, {})[key] = [0.0, 0.0]
            errs.setdefault(grp, {})[key] = {"stat": 0.0, "floor": 0.0, "l1": 0.0, "block": f"{grp}|k={p}",
                                             "zero": True}
            zeros.append(nm)
            continue
        xs = v["reps"] if isinstance(v, dict) and "reps" in v else [v["value"] if isinstance(v, dict) else v[0]] * R
        xs = [str(x) for x in xs]
        m = mp.nstr(sum(mp.mpf(x) for x in xs) / R, 40)
        res.setdefault(grp, {})[key] = [m, "1e-6"]
        reps.setdefault(grp, {})[key] = xs
        ex = {"stat": "1e-6", "l1": 1.0, "block": f"{grp}|k={p}", "floor": v.get("sys", 0) if isinstance(v, dict) else 0}
        errs.setdefault(grp, {})[key] = ex
    eng = {"engine_pipeline": "v2", "floor_rel": 4e-15, "complete": True, "problems": [], "results": res,
           "replicates": reps, "errors": errs, "blocks": {}, "zeros": zeros, "costs": {}}
    can = L.load_engine_results(eng)
    # the earlier v2 draft: zeros as "group:k,j" in 'structural_zeros', no zero flag
    eng_old = json.loads(json.dumps(eng))
    eng_old.pop("zeros")
    eng_old["structural_zeros"] = []
    for g_, ks in eng_old["errors"].items():
        for k_, ex in ks.items():
            if ex.pop("zero", False):
                eng_old["structural_zeros"].append(f"{g_}:{k_}")
    can_old = L.load_engine_results(eng_old)
    check(can_old["scalars"] == can["scalars"], "earlier v2 draft layout ('structural_zeros') gives the same input")
    check(set(can["declared_zeros"]) == set(names3) and can["n_replicates"] == R and
          all(can["scalars"][z] == {"value": "0", "sigma": "0", "exact": True} for z in names3),
          "adapter: 3 structural zeros become exact zeros; R detected")
    re_ = fw.from_replicates(can)
    data0 = json.loads(json.dumps(data, default=str))
    for z in names3:
        data0["scalars"][z] = {"value": "0", "exact": True}
    rr0 = fw.from_replicates(data0)
    ok = all(abs(re_.stats[o][key] - rr0.stats[o][key]) < mp.mpf(10) ** -30 * (1 + abs(rr0.stats[o][key]))
             for o in ("C6", "C7", "K") for key in ("value", "rep_mean", "rep_se"))
    check(ok and re_.meta["n_systematic_floors"] > 0,
          "engine v2 file == canonical file with the 3 zeros (value, rep_mean, rep_se); floors carried as 'sys'")
    check(re_.meta["replicate_blocks"] > 20, f"one replicate block per (group, k): {re_.meta['replicate_blocks']} blocks")

    print("[6] the engine's phase-1 pilot5 results.json through the adapter")
    src = os.path.join(ROOT, "..", "engine", "runs", "pilot5", "results.json")
    if not os.path.exists(src):
        print("  (skipped: engine pilot5 results not present)")
    else:
        cmd = [sys.executable, os.path.join(ROOT, "run_framework.py"), "--raw", src, "--dps", "30"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        check(p.returncode == 2 and all(x in p.stderr for x in names3),
              "strict: exit 2 naming A3[eps^-1 l^1], A3[eps^2 l^1], Z4[eps^-2 l^1]")
        fout = os.path.join(tmp, "pilot5.json")
        p = subprocess.run(cmd + ["--zero", ",".join(names3), "--out", fout], capture_output=True, text=True)
        ok = p.returncode == 0
        if ok:
            o = json.load(open(fout))
            c6, s6 = mp.mpf(o["C"]["C6"]["value"]), mp.mpf(o["C"]["C6"]["sigma"])
            ok = abs(c6 - mp.mpf("-58.6670")) < 1e-3 and abs(s6 / mp.mpf("0.0019") - 1) < 0.05 and \
                o["meta"]["declared_zeros"] == names3
        check(ok, "with the 3 declared zeros: C6 = -58.6670 +- 0.0019 as in the engine's e2e pilot; zeros recorded")

    print("[7] malformed inputs")
    bad = json.loads(json.dumps(data, default=str))
    nm = next(k for k, v in bad["scalars"].items() if isinstance(v, dict) and "reps" in v)
    bad["scalars"][nm]["reps"] = bad["scalars"][nm]["reps"][:-1]
    check(raises(lambda: fw.from_replicates(bad), "replicate block"), "R mismatch inside a block")
    bad = json.loads(json.dumps(data, default=str))
    bad["scalars"][nm]["mean"] = "123.5"
    check(raises(lambda: fw.from_replicates(bad), "differs from the mean"), "inconsistent mean")
    check(raises(lambda: fw.from_replicates(data, sigmas={nm: "1e-3"}), "replicated scalar"), "sigma= on a replicated scalar")
    check(raises(lambda: fw.from_replicates({k: (v["value"] if isinstance(v, dict) and "value" in v else
                                                 (v[0] if isinstance(v, list) else v["reps"][0]))
                                             for k, v in data["scalars"].items()}), "R >= 2"),
          "from_replicates without replicates")
    print("REPLICATE TEST", "PASSED" if not FAIL else f"FAILED ({len(FAIL)})")
    return not FAIL


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
