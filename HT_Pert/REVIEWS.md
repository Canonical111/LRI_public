# Reviews of the HT_Pert packages

Summaries of the code and results reviews of each package (reviewer, rounds, verdict, what changed). Raw review logs are not published.

Assembled from the package authors' texts. Inside a package section, relative paths are relative to that package's folder `code/<package>/` unless they start with `HT_Pert/`. The values themselves are in `note/README.md` and the note.

- d = 1: exact C2..C5(Lambda) sums: `lri_1d_c4_exact`, `lri_1d_c5_exact`
- d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian: `lri_hpc_Hamitonian`, `lri_eh_hpc`
- d = 1: HT C8 and the complete-window coefficient flow: `lri_c8_hpc`, `lri_d1_full_coefficient_flow`, `lri_1d_dconn_refit`, `lri_d1_fullblock_tail_response`
- d = 2: coefficients C2..C8 and the independent check: `lri_d2_coeff_hpc`, `lri_2d_coeff_independent_check`
- d = 3: exact C2..C5(L) sums and the coefficients C2..C8: `lri_3d_c4_exact`, `lri_3d_hpc`

## d = 1: exact C2..C5(Lambda) sums

### `lri_1d_c4_exact`

Folder: `code/lri_1d_c4_exact/`.

#### Reviews: lri_1d_c4_exact

The work followed the claudex loop: a plan reviewed by OpenAI GPT-6 astra (Codex CLI, xhigh), a build by the Claude
Code session, and an inspection by a fresh Codex session.

- **Plan review (2026-10-12).**
  - Round 1: REVISE. Findings:
    - a double count of the slice sign in both the amplitude and g;
    - gate separation;
    - masking of cut4 < 3;
    - memory sizing.
  - Round 2: REVISE. Findings: in-place accumulation and measured-RSS sizing.
  - Round 3: APPROVED.
- **Code inspection round 1 (fresh session): REVISE, 7 findings (6 medium).** All accepted and fixed in d62b236:
  - snapshot identity and gate records bound to result hashes;
  - NaN and grid checks;
  - ΔR4 range;
  - blind-fit protocol;
  - leading-log option;
  - provenance;
  - job prefix.
- **Code inspection round 2 (fresh session): REVISE, 3 findings.** All accepted and fixed in 5a40e72:
  - CLI argument validation;
  - fit coefficients kept as 50-digit strings instead of rounding to float64 before prediction;
  - empty-grid handling.
  The inspection budget was then exhausted, so **the fix-round-2 edits were not re-inspected**. They do not touch the
  numerics: the production results agree with the validation runs and the HT data to 1e-12.
- **Checks after production.**
  - The blind protocol: fits frozen from Λ ≤ 1000 predicted Λ = 2000.
  - The lower orders C2, C3 agree with the C5 package's runs to 1e-12 (A6e of lri_1d_c5_exact).

### `lri_1d_c5_exact`

Folder: `code/lri_1d_c5_exact/`.

#### Reviews: lri_1d_c5_exact

The work followed the claudex loop: a plan reviewed by OpenAI GPT-6 astra (Codex CLI, xhigh, Fast mode), a build by
the Claude Code session, and an inspection by fresh Codex sessions.

- **Plan review.**
  - Round 1 (2026-10-12): REVISE. Findings: separate the physical and storage shell indices, separate the benchmark and
    production gates, and add prototype evidence for the five-vertex kernel.
  - Round 2: APPROVED.
- **Code inspection round 1: REVISE.** All accepted and fixed in f3ae8ab:
  - worst-case benchmark sizing;
  - densities without full copies;
  - exhaustive A6a with a strict A6c;
  - a cancellation-free ΔR5 engine, gated at 1e-14;
  - a PRELIM gate for benchmarks;
  - the ω3 diagnostic;
  - gate-then-publish assembly and its recovery.
- **Code inspection round 2: REVISE.** All accepted and fixed in f6f854b:
  - no canonical publication of failed rungs;
  - gated fit inputs;
  - reuse and archiving of validation rungs;
  - the freeze output directory;
  - the benchmark warm-up.
  The inspection budget was then exhausted, so **f6f854b was not re-inspected**.
- **Validation 574003 failed one sub-gate (A5 rows4 against the reference column).** The reference column carries its
  own fit noise of about 6e-12. The gate was changed to the exact identity on the reference A4/B4 (29a9985, **not
  inspected**), and validation 574043 then passed. The same snapshot ran all production.
- **Cited checks of the constrained fit** (two Claude Code subagents, 2026-10-13):
  - **Theory:** SUPPORTED. It derives w1 = 7/2 as the first-order coefficient of ω = Δ_{φ⁶} − 1, and the top-log
    closed form.
  - **Blind re-implementation:** −731.13 ± 0.10. It finds the ε⁴ top log 0.28 % off the prediction in some bases;
    this is undecided, and it changes the C5 limit by ≤ 0.0013.

## d = 1: thermal HT coefficients C2..C7 and the effective Hamiltonian

### `lri_hpc_Hamitonian`

Folder: `code/lri_hpc_Hamitonian/`.

#### Reviews: lri_hpc_Hamitonian

The review logs and transcripts are not published. Codex = Codex CLI, model gpt-6-astra, effort xhigh. Host = the
coordinating Claude Code session (claude-opus-5-5; the session now named HT1dPert).

##### Plan review (claudex loop, 2026-09-29; one resumed Codex session)
- Round 1: REVISE, 7 findings: LRI-001 high (no result acceptance gates), LRI-002..007 medium. LRI-004 led to
  byte-identical model code in the extended analysis, LRI-007 made the window diagnostic conditional.
- Round 2 (repo 74b0ac0): REVISE: LRI-003 partly open, LRI-008, LRI-009 (low), LRI-010. Fixed in 6583645.
- Round 3 (repo 6583645): REVISE: LRI-011 high (malformed sbatch arguments), LRI-012 high (failure classification),
  LRI-013 high (duplicate-submission race), LRI-014 medium (exhaustion not persisted). Fixed in cd20385.
- Round 4 (repo cd20385): REVISE: LRI-013 (claim not held by the solver; SIGTERM), LRI-015 (lane-level deadline).
  Fixed in f0a7084.
