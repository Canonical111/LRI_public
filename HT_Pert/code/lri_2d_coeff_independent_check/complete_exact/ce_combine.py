#!/usr/bin/env python3
"""Combine raw per-prime chunks of ce_run.py (--chunk) and reconstruct (CRT + rational reconstruction, verified
on the held-out primes).  usage: python3 ce_combine.py out.json chunk0.json chunk1.json ..."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ce_run as cr  # noqa: E402


def main():
    out, files = sys.argv[1], sys.argv[2:]
    per_prime, meta = {}, None
    for fn in files:
        if fn.endswith(".jsonl"):          # incremental per-prime records (meta from --meta-from file)
            for line in open(fn):
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                for v, res in rec["res"].items():
                    per_prime.setdefault(v, {})[int(rec["q"])] = res
            continue
        d = json.load(open(fn))
        meta = meta or d["meta"]
        for v, pp in d["raw"].items():
            for q, res in pp.items():
                per_prime.setdefault(v, {})[int(q)] = res
    primes = meta["primes"]
    ncheck = meta["args"]["ncheck"]
    for v in per_prime:
        missing = [q for q in primes if q not in per_prime[v]]
        assert not missing, f"{v}: {len(missing)} primes missing"
    final = cr.reconstruct_all(per_prime, primes, ncheck)
    meta["chunks"] = files
    with open(out, "w") as f:
        json.dump({"meta": meta, "schemes": final}, f, indent=1)
    print(f"# wrote {out}")


if __name__ == "__main__":
    main()
