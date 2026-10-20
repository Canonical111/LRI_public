#!/usr/bin/env python3
"""
[residual_log copy of ../complete_exact/ce_run.py; adds the Wc schemes (outer-referenced auxiliary windows)]
ce_run.py -- driver: exact multi-modular runs of raw / consistent / zeromode / complete2 (/ complete) schemes with
primaries p = 0..3 and descendant channels, CRT + rational reconstruction verified on held-out primes.
Quantities that depend on t = 1/pi (D_chi coefficient) are obtained as exact polynomials in t by evaluation at
several t residues per prime + Lagrange interpolation, with one extra point as a check.

usage: python3 ce_run.py --L 4 --schemes raw,consistent,zeromode,complete2 --desc odd:all,even:1 --out x.json
"""
from fractions import Fraction as Fr
import argparse, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ce_core as cc  # noqa: E402
import ce_solver as cs  # noqa: E402
from ce_core import ORD  # noqa: E402

_G = {}


def default_tiers(desc=False):
    t = {z: 6 for z in range(7)}
    t.update({z: 4 for z in range(7, 11)})
    t.update({z: 2 for z in range(11, 15)})
    return t


def parse_tiers(s):
    if s in (None, "", "default"):
        return default_tiers()
    t = {}
    for part in s.split(","):
        zr, k = part.split(":")
        a, b = (map(int, zr.split("-")) if "-" in zr else (int(zr), int(zr)))
        for z in range(a, b + 1):
            t[z] = int(k)
    return t


def desc_setups(structs, L, Kprim, capextra, spec):
    """spec: list of ('odd', a) / ('even', a). Returns dict key -> Setup, key = ('d', 'odd<a>')."""
    out = {}
    for kind, a in spec:
        if 2 * a > L:
            continue
        par = 1 if kind == "odd" else 0
        S = structs[par]
        prim = ((0, 1),) if kind == "odd" else ((0, 2),)
        vec = {prim: Fr(1)}
        for _ in range(a):
            vec = S.apply_L(vec, 0)
        for _ in range(a):
            vec = S.apply_L(vec, 1)
        ov = S.orbit_vector(vec)
        g = min(abs(x) for x in ov.values())
        ov = {i: x / g for i, x in ov.items()}
        p = 1 if kind == "odd" else 2
        E0 = Fr(p, 2) + 2 * a
        key = ("d", f"{kind}{a}")
        out[key] = cs.Setup(S, L, p + Kprim + capextra, ov, E0, label=key[1])
    return out


def build_setups(structs, L, schemes_aux, Kprim, capextra, dspec):
    setups = {}
    for p in range(4):
        S = structs[p % 2]
        setups[("p", p)] = cs.Setup(S, L, p + Kprim + capextra, {S.ref_index(p): Fr(1)}, Fr(p, 2), f"p{p}")
    for (z, l, km, cap) in schemes_aux:
        key = ("z", z, l, cap)
        if key in setups:
            continue
        S = structs[z % 2]
        setups[key] = cs.Setup(S, l, cap, {S.ref_index(z): Fr(1)}, Fr(z, 2), f"z{z}l{l}")
    setups.update(desc_setups(structs, L, Kprim, capextra, dspec))
    return setups