- Round 5: **APPROVED**, no findings (plan revision 5; code f0a7084). A static review: the validation job, scheduler
  behaviour and locking were not independently verified, and the reviewer noted that goals G3 and G6 (diagnosis,
  extended analysis) were not covered.

##### Code inspections (fresh Codex sessions)
- I1 on 67b009f..c209890: REVISE, IR-001..IR-005, all medium (retry admission, persisted memory rejections, export
  source gate, overlap-checked merge `tests/test_extended_merge.py`, the UPDATED_RESULTS generator with honest threshold
  provenance). Fixed in 6f97ba7 and d9c6efd.
- I2 on ..d9c6efd: REVISE, IR2-001 (the tail-insensitivity criterion ignored C5), IR2-002 (result identity at
  acceptance), IR2-003 low (completion inventory). Fixed in e1690e8. The inspection budget (two rounds) was then used up:
  **e1690e8 is not re-inspected**. Its edits touch tooling and the protocol generator only; the solver fingerprint is
  unchanged, and 10 φ⁶ d3 records ran from it.
- Post-approval deviation: the large-shared lanes were resubmitted with 64 cores. Everything after e1690e8 (data
  refreshes, the report, the lower-edge study, `stress_test/`, `eh_review/`, `identity_checks/`, `eps5_window/`,
  DIAGNOSIS §§9–12) had **no Codex review**.

##### Host code review (`review/CODE_REVIEW.md`, shipped)
F1 high, fixed: acceptance gates. F2 medium, fixed: the full-recursion test asserts. F3 medium, partly fixed: int64 path
tested on a shard. F4 medium, fixed for Expanse: Slurm templates not deployable. F5 documented: the memory screen is
about 2× conservative. F6 fixed: thread count recorded. F7 not changed: the tests write into `benchmarks/` (the public
test runs on a copy). F8 documented: report text vs code. The `analysis_original` fits reproduce to ≤ 6e-7, with an
independent audit (`analysis/audit_fits.py`) to 2e-11.

##### Validation jobs (Expanse, all PASS)
54519867 (74b0ac0), 54520113 (6583645), 54520360 (cd20385), **54520426 (f0a7084, the production gate)**, **54521491
(e1690e8, the top-up gate)**: full test suite, regressions against the saved tables (thermal Λ = 40, 50 ≤ 1.5e-9
absolute; φ⁶ d5 Λ = 50 ≤ 2.0e-10; d3 Λ = 128 ≤ 5.5e-12; tolerance 1e-7 + 2e-11 |x|) and calibration runs.

##### Internal verification of the analysis workflows (host-run multi-agent workflows; journals not shipped)
- `stress_test/` (not shipped): four lenses "supports", the higher-orders lens "weakens → inconclusive"; it corrected
  DIAGNOSIS §9 (the noise is 1e-12, not 1e-9; floor-level fits give −1.92 to −1.80 × 10⁻³ for the raw C4 offset).
- `eh_review/` (review of lri_eh 0.2.0; see `code/lri_eh_hpc/REVIEWS.md`).
- `identity_checks/`: engines A and B agree to ≤ 8e-13 on 1688 numbers and to 2.9e-14 against exact rationals; top-level
  shift 0.01869099.
- `eps5_window/`: A vs B ≤ 9.6e-12 on 3808 numbers; engine B's four algorithms agree ≤ 1.3e-11; the challenge engine
  `ht5.py` agrees ≤ 2.4e-12. Numerical challenge "upheld"; theoretical challenge "weakened", whose reading DIAGNOSIS §12
  adopted over the reconciler's.
- No Codex results review was run on the analysis.

##### Public-release replay (2026-10-14, builder A of HT1dPert)
- Every quoted value was recomputed from the shipped records (`results_map.md`); no paper value changed.
- Three numbers existed only in the unshipped workflow summaries and are now computed by new public scripts:
  ω₃,eff of the free-exponent and E+zh fits (`public/omega3_eff.py`, with a selection rule fixed here: |C5 − exact| ≤
  0.25, range rounded to 10, giving 377.7–431.4 → 380–430), and the engine agreements (i) 1.26e-11 and (iii) 2.37e-12
  (`public/engine_agree.py`).
- `\HTpIdentThree` (0.003), `\HTpIdentFour` (96–100) and `\HTpIdentFive` (0.1–0.2) are readings of tail-fit
  extrapolations; their rules are stated in `results_map.md` (reading (single-state sectors); reading (range
  contains)). The cutoff-placement statement
  "agrees with the computed correction" (g²D alone at Λ = L + ¼: 0.050 [0.042, 0.056] against 0.0561) stays a judgement
  (INFO).
- Portability: on the acceptance stack (Intel, numpy 2.3.5) the reruns differ from the shipped outputs by up to 4e-6
  relative in fitted C5 and 13 % in condition numbers of near-singular fits; the replay compares with stated tolerances
  and requires the quoted readings on both the shipped and the rerun outputs.

##### Independent verification (2026-10-14, Claude Code verifier session of HT_Pert d = 1)
- Own simulated export, test, replay, smoke and replay-full on symmetry (Intel Xeon 6148): all PASS; every computed
  value equal to the builder's; independent recomputation from the records agrees; no numerical or code defect.
