# C7(3) production on symmetry (started 2026-09-30)

## Plan agreed with the user (2026-09-30)

- **"Same as 2d" (C7(2)): the parallel plan.** Build, test and pilot the delivered code (local git baseline 4de9412,
  unchanged) on symmetry and start production at once. A review runs alongside, and the result is kept only if the
  review clears the numerics. A Codex fix loop may follow afterwards.
- **Review.** Focused: three read-only reviewers on the d=3 port and assembly, mapped against the C7(2) review
  findings (not a full multi-agent workflow). The report goes in `LRI_C7_D3_HPC_review/`.
- **Nodes.** Workers queue in defq/amdq only (no preemptible partitions). The C7(2) campaign holds 28 nodes.
- **Size.** M = 4096, R = 64, gmp.

## Environment (`~/c7d3_prod/env.sh` on symmetry)

- System GCC 11.4, the boost/1.77.0 module (headers), system GMP 6.2.1, and python/3.11 with the C7(2) venv (numpy
  2.3.5, scipy 1.17.1, mpmath 1.3.0, sympy 1.14.0).
- Package: `~/c7d3_prod/pkg`, a `git archive` export of 4de9412.

## Build, tests, thread check and pilot (job 566376, amddebugq, AMD EPYC 7532 node <NODE>)

- **Integrity.** `verify_delivery --strict` before the build: passed, 4909 payload files.
- **Binaries.** bin/c7d3_decimal 24b2b941…; bin/c7d3_gmp 635428f9f9f462b74d261185120b5ea1553fb7989196feef644dd85dd687ae5f
  (production). `--describe` reports decimal300 (328) and gmp350 (372), dimension 3.
- **Delivered tests.** All 7 PASS:
  - validate (18 s) and validate --full (96 s; every graph against the original d=3 code, both backends);
  - check_points (43 s);
  - workflow (12 s);
  - staging, reassemble_reference and test_delivery_verifier.
- **Thread identity.** a_free_L7 and a_power_L7 at 64 vs 16 threads: 5,776 rows, 0 mismatches (255,396 binary128 and
  20,511 gmp promotions).
