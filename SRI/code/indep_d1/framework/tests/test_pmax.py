#!/usr/bin/env python3
"""
Regression test for the latent pmax issue (critique, "Latent"): the internal two-kink series hold
terms only through eps^pcap, so their validity must be pcap (it was INF in phase 1, which would have
silently truncated a product that needs a higher Z2/Q2 order).

  1. the internal Z2/Q2 jets carry pmax = pcap; A1 (eps-independent) keeps pmax = INF;
  2. unit level: [eps^0] of Z2^2 * Z2_dE needs Z2_dE through eps^2.  With pcap = 1 the product is
     flagged (MISSING, 'beyond validity'); the phase-1 bookkeeping (pmax = INF) would have returned a
     wrong number, shown here against the pcap = 8 reference;
  3. framework level: pcap = 2 is too small for D4 -> strict raises TruncationError, non-strict reports
     C7 MISSING with the truncation tag; pcap = 3 is the smallest complete cap, and pcap = 3, 6 (default)
     and 8 give identical outputs on random data.
"""
import os
import random
import sys

import mpmath as mp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import lri_framework as L  # noqa: E402

FAIL = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        FAIL.append(msg)


def ser(terms, pmax, kmax=9):
    return L.LSeries({pk: L.Val(x) for pk, x in terms.items() if pk[1] <= kmax}, pmax)


def main():
    mp.mp.dps = 30
    print("[1] validity of the internal series")
    for pc in (3, 6):
        fw = L.Framework("D4", dps=30, pcap=pc)
        jets = fw._raw_jets({}, True, compare=False)
        z2 = [s.pmax for s in jets[("Z", 2)].values()]
        q2 = [s.pmax for s in jets[("Q", 2)].values()]
        a1 = [s.pmax for s in jets[("A", 1)].values()]
        check(set(z2) == {pc} and set(q2) == {pc} and set(a1) == {L.INF},
              f"pcap={pc}: all {len(z2)} Z2 and {len(q2)} Q2 jets have pmax = pcap; A1 pmax = INF")

    print("[2] unit level: [eps^0] of Z2^2 * Z2_dE")
    kmax = 9
    ref_terms = {"Z": L.two_kink("Z", 0, 0, 0, 8, None, 30), "S": L.two_kink("Z", 0, 1, 1, 8, None, 30)}
    lo_terms = {"Z": L.two_kink("Z", 0, 0, 0, 1, None, 30), "S": L.two_kink("Z", 0, 1, 1, 1, None, 30)}
    ref = ser(ref_terms["Z"], 8).mul(ser(ref_terms["Z"], 8), kmax, 8).mul(ser(ref_terms["S"], 8), kmax, 8)
    new = ser(lo_terms["Z"], 1).mul(ser(lo_terms["Z"], 1), kmax, 1).mul(ser(lo_terms["S"], 1), kmax, 1)
    old = ser(lo_terms["Z"], L.INF).mul(ser(lo_terms["Z"], L.INF), kmax, 1).mul(ser(lo_terms["S"], L.INF), kmax, 1)
    c_new = [new.coef(0, k) for k in range(3)]
    check(all(c.is_missing and any("beyond validity" in m for m in c.miss) for c in c_new),
          "pcap=1, pmax=pcap: [eps^0 l^0..2] flagged MISSING ('beyond validity')")
    diff = max(abs(old.coef(0, k).v - ref.coef(0, k).v) for k in range(3))
    check(diff > mp.mpf("1e-3"), f"phase-1 bookkeeping (pmax=INF) would return a wrong value silently "
                                 f"(max |diff| from the pcap=8 reference = {mp.nstr(diff, 3)})")

    print("[3] framework level")
    fw2 = L.Framework("D4", dps=30, pcap=2)
    need = L.Framework("D4", dps=30).required_names()
    random.seed(8)
    raw = {nm: mp.mpf(random.uniform(-3, 3)) for nm in need}
    try:
        fw2.from_raw(raw)
        ok = False
    except L.TruncationError:
        ok = True
    check(ok, "pcap=2: strict mode raises TruncationError")
    r2 = fw2.from_raw(raw, strict=False)
    check(r2.C[7].is_missing and any("beyond validity" in m for m in r2.C[7].miss),
          "pcap=2, non-strict: C7 MISSING with the truncation tag (never a truncated number)")
    vals = {}
    for pc in (3, 6, 8):
        fw = L.Framework("D4", dps=30, pcap=pc)
        check(not [n for n in fw.required_names() if n.startswith("<")], f"pcap={pc}: no truncation tags")
        vals[pc] = fw.from_raw(raw, track=False).outputs()
    same = all(vals[3][o].v == vals[6][o].v == vals[8][o].v for o in vals[6])
    check(same, "pcap = 3, 6, 8 give identical outputs")
    print("PMAX TEST", "PASSED" if not FAIL else f"FAILED ({len(FAIL)})")
    return not FAIL


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