- Findings, all documentation or wording, fixed 2026-10-14 (builder A): provenance of the supplied archives (now
  "OpenAI GPT-6 astra (via ChatGPT), supplied by the author as …" with the zips' sha256); the tolerance words of the
  identity rows; the ε³ identity row now prints the degenerate 2×2 block P = 2, N = 2 (+0.0063 W) and ∂φ³, ∂φ⁴ (−0.115 W,
  −0.369 W) as reported, outside the single-state bound; the `\HTpEngineAgree` scope Λ ≤ 60 (Λ = 64 gives 2.2e-11) is
  stated; macro fields carry the backslash; counts (16 scripts, 269 KB).
- Recorded for the author: the cutoff-placement statement "agrees with the computed correction" leaves a residual
  δC4 ≈ +0.002 with D^conn, about 10 % of 0.0187 (judgement row `a1.phase.g2D`).
- Paper change of 2026-10-14: the solver-fit C4/C5 readings of this package are note-only macros of the HT_Pert note
  (`\NOneCfourSolver`, `\NOneCfivePre`, `\NOneCfiveSolver`); values and checks unchanged.
- After the fixes, a fresh simulated export placed under node-local `/local1/<USER>/<job>/HT_Pert` passed test, replay
  and smoke on Intel Xeon 6148 and AMD EPYC 7532 and replay-full on Intel, with the same verdicts and readings on both
  CPUs (`TESTS_lri_hpc_Hamitonian.md`).

### `lri_eh_hpc`

Folder: `code/lri_eh_hpc/`.

#### Reviews: lri_eh_hpc

The review logs and transcripts are not published. No Codex review was run on this package.

**Host multi-agent review (2026-10-02)** by the coordinating Claude Code session (claude-opus-5-5, the session now named
HT1dPert): four lenses (correctness, physics impact, readiness, theory), each with a verifier; archived in
`code/lri_hpc_Hamitonian/analysis/eh_review/` (commit 9b475cf of that repository; only the physics-impact tables ship).
- **Correctness: no defect found.** The exact ΔC4 agrees with the solver to ≤ 2e-16; a from-scratch solver agrees to
  1.2e-9; the package's tests pass (32/32, 15.9 s on the personal desktop's older stack).
- **Physics findings.** (1) K = 0.0616119308… is a finite part of this isolated prescription, not a physical
  counterterm; (2) the third-order bubble is missing, so the isolated g²D overstates ΔC5 by 0.123; (3) the log Λ/17496 is a window artifact; (4) a folded term adds +1.41e-3; (5) the "one- and two-body
  defects" are the window. These motivated the complete window D^conn of `code/lri_hpc_Hamitonian/analysis`.
- **Readiness:** not launch-ready as shipped for a campaign (srun without `-c`; `join_campaign.py` refuses the Λ ≤ 50
  raw rows). Neither affects the HT_Pert use (the tables were made with `gen_deltas.py`, not with the campaign tools).

**Supplier's validation** (OpenAI GPT-6 astra (via ChatGPT), the build of
`lri_effective_hamiltonian_campaign_update.zip`; receipt shipped, `a1.eh.receipt`): 32/32 tests in 2.7 s and
`validate_release` PASS in the supplier's container.

**Public-release checks (2026-10-14, builder A of HT1dPert):** `make test` reran the package's release validation on
the acceptance stack (32 passed, sealed receipt with the same source fingerprint); `smoke` and `replay-full`
regenerated the g²D tables and agree with the shipped ones (`TESTS_lri_eh_hpc.md`). No value changed.

**Independent verification (2026-10-14, Claude Code verifier session of HT_Pert d = 1):** own simulated export; test,
replay, smoke and replay-full PASS; no numerical defect. Findings (documentation): the provenance of the supplied
archive (now "OpenAI GPT-6 astra (via ChatGPT), supplied by the author as …") and `"macro": null` in the quoted json;
both fixed. After the fixes, a fresh export under node-local `/local1/<USER>/<job>/HT_Pert` passed test, replay and smoke
on Intel Xeon 6148 and AMD EPYC 7532 and replay-full on Intel.

## d = 1: HT C8 and the complete-window coefficient flow

### `lri_c8_hpc`

Folder: `code/lri_c8_hpc/`.

#### Reviews: lri_c8_hpc

Codex = Codex CLI, model gpt-6-astra, effort xhigh (codex-cli 0.158.0). Host = the coordinating Claude Code session
(claude-opus-5-5), session HT1dPert (named "Hamitonian" at the time), which ported the package on 2026-10-03 and ran it
on 2026-10-04.

##### Code inspection of the symmetry port (claudex loop, inspect mode; 2026-10-03)
- **Setup.** Base 7dc714d (the supplied archive). Eight rounds, each by a fresh Codex session, 12:49–14:37 EDT. There
  was no separate Codex plan review; the plan the rounds reference was not archived.
- **Round 1: REVISE, 9 findings** C8-001..009 (3 high, 6 medium). Fixed in 51dd066. The inspector noted that the
  numerical engine and planner were unchanged.
- **Round 2: REVISE, 5 findings** C8-010..014 (1 high, 3 medium, 1 low). Fixed in e1abc41.
- **Round 3: REVISE, 4 findings** C8-015..018 (1 high, 3 medium). Fixed in 9540e6a.
- **Round 4: REVISE, 4 findings** C8-019..022 (2 high, 2 medium). Fixed in 937067d.
- **Round 5: REVISE, 2 medium** C8-023, 024. Fixed in 07d39a3.
- **Round 6: REVISE, 1 medium** C8-025. Fixed in 9bd5505.
- **Round 7: REVISE, 1 medium** C8-026. Fixed in 529f208.
- **Round 8: APPROVED 529f208, no findings.** "No material unresolved defects found in the static review. Compute-node
  validation remains required before production submission."
- **In total** 26 findings (7 high, 18 medium, 1 low), all accepted and fixed. None was overruled or deferred, and
  every fix was re-inspected by the next round. Topics:
  - errexit lost in the batch scripts;
  - a missing submission mutex;
  - journal and owner races on BeeGFS, whose flock is node-local;
  - inherited `SBATCH_*`/`SQUEUE_*` variables overriding the batch directives;
  - the solver not owning its checkpoint;
  - enforcement of the validation receipt and of the frozen campaign.
- **Records.** The raw inspection logs are kept in the author's archive, not shipped (rule 2).

##### Checks after the review (host)
- **Compute-node validation job 569659 passed** (receipt, row `c8.validation`):
  - 164 manifest files;
  - pytest 74 of 74 with a fresh Numba cache;
  - the 38-point saved-grid replay bitwise equal to the bundled grid;
  - the original solver against both backends at Λ = 60: raw max |ΔC| 2.0e-8, vacuum_only 7.5e-9, stored = ranked
    (row `c8.original`);
  - the BeeGFS probe.
- **Production array 569698**: every lane accepted on its first attempt (row `c8.lanes`). The measured peak RSS was
  0.63–0.66 of the conservative plan.
