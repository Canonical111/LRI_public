#!/usr/bin/env python3
"""After the WINDOW_SPEC 2.10 change (2026-10-09): merge the reruns of the W family (partners projected out of
the window objects) into raw_out/prod_L<L>.json and raw_out/ext_L<L>.json.  The earlier runs (B-equation in the
auxiliary channels) are kept under the names WB, W+VB, W2B, WnoMB (+ legacy Wn, W+Vn, W2n).
usage: python3 merge_new.py"""
import glob, json, os, re, shutil, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RO = os.path.join(HERE, "raw_out")
REN = {"W": "WB", "W+V": "W+VB", "W2": "W2B", "WnoM": "WnoMB"}


def ren(name):
    base, suf = (name[:-8], "_garbage") if name.endswith("_garbage") else (name, "")
    return REN.get(base, base) + suf


def combine(tag, L):
    chunks = sorted(glob.glob(os.path.join(RO, f"{tag}c*_L{L}.json")))
    out = os.path.join(RO, f"{tag}_L{L}.json")
    if chunks and not os.path.exists(out):
        r = subprocess.run([sys.executable, os.path.join(HERE, "ce_combine.py"), out] + chunks)
        if r.returncode != 0:
            print(f"   {tag} L={L}: chunks incomplete ({len(chunks)} files)")
            return None
    return out if os.path.exists(out) else None


def merge_ext():
    for ef in sorted(glob.glob(os.path.join(RO, "ext_L*.json"))):
        m = re.search(r"/ext_L(\d+)\.json$", ef)
        if not m:
            continue
        L = int(m.group(1))
        nf = os.path.join(RO, f"newext_L{L}.json")
        if not os.path.exists(nf):
            continue
        e = json.load(open(ef))
        if e["meta"].get("merged_new"):
            continue
        ne = json.load(open(nf))
        e["schemes"] = {ren(s): v for s, v in e["schemes"].items()}
        e["schemes"].update(ne["schemes"])
        e["meta"]["merged_new"] = os.path.basename(nf)
        json.dump(e, open(ef, "w"), indent=1)
        print(f"   ext L={L}: merged {sorted(ne['schemes'])}")


def main():
    merge_ext()
    for fn in sorted(glob.glob(os.path.join(RO, "prod_L*.json"))):
        m = re.search(r"/prod_L(\d+)\.json$", fn)
        if not m:
            continue
        L = int(m.group(1))
        prod = json.load(open(fn))
        if prod["meta"].get("merged_new"):
            print(f"L={L}: already merged"); continue
        newf = os.path.join(RO, f"new_L{L}.json") if L <= 12 else combine(f"new{L}", L)
        if not newf or not os.path.exists(newf):
            print(f"L={L}: no new results yet"); continue
        new = json.load(open(newf))
        bak = fn.replace(".json", ".preB.json")
        if not os.path.exists(bak):
            shutil.copy(fn, bak)
        S = {ren(s): v for s, v in prod["schemes"].items() if s != "_garbage_report"}
        gr = {ren(s): v for s, v in prod["schemes"].get("_garbage_report", {}).items()}
        for s, v in new["schemes"].items():
            if s == "_garbage_report":
                gr.update(v)
            else:
                S[s] = v
        if gr:
            S["_garbage_report"] = gr
        prod["schemes"] = S
        prod["meta"]["merged_new"] = {"file": os.path.basename(newf), "primes": len(new["meta"]["primes"]),
                                      "note": "W-family rerun after WINDOW_SPEC 2.10 change; earlier runs renamed "
                                              + str(REN)}
        json.dump(prod, open(fn, "w"), indent=1)
        print(f"L={L}: merged {sorted(new['schemes'])}")


if __name__ == "__main__":
    main()
