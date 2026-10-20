#!/usr/bin/env python3
"""
run_framework.py -- command-line driver for lri_framework.py   (input formats: INPUT_FORMAT.md)

  python3 run_framework.py --required [--order D4|C8] [--out req.json]
      list the raw coefficients [eps^p l^k] the outputs need (exact two-kink sector built in)
  python3 run_framework.py --raw FILE [--raw FILE2 ...] [--format auto|flat|spec|engine|canonical]
                           [--sigmas sig.json] [--cov cov.json] [--zero NAME ...] [--allow-missing]
                           [--no-replicates] [--outputs C6,C7] [--convention derivative|taylor]
                           [--order D4|C8] [--dps 50] [--out res.json]
      FILE formats (auto-detected):
        flat       {"A5_vvd[eps^-1 l^1]": "1.234...", "Q4[eps^0 l^1]": ["value", "sigma"], ...}
        spec       {"A5_vvd": {"-1": {"0": "...", "1": "..."}}, "EA3_v": {...}, ...}
        engine     campaign results.json {"results": {...}, "replicates"?: {...}, "zeros"?: [...]}
        canonical  {"format": "lri-framework-raw/1", "scalars": {name: {"reps": [...]} | {"value", "sigma", "exact"}}}
      Several --raw files are merged (a name in two files is an error).  If any scalar carries
      replicates, the full assembly is run once per replicate (mean and replicate standard error
      are reported next to the linear propagation), unless --no-replicates.
      Replicate blocks of different files must have different ids unless --independent-files (blocks are
      renamed per file: the files come from independent runs).  Blocks with different R: the per-replicate
      assembly needs --mixed-R group (grouped by R); otherwise linear errors only.
  python3 run_framework.py --normalized norm.json ...   ({"C5_vd[l^1]": "...", ...})
  python3 run_framework.py --beta beta.json ...         ({"a": "...", "Omega": "...", ...})
C8 (--order C8; phase 3): besides C8 = 8 T4 the eq:C8assembly pieces are reported: B_old8 (also at order
D4), B_done8, C8_asm (= 8 T4, checked) and C8_partial (B_old + the available new terms; the absent ones are
listed, never zeroed).  With --allow-missing these are the partial results.  --beta-extra FILE adds
beta-level values of absent NEW inputs from an independent source ({"W": ["value", "sigma"]}).
STRICT by default: if a required input is absent the run stops (exit code 2) and lists every absent
name; absent inputs are never zeros.  --allow-missing reports MISSING outputs instead.
Prints a table (value, propagated sigma, or MISSING with the names it needs) and the differences
from the claimed closed forms of D2..D4, C3..C7 (with pulls when sigmas are known).
"""
import argparse
import hashlib
import json
import os
import sys

import mpmath as mp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lri_framework as L  # noqa: E402


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load_json(path):
    with open(path) as f:
        return json.load(f)