- **Cross-check with the thermal campaign**: raw C0..C7 agree with the separate thermal campaign of
  `lri_hpc_Hamitonian` (same `lri_hpc` core; different driver, cluster and runs) to 6.1e-14 relative (row
  `c8.thermal`). Both codes share the Fock-space and operator construction (`PROVENANCE_lri_c8_hpc.md`), so this checks
  the eighth-order driver, the assembly and the runs, not that construction.

##### Not reviewed
- The Codex review was static. On the cluster, numerical equivalence with the original solver was checked only at
  Λ ≤ 60; the C8 values at Λ = 52..92 rest on the internal gates and the C0..C7 cross-check with the separate thermal
  campaign (same `lri_hpc` core).
- There was no Codex review of the campaign results.
- The four-lens C8 extrapolation of 2026-10-04 was not reviewed by Codex either. It was re-derived lens by lens by
  independent Claude Code verifiers (linked-joint adjusted; the other three confirmed). It is superseded and not
  shipped.
- `public/` (2026-10-14, including the fix-round helper `public/rehash_manifest.py`) was not reviewed by Codex. It
  reads records and reruns the package's own scripts; it changes no shipped file. The rehash helper writes only the
  manifest of a working copy outside the published layout.

##### Public-release checks (2026-10-14)
- The replay recomputes every row from the shipped records.
- The C8 table of the HT note (13 rows) is reproduced as printed.
- No quoted number needed a correction.
- **One portability finding.** With Python 3.12.9, numpy 2.3.5, numba 0.68.0, no tbb and Numba's default threading
  layer, two tests failed on the configuration fingerprint: `test_cli_and_shard_assembly` and
  `test_export_mixed_threads_and_backends`.
  - Cause: the threadpoolctl library list in each output's configuration has a load-order-dependent order (libgomp vs
    OpenBLAS).
  - No number is affected.
  - `public/run_tests_c8.py` therefore pins the layer, as the production environment does. With it, all 74 tests pass
    on both stacks.
- See `TESTS_lri_c8_hpc.md`.

##### Independent verification of the public export (2026-10-14)
- **Verifier**: an independent Claude Code (claude-opus-5-5) verifier spawned by the HT1dPert workflow. It built its
  own simulated export and did not use the builder's trees, logs or results.
- **Runs**: symmetry defq job 575032 (Xeon Gold 6148, default `THREADS=4`): `test`, `replay`, `smoke` and
  `replay-full` PASS on the acceptance stack, on a scrubbed copy and on the production stack; replay 10 PASS, 1 SKIP
  without the thermal records. Mutation tests (changed values, edited src files, deleted journals, a changed thermal
  digit) each make the replay fail.
- **Every quoted value equals its source**; privacy and size are clean. Verdict: FIXES NEEDED (documentation only).
- **Findings and their resolution** (fix round, same day):
  - M1 (medium): the C0..C7 cross-check was called "independent" although the `lri_hpc` core is shared. Fixed: README,
    this file, `quoted_lri_c8_hpc.json`, `results_map.md`, the replay docstring and PROVENANCE now say "separate thermal
    campaign (same `lri_hpc` core; different driver, cluster and runs)" and name the shared files.
  - M2 (medium): REPRODUCE did not say how to obtain a passing receipt in the public tree; the original manifest check
    fails on scrubbed or adapted files, so `make_campaign` refuses. Fixed: new `public/rehash_manifest.py` (rehashes the
    164 listed files of a working copy; refuses the published layout and any change under `src/`) and a step in
    REPRODUCE section 5, allowed explicitly under "Decisions you must not make". Demonstrated on symmetry
    (`TESTS_lri_c8_hpc.md`).
  - L1: the paper's HT section was removed from main.tex. Fixed: the docs name the HT_Pert note as the place the numbers
    are quoted.
  - L2: the note's provisional rows used `c8.lmax`. The package keeps `c8.reach`; the note will use the package ids.
  - L3: `d1/export_entries.json` holds an older copy of the data entry (byte-identical export). Left to the d = 1
    merge (HT1dPert re-merges from `entries_lri_c8_hpc.json`); this fix round writes only in the package folder.
  - L4: PROVENANCE wording (session name, GPT-6 astra baseline, authorship of `reference/HPC_CAMPAIGN_REPORT.md` and
    `reference/check_lri_hamiltonian.py`). Fixed.
  - L5: the 42 lane journals ship. They are machine-written, self-hashed Slurm records, not agent workflow journals;
    DATA now says so (record-bound, D1).
  - L6: stale job ids and 8-core costs. Fixed: costs are given for the default `THREADS=4` (jobs 575032 and the fix-round
    jobs), and the docstrings cite the final jobs.

### `lri_d1_full_coefficient_flow`

Folder: `code/lri_d1_full_coefficient_flow/`.

#### Reviews: lri_d1_full_coefficient_flow (S10)

**The supplied engine** (OpenAI GPT-6 astra, via ChatGPT) was not reviewed as a whole. Its internal tests pass (exact
Fraction stationarity of the half-order quotient, fresh full-order runs at L ≤ 28 against the vendored ordinary and
exact-Fraction references, forecast replay). The coordinating Claude Code session checked it against the HT solver:
- raw controls agree with the HT raw coefficients to 3e-14;
- D^conn dC4 and dC5 at L ≤ 44 agree with the reconciled exact windows to about 1e-12 (the delta stage of the refits
  measures 6.2e-13 and 1.24e-11).

**The symmetry extension** was inspected by Codex (Codex CLI, gpt-6-astra, effort xhigh; read-only, base = the zip as
received, commit 1ff8cfd), four rounds on 2026-10-08:
- **Round 1: REVISE, 4 findings, all fixed in 91e7755.**
  - S10-R1 (high): production was not gated on a passing validation.
  - S10-R2 (medium): the cutoff range was not limited to 46..72.
  - S10-R3 (medium): race between squeue and sbatch.
  - S10-R4 (low): lock-read race (exit 1 instead of 73).
- **Round 2: REVISE, 3 findings, all fixed in cd3740e.**
  - S10-R5 (high): mutable checkout; the source was hashed after the solve. Fixed with an immutable snapshot and a
    node-side sha256 check.
  - S10-R6 (medium): the gate trusted compare.json. It now recomputes the comparisons against archive records pinned
    by sha256.
  - S10-R7 (medium): octal cutoffs were accepted.
