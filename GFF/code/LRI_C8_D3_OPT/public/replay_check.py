#!/usr/bin/env python3
"""Replay of the independent C8(3) check (LRI_C8_D3_OPT, production prod1) from the shipped records.

Run from the package folder (GFF/code/LRI_C8_D3_OPT), normally through `make -f public.mk replay`.

What it does, without the native outputs (which stay on the production cluster):
  R0  integrity: SHA-256 of the result, manifest, graph statistics and allocation, and every binding between them
      and the shipped package (manifest inputs and tool pins, the result's assembly-source pins, coverage certificate);
  R1  recomputes the estimator from the means and input covariances stored in the result, per loop and sector, with
      the package's own fixed-point code (tools/rg.py: coefficients, jacobians), using the covariance propagation of
      tools/assemble.py calculate(): C0..C8, standard errors, covariance, power-free part and power correction,
      error by loop, lower-order pulls;
  R2  runs the package's own tools/assemble.py calculate() unchanged on synthetic replicate matrices whose means and
      covariances of the mean equal the stored ones (both campaigns identical), and compares its pooled outputs;
  R3  the numbers quoted by the note (rounded as quoted): C8(3), its SE, the lower-order pulls, the C6/C7 by-products;
  R4  the two campaigns: recomputed independently from the per-graph projected means in graph_statistics (linearized
      about the pooled fixed point; checked against the stored campaign coefficients), and their pull;
  R5  the comparison with the main C8(3) result (-0.40 combined standard errors);
  R6  the campaign design: 24,173 kernels per campaign, >= 4,096 points, 16 replicates, rates 0.8/0.7, group seeds
      derived from the base seed, a base seed differing from the delivered pilot's, the job count recomputed by the
      planner's rule from the allocation (1,994), 2 x 16 x sum(points) = 37,121,687,552 evaluations;
  R7  the allocation (prod1_2000.json) recomputed byte for byte by tools/allocate.py from the delivered pilot's
      graph statistics with a 2,000 core-hour budget (needs `make fetch-data`; SKIP without it, FAIL with --full);
  D   documented accounting (service units, nodes, dates): arithmetic only, from the production README.

Writes a PASS/FAIL table to stdout and to <out>/replay_report.txt and .json; exits 1 if any row FAILs.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]          # GFF/code/LRI_C8_D3_OPT
sys.path.insert(0, str(ROOT / "tools"))
sys.dont_write_bytecode = True

from io_utils import digest  # noqa: E402  (package code, unchanged)
from rg import coefficients, jacobians, load_two_loop  # noqa: E402
import assemble  # noqa: E402
from campaign import derive_seed  # noqa: E402
from allocate import allocate  # noqa: E402

LOOPS = tuple(range(3, 9))
SECTORS = ("free", "power")

# Pinned identities of the shipped records (production README and the records themselves).
SHA = {
    "result": "58de4f971f6b2330b6f109fa1f32df0778d1f7497effd3c4d085c1dd79808184",
    "manifest": "9906a8daae3016178dd9d099efed2ec04283e1452b90a8c5a5738eaf6cee28ac",
    "graph_statistics": "537258cb8d2e8ab9cfd16302a4bb5a0282aa4b52057d06bea0b555f0b1ea7bc1",
    "allocation": "fccf89698d0818b7e5eb05309ede7b0edd24387c723b477ee8501104ac48f27f",
    "pilot_statistics": "41e3a0d74865f0f05a7d55273fd6eae3a070d4c1bc67bb434a7713e1f7c5c9eb",
    "main_result": "b077625830dd4dcffd78052f06620914f27c3378e0c1e2271fac3656f3012e16",
}
# The main C8(3) production (LRI_C8_D3_HPC prod1, note Section 32.1), used when its record is not found.
MAIN_PINNED = (1602.6052229663408, 0.9516489064069612)
MAIN_CANDIDATES = (
    "../../results/C8_3/C8_result.json",                                             # GFF/results/C8_3 (public layout)
    "../LRI_C8_D3_HPC/benchmarks/symmetry_2026-10-c8/production/prod1/C8_result.json",  # package-internal copy
)
DOC_EXAMPLE_SEEDS = (6129871430538291,)   # README example seed of the package

ROWS = []


def row(rid, what, expected, got, tol, ok, note=""):
    status = ok if isinstance(ok, str) else ("PASS" if ok else "FAIL")
    ROWS.append({"id": rid, "check": what, "expected": str(expected), "replayed": str(got), "tolerance": tol,
                 "status": status, "note": note})


def rel(a, b):
    return abs(a - b) / max(abs(b), 1e-300)


def close(a, b, rtol, atol=0.0):
    return abs(a - b) <= max(rtol * abs(b), atol)


def fmt(x, nd):
    return f"{x:.{nd}f}"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text())


# --------------------------------------------------------------------------------------------------------------
def r0_integrity(res_dir, result, manifest):
    files = {
        "result": res_dir / "runs/prod1/C8_result_54838171.json",
        "manifest": res_dir / "runs/prod1/manifest.json",
        "graph_statistics": res_dir / "runs/prod1/graph_statistics_54838171.json",
        "allocation": res_dir / "allocations/prod1_2000.json",
    }
    for key, path in files.items():
        got = digest(path)
        row("R0", f"sha256 {path.relative_to(res_dir)}", SHA[key][:16], got[:16], "exact", got == SHA[key])
    row("R0", "result.manifest_sha256 = sha256(manifest.json)", result["manifest_sha256"][:16],
        digest(files["manifest"])[:16], "exact", result["manifest_sha256"] == digest(files["manifest"]))
    row("R0", "manifest.allocation_source.sha256 = sha256(prod1_2000.json)",
        manifest["allocation_source"]["sha256"][:16], digest(files["allocation"])[:16], "exact",
        manifest["allocation_source"]["sha256"] == digest(files["allocation"]))
    for name, expected in manifest["inputs"].items():
        got = digest(ROOT / "inputs" / name)
        row("R0", f"manifest input inputs/{name}", expected[:16], got[:16], "exact", got == expected)
    row("R0", "result.two_loop_sha256 = manifest input two_loop.json", result["two_loop_sha256"][:16],
        manifest["inputs"]["two_loop.json"][:16], "exact",
        result["two_loop_sha256"] == manifest["inputs"]["two_loop.json"])
    coverage = load_json(ROOT / "inputs/coverage.json")
    row("R0", "coverage.json complete and bound to inventory.json", "True, " + manifest["inputs"]["inventory.json"][:16],
        f"{coverage.get('complete')}, {coverage.get('inventory_sha256', '')[:16]}", "exact",
        coverage.get("complete") is True and coverage.get("inventory_sha256") == manifest["inputs"]["inventory.json"])
    for name, expected in manifest["tools"].items():
        got = digest(ROOT / "tools" / name)
        row("R0", f"manifest tool pin tools/{name}", expected[:16], got[:16], "exact", got == expected)
    for name, expected in result["assembly_sources"].items():
        got = digest(ROOT / "tools" / name)
        row("R0", f"result assembly pin tools/{name}", expected[:16], got[:16], "exact", got == expected)
    row("R0", "result purpose / coverage / jobs assembled", "production, True, 1994",
        f"{result['purpose']}, {result['complete_graph_coverage']}, {result['streaming_assembly']['jobs']}", "exact",
        result["purpose"] == "production" and result["complete_graph_coverage"] is True
        and result["streaming_assembly"]["jobs"] == len(manifest["jobs"]) == 1994)


# --------------------------------------------------------------------------------------------------------------
def stored_inputs(result):
    means = {s: {L: np.asarray(result["means"][s][str(L)], dtype=float) for L in LOOPS} for s in SECTORS}
    vc = {s: {L: np.asarray(result["input_covariances"][s][str(L)], dtype=float) for L in LOOPS} for s in SECTORS}
    return means, vc


def r1_direct(result, means, vc, b2):
    """The covariance propagation of assemble.calculate(), applied to the stored means and covariances."""
    full_means = {L: means["free"][L] + means["power"][L] for L in LOOPS}
    full = coefficients(full_means, b2)
    free = coefficients(means["free"], b2)
    power = full - free
    J = jacobians(full_means, b2)
    Jf = jacobians(means["free"], b2)
    Jd = {L: J[L] - Jf[L] for L in LOOPS}
    contrib = {s: {L: J[L] @ vc[s][L] @ J[L].T for L in LOOPS} for s in SECTORS}
    cov = sum(v for block in contrib.values() for v in block.values())
    covf = sum(Jf[L] @ vc["free"][L] @ Jf[L].T for L in LOOPS)
    covd = sum(Jd[L] @ vc["free"][L] @ Jd[L].T + contrib["power"][L] for L in LOOPS)
    cross = sum(Jf[L] @ vc["free"][L] @ Jd[L].T for L in LOOPS)
    ident = np.allclose(cov, covf + covd + cross + cross.T, rtol=2e-9, atol=1e-7)
    se = np.sqrt(np.maximum(0, np.diag(cov)))
    out = {
        "full": full, "free": free, "power": power, "se": se, "cov": cov, "J": J,
        "pf_se": math.sqrt(max(0, covf[8, 8])), "pc_se": math.sqrt(max(0, covd[8, 8])), "cross": cross[8, 8],
        "pd_err": np.sqrt(np.maximum(0, np.diag(covd))),
        "ebl": {L: {s: math.sqrt(max(0, contrib[s][L][8, 8])) for s in SECTORS} for L in LOOPS},
    }
    T_EST, T_SE = 1e-12, 1e-10
    row("R1", "C8(3) estimator from stored means (rg.coefficients)", repr(result["C8_estimate"]), repr(float(full[8])),
        f"rel {T_EST:g}", close(full[8], result["C8_estimate"], T_EST))
    row("R1", "C8(3) sampling SE (Jacobian covariance propagation)", repr(result["sampling_standard_error"]),
        repr(float(se[8])), f"rel {T_SE:g}", close(se[8], result["sampling_standard_error"], T_SE))
    worst = max(abs(a - b) / max(abs(b), 1.0) for a, b in zip(full, result["coefficients"]))
    row("R1", "C0..C8 coefficients", "record", f"max rel diff {worst:.1e}", f"rel {T_EST:g}", worst <= T_EST)
    worst = max(abs(a - b) / b if b else abs(a) for a, b in zip(se, result["standard_errors"]))
    row("R1", "standard errors of C0..C8", "record", f"max rel diff {worst:.1e}", f"rel {T_SE:g} (abs 1e-15 at 0)",
        all(close(a, b, T_SE, 1e-15) for a, b in zip(se, result["standard_errors"])))
    rc = np.asarray(result["covariance"])
    worst = float(np.max(np.abs(out["cov"] - rc)) / np.max(np.abs(rc)))
    row("R1", "covariance matrix of C0..C8", "record", f"max diff / max entry {worst:.1e}", f"{T_SE:g}", worst <= T_SE)
    row("R1", "covariance identity full = free + correction + cross terms", "holds", str(ident),
        "assemble.py's own test", ident)
    row("R1", "power-free C8", repr(result["power_free_C8"]), repr(float(free[8])), f"rel {T_EST:g}",
        close(free[8], result["power_free_C8"], T_EST))
    row("R1", "power-free SE", repr(result["power_free_se"]), repr(out["pf_se"]), f"rel {T_SE:g}",
        close(out["pf_se"], result["power_free_se"], T_SE))
    row("R1", "power correction", repr(result["power_correction"]), repr(float(power[8])), f"abs {T_EST * 1600:g}",
        close(power[8], result["power_correction"], 0, T_EST * 1600))
    row("R1", "power-correction SE", repr(result["power_correction_se"]), repr(out["pc_se"]), f"rel {T_SE:g}",
        close(out["pc_se"], result["power_correction_se"], T_SE))
    row("R1", "power-free/correction covariance", repr(result["power_free_correction_covariance"]),
        repr(float(out["cross"])), "rel 1e-8", close(out["cross"], result["power_free_correction_covariance"], 1e-8))
    worst = max(abs(out["ebl"][L][s] / result["error_by_loop"][str(L)][s] - 1) for L in LOOPS for s in SECTORS)
    row("R1", "error by loop and sector (12 entries)", "record", f"max rel diff {worst:.1e}", f"rel {T_SE:g}",
        worst <= T_SE)
    worst = max(abs(a - b) for a, b in zip(power, result["power_differences"]))
    row("R1", "power differences C0..C8", "record", f"max abs diff {worst:.1e}", "abs 1e-9", worst <= 1e-9)
    ok = all(close(a, b, 1e-8, 1e-15) for a, b in zip(out["pd_err"], result["power_difference_errors"]))
    row("R1", "power-difference errors C0..C8", "record", "see tolerance", "rel 1e-8 (abs 1e-15)", ok)
    pulls = {}
    for chk in result["lower_order_checks"]:
        n = chk["order"]
        ref, ref_se = assemble.REFERENCES[n]
        pull = float((full[n] - ref) / np.hypot(se[n], ref_se))
        pulls[n] = pull
        row("R1", f"lower-order pull C{n} vs package reference", f"{chk['pull']:.12f}", f"{pull:.12f}", "abs 1e-9",
            abs(pull - chk["pull"]) <= 1e-9 and ref == chk["reference"] and ref_se == chk["reference_se"])
    out["pulls"] = pulls
    return out


# --------------------------------------------------------------------------------------------------------------
def helmert(R):
    """R x (R-1) orthonormal columns, each orthogonal to the vector of ones."""
    H = np.zeros((R, R - 1))
    for k in range(1, R):
        H[:k, k - 1] = 1.0
        H[k, k - 1] = -k
        H[:, k - 1] /= math.sqrt(k * (k + 1))
    return H


def r2_package_calculate(result, means, vc, b2, R=16):
    """assemble.calculate() itself, on replicate matrices with exactly the stored first and second moments."""
    H = helmert(R)
    arrays = {s: {t: {} for t in ("a", "b")} for s in SECTORS}
    for s in SECTORS:
        for L in LOOPS:
            m, V = means[s][L], vc[s][L]
            w, U = np.linalg.eigh((V + V.T) / 2)
            # each campaign: covariance of its mean = 2V, i.e. sample covariance 2 R V; pooled /4 over two gives V
            S = U * np.sqrt(np.clip(w, 0, None) * 2 * R)
            Z = math.sqrt(R - 1) * H[:, :len(m)] @ S.T
            for t in ("a", "b"):
                arrays[s][t][L] = m + Z
    calc, _ = assemble.calculate(arrays, b2, bootstrap=0)
    row("R2", "assemble.calculate(): C8(3)", repr(result["C8_estimate"]), repr(calc["C8_estimate"]), "rel 1e-11",
        close(calc["C8_estimate"], result["C8_estimate"], 1e-11))
    row("R2", "assemble.calculate(): SE", repr(result["sampling_standard_error"]),
        repr(calc["sampling_standard_error"]), "rel 1e-8",
        close(calc["sampling_standard_error"], result["sampling_standard_error"], 1e-8))
    ok = all(close(a, b, 1e-11, 1e-12) for a, b in zip(calc["coefficients"], result["coefficients"]))
    row("R2", "assemble.calculate(): C0..C8", "record", "see tolerance", "rel 1e-11", ok)
    ok = all(close(a, b, 1e-8, 1e-15) for a, b in zip(calc["standard_errors"], result["standard_errors"]))
    row("R2", "assemble.calculate(): SEs of C0..C8", "record", "see tolerance", "rel 1e-8 (abs 1e-15)", ok,
        "moment-matched synthetic replicates; covariance rebuilt by an eigen-decomposition")
    for key in ("power_free_C8", "power_correction"):
        row("R2", f"assemble.calculate(): {key}", repr(result[key]), repr(calc[key]), "abs 1e-8",
            close(calc[key], result[key], 0, 1e-8))
    for key in ("power_free_se", "power_correction_se"):
        row("R2", f"assemble.calculate(): {key}", repr(result[key]), repr(calc[key]), "rel 1e-8",
            close(calc[key], result[key], 1e-8))
    worst = max(abs(a["pull"] - b["pull"]) for a, b in zip(calc["lower_order_checks"], result["lower_order_checks"]))
    row("R2", "assemble.calculate(): lower-order pulls C3..C7", "record", f"max abs diff {worst:.1e}", "abs 1e-7",
        worst <= 1e-7)
    worst = max(abs(calc["error_by_loop"][str(L)][s] / result["error_by_loop"][str(L)][s] - 1)
                for L in LOOPS for s in SECTORS)
    row("R2", "assemble.calculate(): error by loop", "record", f"max rel diff {worst:.1e}", "rel 1e-7", worst <= 1e-7)


# --------------------------------------------------------------------------------------------------------------
def r3_quoted(result, d):
    c8, se = float(d["full"][8]), float(d["se"][8])
    row("R3", "note: C8(3) = 1600.98 +- 3.97 (sampling SE)", "1600.98 +- 3.97", f"{fmt(c8, 2)} +- {fmt(se, 2)}",
        "2 decimals", fmt(c8, 2) == "1600.98" and fmt(se, 2) == "3.97")
    worst = max(abs(p) for p in d["pulls"].values())
    row("R3", "note: lower orders within 1.73 SE (max |pull| over C3..C7)", "1.73", fmt(worst, 2), "2 decimals",
        fmt(worst, 2) == "1.73" and worst < 3)
    quoted = {3: "-1.41", 4: "-1.55", 5: "-0.10", 6: "1.73", 7: "-0.21"}
    got = {n: fmt(d["pulls"][n], 2) for n in quoted}
    row("R3", "README: pulls C3..C7", ", ".join(quoted.values()), ", ".join(got.values()), "2 decimals", got == quoted)
    c6, s6, c7, s7 = float(d["full"][6]), float(d["se"][6]), float(d["full"][7]), float(d["se"][7])
    row("R3", "note: C6 by-product 33.599 +- 0.014", "33.599 +- 0.014", f"{fmt(c6, 3)} +- {fmt(s6, 3)}", "3 decimals",
        fmt(c6, 3) == "33.599" and fmt(s6, 3) == "0.014")
    row("R3", "note: C7 by-product -220.40 +- 0.19", "-220.40 +- 0.19", f"{fmt(c7, 2)} +- {fmt(s7, 2)}", "2 decimals",
        fmt(c7, 2) == "-220.40" and fmt(s7, 2) == "0.19")
    pf, pfs, pc, pcs = float(d["free"][8]), d["pf_se"], float(d["power"][8]), d["pc_se"]
    row("R3", "README: power-free 1602.61 +- 2.96, correction -1.63 +- 2.64", "1602.61 +- 2.96, -1.63 +- 2.64",
        f"{fmt(pf, 2)} +- {fmt(pfs, 2)}, {fmt(pc, 2)} +- {fmt(pcs, 2)}", "2 decimals",
        (fmt(pf, 2), fmt(pfs, 2), fmt(pc, 2), fmt(pcs, 2)) == ("1602.61", "2.96", "-1.63", "2.64"))
    row("R3", "result flags", "reportable_precision_established False, empirical_allowance None",
        f"{result['reportable_precision_established']}, {result['empirical_allowance']}", "exact",
        result["reportable_precision_established"] is False and result["empirical_allowance"] is None,
        "the package assigns no allowance; the note quotes the sampling SE only")


# --------------------------------------------------------------------------------------------------------------
def r4_campaigns(result, d, gstats, means):
    J = d["J"]
    proj = {"a": 0.0, "b": 0.0}
    for s in SECTORS:
        for L in LOOPS:
            for graph in gstats[s][str(L)].values():
                for t in ("a", "b"):
                    proj[t] += graph[t]["projected_mean"]
    pooled = sum(float(J[L][8] @ means[s][L]) for s in SECTORS for L in LOOPS)
    row("R4", "graph statistics: (P_a + P_b)/2 = sum_L J_L[8] . pooled means", f"{pooled:.9f}",
        f"{(proj['a'] + proj['b']) / 2:.9f}", "abs 1e-8", abs((proj["a"] + proj["b"]) / 2 - pooled) <= 1e-8,
        "ties the per-graph projections to the stored means")
    c8 = float(d["full"][8])
    lin = {"a": c8 + (proj["a"] - proj["b"]) / 2, "b": c8 - (proj["a"] - proj["b"]) / 2}
    ind = result["individual_campaigns"]
    for t in ("a", "b"):
        stored = ind[t]["coefficients"][8]
        row("R4", f"campaign {t}: linearized from graph statistics vs stored coefficient", f"{stored:.6f}",
            f"{lin[t]:.6f}", "abs 1e-4", abs(lin[t] - stored) <= 1e-4,
            "first order about the pooled fixed point; loops 5-8 enter affinely at order 8")
    qa = f"{fmt(ind['a']['coefficients'][8], 2)} +- {fmt(ind['a']['standard_errors'][8], 2)}"
    qb = f"{fmt(ind['b']['coefficients'][8], 2)} +- {fmt(ind['b']['standard_errors'][8], 2)}"
    row("R4", "note: campaigns 1603.53 +- 4.91 and 1598.42 +- 6.24", "1603.53 +- 4.91; 1598.42 +- 6.24",
        f"{qa}; {qb}", "2 decimals", (qa, qb) == ("1603.53 +- 4.91", "1598.42 +- 6.24"),
        "values replayed above; campaign SEs are stored (they need the replicate matrices)")
    ab_se = math.hypot(ind["a"]["standard_errors"][8], ind["b"]["standard_errors"][8])
    pull = (ind["a"]["coefficients"][8] - ind["b"]["coefficients"][8]) / ab_se
    row("R4", "note: campaign difference 0.64 combined SE (assemble.py formula)", "0.64", fmt(pull, 2), "2 decimals",
        fmt(pull, 2) == "0.64" and abs(pull - result["campaign_difference_pull"]) <= 1e-12)
    hs = [h[8] for h in result["half_streams"]]
    row("R4", "README: half streams 1599.79 and 1602.17 (stored)", "1599.79, 1602.17",
        f"{fmt(hs[0], 2)}, {fmt(hs[1], 2)}", "2 decimals", [fmt(x, 2) for x in hs] == ["1599.79", "1602.17"],
        "record lookup only: half streams need the replicate matrices")


# --------------------------------------------------------------------------------------------------------------
def r5_main(c8, se, main_arg):
    path, used = None, None
    candidates = [main_arg] if main_arg else [ROOT / p for p in MAIN_CANDIDATES]
    for p in candidates:
        if p and Path(p).exists():
            path = Path(p)
            break
    if path is not None:
        got = digest(path)
        rec = load_json(path)
        main = (rec["C8_full"], rec["sampling_standard_error"])
        shown = os.path.relpath(path.resolve(), (ROOT / "../..").resolve())
        row("R5", f"main C8(3) record sha256 ({shown})", SHA["main_result"][:16], got[:16], "exact",
            got == SHA["main_result"])
        row("R5", "main C8(3) record = note Section 32.1 values", f"{MAIN_PINNED[0]!r} +- {MAIN_PINNED[1]!r}",
            f"{main[0]!r} +- {main[1]!r}", "exact", main == MAIN_PINNED)
        used = "record"
    else:
        main = MAIN_PINNED
        used = "pinned constants (main record not found; pass --main-result)"
        row("R5", "main C8(3) record (GFF/results/C8_3/C8_result.json)", SHA["main_result"][:16], "not found", "-",
            "SKIP", "the difference below uses the note's values 1602.6052229663408 +- 0.9516489064069612")
    pull = (c8 - main[0]) / math.hypot(se, main[1])
    row("R5", "note: difference from the main estimator, combined SE", "-0.40", fmt(pull, 2), "2 decimals",
        fmt(pull, 2) == "-0.40", f"main value from {used}; \\CeightThreeIndepPull = 0.40")


# --------------------------------------------------------------------------------------------------------------
def r6_design(result, manifest, gstats, allocation):
    inventory = load_json(ROOT / "inputs/inventory.json")
    pilot = load_json(ROOT / "inputs/pilot_design.json")
    groups = {g["name"]: g for g in manifest["groups"]}
    per_campaign = {t: sum(len(g["graphs"]) for g in groups.values() if g["campaign"] == t) for t in ("a", "b")}
    inv_count = sum(len(inventory[s][str(L)]) for s in SECTORS for L in LOOPS)
    row("R6", "note: 24,173 kernels per campaign (manifest groups = inventory)", "24173, 24173, 24173",
        f"{per_campaign['a']}, {per_campaign['b']}, {inv_count}", "exact",
        per_campaign["a"] == per_campaign["b"] == inv_count == 24173)
    hashes_ok = all(manifest["graph_hashes"].get(f"{s}/L{L}/G{r['id']}.txt") == r["sha256"]
                    for s in SECTORS for L in LOOPS for r in inventory[s][str(L)])
    row("R6", "manifest graph hashes = inventory payload hashes", "24173 equal",
        f"{len(manifest['graph_hashes'])} entries, all equal: {hashes_ok}", "exact",
        hashes_ok and len(manifest["graph_hashes"]) == inv_count)
    alloc_ok = all(int(allocation[g["sector"]][str(g["L"])][str(r["id"])]) == r["points"]
                   for g in groups.values() for r in g["graphs"])
    min_points = min(r["points"] for g in groups.values() for r in g["graphs"])
    row("R6", "note: >= 4,096 points per graph; manifest points = allocation", "4096, True",
        f"{min_points}, {alloc_ok}", "exact", min_points == 4096 and alloc_ok)
    row("R6", "note: 16 replicates per campaign", "16", str(manifest["replicates"]), "exact",
        manifest["replicates"] == result["replicates_per_campaign"] == 16)
    rates = sorted({(g["campaign"], g["rate"], g["bits"]) for g in groups.values()})
    row("R6", "note: sampler rates 0.8 (a) and 0.7 (b)", "[('a', 0.8, 52), ('b', 0.7, 60)]", str(rates), "exact",
        rates == [("a", 0.8, 52), ("b", 0.7, 60)])
    seeds_ok = all(g["seeds"][role] == derive_seed(manifest["base_seed"], g["campaign"], g["sector"], g["L"], role)
                   for g in groups.values() for role in ("net", "shift"))
    row("R6", "group seeds derived from the base seed (campaign.derive_seed)", "48 equal", str(seeds_ok), "exact",
        seeds_ok)
    fresh = manifest["base_seed"] not in (pilot["seed"], *DOC_EXAMPLE_SEEDS)
    row("R6", "note: fresh base seed (differs from the delivered pilot and documented examples)",
        f"!= {pilot['seed']}", str(manifest["base_seed"]), "exact", fresh)
    # The planner's job rule (tools/campaign.py plan): per group, blocks of graph_block graphs in id order, one job per
    # chunk_points interval of the block's largest net.
    jobs = 0
    for g in manifest["groups"]:
        rows = sorted(g["graphs"], key=lambda r: r["id"])
        for off in range(0, len(rows), manifest["graph_block"]):
            block = rows[off:off + manifest["graph_block"]]
            jobs += math.ceil(max(r["points"] for r in block) / manifest["chunk_points"])
    row("R6", "note: 1,994 jobs (planner rule on the allocation; manifest; assembly)", "1994",
        f"{jobs}, {len(manifest['jobs'])}, {result['streaming_assembly']['jobs']}", "exact",
        jobs == len(manifest["jobs"]) == result["streaming_assembly"]["jobs"] == 1994)
    ev = 2 * manifest["replicates"] * sum(r["points"] for g in groups.values() if g["campaign"] == "a"
                                          for r in g["graphs"])
    ev_stats = sum(graph[t]["points"] for s in SECTORS for L in LOOPS for graph in gstats[s][str(L)].values()
                   for t in ("a", "b"))
    row("R6", "note: 3.7e10 evaluations = 2 x 16 x sum(points)", "37121687552 (3.7e10)",
        f"{ev}, {manifest['evaluations']}, {result['evaluations']}, {ev_stats}", "exact",
        ev == manifest["evaluations"] == result["evaluations"] == ev_stats == 37121687552 and f"{ev:.1e}" == "3.7e+10")
    desc = manifest["executable"]["description"]
    row("R6", "worker build recorded in the plan", "gmp350, GCC 13.3.0, order 8, d 3",
        f"{desc['mp_backend']}, GCC {desc['compiler']}, order {desc['order']}, d {desc['dimension']}", "exact",
        (desc["mp_backend"], desc["compiler"], desc["order"], desc["dimension"]) == ("gmp350", "13.3.0", 8, 3))


# --------------------------------------------------------------------------------------------------------------
def r7_allocation(pilot_path, manifest, full):
    if pilot_path is None or not Path(pilot_path).exists():
        row("R7", "note: allocation of about 2,000 core-hours (allocate.py on the pilot statistics)", "fccf8969...",
            "pilot statistics absent", "-", "FAIL" if full else "SKIP",
            "run `make -f public.mk fetch-data` (pilot bundle) and `make -f public.mk replay-full`")
        return
    got = digest(pilot_path)
    row("R7", "sha256 pilot graph_statistics.json (bound by the dispatch index)", SHA["pilot_statistics"][:16],
        got[:16], "exact", got == SHA["pilot_statistics"])
    data = load_json(pilot_path)
    inventory = load_json(ROOT / "inputs/inventory.json")
    cover = all(set(data[s][L]) == {str(r["id"]) for r in inventory[s][L]} for s in inventory for L in inventory[s])
    alloc, report = allocate(data, 2000.0, 16, 4096)
    text = json.dumps(alloc, indent=2, allow_nan=False) + "\n"          # io_utils.save() byte format
    h = sha_bytes(text.encode())
    row("R7", "allocate.py --core-hours 2000 --replicates 16 reproduces prod1_2000.json", SHA["allocation"][:16],
        h[:16], "exact (bytes)", cover and h == SHA["allocation"] == manifest["allocation_source"]["sha256"])
    row("R7", "note: about 2,000 core-hours of the development host (allocate.py estimate)", "about 2000",
        f"{report['estimated_core_hours']:.2f}", "rounds to 2000",
        round(report["estimated_core_hours"]) == 2000 and report["kernel_evaluations"] == 37121687552)


def d_accounting():
    # Production README, Cost: lanes job 6 compute nodes x 45,814 s (sacct elapsed 12:43:34); tail lanes 0.19 node-h
    # (11:31 on one node); shared plan, index and assembly jobs about 0.11 node-h. Expanse: 128 SU per node-hour.
    lanes = 6 * 45814 / 3600
    total = lanes + 0.19 + 0.11
    su = total * 128
    row("D", "note: about 9,800 service units (documented accounting, arithmetic only)", "about 9800",
        f"{lanes:.2f} + 0.19 + 0.11 node-h = {total:.2f} node-h = {su:.0f} SU", "rounds to 9800",
        round(su, -2) == 9800, "inputs from results/C8_3_check/README.md (Slurm accounting); not recomputable")
    row("D", "note: six whole AMD EPYC 7742 nodes on 10 and 11 October 2026", "documented", "documented", "-", "DOC",
        "README (lanes job 54823471: 6 nodes x 16 lanes x 8 threads; manifest created 2026-10-10T21:00:28Z)")


# --------------------------------------------------------------------------------------------------------------
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--results", type=Path, default=ROOT / "../../results/C8_3_check")
    p.add_argument("--main-result", type=Path, help="the main C8(3) production C8_result.json (LRI_C8_D3_HPC prod1)")
    p.add_argument("--pilot-statistics", type=Path, default=ROOT / "results/pilot_20261008/graph_statistics.json")
    p.add_argument("--full", action="store_true", help="the allocation replay R7 is required (FAIL instead of SKIP)")
    p.add_argument("--out", type=Path, default=ROOT / ".work/replay")
    a = p.parse_args()
    res_dir = a.results.resolve()
    result = load_json(res_dir / "runs/prod1/C8_result_54838171.json")
    manifest = load_json(res_dir / "runs/prod1/manifest.json")
    gstats = load_json(res_dir / "runs/prod1/graph_statistics_54838171.json")
    allocation = load_json(res_dir / "allocations/prod1_2000.json")
    b2 = load_two_loop()
    means, vc = stored_inputs(result)

    r0_integrity(res_dir, result, manifest)
    d = r1_direct(result, means, vc, b2)
    r2_package_calculate(result, means, vc, b2)
    r3_quoted(result, d)
    r4_campaigns(result, d, gstats, means)
    r5_main(float(d["full"][8]), float(d["se"][8]), a.main_result)
    r6_design(result, manifest, gstats, allocation)
    r7_allocation(a.pilot_statistics, manifest, a.full)
    d_accounting()

    buf = io.StringIO()
    width = max(len(r["check"]) for r in ROWS)
    shown = os.path.relpath(res_dir, (ROOT / "../..").resolve())
    print(f"Replay of the independent C8(3) check (LRI_C8_D3_OPT prod1); records in GFF/{shown}", file=buf)
    print(f"{'id':3s} {'status':6s} {'check':{width}s} | expected | replayed | tolerance", file=buf)
    for r in ROWS:
        print(f"{r['id']:3s} {r['status']:6s} {r['check']:{width}s} | {r['expected']} | {r['replayed']} | "
              f"{r['tolerance']}" + (f"   [{r['note']}]" if r["note"] else ""), file=buf)
    counts = {s: sum(r["status"] == s for r in ROWS) for s in ("PASS", "FAIL", "SKIP", "DOC")}
    verdict = "FAIL" if counts["FAIL"] else "PASS"
    print(f"SUMMARY: {verdict}  ({counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['SKIP']} SKIP, "
          f"{counts['DOC']} DOC)", file=buf)
    text = buf.getvalue()
    print(text, end="")
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "replay_report.txt").write_text(text)
    (a.out / "replay_report.json").write_text(json.dumps({"verdict": verdict, "counts": counts, "rows": ROWS},
                                                         indent=2) + "\n")
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