- **Pilot** (seed 3272672730315656627; M=1, R=8, gmp, 64 threads; 80 jobs in 4.7 min):
  - C7 = −223.31 ± 8.18, against the archived −227.62 ± 3.83;
  - 1,181 task core-s, 83% of it in L7;
  - error by (loop, sector): L7 free 6.94, power 3.01; L6 free 2.39, power 1.70;
  - cost model `<SCRATCH>/c7-d3/pilot-566376/costs.json`;
  - projection: SE ≈ 2.9/√M at R=64 (the reviewer's archive-based projection gives 2.34/√M); cost ≈ 2.6·M core-h.

## Campaign run1: `<SCRATCH>/c7-d3/run1-20260930-m4096`

- **Plan** (job 566380). Seed 4805754955154533039 (fresh). `--backend gmp --replicates 64 --multiplier 4096
  --primitive-mode recompute --primitive-points 1024 --shards 64 --threads 64 --checkpoint-tasks 1024 --chunk-points
  1048576 --cost-model pilot-566376/costs.json`.
  - 1,280 jobs, 8.68e11 samples; queue 184.9 AMD-lane-hours; heaviest element about 48 min.
  - `--primitive-points 1024` rather than C7(2)'s 16384, per the review: the flat primitive allocation at 16384 costs
    15.6% of CPU for 0.03% of the variance; 1024 costs 1.1% for 0.4%. This is a plan flag only; no code changed.
- **Execution.**
  - 28 whole-node claim-based workers (`~/c7d3_prod/sym_node.slurm`, 24 h), listed in `$RUN/NODEJOBS`:
    - 14 amdq (--mem=240G): 566381–566394;
    - 14 defq (--mem=180G): 566395–566408.
  - AMD nodes run one 64-thread lane; Intel nodes run two socket-bound 20-thread lanes.
  - Lanes claim indices heaviest first with an atomic `mkdir claims/<idx>`.
  - Merge and assembly job 566409 (afterany on all workers): checks completeness, merges the 20 groups in parallel
    and runs `assemble.py --bootstrap 4096`.
  - Status: `python3 ~/c7d3_prod/c7prod_status.py RUN` (exit 0 when complete).
  - Recovery: a failed or timed-out index keeps `claims/<idx>`. Remove it, then submit another `sym_node.slurm`.
- **Expected.** About 9 h once the workers run (the C7(2) nodes free up first).
- **Projected SE.** About 0.037–0.045, against the archived 3.83.

## AMD vs Intel identity (job 566410, Intel Gold 6148 <NODE>, 2026-09-30 18:00)

- **Test.** The thread-check plan of job 566376 was re-planned with the same seed and flags (task tables identical) and
  run on Intel at 20 threads. Its a_free_L7 and a_power_L7 blocks were compared with the AMD 64-thread checkpoints.
- **Result.** 5,393 of 5,776 rows differ in their values. The binary128 and GMP promotion counts are identical in every
  row. The largest normalized difference is 2.0e-11 in a_power_L7 and 1.6e-13 in a_free_L7.
- **Interpretation.** On AMD, 64 vs 16 threads gives 0 mismatches, so the difference comes from the CPU type. The most
  likely cause is the CPU-dependent last bits of glibc's x87 long-double transcendental functions, amplified by the
  kernel's accepted cancellation (up to the 1e-9 promotion threshold).
- **Consequence.** The differences are about 1e-7 of the campaign's relative statistical error (SE/|C7| ≈ 2e-4). They
  are within the numerical contract and cause no bias, but results are bit-reproducible only on the same CPU type.
  The run mixes amdq and defq nodes, as C7(2) does; each index's host is recorded in `claims/<idx>/owner`.

## Review outcome (2026-09-30 18:05)

- **Verdict.** `LRI_C7_D3_HPC_review/REVIEW.md`: numerics sound, nothing biasing, **GO** for this campaign.
- **Replay** (job 566411). All 168,528 archived rows reproduce with the delivered worker: 96% bit for bit, the rest
  ≤ 1e-11; fallback counts identical in all 20 groups. C7(3) rebuilt: −227.61810947469922 against the published
  −227.61810947469945.
- **Result gates.** The result is judged with the manual gates below: the new C6 reference, and power_differences
  against 0.

## Proposed reporting rule (written before any production result; for the user to confirm)

1. **Primary estimate.** The frozen a/b combination in `C7_result.json` (C7_full), with its sampling SE; the bootstrap
   is diagnostic only.
2. **Quoted allowance.** 4 × SE, rounded up to 0.01. This is the archived four-SE convention; the archived report was
   −228 ± 16.
3. **Consistency gates.** These are computed by hand from `C7_result.json` and the `merged.json` files; they are
   checked, never used to tune or select:
   - **a/b campaigns.** |C7_a − C7_b| / sqrt(se_a² + se_b²) ≤ 3.
   - **Bootstrap.** The bootstrap SE must be within ±20% of the covariance SE.
   - **Archived value.** Agreement with the archived −227.62 ± 3.83 (SE) within 3 of the archived SE.
   - **Lower orders.**
     - C3–C5 against the published exact values.
     - Full C6 against the NEW C6(3) = 33.57543 ± 0.00012, with the uncertainties combined. The package's built-in
       C6 reference (33.5682) is stale and would give a spurious pull of about 3 at this precision.
     - power_differences[3..6] against 0.
     - A |pull| > 3 in any of these is flagged, investigated and reported. It does not change C7.
4. **Caveat to report.** In C7(1) the degree-6 quadrature truncation, not sampling, became the limit at high
   precision. Any analogous truncation effect in C7(3) is outside the sampling allowance and would be reported
   separately.

## Completion (2026-10-01 04:03 EDT)

- **Workers.** All 1,920 blocks were committed by about 03:51 EDT. The run never started any longq or preemptible job,
  and there were 0 failed claims and 0 native failure logs.
- **Merge job 566409 FAILED after 6 s, after merging all 20 groups.** A bug in the merge script copied from C7(2):
  `grep -l "MERGE FAILED" /dev/null` exits 1, which aborts under `set -e` before assembly. The C7(2) merge 566287
  failed the same way; that session assembled by hand.
  - Fixed in `~/c7d3_prod/sym_merge.slurm` (the original is kept as `.orig`).
  - Rerun as job 566671 (amddebugq, 6 s): the 20 groups were already merged and skipped; `assemble.py --bootstrap 4096`
    wrote `C7_result.json`.
- **Data.**
  - `results_run1-20260930-m4096/`: `C7_result.json`, manifest, configs, `merged.json`, node and merge logs.
  - `run1-20260930-m4096_full.tgz`: the complete run directory, 130 MB, 7,260 entries, sha256 08969c10… in `.sha256`.
  - The original remains on symmetry BeeGFS.

## Result

- **C7(3) estimate.** −220.35448047392794; sampling SE 0.031818800575016494. That is 120× below the archived 3.83 and
  1.3× below the plain-MC projection of 0.04.
  - Power-free C7: −220.37236 ± 0.02771.
  - Power correction: +0.01788 ± 0.01565 (archived −3.84 ± 2.01).
  - Error by loop: L7 free 0.0248, power 0.0145; L6 free 0.0119, power 0.0058; L5 free 0.0034, power 0.0014.
- **Under the proposed reporting rule** (written at launch, before the result; NOT yet confirmed by the user; the text
  above is unchanged): **C7(3) = −220.35 ± 0.13** (4 × SE = 0.127, rounded up to 0.01).
- **Gates.** All PASS:
  - **a/b campaigns.** a = −220.32200 ± 0.04308, b = −220.38696 ± 0.04684; pull 1.02.
  - **Bootstrap.** Bootstrap SE 0.03204, ratio 1.007.
  - **Archived value.** −220.354 − (−227.618) = +7.26 = 1.90 archived SE. The archived report −228 ± 16 is consistent.
  - **Lower orders:**

    | Check | Pull |
    |---|---|
    | C3 | +2.30 (estimate −0.353580696 ± 3.6e-7) |
    | C4 | +1.08 |
    | C5 | +0.04 |
    | C6 against the new 33.57543 ± 0.00012 | −0.79 (estimate 33.57387 ± 0.00198) |
    | power_differences[4..6] against 0 | +0.97, +0.62, −0.36 |

    Against the package's stale C6 reference, 33.5682, the C6 pull would be +2.87, as the review predicted.
- **Caveat.** This is a sampling allowance only. As in C7(1), a quadrature-truncation effect, if present in d=3, is
  not covered. The result also relies on the retained analytic power compensation inherited from the original
  calculation.

## Re-verification with the fixed package (2026-10-01)
- **Report.** `tools/report.py` of the symmetry-ready package (`LRI_C7_D3_HPC` ffb8435; validation job 567128 on
  <NODE>, AMD EPYC 7532) re-verified run1 read-only, by data identity: manifest, the 20 configs, merged.json files
  and graph_replicates.csv digests. Assembly inputs were checked against run1's inputs manifest.
- **Result.** It reproduces C7(3) = −220.35448047392794 ± 0.031818800575016494 **bitwise**. The gate values are
  identical to those above. Report: `run1_report_ffb8435.json`.
- **CPU dependence of the assembly.** Re-assembling the same data on the AVX-512 node cn112 (EPYC 8534P) gives
  …805, 4 ulp away, also with the delivered tools. On AVX2 nodes (7532 and 7543) it is bitwise. This is a last-bit
  NumPy/OpenBLAS effect, about 1e-13 against an SE of 0.03, and does not affect the result.
- **Reporting rule.** It is still PROPOSED and awaits the user's confirmation.
- **Final package.** The fix loop's final package (`LRI_C7_D3_HPC` main c71cc56; code bb9d2ca; Codex APPROVED)
  re-verified run1 again: job 567197, <NODE>, bitwise, same gates. Report: `run1_report_bb9d2ca.json`.

## Reporting rule confirmed (2026-10-01, by the user)

- **Confirmation.** The user confirmed the reporting rule above unchanged ("yes sounds good to me"). It was written
  at launch, before any result existed; the confirmation came after the result was known. The text of the rule is
  not altered.
- **Reported result.** **C7(3) = −220.35 ± 0.13**: estimator −220.35448047392794, sampling SE 0.031818800575016494,
  and 4 × SE = 0.127, rounded up to 0.01.
- **Gates.** All gates of the rule pass (see "Completion" and "Re-verification with the fixed package").

## Erratum (2026-10-01, found while preparing the results review)

- **Caveat in "Result".** "The result also relies on the retained analytic power compensation inherited from the
  original calculation" is wrong; it was carried over from C6(3). Nothing in C7(3) is retained or analytically
  compensated: both the power-free and the power-containing sectors are integrated explicitly (`docs/NUMERICS.md`,
  `manifest.json` `power_sector`, `C7_result.json` `scope`). What the result does inherit are the graph
  combinatorics, the local-subtraction (finite-scheme) framework and the analytic low-loop inputs (the two-loop jet
  B2, C0 = 3/2, C1 = −1/6), which the package uses but does not re-derive.
- **Primitive allocation (clarification).** Run1 used the delivered code's flat allocation for the 44 seven-loop
  primitive classes (free sector, L7): 1024 × 4096 points per replicate each, instead of their frozen Neyman counts
  (64–2048) × 4096. Every other stratum, the primitives at L ≤ 6 included, uses its frozen Neyman count × 4096. This
  changes only the variance, not the expectation.

## Codex results review (2026-10-01)

- **Verdict: APPROVED in round 2** (`LRI_C7_D3_results_review/`): "C7(3) = −220.35 ± 0.13 is supported within its
  stated empirical sampling-only scope."
- **Round 1 findings.** Both were low and neither changed the result:
  - the dossier misdescribed run1's seed derivation, which uses the delivered tools' arithmetic offsets, not hashes;
  - the package flagged the archived value by the combined pull instead of 3 archived SE.
- **Package fix.** `LRI_C7_D3_HPC` commit `a6ce987` (gate in archived SE plus a regression test). Run1's gates are
  unchanged.