- **Round 3: REVISE, 1 finding, fixed in fec60a2.** S10-R8 (medium): 64-bit wraparound of long decimal cutoffs; fixed
  with an exact string whitelist.
- **Round 4: APPROVED at fec60a2.** The solver that Codex inspected (sha256 854fc763…) is the one that ran every
  production record.
- Every round's coverage note says the review was static: the bitwise claims and the cluster behaviour were not checked
  by Codex. They were checked by the session (bitwise identity to the baseline at L = 8, 16, 20) and by the cluster
  validation job 571525 (PASS).

**After production.**
- The S1B verifier (an independent Claude Code subagent, 2026-10-09, see `code/lri_1d_dconn_refit/REVIEWS.md`)
  recomputed the dC table (equal to S10 C minus the C8 campaign's raw values, exactly), and found dC4/dC5 at
  L = 46..72 within 2.0e-11 of the reconciled windows.
- It also confirmed that the S10 D^conn values at L = 46..72 carry about 1e-13 relative noise (finite differences
  2–3.5e-10, 1e-8, 1.1e-7 on dC6, dC7, dC8). Two raw engines agree to 7.6e-11 (C6) and 1.5e-9 (C7) there, so the noise
  is in the S10 values themselves. The refits handle it (row rf.noise of the refit package).

**Public-export verification** (2026-10-14, an independent Claude Code subagent, not the builder). It rebuilt the
simulated export with the producers' real entries, recomputed every quoted number with its own code (manifest, solver
binding, the dC table byte for byte, `\HTpWinLamEight`, `\HTpSTenMatch`), ran test, replay and smoke on symmetry
(job 575023) with negative controls, and found the package READY. Its two low findings (attribution of the vendored
archives in PROVENANCE, "personal desktop" wording in the test log) were fixed the same day.

The raw review outputs are not shipped (rule 2).

### `lri_1d_dconn_refit`

Folder: `code/lri_1d_dconn_refit/`.

#### Reviews: lri_1d_dconn_refit

**No Codex review** was run on any stage of these refits; every stage result says so.

**Internal verifier** (Claude Code subagent "verify" of the same workflow, 2026-10-09). It used its own code
(`verify/code`): a loader from the source files, 320-bit arb least squares, an independent noise-weighted continuation
of dC6..dC8, an independent linked joint fitter and an independent model-independent primary family. A full hi = 92 grid
ran as symmetry job 572083. Verdict: **"Mostly confirmed, with adjustments."**

- **Reproduced exactly.**
  - The corrected tables (floor-mean primary, run-1 table, floor-medoid file) match bit for bit.
  - The dC table equals S10 C minus the C8 campaign's raw values; dC4/dC5 at 46..72 match the reconciled windows to
    ≤ 2.0e-11; the frozen hi = 44 forecasts land within 0.099 of the typical uncertainty.
  - Joint lens: 1,117 sampled scan records in every dataset, and every headline: fixed A–F C6 +5.60 [+0.92, +10.08],
    C7 −192, the paired shifts, the floor+stat ensembles, the calibrated C8 8,065,157 / 8,065,189 / 8,065,256, the
    uncalibrated family medians, the delta-free hi = 72 values.
  - Model-independent lens: primary 8,064,938 / 8,061,658, s46 8,065,419 / 8,062,893, C6 14328.00, C7 −322614.
- **Medium issues** (the quoted values are unchanged; the caveats enter the note):
  1. The model-independent C8 changes from run 1 (−543 calibrated, −1,251 uncalibrated) are a noise-induced selection
     bias, not a physical shift. A Monte Carlo of S10-like noise on the noise-free table gives −574 ± 133 / −416 ± 112.
     The noise-free s46 values (8,065,419 calibrated, 8,062,893 uncalibrated) are the better model-independent central
     estimates.
  2. The model-independent window stability (hi = 72 vs 92 within 192) is an artefact of opposite noise shifts. The
     realistic window term is about 400 (calibrated), still below the family spread.
  3. The joint lens's delta-model systematic on calibrated C8 (about ±140) depends on the continuation family assumed.
     With the verifier's validated members it is about −0.7e3 / +0.1e3.
  4. The published default central `delta_v1_hi72_corrected.json` (pointwise median) has a seam step at 72/74 (about
     −4e-7 in dC7, +5–7e-6 in dC8) and is not fit-ready. Neither lens used it (they used the floor-mean and
     floor-medoid tables).
- **Low and info findings.**
  - The stages' suggested noise fix ("compute S10 raw at 46..72") rests on a misreading: the noise is in the S10 D^conn
    values, since two raw engines agree to 7.6e-11 / 1.5e-9 there.
  - The lenses' noise model is 1.1–1.9 times too large for dC7 and dC8.
  - A minor ratio misstatement.
- **Adjusted reading (verifier):** C4 and C5 unchanged; the fixed bases still give C4 = 45.4155–45.4189; "realistic
  overall calibrated range stays about 8.061–8.067e6", consistent with the diagrammatic C8 but not a sharp test.

**Run 1** (2026-10-08) had its own verifier stage: "MOSTLY CONFIRMED, WITH ADJUSTMENTS".

**Public-export verification** (2026-10-14, an independent Claude Code subagent, not the builder). It recomputed the
quoted values with its own scripts (frozen forecast and blind check, the fit unions, C8 sel67), ran test (bitwise),
replay and negative controls on symmetry (job 575023), and found one medium documentation issue: the README said the
quoted C6..C8 come from the weighted fits, while the fixed A–F component of C6 and C7 uses the unweighted dataset
(with the weighted one the C7 lower end would round to −322,900). Fixed the same day: every union component now names
its dataset, the weighted alternative is printed as INFO row rf.C7w, the rounding rule of every union is stated, the
fallback tolerance of `test` is field-scaled, the five derived delta tables are classed scrubbable, and the raw joint
scans were copied to the authors' archive. No quoted value changed.

The workflow journal holds the raw stage results and is not shipped (rule 2). Every quoted number is replayed from the
shipped JSON outputs instead.

### `lri_d1_fullblock_tail_response`

Folder: `code/lri_d1_fullblock_tail_response/`.

#### Reviews: lri_d1_fullblock_tail_response

