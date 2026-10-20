# Reviews of LRI_C7_HPC and of the C7(1) result

Summary of three review processes. The raw logs, plans and reviewer outputs are not published.

## 0. First review of the delivered package (2026-09-25)

- **Reviewer:** Claude Code (Claude Opus 5.5), multi-agent review with live tests on a personal desktop and an Expanse
  launch probe.
- **Result:** 41 verified findings, which became the fix list of the plan below. The high-severity one was the Slurm
  launch: on Slurm 22.05–23.02 the `srun` step did not inherit the job's CPUs per task, so every OpenMP thread ran on
  one CPU (effective parallelism 0.99 of 8 threads on Expanse). Others concerned build portability, checkpoint
  integrity (no content digest, silent default index, no coverage check at merge), missing production tooling for
  independent batches, and documentation errors (srun statement, replay-record provenance, benchmark weighting).

## 1. Code plan and inspections (claudex-loop, 2026-09-25 to 2026-09-26)

- **Roles:** host, planner and builder: Claude Code (Claude Opus 5.5) with Claude helper agents. Plan reviewer and
  inspector: Codex CLI 0.157.0, model gpt-6-astra, effort xhigh (fast mode from inspection 2). Every inspection used a
  fresh Codex session. The reviewer had a write-capable REPL tool enabled by the user's explicit choice and was
  instructed to stay read-only.
- **Plan (fix the package, add a degree 6→7 check, run fresh-seed batches on Expanse):** round 1 REVISE (12 findings:
  5 high, 7 medium), round 2 REVISE (3: 1 high, 1 medium, 1 low), round 3 **APPROVED** with no findings. All findings
  were accepted.
- **Acceptance criteria:** A1 `make test` on a personal desktop and Expanse PASS; A2 kernels bitwise identical to the delivered source
  (23 workloads, 0 differing rows, on a personal desktop and Expanse) PASS; A3 archived reassembly reproduced exactly, diagnostics to
  2e-15 PASS; A4 launch fix proven (15.74 of 16 CPUs effective) PASS; **A5 NOT MET** (see below); A6 pilot PASS;
  A7 production PASS.
- **Inspections:**
  1. REVISE, 6 findings (primitive-sector guard, quarantine/merge interplay, an explicit accuracy criterion in
     `check_quad.py`, estimator-only design prediction, template strict mode, checksum list). Fixed.
  2. REVISE, 3 findings (verify must rebuild coverage, design must reject non-unit pilot multipliers, primitive-class
     metadata). Commit **3213ce0** is the state this inspection covered, including the round-1 fixes; the production
     workers ran a frozen copy of it. The three fixes came after it.
  3. (Quota raised from 2 to 5 inspections by the user.) REVISE, 3 findings: accuracy must be judged per element, not
     by slot maxima; the rounding-floor exception was not in the approved plan; the design accepted incomplete pilots.
     Fixed. The per-element evaluation showed that the optimized power quadrature is less accurate than the original
     on 9 of 112 degree-7 replay elements (worst 18×, 4.2e-14 relative), although its aggregate projected C7 error is
     smaller (2.8e-12 against 1.9e-11).
  4. REVISE: A5 (acknowledged, no code change, see below) and two design-validation findings (fixed).
  5. REVISE: A5 (acknowledged) and three validation findings (exact pilot counts, source identity, missing archived
     variances), fixed in a fifth fix round that is **uninspected** (inspection budget exhausted). Commit 3129a97 holds
     fix rounds 2–5; the frozen design reproduces byte-identically under every version.
- **Recommendation not adopted:** the element-wise accuracy criterion A5. By the user's decision (2026-09-26) it is
  reported as not met instead of being amended; the strict criterion stays the default gate of `check_quad.py`, and
  the rounding-floor criterion (whose 64·2^-64 threshold was chosen after seeing the data, as the log discloses) is a
  diagnostic only. The deviations are about 1e-10 of the sampling noise.

## 2. Direct primitive campaign and parallel combine (PLAN2, 2026-09-26)

- **Roles:** as above (Claude builds, Codex gpt-6-astra xhigh reviews and inspects).
- **Plan:** round 1 REVISE (4 findings, 1 high: source metadata must be bound to verified manifests), round 2 REVISE
  (archived power records lack counts), round 3 REVISE (high: the guarded primitive sector is primitive && !power,
  44 classes, not the 64 raw flags), round 4 **APPROVED**.
- **Inspections:** 1 REVISE (2 high: primitive inputs not compared with the batches; class support read from the merged
  file instead of the manifest; 1 medium: the baseline test needed git history), fixed; 2 REVISE (1 high: a mixed
  archived/direct assembly did not bind a new campaign's Gamma input to the authenticated archive), fixed;
  3 **APPROVED**, committed as b0d2cd3; 4 (the added `combine.py --jobs`, byte-identical output) **APPROVED**, committed
  as **7320afc**, the code of the final combination.

## 3. Results review (2026-10-01)

- **Reviewer:** Codex CLI, gpt-6-astra, effort xhigh, read-only, on a results dossier for C6(1) and C7(1) prepared by
  Claude Code.
- **Round 1 REVISE**, 4 findings, all accepted: input rounding of the C6 lower amplitudes (measured, allowance
  unchanged); an unlabelled C7 by-product in the C6 report; **C7 overclaim**: ±41 is the registered policy output, not
  a total accuracy, since it does not add the modelled truncation bias to the sampling error; combination wording. The
  C7 report was revised (commit 68dc6be): conditional-consistency wording and the post hoc truncation-aware estimate
  −322524 ± 38 shown alongside.
- **Round 2 APPROVED.** Reviewer limitations, recorded: static review, remote records and executables not reproduced;
  the 100 % tail-model uncertainty has no established coverage; first-order propagation through the data-derived tail
  gives 18.8 instead of 18.6 (the doubled value stays 38); the A5 failure and the absence of degree-8 data remain, so
  the approval does not establish the total C7 accuracy at the ±40 level.

## 4. Public export (2026-10-13)

The public replay scripts (`public/replay7.py`, `public/replay7_full.py`, `public/make_data_archive.py`) were written
by a Claude Code helper session for this export. They have not been reviewed by Codex. Tier 1 was run (214 checks,
no FAIL); Tier 2 has not been run yet.

Update 2026-10-14: the archive was built and Tier 2 run on Expanse on 2026-10-13 (Slurm job 54901438, by C71d):
`make_data_archive.py` selected 35,115 files and checked 14,365 merged streams against `C7_final.json`; Tier 2, run from
the unpacked tarball, passed all 14 checks (`combined_assembly.json` and `C7_final.json` byte-identical, C7_full,
sampling and bootstrap SE, half splits, 399 per-batch results). On 2026-10-14 it was repeated from the export on symmetry:
byte-identical on Intel; on AMD two fields that assemble.py forms as differences of nearly equal numbers missed the
1e-12 self-relative tolerance (by 1.6e-12 and 2.7e-12), so replay7_full.py now compares those two to 1e-12 of their
inputs, and the AMD rerun passed. That change is not Codex-reviewed. These are runs, not reviews.