def print_claims(get, dps):
    """get(key) -> (value, sigma) or None"""
    _, tgt = L.closed_forms(dps)
    print("differences from the claimed closed forms (value - claim; pull = difference/sigma):")
    for key in ("D2", "T2", "D3", "T3", "D4", "C3", "C4", "C5", "C6", "C7"):
        vs = get(key)
        if vs is None:
            continue
        v, s = vs
        d = v - tgt[key]
        pull = "" if not s else f"   pull {mp.nstr(d / s, 3)}"
        print(f"  {key:3s}: {mp.nstr(d, 5):>12s}{'' if s is None else '   sigma ' + mp.nstr(s, 3)}{pull}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--required", action="store_true", help="list the required raw inputs")
    g.add_argument("--raw", action="append", help="raw-coefficient file (repeatable; merged)")
    g.add_argument("--normalized", help="normalized-coefficient file")
    g.add_argument("--beta", help="beta-input file")
    ap.add_argument("--format", default="auto", choices=["auto", "flat", "spec", "engine", "canonical"],
                    help="format of the --raw files (default: auto-detect)")
    ap.add_argument("--sigmas", help="JSON {name: sigma} (independent errors), any level")
    ap.add_argument("--cov", help='JSON {"names": [...], "matrix": [[...]]} or a list of such blocks')
    ap.add_argument("--zero", action="append", default=[],
                    help="declare a raw scalar an exact zero by hand (repeatable or comma-separated); recorded")
    ap.add_argument("--allow-missing", action="store_true",
                    help="non-strict: report outputs that need absent inputs as MISSING instead of stopping")
    ap.add_argument("--no-replicates", action="store_true",
                    help="with replicated inputs: central assembly with linear errors only")
    ap.add_argument("--independent-files", action="store_true",
                    help="the --raw files come from independent runs: rename their replicate blocks per file")
    ap.add_argument("--mixed-R", choices=["refuse", "group"], default="refuse",
                    help="replicate blocks with different R: 'group' runs the per-replicate assembly grouped by R "
                         "(default 'refuse': linear errors only)")
    ap.add_argument("--beta-extra", help="JSON {new C8 input: [value, sigma]} from an independent source, for the "
                                         "C8 pieces (only inputs the assembly lacks)")
    ap.add_argument("--outputs", help="comma-separated outputs whose inputs strict mode must check (default: all)")
    ap.add_argument("--convention", default=None, choices=["derivative", "taylor"],
                    help="input convention (default: the file's, else derivative)")
    ap.add_argument("--order", default="D4", choices=["D4", "C8"])
    ap.add_argument("--dps", type=int, default=50)
    ap.add_argument("--no-internal-two-kink", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    fw = L.Framework(a.order, dps=a.dps)
    use_int = not a.no_internal_two_kink
    if a.required:
        need = fw.required_inputs(use_internal_two_kink=use_int)
        allnames = sorted({x for v in need.values() for x in v})
        print(f"{len(allnames)} raw coefficients needed (order {a.order}); all are mandatory in strict mode")
        for o, lst in need.items():
            print(f"  {o:7s} {len(lst):4d}")
        if a.out:
            with open(a.out, "w") as f:
                json.dump({"all": allnames, "by_output": need}, f, indent=1)
        return 0
    sig = load_json(a.sigmas) if a.sigmas else None
    cov = load_json(a.cov) if a.cov else None
    outputs = [o.strip() for o in a.outputs.split(",")] if a.outputs else None
    strict = not a.allow_missing
    zeros = [z.strip() for zz in a.zero for z in zz.split(",") if z.strip()]
    files = []
    try:
        if a.raw:
            items = [L.load_inputs(path, a.format) for path in a.raw]
            files = [{"path": os.path.abspath(p), "sha256": sha256(p)} for p in a.raw]
            data = L.merge_inputs(items, zeros=zeros, independent=True if a.independent_files else None)
            for it in items:
                prod = it.get("producer") or {}
                if prod.get("complete") is False or prod.get("problems"):
                    print(f"WARNING: producer {prod.get('source')} reports an incomplete run: {prod.get('problems')}")
            blockR = {}
            for v in data["scalars"].values():
                if isinstance(v, dict) and "reps" in v:
                    blockR.setdefault(str(v.get("block", L.DEFAULT_REP_BLOCK)), set()).add(len(v["reps"]))
            Rs = sorted({R for x in blockR.values() for R in x})
            has_reps = bool(blockR)
            if has_reps and len(Rs) > 1 and not a.no_replicates and a.mixed_R == "refuse":
                print(f"NOTE: replicate blocks have different numbers of replicates {Rs}: per-replicate assembly "
                      "skipped (use --mixed-R group); linear errors with the per-block sample covariances")
            if has_reps and not a.no_replicates and (len(Rs) == 1 or a.mixed_R == "group"):
                res = fw.from_replicates(data, sigmas=sig, cov=cov, convention=a.convention,
                                         use_internal_two_kink=use_int, strict=strict, outputs=outputs,
                                         mixed_R=a.mixed_R)
            else:
                res = fw.from_raw(data, sigmas=sig, cov=cov, convention=a.convention,
                                  use_internal_two_kink=use_int, strict=strict, outputs=outputs)
        else:
            if zeros:
                ap.error("--zero applies to raw inputs only")
            path = a.normalized or a.beta
            files = [{"path": os.path.abspath(path), "sha256": sha256(path)}]
            if a.normalized:
                res = fw.from_normalized(load_json(path), sigmas=sig, cov=cov, convention=a.convention,
                                         use_internal_two_kink=use_int, strict=strict, outputs=outputs)
            else:
                res = fw.from_beta(load_json(path), sigmas=sig, cov=cov, strict=strict, outputs=outputs)
    except L.MissingInputError as e:
        print(f"ERROR (strict mode): {len(e.missing)} required {e.level} input(s) not supplied:", file=sys.stderr)
        for nm in e.missing:
            print("   ", nm, file=sys.stderr)
        print("Supply them (exact zeros explicitly), declare proved zeros with --zero NAME, or use "
              "--allow-missing to get MISSING outputs.", file=sys.stderr)
        return 2
    except L.TruncationError as e:
        print("ERROR:", e, file=sys.stderr)
        return 3
    except ValueError as e:
        if "replicate block id" in str(e):
            print("ERROR:", e, file=sys.stderr)
            return 4
        raise
    for w in res.warnings:
        print("WARNING:", w)
    with mp.workdps(a.dps):
        if isinstance(res, L.ReplicateResult):
            m = res.meta
            if m.get("replicate_groups"):
                print(f"per-replicate assembly grouped by R: {m['replicate_groups']} ({m['n_replicated']} replicated "
                      f"scalars, {m['n_fixed']} fixed); degrees of freedom: Welch-Satterthwaite per output")
            else:
                print(f"per-replicate assembly: R = {m['n_replicates']} replicates ({m['n_replicated']} replicated "
                      f"scalars, {m['n_fixed']} fixed); replicate SE has {m['dof']} degrees of freedom")
            print("  %-7s %32s %10s %32s %10s %10s" % ("output", "value (at means)", "sig_lin", "replicate mean",
                                                        "sig_rep", "nonlin"))
            for row in res.table():
                print("  %-7s %32s %10s %32s %10s %10s" % row)

            def get(key):
                st = res.stats.get(key)
                if st is None or "missing" in st:
                    return None
                return st["rep_mean"], st["sigma_rep_total"]
        else:
            for row in res.table():
                print("  %-5s %-8s %40s  %s" % row)

            def get(key):
                x = res.outputs().get(key)
                if x is None or x.is_missing:
                    return None
                return x.v, (x.sigma(res.sig) if res.sig else None)
        print_claims(get, a.dps)
        cen = res.central if isinstance(res, L.ReplicateResult) else res
        info = cen.c8_info
        comb = None
        if a.order == "C8" or a.beta_extra:
            extra = load_json(a.beta_extra) if a.beta_extra else None
            comb = L.c8_combine(res, extra, dps=a.dps)
            print("C8 pieces (eq:C8assembly; C8 = 8 T4 is the C8 row above):")
            for k, e in comb["parts"].items():
                if "missing" in e:
                    print(f"  {k:10s} MISSING (needs {', '.join(e['missing'][:6])}{' ...' if len(e['missing']) > 6 else ''})")
                    continue
                sg = e.get("sigma_rep_total", e["sigma_linear"])
                print(f"  {k:10s} {mp.nstr(e['value'], 25):>32s}  sigma {mp.nstr(max(sg, e['sigma_linear']), 3)}")
            print(f"  terms: " + ", ".join(f"{nm} {t['source']}" for nm, t in comb["terms"].items()))
            if comb["partial_missing"]:
                inc = " + ".join(f"({L.C8_LINEAR[nm]}) {nm}" for nm in comb["partial_included"]) or "(nothing)"
                print(f"  C8_partial = B_old + {inc}; missing terms NOT included (never zero): "
                      f"{', '.join(comb['partial_missing'])}")
            if "C8_asm_minus_8T4_exact_tree" in info:
                print(f"  check: C8_asm - 8 T4[exact tree data] = {mp.nstr(info['C8_asm_minus_8T4_exact_tree'], 3)} "
                      f"(gradients {mp.nstr(info['C8_asm_minus_8T4_exact_tree_gradient_max'], 3)}); "
                      f"8 T4 - 8 T4[exact tree data] = {mp.nstr(info.get('8T4_minus_8T4_exact_tree', mp.mpf(0)), 3)} "
                      f"(supplied b3(0,0), h2 off by {mp.nstr(info['tree_data_max_deviation'], 3)})")
        if a.out:
            d = res.as_dict()
            if comb is not None:
                d["C8_combined"] = json.loads(json.dumps(comb, default=lambda x: mp.nstr(x, 30) if isinstance(x, mp.mpf) else str(x)))
            d["meta"] = dict(d["meta"])
            d["meta"]["input_files"] = files
            d["meta"]["command"] = " ".join(sys.argv if argv is None else ["run_framework.py"] + list(argv))
            with open(a.out, "w") as f:
                json.dump(d, f, indent=1, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