The review logs and transcripts are not published. "Host" is the coordinating Claude Code session, HT1dPert
(claude-opus-5-5); on 2026-10-07 it was still named "Hamitonian".

There was no Codex review of this package or of its review, and no plan or code inspection: the package was received
as a finished research bundle (OpenAI GPT-6 astra).

##### The review of 2026-10-07 (Claude Code workflow, host HT1dPert)

**Setup.**
- The review covered `lri_1d_complete_phase_overlap_tails.zip`, the tails bundle. This package is nested in it,
  unchanged, as an upstream, and the review used it as the source of the outer matching formula (METHOD Eq. 3).
- Three lenses (derivation, numerics, relevance to the HT tail fits) each wrote their own code. An independent
  adversarial verifier then checked each lens with its own code.
- The jobs ran on a personal desktop (Slurm jobs 308, 311, 324, 333, 334 and 336) and on the author's Mac.

**Verdict on the bundle: correct.**
- Every closed form was re-derived independently.
- Two analytic routes reproduce the bundle's finite parts to about 1e-28 relative.
- The bundle's own test suites pass: 6/6 stages, and 5/5 for its upstream.
- The minor issues found (misprinted last digits in the bundle's REPORT, a weak inequality test, a misleading section
  title) concern the tails bundle itself, which is not shipped, not this package.

**Checks that bear on this package.**
- **Integrity.** All three nested manifests verify, this package's 108 entries included.
- **Independent G_π convolution.** One verifier wrote its own convolution, taking only the 38 rational Wick weights as
  data. It reproduces this package's ε⁴ phase susceptibility S_phase,4(μ), which `code/response.py` computes with a
  Fock-space Taylor engine, at μ = 2, 4, …, 28 to 3.6e-15. Raw equals Dconn at ε⁴ for both the phase and the number
  part.
- **Normalisation of Eq. (3), through the φ⁶ channel.**
  - With S_Φ6,2 = −40/9, the φ⁶ term gives the leading C2 tail −40/(81√π) Λ^(-1/2) = −0.27861 Λ^(-1/2). The HT data's
    C2 tail T2 has T2·√Λ = −0.27950 at Λ = 118.
  - With μ = Λ and the S_Φ6,3 log coefficient 40/3, Eq. (3) gives the C3 coefficient of log Λ · Λ^(-1/2) as
    140/(81√π) = 0.975142. The HT fit gives 0.97513, which corresponds to ω₁ = 7/2.
  - So identifying μ with Λ works at leading log for the φ⁶ channel.

**Not verified.**
- The operator definitions (J^P, V, the thermal combination) were taken from the documentation.
- The K3 J coefficient of Eq. (2) was not re-derived.
- The **sign and normalisation of the J insertion**, a C4 tail term −2/(3√π) Λ^(-1/2) S_J,4, were rated
  **"plausible"**: internally consistent with Eq. (3) and with the package's partial assembly, but not derived.
- The amplitude 2/(3√π) and any use of B in a C4 tail are therefore unverified. Public row fb.unverified.

**Relevance to the HT fits.**
- **Direct use: none.** The bundle's new numbers (κ5..κ8, R_d) belong to one tagged subgraph class of S_J. They are
  scheme dependent, and R_d enters only at order Λ^(-1).
- **Structural lesson** (from this package): there is a second outer Λ^(-1/2) channel, the regulator-phase J channel
  Λ^(3α−2) S_J, starting at ε⁴, next to the φ⁶ channel. Tying the C_n log coefficients to the gaps ω_k is therefore
  not exact. This is the sentence the paper uses.
- **The data agree.** Freed-tail fits prefer ω₂,eff = −29.75 to −31.69, against −29.552.
- **"J-informed" C4 misses.**
  - Inserting the ε⁴ phase-class log coefficient B with the factor 2/(3√π), with no free parameter, reduces the
    Dconn-corrected C4 miss from −0.006…−0.0096 to about −0.001…−0.004.
  - The verifier showed this is suggestive, not evidence. Other one-term extensions fit equally well, with misses from
    −0.0051 to +0.0113. The √μ term, inserted at μ = Λ, alone shifts C4 by −0.0034. The number part's log coefficient
    was only extrapolated (±0.05).
  - These misses are not quoted in the paper and are not replayed.
- **Open, as the review left it.**
  - The exact ε⁴ number-part asymptotics, with the ε⁴ overlap and hard-kernel matching. These would fix the C4
    Λ^(-1/2) log coefficient.
  - The complete ε⁵ J-channel log coefficient.

##### Public-release checks (2026-10-14, builder D)
- **Shipped files.** The 109 files are byte-identical to the members of the supplied zip, and `MANIFEST.sha256`
  verifies.
- **`public/replay_fb.py`** recomputes:
  - the structural facts: the power, and the onset at ε⁴ from the operator, the exact rationals and the 13 response
    records;
  - the prefactor arithmetic;
  - B;
  - the 36 annulus comparisons.

  Details are in `TESTS_lri_d1_fullblock_tail_response.md`.
- **No paper value changed.** None is quoted from this package.

## d = 2: coefficients C2..C8 and the independent check

### `lri_d2_coeff_hpc`

Folder: `code/lri_d2_coeff_hpc/`.

#### Reviews: lri_d2_coeff_hpc (summary; no raw review logs are shipped)

##### Code review of the cluster port (2026-10-08)
The delivered solver (baseline commit 8db8f15 = `lri_2d_coefficients_hpc_optimized.zip`, sha256 94edc677…, an
optimization of `lri_2d_C8_perturbative_check.zip`, kept in `reference/lri_d2_perturbative_C8/`; both written by OpenAI
GPT-6 astra via ChatGPT) was made runnable on SDSC Expanse and the symmetry cluster by a Claude Code session
(commits 0d99d55..f847d38), with OpenAI Codex as inspector (`gpt-6-astra`, effort xhigh). The solver source `src/lri_coeff` was not changed (source digest 550e9266… before and
after); every change is in the cluster layer, scripts, tests and documentation.

