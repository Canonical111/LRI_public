#!/usr/bin/env python3
"""`make -f public.mk test` for HT_Pert/code/lri_d1_fullblock_tail_response.

Stages (the package's own checks, unchanged; README "Validate and regenerate"):
  manifest           MANIFEST.sha256 (108 files) against the shipped tree; files listed in public/SCRUBBED.txt are
                     reported, not failed (public/fb_common.py)
  verify_manifest    the package's own tests/verify_manifest.py on the shipped tree (SKIP when public/SCRUBBED.txt
                     lists files: that verifier knows no scrub list, and the stage above covers it)
  check_annulus      tests/check_annulus.py: 468 exact threshold identities and 36 direct finite-annulus comparisons
                     of the general low-bath kernel, Eq. (2) of docs/METHOD.md
  mixing_asymptotics code/mixing_asymptotics.py: sympy derivation of A, 1/81 and B of Eq. (6) from the 38 Wick weights
  finite_response    tests/check_finite_response.py: finite-epsilon Schur/Hellmann-Feynman check of two responses
  validate           tests/validate.py (fresh vs saved responses, exact rationals, shell sums, FFT backend, finite
                     part); it needs x86-64 80-bit long double (np.finfo(np.longdouble).nmant >= 63), SKIP otherwise
The last four stages are tests/run_all.py's four scripts, in its order and with its thread settings. They rewrite
results files, so they run on a fresh copy of the package under WORK/test_tree.
Exit status 1 if any stage FAILs. The table is also written to WORK/test_lri_d1_fullblock_tail_response.txt.
usage: python3 public/run_tests_fb.py [--work .work]"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fb_common as fc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=os.path.join(fc.PKG, ".work"))
    a = ap.parse_args()
    work = os.path.abspath(a.work)
    os.makedirs(work, exist_ok=True)
    rows = []

    def add(stage, verdict, secs, detail):
        rows.append((stage, verdict, secs, detail))
        print(f"{stage:19s} {verdict:4s} {secs:7.2f}s  {detail}", flush=True)

    n, ok, sc, bad = fc.verify_manifest()
    add("manifest", "FAIL" if bad else "PASS", 0.0,
        f"{ok}/{n} byte-identical, {len(sc)} listed in public/SCRUBBED.txt {sc}, failures {bad}")
    if fc.scrubbed():
        add("verify_manifest", "SKIP", 0.0, f"{len(fc.scrubbed())} files listed in public/SCRUBBED.txt; "
            "the verbatim verifier has no scrub list (stage 'manifest' checks the rest)")
    else:
        rc, out, err, s = fc.run_py(["tests/verify_manifest.py"], fc.PKG)
        add("verify_manifest", "PASS" if rc == 0 else "FAIL", s, (out.strip() or err.strip()[-300:]))

    tree = fc.copy_tree(os.path.join(work, "test_tree"))
    for stage, script in [("check_annulus", "tests/check_annulus.py"),
                          ("mixing_asymptotics", "code/mixing_asymptotics.py"),
                          ("finite_response", "tests/check_finite_response.py")]:
        rc, out, err, s = fc.run_py([script], tree)
        detail = out.strip().splitlines()[0][:160] if (rc == 0 and out.strip()) else err.strip()[-400:]
        if stage == "finite_response" and rc == 0:
            detail = "halving ratios in (300, 700) for phi6 and full (asserted); results/finite_response_validation.json"
        add(stage, "PASS" if rc == 0 else "FAIL", s, detail)

    bits = fc.longdouble_bits()
    if bits >= 63:
        rc, out, err, s = fc.run_py(["tests/validate.py"], tree)
        add("validate", "PASS" if rc == 0 else "FAIL", s,
            "all asserted identities hold; results/validation.json rewritten in the copy" if rc == 0
            else err.strip()[-400:])
    else:
        add("validate", "SKIP", 0.0, f"tests/validate.py needs x86-64 80-bit long double; here "
            f"np.finfo(np.longdouble).nmant = {bits} (< 63). Run it on an x86-64 machine.")

    npass = sum(r[1] == "PASS" for r in rows)
    nfail = sum(r[1] == "FAIL" for r in rows)
    nskip = sum(r[1] == "SKIP" for r in rows)
    summary = f"{npass} PASS, {nfail} FAIL, {nskip} SKIP"
    print(summary)
    with open(os.path.join(work, f"test_{fc.NAME}.txt"), "w") as fh:
        fh.write(f"# make -f public.mk test, {fc.NAME}; python {sys.version.split()[0]}\n")
        for st, v, s, d in rows:
            fh.write(f"{st:19s} {v:4s} {s:7.2f}s  {d}\n")
        fh.write(summary + "\n")
    sys.exit(1 if nfail else 0)


if __name__ == "__main__":
    main()
