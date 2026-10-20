# Reviews: C6(1) from exact all-graph sums (`LRI_C6_1D_HPC`)

All reviews ran through the claudex-loop workflow. The host, planner and builder was Claude Code (claude-opus-5-5,
1M context). The reviewer and inspector was Codex CLI 0.158.0 with model gpt-6-astra at effort xhigh, in
read-only mode, as static reviews.

The raw logs and artifacts (`LRI_C6_1D_HPC_loop/PLAN-REVIEW-LOG.md`, `artifacts/`, and the results-review dossier
and log) are not shipped. The plan that was approved ships as `GFF/results/C6_1/PLAN.md`: rev 8 plus the Sec 9
build-phase amendments.

## 1. Plan review: 8 rounds, APPROVED in round 8 (2026-09-28/29)

| Round | Verdict | Findings | Main subjects |
|---|---|---|---|
| 1 | REVISE | 12 (4 high, 7 medium, 1 low) | assembly file discovery, degree validation, mandatory inputs for a headline, unmeasured L5 rounding, deterministic group order, merge coverage, graph reader, weight self-check, 12−10 diagnostic, perturbation definition |
| 2 | REVISE | 5 (1 high) | provenance between rounding and assembly, pair checks and a weights manifest, light diagnostics from the production vectors, zero-proxy calibration policy, a wrong conditioning claim |
| 3 | REVISE | 5 (1 high) | draft scripts: build naming, fail-fast gate order, concurrent record writes, a single entry point, provisional mode |
| 4 | REVISE | 4 (1 high) | validation evidence bound to code/data identities, approval bypass, node budget, unchecked batch submissions |
| 5 | REVISE | 3 medium | superseded collector restoring approval, queue guard failing open, non-idempotent retries |
| 6 | REVISE | 2 medium | one strict merged-level validator, stranded dependent jobs |
| 7 | REVISE | 1 medium | NaN totals accepted by the validator |
| 8 | **APPROVED** | 0 | "R7-01 is resolved … No additional material defects found in this revision review." |

- **What changed.** Every finding was accepted and fixed in the next revision. Round 1 also brought in a new
  measurement: the binary64 error of the hard stratum grows with N. As a result the design became mixed precision,
  with the hard stratum and all five-loop inputs in long double, and the allowance gained the calibrated rounding
  term ρ.
- **Budget.** The configured limit was 5 rounds. The user allowed a sixth ("One more round") and then rounds 7 and
  8 ("two more rounds").
- **Reviewer limitations, stated at approval.** The review was static. Host-reported test results and the
  cluster validation were not verified independently, and the numerical kernel was not revalidated in the last
  round.

## 2. Code inspections: 3 rounds, all REVISE, every finding fixed (2026-09-29)

| Inspection | Snapshot | Verdict | Findings |
|---|---|---|---|
| 1 | 33ecb6f | REVISE | REV-001, REV-002 high (an unlocked standalone submitter; validation not isolated from production); REV-003 to REV-005 medium (a non-atomic merge publish; the final report dropped the L5 identities; the resource stopping rules were not recorded) |
| 2 | b67122a | REVISE | REV2-001 to REV2-003 medium (no stopping guard in the standalone submitter; resource evidence unvalidated; reports hashed in a second read) |
| 3 | 88626f1 | REVISE | REV3-001 to REV3-003 medium, all in the resource accounting `c6_resources` (a recovered timeout blocked coverage; task counts not reconciled; requeued attempts hidden without `--duplicates`) |

- **What changed.**
  - Inspection 1 led to one campaign lock and isolated validation attempts, atomic write-once merges, a final
    report that keeps all level identities, and `--resources` and `--decision-dir` in `analyze.py` (commit
    b67122a).
  - Inspection 2 led to the shared continuation guard `c6_require_continuation`, the `coverage_complete`
    evidence, and read-once hashing (88626f1).
  - Inspection 3 led to a rewrite of `c6_resources` from the job ledger with `sacct --duplicates` (b0763b4).
- **Budget.** The configured limit was 2 inspections. The user approved a third.
- **Changes never inspected:**
  - the inspection-3 fixes (b0763b4), by the user's standing choice to fix small findings and report them as
    uninspected;
  - the portable AVX2 / x86-64-v3 engines and the amdq-first routing (38f8847), made at the user's request
    ("prioritize amdq") after the inspections;
  - the V11 tolerance change (8680864);
  - the operator driver `ops/driver.sh`, which is not part of the package.

  All of these were covered empirically by the validation attempt at 8680864, which passed V1–V11. V11 shows that
  AMD and Intel give bitwise-equal double results and long double agreeing to ≤ 1.7e-16.

## 3. Results review: 2 rounds, APPROVED in round 2 (2026-10-01)

One dossier covered both C6(1) and C7(1).

| Round | Verdict | Findings |
|---|---|---|
| 1 | REVISE | RR-001 medium: rounding of the inherited L2–L4 amplitudes not assessed. RR-002 medium: the "C7 by-product 14331.62 ± 0.31" was a tail-extrapolated value, hardcoded and unlabelled. RR-003 medium and RR-004 low concern C7(1) only |
| 2 | **APPROVED** | "The four prior findings are addressed within the revised empirical and model-dependent scope. The headline arithmetic remains consistent with the committed evidence. No material unresolved defects were found." |

The reviewer reproduced every C6 level value, U = 4.9e-7 and the stopping decision from the committed JSON.

**What changed for C6:**
- **RR-001 (commit cef6fa7).** The lower amplitudes were rerun at degree 28 in long double and in float64 on
  symmetry, and the result was propagated through R6 (`tools/lowercheck.py`, `tools/lowercmp.py`,
  `lower_amplitude_precision/`, REPORT addendum). Long-double rounding is about 2.9e-11 in C6, and U is unchanged.
- **RR-002 (commit ee2e013).** `tools/c7_crosscheck.py` derives three labelled stages from `C7_final.json` and
  binds its inputs by hash: degree 6 at +2.46σ, plus the degree-7 step at +0.97σ, plus the tail at −0.22σ
  (model-dependent). The hardcoded constant was removed from `analyze.py`, and REPORT identifies the old
  `C6_final.json` field as the tail stage.
- **C6 numbers unchanged.** No C6 number changed in either round.

**Reviewer limitations, recorded at approval:**
- the review was static, and the remote records and executables were not reproduced;
- the lower-amplitude long-double error is inferred by roundoff scaling, not measured against a higher-precision
  truth;
- the other C6 rounding proxies are empirical too.

## 4. Recommendations not applied as written

- **RR-001.** The reviewer proposed comparing the lower amplitudes with a *higher-precision* evaluation. The host
  measured the float64-versus-long-double sensitivity instead, and scaled it by the unit-roundoff ratio 2^-11. The
  reviewer accepted this in round 2 and recorded the limitation above. No Ulow_round term was added to the formula
  for U: it would be 1.2e-10, and U = ceil_2sf(4.8853e-7 + 1.2e-10) stays 4.9e-7.
- **Process limits.** The plan-round and inspection budgets were exceeded with the user's approval, and some
  changes were never inspected (Sec 2). No other finding was declined.

## 5. This export (2026-10-13)

The public scripts (`public.mk`, `public/`) were written by a C71d helper and were not reviewed by Codex.
`make -f public.mk replay` regenerates every shipped record bitwise. It found one wording error in the condensed
note, Sec 22.4: "from M = 24 onward, successive changes of C6 are below 1e-11". The records give up to 4.35e-9,
which is U5/2. The error is reported in SUMMARY.md, and the replay marks it FLAG.