| round | findings | fixed in | topics |
|---|---|---|---|
| r1 | 9 (LRI-001..009) | c606cbd | private node-local job directory; staged-source PYTHONPATH; node-local checkpoints with one published archive per task; signal forwarding; site environment scrubbing; validation test count; output reservation across manifests; partition time caps; receipt fields |
| r2 | 5 (LRI-010..014) | 3e2ef17 | read-back of the checkpoint archive before rename, exit 76 for an unpublished newest checkpoint; job names from the output path; loud failure on journal-write errors; refusal of shared graph caches; umask |
| r3 | 3 (LRI-015..017) | f847d38 | digest verification of every checkpoint member (local and read back); retry/reporting of publication errors; output-path job names in dry runs; corruption tests (61 tests) |
| r4 | none | — | **APPROVED at f847d38** |

##### Validation on the clusters (release lri2d_coeff-f847d38db8bd.tar, sha256 2e2edf6c…)
- symmetry, job 571623 (amdq, AMD EPYC 7532, 64 threads): 61 tests passed; replay of the archived L = 22 pilot to
  ≤ 1.6e-13 (rtol 1e-10 required). Receipt: `data/HT_2d/prod/prod1_symmetry/validation_571623/`.
- Expanse, job 54765932: the same checks, bitwise equal to symmetry. Receipt:
  `data/HT_2d/prod/prod2_expanse/2e2edf6c3153252b_expanse_54765932/`.

##### Independent verification of the numbers (2026-10-08..14)
The finite-cutoff coefficients were checked by codes written without the package (`code/lri_2d_coeff_independent_check`):
a clean-room exact-rational Rayleigh–Schrödinger solver (L ≤ 18, every scheme, all C_n, r_n, g_n, E_p and vacua) agrees
with the production records to 3.9e-13 (scaled), and a clean-room non-perturbative Cauchy-integral solver (L ≤ 8)
agrees with the exact solver to 5e-46 and with the package to 1.6e-14. See that package's REVIEWS.md.

##### What the reviews did not cover
The window prescriptions (raw, consistent, literal) are inputs of the delivered package; the reviews and checks verify
that the package computes them correctly, not that they give the continuum coefficients. In d = 2 they do not beyond
ε³ (see the HT_Pert note and `lri_2d_coeff_independent_check`).

### `lri_2d_coeff_independent_check`

Folder: `code/lri_2d_coeff_independent_check/`.

#### Reviews and checks: lri_2d_coeff_independent_check (summary; no raw logs or transcripts are shipped)

All code here was written by Claude Code sessions (2026-10-08..14), one coordinating session and subagents it
launched. There was no external (Codex) code review of this tree. Its reliability rests on redundancy: independent
implementations that agree to their working precision, exact rational arithmetic wherever possible, and checks of
every derived claim by the coordinating session from the exact output files, with its own scripts.

##### Independent implementations
- **Clean room.** `rs_exact` (exact-rational RS) and `cauchy` (non-perturbative Cauchy integrals at 256 bits) were
  written by separate agents that saw neither the production package nor each other's work, only the model
  specification `SPEC.md` (written from first principles; for the consistent and literal windows the definition was
  taken from the package's METHOD.md). Agreement: RS vs package 3.9e-13 (25 scheme/cutoff pairs, all quantities), Cauchy
  vs RS 4.8e-46 (15 cases), package vs Cauchy 1.6e-14 (`compare_*.txt`).
- **Large-L codes.** Each large-cutoff code was checked against brute-force exact rationals at small cutoff:
  - `continuum/exact_low_orders.py` (C2, C3) vs the package: ≤ 4e-14;
  - `c4_exact` vs rs_exact, the package and zeromode_exact: ≤ 1.1e-13 (`c4_exact/validate_*.txt`);
  - the ε⁵ engine vs rs_exact, the package, complete_exact and brute force: ≤ 2.2e-13 (`residual_log/results/eps5/validation_*.txt`);
  - `large_L/tagchan.py` (δ⁽³⁾) vs exact rationals at L = 2..16: ≤ 4e-16 (`large_L/results/validation_small.txt`);
  - the all-order solver `ce_wc` vs complete_exact and brute force at small L (exact).
- **Two exact window implementations.** `complete_exact` and the residual_log codes implement `WINDOW_SPEC.md`
  separately; they agree exactly on C4 of W (L = 2..12) and to ≤ 7e-14 on `C4W_by_L.csv`.

##### Checks of derived results by the coordinating session
- **ε⁴ complete window.** Own refit of C4^W(L): 5.0488682–5.0488685, against the derivation's 5.0488682(6).
- **ε³ external-line window (Wcs).** `residual_log/fits/parent_check_wcs`:
  - δ⁽³⁾(L) recomputed from the tagged-φ files equals the value each Wcs run used;
  - C0..C4, r, g are unchanged by Wcs;
  - C5^Wcs − C5^Wc = δ⁽³⁾(L) S(L) to 1.2e-16;
  - blind L = 16 predictions.
- **Partial ε⁴ χ-line window.** `residual_log/fits/parent_check_p5`: invariances, χ-line gaps.
- **C5 at L ≤ 300.** `residual_log/fits/parent_check_largeL/refit_c5_300`: independent refit, C4^W null test, fixed-b shifts.
  It agrees with the large-L agent's `large_L/c5_fits300.txt`.
- **Optimized engine.** `large_L/lib_opt` was regression-tested against the unmodified engine `large_L/lib` per task
  (≤ 7.3e-16 over 1448 tasks, requirement 1e-12) and on the assembled C5 (≤ 1.2e-13 at L ≤ 60; the L = 300
  assembly reproduces the L ≤ 200 production data to 7.6e-13), `large_L/results/regression_opt.txt`.

##### Errors found and corrected during the work (all corrected in the shipped outputs and the note)
- **δ⁽³⁾(∞).** Extrapolations from L ≤ 16 had given −0.0159 to −0.0160 and "excluded" −4/(81π). The exact chain sums to
  L = 16000 show that δ⁽³⁾(L) is not monotone (minimum at L = 34) and tends to −4/(81π) to 3e-11.
- **"Free ln L" in C5.** The earlier free ln L coefficient (−0.014 … −0.059) came from tail towers without ln³L/L. With
  the ln³L/L tail and data to L = 300 it drifts to +0.004, consistent with 0.
- **Growth of the ε⁴ descendant residual.** It was once quoted as 0.0145 ln L; the correct value is 0.028 ln L.
- **A refit "calibration".** One that added β ln L to the data itself tested nothing (the fit is linear) and was removed.
- **First cost estimate of the L = 300 run.** It was too low by about an order of magnitude; the run was stopped
  after 130 node-hours and finished with the optimized engine (37 node-hours).

##### What the checks do not establish
- The windows were derived after their effects had been seen and with the continuum values known, though with no
  fitted parameter.
- δ⁽³⁾(∞) = −4/(81π) is identified numerically (3e-11), not proven.
- A residual ln L in C5 with |b| ≲ 0.01 is not excluded at L ≤ 300.
- The ε³ identities of the φ² descendants are not settled at L ≤ 16.
- The ε⁴ window is not known completely, so C6..C8 are not reproduced in d = 2.

## d = 3: exact C2..C5(L) sums and the coefficients C2..C8

### `lri_3d_c4_exact`

Folder: `code/lri_3d_c4_exact/`.

#### Reviews of lri_3d_c4_exact

No AI code review (Codex or other) was run on this package. Its checks are numerical and are replayed:

- **Against an independent code.** The production package `lri_3d_hpc` builds the truncated Hamiltonian explicitly
  (supplied by the author, written by OpenAI GPT-6 astra; Expanse/symmetry port reviewed by Codex in 11 rounds). This
  package sums diagrams. They agree on C2..C5, r, g and the seed energies for every even L <= 20, raw and with the
  vacuum window, to 2.7e-13 or better (`make replay`, VAL-PKG-C4 and VAL-PKG-C5; `make test` repeats it with sums
  recomputed from scratch).
- **Against a brute force on the package's own operators.** The window schemes that the package does not have (W2,
  W3m, Wb, Wc, Zb) are built as explicit operators on the package's reference Hamiltonian at L <= 14
  (`eps5/brute3d_W5.py`) and agree to 4.3e-13; the zero-mode window at L <= 6 (`brute_zm.py`) to 1e-14.