def make_scheme(name, q, a, tval=0, garbage_seed=None):
    L = a["L"]
    zrows = max(_G["structs"][0].Pmax, _G["structs"][1].Pmax) + 1
    if name == "raw":
        return cs.Raw()
    if name == "consistent":
        return cs.DiagWindow("consistent", _G["ctiers"], q, L, zrows, garbage_seed)
    if name == "zeromode":
        return cs.DiagWindow("zeromode", _G["tiers"], q, L, zrows, garbage_seed)
    if name == "complete2":
        return cs.Complete2(q, L, a["zc"], tval)
    if name == "complete2_zmonly":
        return cs.Complete2(q, L, a["zc"], tval, chi=False)
    if name == "complete2_bloch":
        return cs.Complete2(q, L, a["zc"], tval, hmode="bloch")
    if name.startswith("Wcx_"):
        # diagnostics: Wcx_<flags>: z2 = D^zm only to order 2; zd2/zd3 = D^zm diagonal at order 2/3;
        # m2only / m3only = D^M only at order 2 / 3
        fl = name[4:].split("_")
        kw = dict(zm_kmax=(2 if "z2" in fl else ORD), zm_diag=tuple(k for k in (2, 3) if f"zd{k}" in fl),
                  M_only=({2} if "m2only" in fl else ({3} if "m3only" in fl else None)))
        return cs.SchemeW(q, L, _G["book"], withV=False, garbage_seed=garbage_seed, name=name, zm=True, M=True,
                          nopartner=True, outer_ref=True, **kw)
    if name in ("Wcs4X", "Wcs4Xall"):
        # README Sec. 12: chi-line calibrated eps^4 window (uniform part c1chi^(4) + leg part delta4)
        x4 = json.load(open(a["x4file"]))
        return cs.SchemeW(q, L, _G["book"], withV=False, garbage_seed=garbage_seed, name=name, zm=True, M=True,
                          nopartner=True, outer_ref=True, delta3=Fr(a["delta3"]), delta4=Fr(a["delta4"]),
                          x4={int(k): v for k, v in x4.items()}, x4mode=("all" if name.endswith("all") else "cc"))
    if name == "Wcs4":
        return cs.SchemeW(q, L, _G["book"], withV=False, garbage_seed=garbage_seed, name=name, zm=True, M=True,
                          nopartner=True, outer_ref=True, delta3=Fr(a["delta3"]), delta4=Fr(a["delta4"]))
    if name in ("Wcs", "Wcs3"):
        # residual_log 2026-10-09: Wc + slice-resolved eps^3 self-window (WINDOW_SPEC Sec. 2.5a);
        # Wcs3: diagnostic, windows of order >= 4 switched off (comparison with brute_desc_tag4.py)
        return cs.SchemeW(q, L, _G["book"], withV=False, garbage_seed=garbage_seed, name=name, zm=True, M=True,
                          nopartner=True, outer_ref=True, delta3=Fr(a["delta3"]), kD=(3 if name == "Wcs3" else ORD))
    if name in ("Wc", "WcnoM", "Wc2", "WcM2", "WcM3"):
        # residual_log 2026-10-09: auxiliary windows referenced to the outer cutoff L (WINDOW_SPEC changelog)
        kM = {"WcM2": 2, "WcM3": 3}.get(name, ORD)
        return cs.SchemeW(q, L, _G["book"], withV=False, kD=(2 if name == "Wc2" else ORD), kM=kM,
                          garbage_seed=garbage_seed, name=name, zm=True, M=(name != "WcnoM"), nopartner=True,
                          outer_ref=True)
    if name.startswith("W"):
        # W, W+V: WINDOW_SPEC schemes (sec. 2.10 as changed 2026-10-09: partners projected out of the window
        #   objects); suffix B (WB, W+VB): earlier literal reading, B-equation in the auxiliary channels;
        # W2: windows of order 2 only (sec. 5.2); WnoM: no D^M; WM2/WM3: D^M truncated at eps^2/eps^3;
        # legacy suffix n (Wn, W+Vn, W2n): B-equation + explicit second-order h^(2).
        withV = name.startswith("W+V")
        base = name[3:] if withV else name[1:]
        legacy_n = base.endswith("n")
        Bread = base.endswith("B")
        core = base[:-1] if (legacy_n or Bread) else base
        kD = 2 if core.startswith("2") else ORD
        kM = int(core[1:]) if (core.startswith("M") and core[1:].isdigit()) else ORD
        return cs.SchemeW(q, L, _G["book"], withV=withV, kD=kD, h2naive=legacy_n, garbage_seed=garbage_seed,
                          name=name, zm=True, M=(core != "noM"), kM=kM, nopartner=not (Bread or legacy_n))
    raise ValueError(name)


def flatten(res, sc=None, L=None):
    out = {}
    for k in ("C", "r", "g"):
        for i, v in enumerate(res[k]):
            out[f"{k}|{i}"] = int(v)
    for p, row in enumerate(res["E"]):
        for i, v in enumerate(row):
            out[f"E|{p}|{i}"] = int(v)
    for zl, row in res["Eaux"].items():
        for i, v in enumerate(row):
            out[f"Ez|{zl}|{i}"] = int(v)
    for dn, row in res["Edesc"].items():
        for i, v in enumerate(row):
            out[f"Ed|{dn}|{i}"] = int(v)
    if isinstance(sc, cs.SchemeW):
        # window tables: claimed h^(k)_{z'z}(l) entries and c_1, c_2 (every l)
        for k, zp, z in sc.book["h"]:
            if k > sc.kD and k >= 2:
                continue
            for li in range(sc.nl):
                out[f"H|{k}|{zp}|{z}|{2 * li}"] = int(sc.H[k, zp, z, li])
        for k in range(1, ORD + 1):
            for li in range(sc.nl):
                if k in sc.book["c1"] or k == 1:
                    out[f"c1|{k}|{2 * li}"] = int(sc.c1[k, li])
                if k in sc.book["c2"] or k == 1:
                    out[f"c2|{k}|{2 * li}"] = int(sc.c2[k, li])
    return out


