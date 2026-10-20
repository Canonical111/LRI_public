#!/usr/bin/env python3
"""Replay the integrity of the d = 2 eighth-order production records (no solver run).

Run from HT_Pert/code/lri_d2_coeff_hpc (make -f public.mk replay). Inputs, relative to that folder:
  src/lri_coeff/*.py, *.cpp                         the solver (its source digest)
  reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv   (cited by HT/data/HT_2d/pert_crosscheck)
  ../../data/HT_2d/prod/<campaign>/d8/*.json       the 41 lri-coeff-v1 records (self-hashed)
  ../../data/HT_2d/prod/<campaign>/coefficients.csv, campaign.json, validation receipts
Checks (names p2.prod.*, as in results_map.md): record and campaign-manifest self-hashes, solver source digest = the records' source_digest,
tables = records, sha256 of the two tables cited by HT, the cutoff range (\\HTpTwoLprod = 34), the validation receipts.
Exit 1 on any FAIL. Python standard library only.
"""
import argparse
import csv
import glob
import hashlib
import json
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent
ROWS = []
SRC_DIGEST = "550e9266d37cdb879cd50236bd4b0675c8c9410ab568cc6d7aee3710e6eb358a"
CITED = {"prod1_symmetry/coefficients.csv": "d86743c1e2592ea2ed29d51680ad497970b851ef0d83a89c9e69cd98bb96bc6c"}
CITED_REF = {"reference/lri_d2_perturbative_C8/results/coefficients_C0_C8.csv":
             "ee72158e2d9821f5aa330a09f8a094968083282078ff03a12b97067dad20b7bb"}


def check(name, ok, value, expected, tol):
    ROWS.append((name, "PASS" if ok else "FAIL", str(value), str(expected), str(tol)))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prod", default=str(PKG.parent.parent / "data" / "HT_2d" / "prod"))
    prod = Path(ap.parse_args().prod)

    recs = {}
    bad = []
    for f in sorted(glob.glob(str(prod / "*" / "d8" / "*.json"))):
        d = json.loads(Path(f).read_bytes())
        ok = d.get("schema") == "lri-coeff-v1" and sha(canonical(d["payload"])) == d.get("sha256")
        if not ok:
            bad.append(f)
        p = d["payload"]
        recs[(Path(f).parent.parent.name, p["configuration"]["scheme"], p["configuration"]["L"])] = (f, p)
    check("p2.prod.records", len(recs) == 41 and not bad, f"{len(recs)} records, {len(bad)} self-hash failures",
          "41 lri-coeff-v1 records, sha256 = sha256(canonical payload)", "exact")

    camp = []
    for f in sorted(glob.glob(str(prod / "*" / "campaign.json"))):
        d = json.loads(Path(f).read_bytes())
        camp.append(d.get("sha256") == sha(canonical(d["payload"])) and d["payload"].get("source_digest") == SRC_DIGEST)
    check("p2.prod.campaigns", len(camp) == 3 and all(camp), f"{len(camp)} campaign manifests, {sum(camp)} self-hash and source digest OK",
          "3 self-hashed campaign manifests (check_small_symmetry, prod1_symmetry, prod2_expanse)", "exact")

    src = PKG / "src" / "lri_coeff"
    files = {p.name: sha(p.read_bytes()) for p in sorted(src.iterdir()) if p.suffix in (".py", ".cpp")}
    dig = sha(canonical(files))
    nrec = sum(p["source_digest"] == dig for _, p in recs.values())
    check("p2.prod.source", dig == SRC_DIGEST and nrec == len(recs), f"source digest {dig[:16]}...; equal in {nrec}/{len(recs)} records",
          f"{SRC_DIGEST[:16]}... (storage.source_digest of src/lri_coeff)", "exact")

    nrow, mism = 0, []
    for camp in ("prod1_symmetry", "prod2_expanse"):
        for r in csv.DictReader(open(prod / camp / "coefficients.csv")):
            key = (camp, r["scheme"], int(r["L"]))
            if key not in recs:
                mism.append(f"{key}: no record")
                continue
            p = recs[key][1]
            C = [float(r[f"C{k}"]) for k in range(9)]
            if C != p["result"]["C"] or r["identity"] != p["identity"] or r["source_digest"] != p["source_digest"]:
                mism.append(str(key))
            nrow += 1
    check("p2.prod.tables", nrow == 20 and not mism, f"{nrow} table rows, {len(mism)} mismatches",
          "coefficients.csv rows = records (C0..C8 exact, identity, source digest)", "exact")

    got = {k: sha((prod / k).read_bytes()) for k in CITED}
    got.update({k: sha((PKG / k).read_bytes()) for k in CITED_REF})
    want = {**CITED, **CITED_REF}
    check("p2.prod.cited", got == want, "; ".join(f"{k}: {v[:12]}..." for k, v in got.items()),
          "d86743c1..., ee72158e... (cited by HT/data/HT_2d/pert_crosscheck)", "sha256")

    Ls = {s: sorted(L for (c, sc, L) in recs if sc == s) for s in ("raw", "consistent", "literal")}
    ok = Ls["raw"] == list(range(2, 35, 2)) and Ls["consistent"] == list(range(2, 35, 2)) and Ls["literal"] == list(range(2, 15, 2))
    check("p2.prod.lprod", ok and max(Ls["consistent"]) == 34,
          f"raw, consistent L = 2..{max(Ls['consistent'])}; literal L = 2..{max(Ls['literal'])}",
          "34 (\\HTpTwoLprod)", "exact")
    deg = {p["configuration"]["degree"] for _, p in recs.values()}
    check("p2.prod.degree", deg == {8} and all(len(p["result"]["C"]) == 9 for _, p in recs.values()),
          f"degree {sorted(deg)}; C0..C8 in every record", "eighth order", "exact")

    rec_ok = []
    for f in glob.glob(str(prod / "*" / "*" / "receipt.json")):
        r = json.load(open(f))
        c = r["checks"]
        rec_ok.append((r["site"], r["slurm"].get("SLURM_JOB_ID") if isinstance(r["slurm"], dict) else None,
                       str(r["passed"]) == "True" and c["tests"]["ok"] and c["replay"]["ok"] and r["source_digest"] == SRC_DIGEST))
    check("p2.prod.validation", len(rec_ok) == 2 and all(x[2] for x in rec_ok),
          ", ".join(f"{s} job {j}: {'passed' if o else 'FAILED'}" for s, j, o in rec_ok),
          "release validated on symmetry (571623) and Expanse (54765932): tests + L = 22 replay", "receipts")

    w = max(len(r[0]) for r in ROWS)
    for name, st, val, exp, tol in ROWS:
        print(f"{st}  {name:<{w}}  {val}\n      {'':<{w}}  expected: {exp}  [{tol}]")
    for b in bad[:5] + mism[:5]:
        print("NOTE", b)
    nf = sum(r[1] == "FAIL" for r in ROWS)
    print(f"\n{len(ROWS) - nf}/{len(ROWS)} PASS" + (f", {nf} FAIL" if nf else ""))
    sys.exit(1 if nf else 0)


if __name__ == "__main__":
    main()