- **Internal.** Window shifts by two independent routes (full engine against the cancellation-free window sums, 5e-9 at
  L <= 600); runs with different maximal cutoffs and quadratures (7e-10 at L <= 300 for C4, 1.4e-9 for the C5 shifts);
  regression of the final, memory-fixed eps^5 engine against the stored L <= 20 run (5e-13) and recomputation of all
  34 reduced L = 40 boxes (bitwise identical).

What the checks do not cover:

- They verify that the stated model is computed, not that the windows are the right ones. The complete window W and
  the eps^5 windows Wc, Wcs were derived in d = 2 after the d = 2 divergences were seen and with the continuum values
  known, and applied to d = 3 after the exact sums had shown the d = 3 divergence at eps^4. The chi window is used in its
  leading-order linear form, not derived for d = 3.
- The extrapolations: fit forms (towers from the d = 2 protocol) and fit windows were chosen after the data were seen,
  with C4(3) and C5(3) known. The C5 extrapolation is provisional: an L^-1/2 term, which L <= 40 cannot exclude, would
  move it by 0.5 to 1.
- This public overlay (`public.mk`, `public/`) was written on 2026-10-14 and was not reviewed by Codex.

### `lri_3d_hpc`

Folder: `code/lri_3d_hpc/`.

#### Reviews of lri_3d_hpc (d = 3 perturbative HT)

Raw review logs and transcripts are not published; this is their summary.

##### Code review of the Expanse/symmetry port (Codex, OpenAI GPT-6 astra, effort xhigh; 2026-10-08)

The port (`cluster/` layer and the changes around the solver) was inspected by Codex in 11 rounds against the
package at each fix commit. Rounds 1 to 10 returned REVISE with 1 to 11 findings each; every finding was fixed in the
commit named in `PROVENANCE.md`. Round 11 APPROVED commit `7c8a67e`, the release of the production campaign.

The findings concerned the cluster workflow, not the arithmetic of the solver:

- **Release identity:** tarball authentication before any script is sourced, member-by-member checks against the
  release manifest, receipts bound to the tarball's sha256 and fingerprint (R2, REV-007, REV-008).
- **Result identity:** an existing result or gate is reused only for the exact case and solver source; production
  solves require both cutoff-14 gates of the current store validated against the shipped reference at 5e-13
  (F1, R3, REV-003).
- **Store integrity:** every consuming job re-hashes the store; the verify stage always re-hashes; a padding-free value
  fingerprint of the store (R11, REV-006, REV-009, REV-011, REV-012).
- **Environment identity:** campaigns frozen to the receipt's interpreter, packages, compiler, mpi4py build and the MPI
  runtime libraries by path and sha256 (F2, REV-002, REV-013, REV-016).
- **Comparisons:** crosscheck and MPI comparisons count only with a passing record bound to both results' sha256
  (R1, R4).
- **Scheduler safety:** array semantics, dependency checks against accounting, the Expanse job-count guard, lane stop
  on SIGTERM, memory limits from the whole cgroup chain (F3-F5, R5-R10, REV-001, REV-004, REV-005, REV-010,
  REV-014, REV-015).

None of the findings changed a coefficient: the L14 gates and the 32-case L14 grid were rerun in the validation
receipts of every release on both sites.

##### Results

The production results were not reviewed by a separate AI. Their checks are internal and are replayed by
`make replay`:

- the cutoff-14 gate of every production store against the supplier's reference results (scaled error at most
  1.25e-14, tolerance 5e-13);
- the recursion residual of every result (at most 5.1e-19, limit 1e-16);
- the recurrence strategy against the stationary strategy at L = 16 (at most 4.1e-16);
- the L = 16 and 18 coefficients re-solved from the L20 store against the L16 and L18 stores (at most 9.8e-15).

##### Not reviewed

- The supplied archive itself (the original calculation and the optimized solver, `14b10e2`) was reviewed only
  through the port: Codex inspected the port's changes and their interaction with the solver, not the derivation of
  the coefficients. The supplier's validation (`results/*.json`) compares the optimized solver with the original code
  for L <= 14.
- This public overlay (`public.mk`, `public/`) was written on 2026-10-14 and was not reviewed by Codex. It reads
  records and runs the package's own checks; it changes nothing in the package.