def worker(q):
    t0 = time.time()
    a = _G["args"]
    structs, setups = _G["structs"], _G["setups"]
    opsd = {par: cc.ModOps(structs[par], q) for par in (0, 1)}
    res = {}
    for name in _G["schemes"]:
        sc0 = make_scheme(name, q, a)
        dkeys = _G["dkeys"]
        if sc0.tdeg == 0:
            out, sc = cs.run_mod(structs, opsd, setups, a["L"], q, sc0, dkeys, a["Kprim"], a["capextra"])
            res[name] = flatten(out, sc, a["L"])
        else:
            tps = list(range(2, 2 + a["tpoints"]))
            ys = []
            for tv in tps:
                sc = make_scheme(name, q, a, tval=tv)
                out, _ = cs.run_mod(structs, opsd, setups, a["L"], q, sc, dkeys, a["Kprim"], a["capextra"])
                ys.append(flatten(out))
            flat = {}
            m = len(tps) - 1
            for key in ys[0]:
                vals = [y[key] for y in ys]
                coef = cc.lagrange_coeffs_mod(tps[:m], vals[:m], q)
                tv = tps[m]
                ev = 0
                for j in reversed(range(m)):
                    ev = (ev * tv + coef[j]) % q
                if ev != vals[m] % q:
                    flat[f"{key}|tcheckfail"] = 1
                for j in range(m):
                    flat[f"{key}|t{j}"] = coef[j]
            res[name] = flat
        gl = a.get("garbage")
        if gl and (name in gl.split(",") or (gl == "all" and (name in ("consistent", "zeromode") or
                                                              name.startswith("W")))):
            # closure test: every window entry outside the claimed set replaced by random residues; compared
            # residue by residue (identical residues for every prime <=> identical rationals)
            scg = make_scheme(name, q, a, garbage_seed=12345)
            out, _ = cs.run_mod(structs, opsd, setups, a["L"], q, scg, _G["dkeys"], a["Kprim"], a["capextra"])
            fg = flatten(out)
            ref = res[name]
            keys = [k for k in ref if k.split("|")[0] in ("C", "r", "g", "E", "Ed")]
            res.setdefault("_garbage_report", {})[name] = {"compared": len(keys),
                                                          "differ": [k for k in keys if fg.get(k) != ref[k]]}
    return q, res, time.time() - t0


def reconstruct_all(per_prime, primes, ncheck, verbose=True):
    final = {}
    if "_garbage_report" in per_prime:
        rep = per_prime["_garbage_report"]
        summ = {}
        for q, d in rep.items():
            for name, r in d.items():
                e = summ.setdefault(name, {"primes": 0, "compared_per_prime": r["compared"], "differ": set()})
                e["primes"] += 1
                e["differ"].update(r["differ"])
        final["_garbage_report"] = {n: {"primes": e["primes"], "compared_per_prime": e["compared_per_prime"],
                                        "differ": sorted(e["differ"])} for n, e in summ.items()}
        if verbose:
            for n, e in final["_garbage_report"].items():
                print(f"# garbage test {n}: {e['primes']} primes x {e['compared_per_prime']} residues, "
                      f"{len(e['differ'])} keys differ {e['differ'][:5]}", flush=True)
    for v in per_prime:
        if v == "_garbage_report":
            continue
        tfail = sorted({k for q in per_prime[v] for k in per_prime[v][q] if k.endswith("|tcheckfail")})
        if tfail and verbose:
            print(f"# WARNING {v}: t-polynomial check failed for {len(tfail)} keys, e.g. {tfail[:3]}", flush=True)
        clean = {q: {k: x for k, x in d.items() if not k.endswith("|tcheckfail")} for q, d in per_prime[v].items()}
        rec, bad = cc.reconstruct(clean, primes, ncheck)
        if bad and verbose:
            print(f"# WARNING {v}: {len(bad)} quantities failed verification, e.g. {bad[:5]}", flush=True)
        maxdig = max(len(str(abs(f.numerator))) + len(str(f.denominator)) for f in rec.values() if f is not None)
        final[v] = {"bad": bad, "tcheckfail": tfail,
                    "values": {k: (str(x) if x is not None else None) for k, x in rec.items()},
                    "max_digits": maxdig}
        if verbose:
            print(f"# {v}: max num+den digits {maxdig}, failed {len(bad)}", flush=True)
    return final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--L", type=int, required=True)
    ap.add_argument("--schemes", default="raw,consistent,zeromode,W")
    ap.add_argument("--desc", default="odd:all,even:1-2", help="odd:all|odd:1-3,even:1-2|none")
    ap.add_argument("--tiers", default="auto", help="auto (bookkeeping files), auto_ext (closure test) or explicit")
    ap.add_argument("--kvac", type=int, default=8, help="(explicit tiers only) order of the consistent vacua")
    ap.add_argument("--zc", type=int, default=14, help="complete2: largest z with a zero-mode window")
    ap.add_argument("--tpoints", type=int, default=8)
    ap.add_argument("--Kprim", type=int, default=16)
    ap.add_argument("--capextra", type=int, default=0)
    ap.add_argument("--Pmax", type=str, default="auto")
    ap.add_argument("--garbage", default="", help="'all' or comma list of schemes for the garbage closure test")
    ap.add_argument("--book", default=None, help="bookkeeping json for the W schemes")
    ap.add_argument("--bookext", action="store_true", help="extend the channel set (closure test)")
    ap.add_argument("--nprimes", type=int, default=88)
    ap.add_argument("--ncheck", type=int, default=8)
    ap.add_argument("--chunk", type=str, default=None, help="i/n: only this chunk of the primes; writes raw residues")
    ap.add_argument("--procs", type=int, default=1)
    ap.add_argument("--delta3", type=str, default=None, help="scheme Wcs: delta^(3)(L) (exact rational)")
    ap.add_argument("--delta4", type=str, default=None, help="scheme Wcs4: delta^(4)(L) (exact rational)")
    ap.add_argument("--x4file", type=str, default=None, help="scheme Wcs4X: json {N: X4(L, N)} (README Sec. 12)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0 = time.time()
    schemes = a.schemes.split(",")
    desc_on = a.desc != "none"
    if a.tiers in ("auto", "auto_ext"):
        tf = os.path.join(HERE, "results", "tiers_zeromode%s.json" % ("_desc" if desc_on else ""))
        cf = os.path.join(HERE, "results", "tiers_consistent%s.json" % ("_desc" if desc_on else ""))
        tiers = {int(z): (d["kmax"], d["cap"]) for z, d in json.load(open(tf)).items()}
        ctiers = {int(z): (d["kmax"], d["cap"]) for z, d in json.load(open(cf)).items()}
        if a.tiers == "auto_ext":     # closure test: one more order, cap + 2, z range + 2
            zm = max(tiers)
            tiers = {z: (min(ORD, k + 1), c + 2) for z, (k, c) in tiers.items()}
            tiers[zm + 1] = (tiers[zm][0], zm + 1 + 6)
            tiers[zm + 2] = (tiers[zm][0], zm + 2 + 6)
            ctiers = {z: (min(ORD, k + 1), c + 2) for z, (k, c) in ctiers.items()}
    else:
        tiers = parse_tiers(a.tiers)
        ctiers = {0: a.kvac}
    _G["ctiers"] = ctiers
    dspec = []
    if desc_on:
        for part in a.desc.split(","):
            kind, rng = part.split(":")
            if rng == "all":
                lst = range(1, a.L // 2 + 1)
            elif "-" in rng:
                x, y = map(int, rng.split("-"))
                lst = range(x, y + 1)
            else:
                lst = [int(rng)]
            dspec += [(kind, aa) for aa in lst]
    need = [19 + a.capextra, 18 + a.capextra]
    tcap = lambda z, k: k[1] if isinstance(k, tuple) else z + 4 * (k // 2)
    if "zeromode" in schemes:
        need.append(max(tcap(z, k) for z, k in tiers.items()) + a.capextra)
    if "consistent" in schemes:
        need.append(max(tcap(z, k) for z, k in ctiers.items()) + a.capextra)
    if any(s.startswith("complete") for s in schemes):
        need.append(a.zc + 8 + a.capextra)
    if any(s.startswith("W") for s in schemes):
        bf = a.book or os.path.join(HERE, "results", "book_W_V_desc.json" if desc_on else "book_W_V.json")
        book = json.load(open(bf))
        if a.bookext:
            ch = book["channels"]
            zmx = max(int(z) for z in ch)
            for z in list(ch):
                ch[z] = {"kmax": min(ORD, ch[z]["kmax"] + 1), "cap": ch[z]["cap"] + 2}
            for z in (zmx + 1, zmx + 2):
                ch[str(z)] = {"kmax": ch[str(zmx)]["kmax"], "cap": z + 4 + 2}
        need.append(max(d["cap"] for d in book["channels"].values()) + a.capextra)
        _G["book"] = book
        _G["bookfile"] = bf
    top = max(need)
    if a.Pmax != "auto":
        top = max(top, int(a.Pmax))
    Pm = {0: top if top % 2 == 0 else top - 1, 1: top if top % 2 == 1 else top - 1}
    withVp = any(s.startswith("W+V") for s in schemes)
    withX = any(x.startswith("Wcs") for x in schemes)
    withZ = any(x.startswith("Wcs4X") for x in schemes)
    structs = {par: cc.Structure(a.L, par, Pm[par], with_Vp=withVp, with_Xnu=withX, with_MpZ=withZ) for par in (0, 1)}
    _G.update(structs=structs, tiers=tiers)
    args = vars(a)
    _G["args"] = args
    auxall = []
    for name in schemes:
        sc = make_scheme(name, 1000003, args)
        auxall += sc.aux_specs(a.L, a.capextra)
    setups = build_setups(structs, a.L, auxall, a.Kprim, a.capextra, dspec)
    dkeys = [k for k in setups if k[0] == "d"]
    _G.update(setups=setups, dkeys=dkeys, schemes=schemes)
    desc_info = {k[1]: {"E0": str(s.E0), "E1": str(s.E1), "ref_block_dim": s.dims["ref"],
                        "other_block_dims": s.dims["other"], "other_block_keys(level,P)": s.otherkeys,
                        "refvec": {str(structs[int(2 * s.E0) % 2].states[i]): str(x) for i, x in s.refvec.items()},
                        "uvec": {str(structs[int(2 * s.E0) % 2].states[i]): str(x) for i, x in s.uvec.items()},
                        "ref_block_rational_eigs": getattr(s, "refblock_rational_eigs", None)}
                 for k, s in setups.items() if k[0] == "d"}
    partner_info = {f"{k[1]},{k[2]}": s.dims for k, s in setups.items() if k[0] == "z" and s.otherblocks}
    print(f"# structures {[len(structs[p].states) for p in (0, 1)]} (Pmax {Pm}) + {len(setups)} setups in "
          f"{time.time()-t0:.1f}s; schemes {schemes}; desc {[k[1] for k in dkeys]}", flush=True)
    primes = cc.primes_below(1 << 23, a.nprimes + a.ncheck)
    mine = primes
    if a.chunk:
        i, n = map(int, a.chunk.split("/"))
        mine = primes[i::n]
    per_prime = {}
    # incremental per-prime output (robust against wall-time kills): one JSON line per finished prime
    partial = a.out + ".partial.jsonl"
    done = set()
    if os.path.exists(partial):
        for line in open(partial):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            q = int(rec["q"])
            done.add(q)
            for v, d in rec["res"].items():
                per_prime.setdefault(v, {})[q] = d
        print(f"# resumed {len(done)} primes from {partial}", flush=True)
    mine = [q for q in mine if q not in done]
    pf = open(partial, "a")

    def record(q, res):
        pf.write(json.dumps({"q": q, "res": res}) + "\n")
        pf.flush()
    if a.procs > 1:
        import multiprocessing as mp
        ctx = mp.get_context("fork")
        with ctx.Pool(a.procs) as pool:
            for q, res, dt in pool.imap_unordered(worker, mine):
                record(q, res)
                for v in res:
                    per_prime.setdefault(v, {})[q] = res[v]
                nd = len(per_prime[schemes[0]])
                if nd in (1, len(mine)) or nd % 16 == 0:
                    print(f"#   {nd}/{len(mine)} primes done (last {q}: {dt:.1f}s)", flush=True)
    else:
        for q in mine:
            q, res, dt = worker(q)
            record(q, res)
            for v in res:
                per_prime.setdefault(v, {})[q] = res[v]
            print(f"#   prime {q} done in {dt:.1f}s", flush=True)
    meta = {"L": a.L, "args": {k: v for k, v in args.items()}, "Pmax": Pm, "primes": primes,
            "tiers": {str(z): k for z, k in tiers.items()}, "ctiers": {str(z): k for z, k in ctiers.items()},
            "n_states": {par: len(structs[par].states) for par in (0, 1)},
            "desc_info": desc_info, "aux_partner_blocks": partner_info, "seconds": time.time() - t0,
            "book": _G.get("bookfile"), "bookext": a.bookext}
    if a.chunk:
        with open(a.out, "w") as f:
            json.dump({"meta": meta, "raw": {v: {str(q): d for q, d in pp.items()} for v, pp in per_prime.items()}}, f)
        print(f"# wrote raw chunk {a.out}  total {time.time()-t0:.1f}s", flush=True)
        return
    final = reconstruct_all(per_prime, primes, a.ncheck)
    with open(a.out, "w") as f:
        json.dump({"meta": meta, "schemes": final}, f, indent=1)
    print(f"# wrote {a.out}  total {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
