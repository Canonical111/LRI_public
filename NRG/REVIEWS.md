# NRG: reviews and checks

This file summarizes every review of the NRG study: who reviewed what, the verdicts, what was fixed, and what was never
reviewed. The raw review transcripts are not released. There was no human referee.
- §2–3: the reviewer of the cluster port was OpenAI Codex (requested model gpt-6-astra at extra-high reasoning effort;
  the CLI did not report which model actually ran). Claude Code coordinated the work, wrote the plan and built every fix.
  Codex reviewed the port (plan and code), not the numerics, the analysis or the results.
- §6: the analysis and the note were reviewed on 2026-10-13 by Claude Opus 5.5 agents (read-only, one per review
  lens), launched by a separate Claude Code session that coordinates the public release. They are independent of each
  other and of the session that wrote the analysis, not of the model family.
- The solver itself was written by GPT-6 astra (OpenAI, via ChatGPT); see `PROVENANCE.md`.

## 1. Code review before the port (Claude Code, 2026-10-02)

The supplied package `lri_spin_boson_hpc` was read line by line against the reference solver of the original study
(`code/lri_spin_boson_hpc/reference/`). The review re-derived the site-0 and site-n Hamiltonians, the truncation, the
projected ladder operators, the observers, the derivative terms, the kept-projector derivative, the ground-shift
subtraction and the window audit.

- **Numerics: no defect found.** No numerical code was changed.
- **Critical search.** It deviates from the reference script only in conservative ways: an exhausted bisection is
  rejected instead of accepted, and α = 128 is never evaluated.
- **Window correction.** The Hamiltonian-truncation "complete window correction" does not apply to NRG (note §9, last item).
  Nothing was added.
- **Operational defects, all fixed or mitigated for the cluster:**

  | id | severity | defect | resolution |
  |---|---|---|---|
  | R1 | high | item locks (`flock`) are node-local on the cluster file system | campaign roots with explicit ownership |
  | R2 | high | one small item per exclusive 64-core node wastes 30–60× of the allocation | lanes pack many items per node |
  | R3 | medium | one AVX-512 node in the AMD partition would break runtime-bound records | excluded from every job |
  | R4 | medium | generic Slurm templates (no environment, partition or memory) | cluster drivers in `cluster/symmetry/` |
  | R5 | low | the bracket rule differs from the reference script | documented, conservative |
  | R6 | medium | signal forwarding could kill a child that was still starting | fixed |
  | R7 | medium | unsafe item IDs (e.g. `../x`) were accepted | rejected at manifest time |
  | R8 | low | the memory planner `plan()` is uncalibrated | lanes log peak memory; conservative by about 3.5× |
  | R9 | low | the record identity lists only the BLAS libraries loaded so far | noted |

## 2. Plan review (Codex, 2026-10-02): approved after four rounds

The plan (rev 1–4) for making the package safe on the cluster went through four rounds:

| round | verdict | findings | resolution |
|---|---|---|---|
| 1 | REVISE | 2 high, 3 medium: stale-owner takeover not mutually exclusive; lane admission ignores memory; legacy writers bypass ownership; unsafe IDs; signal forwarding during child startup | all accepted: serialized reclamation, memory-aware admission, ownership for every writer, ID checks, safe forwarding |
| 2 | REVISE | 1 high, 1 medium: a paused old writer could replace a reclaimed item's files; an owner without a job id is unrecoverable | generation-isolated write folders seeded from the previous generation; reconciliation by unique job name |
| 3 | REVISE | 1 high, 1 medium: a Slurm requeue after a node failure reuses job id, token and generation (requeue is on at this site); export destinations collide | `--no-requeue`, a restart-count guard, per-execution stop and log folders, campaign-aware export |
| 4 | APPROVED | none | the reviewer noted that approval covers the plan only, not the implementation |

The reviewer also confirmed, from the code, that the window correction does not apply.

## 3. Code inspection after the build (Codex, fresh sessions)

| round | snapshot | verdict | findings | fixes |
|---|---|---|---|---|
| 1 | `f2e9e73` | REVISE | 10. High: "done" without an identity check, mutable manifest and receipt paths, symlinked generation folders. Medium: other writers inside a campaign, reserved names, non-atomic owner publication, export coherence, orphan quarantine bypass. Low: lane node evidence, status details. | all accepted, commit `35037e8` |
| 2 | `35037e8` | REVISE | 4. High: benchmark writers could write into campaign state. Medium: export destinations not resolved, concurrent exporters not serialized, status did not check the item hash. | all accepted, commit `af9b1dc` |

The agreed budget of two inspection rounds and two fix rounds was then used up. **The last fix round (`af9b1dc`) was not
re-inspected.** It changed scripts and benchmarks only; the solver source and its SHA-256 are unchanged.

## 4. Validation, smoke runs and drills on the cluster (2026-10-02/03)

- **Validation.** The full test suite passed on an AMD compute node for each code state:
  - 72 tests (job 569091);
  - 82 tests after fix round 1 (569134);
  - 85 tests for the final code (569161). This run issued `inputs/validation_receipt/receipt.json`.
- **Smoke lane.** Five small items ran packed on one node and finished with gated records. Their peak memory showed
  `plan()` to be conservative by about 3.5×.
- **Reproducibility.** A second smoke run on another node of the same runtime reproduced the first **bitwise**: the same
  flow records and the same critical coupling.
- **Interruption drill.** A stop signal produced exit 75 with a checkpoint. `resubmit` created generation 2, which resumed
  from the checkpoint and completed with all gates passed.
- **Ownership drill.** Direct writes without the owner token were refused with exit 76 and wrote nothing, both from the
  login node and from another compute node. Two simultaneous `resubmit` calls produced exactly one new generation.
- **Workstation vs cluster.** Runs at a fixed α differ late in the chain between a workstation and the cluster, and
  between thread counts. The difference starts at 2e-16 at site 0 and grows as Λ^(y_t n): rounding noise amplified
  along the relevant direction. The window audit of 1-thread and 4-thread derivatives agreed to 1e-8. Hence every item
  retunes α_c on its own runtime (note §5.3).

## 5. Checks of the results (2026-10-08)

These are checks, not reviews. Details are in note §8.

- **Second implementation.** A separate Claude agent wrote it from a physics-only specification
  (`independent_check/SPEC.md`), without access to the production code. That it did not open the forbidden files rests
  on the instruction and on its own statement (`independent_check/NOTES.md`); there is no access log. Results:
  - chain coefficients agree to rounding (about 5e-16);
  - α_c is bitwise identical in 5 of 8 configurations and agrees to 7e-14 in the rest;
  - Δ_E agrees window by window to 3e-7 in all 316 trusted windows.
- **Methods that do not use NRG**, as evaluated on 2026-10-08 with the midpoint estimator of that time (superseded,
  see §6):
  - the values at Δσ = 0.249, 0.24 and 0.225 lay +0.0088, +0.0051 and +0.0020 above the ε expansion;
  - at the seven points shared with the 1D cluster Monte Carlo study, |NRG − MC| ≤ σ_stat + σ_sys + δ_tot. (An earlier
    version of this file said "within its systematic scale plus the NRG error"; that is false at Δσ = 0.05, where
    |NRG − MC| = 2.472e-3 > σ_sys + δ_tot = 2.451e-3.) Two of the seven Monte Carlo values carry the label CROSS-CHECK
    FAILED and should not have been used as infinite-size references.

  The comparisons with the present estimator are in note §8.

**Recommendation and decision.** The report written after these checks (2026-10-08) recommended the following:
- exclude Δσ = 0.249 and 0.24, or replace them with the series values 0.49934 and 0.4942;
- enlarge the error at 0.225 to cover +0.002;
- add a caveat of order 1e-3 at 0.2.

The author chose instead to keep all three points as computed, marked "biased" and used in no comparison, with the bias
stated. The caveat at 0.2 was kept. Since 2026-10-13 the three points are labelled "not converged in chain depth" (§6);
the decision to show them and use them nowhere stands.

## 6. Review of the analysis and the note (2026-10-13)

Three read-only reviews of the then public note and its patches, each by a separate agent:
- physics and method;
- statistics and the error budget;
- readability for an outside physicist.

Claude Opus 5.5 agents ran them, launched one per lens from a written brief by the Claude Code session that
coordinates the public release. They did not see the analysis session or each other's reports. The coordinating session
verified the central claims against the records and consolidated them. Two further lenses, numbers against data and note
against code, are to run on the revised note.

**Findings on the science.** Claude Code verified each from the records with its own scripts before changing anything.
- **A1. The estimator.** The note's value of a point was the midpoint of the quality range of windows.
  - Along the quality windows Δ_E falls monotonically at 11 of 13 points; the early ones are the transient towards the
    fixed point.
  - The midpoint sat 1.7–3.7e-4 above a plateau that is flat to about 1e-6 at 0.025 ≤ Δσ ≤ 0.15.
  - The half-width measured the transient, not a precision floor.
  - The midpoint was this study's choice (2026-10-04); the inherited analyzer reports the settled window.
- **A2. The Λ error.** The Λ dependence, the factor 2 on the Λ shift and "Δ_E rises as Λ decreases" came from the same
  estimator: the window rule counts sites while N ∝ 1/ln Λ. On plateau values Λ = 2–4 agree to ≤ 2e-5 at Δσ = 0.1 and
  0.05.
- **A3. The excess near s = 1/2.**
  - It is slow approach to the fixed point (ω ≈ ε), not a truncation bias of bosonic NRG.
  - At s = 0.502, 1/(Δ_loc − series) grows linearly in the RG time with the one-loop slope 3.
  - At fixed RG time the local exponent does not depend on K or n_b.
- **A4.** The "biased" label at 0.225 rested on the Borel–Padé reference alone.
- **A5. The Monte Carlo comparison.**
  - Two of seven Monte Carlo points are CROSS-CHECK FAILED.
  - The signs of NRG − MC are correlated.
  - `compare_methods.py` printed a quadrature "σ pull".
  - The sentence in §5 above was false at Δσ = 0.05.
- **A6.** A published next-to-leading-order result makes the s → 1 check quantitative.
- **A7.** Published exponents and some references were missing; one reference was misused.
- **A8. Timeline and provenance.**
  - Several choices were made after the NRG data were seen.
  - The scope of the Codex review was overstated.
  - The authorship of the solver was missing.
- **A9.** Several smaller points.

**Readability** (15 ranked fixes, about 70 terms):
- vocabulary and symbol collisions;
- a glyph bug for the identity operator;
- figure defects (raw marker codes, overlapping ticks);
- inconsistent counts and times;
- process language in the body.

**Outcome.** The author decided the following (2026-10-13):
1. **Estimator.** The settled late-window value with a chain-depth error, extrapolated where there is no plateau. The
   rule is fixed before the comparisons are recomputed and stated with its plateau test. At Δσ = 0.001 the 1e-4
   ambiguity is carried by an allowance.
2. **Label.** "Not converged in chain depth (slow approach, ω ≈ ε)" replaces "truncation bias" everywhere.
3. **Δσ = 0.225.** It stays shown and unused with 0.249 and 0.24. Its extrapolation is a cross-check only.
4. **Λ error.** The measured Λ spread replaces the factor 2.
5. **Old values.** They go into an appendix, with the reason for the change.

All of this is implemented: `code/analysis/estimator.py`, note §3.7, §4, §7.1, §8 and App. E. The A4–A9 and readability
items were addressed in the same revision, which was then reviewed again (§7).

## 7. Second review round (2026-10-13)

Three read-only reviews of the revised note and release, by the same kind of agents (Claude Opus 5.5, launched by the
coordinating session, blind to each other):
- numbers against the raw records, with an independent recomputation of the estimator;
- note against code on the assembled release, with replay and smoke on two library stacks;
- a recheck of §6 with a scrutiny of the new rule.

**Verdict.**
- All 13 values and their error components reproduce from the raw records to ≤ 5e-10.
- The rule's plateau split is robust for any threshold between 1.9e-5 and 7.7e-5. It also depends on h and the window
  width, but the values do not.
- An independent fit with a detuning term confirms the plateau values to ≤ 3e-6. The errors are not too small.
- Code, docs and method claims agree. Manifest, solver source, records and receipt are byte-identical to the frozen
  source.

**Found, and fixed in this version:**
- **Blocker.** `make replay` failed (50 PASS, 5 FAIL) with the oldest library versions that `requirements.txt` allows,
  NumPy 1.24 / SciPy 1.11. The least-squares extrapolations differ in their last bits between builds.
  - Fix: replay now compares with tolerances (REPRODUCE §6), and the undetermined extrapolation at Δσ = 0.001 is
    reported as "n.d.".
  - Checked: 58 PASS with NumPy 2.2.6 / SciPy 1.15.3 and with NumPy 1.24.4 / SciPy 1.11.4.
- **Cross-checks.** The reviewers' detuning fits are now shown as cross-checks, not adopted (`crosscheck.py`; note §3.7,
  §8.2). They replace a near-circular test of the extrapolation.
- **Timeline wording.** The reviews had already compared candidate estimators with the series and the Monte Carlo study
  before the rule was written. Note §4 now says so.
- **Release scrubs.** They are now described as actually done (DATA.md, PROVENANCE.md). `run_all.sh`, which wrote into the
  released folders, now only calls `make replay`.
- **Borel–Padé.** The central value is the upper of the two middle approximants, not their median; it is now named so.
  At Δσ = 0.2 the series is not presented as agreeing with NRG.
- **Wrong literals:**
  - 38 self-tests, not 39;
  - the C_8 update moves the series by up to 2.7e-6, not 3e-8;
  - the terminal residuals near s = 1.
- **Wording and rounding:**
  - bounds are now rounded up;
  - the slope at Δσ = 0.249 "approaches 3 from below";
  - the small monotone Λ trend;
  - the K-doubling allowance is named where δ_Λ is described;
  - the Monte Carlo sentence of the abstract;
  - the Angelini et al. point is interpolated;
  - the memory planner factor;
  - production dates;
  - missing TeX packages, the smoke reference environment, the appendix letter, and the replay check of the solver
    source (V0).

## 8. Not reviewed, or not run

- **Human review.** None exists, of anything.
- **The fixes after the second round (§7).** They have not been reviewed again:
  - `crosscheck.py`;
  - the tolerant `verify.py`;
  - the n.d. rule;
  - the rewording;
  - the platform fix of 2026-10-14 (the chain agreement quoted as a bound; V3 compared numerically);
  - `results_map.md`, `verify/quoted_numbers.json` and check V8 (2026-10-15), including the differences from the
    short-range dual series at Δσ = 0.01;
  - the revision of the note after the reading of 15 October (§9).
- **Conventions.** The estimator's constants (plateau threshold, neighbourhood, fit form and ranges) and the budget's
  judgements (linear sum, full extrapolation length, K-doubling allowance) are the author's conventions (note §4).
  The reviews tested their effect but did not choose them.
- **Cluster port.** The last fix round of the cluster scripts (`af9b1dc`) was not re-inspected (§3).
- **Never run on a cluster:** the Slurm templates in `slurm/` (`validate.sbatch`, `items_array.sbatch`,
  `independent_check.sbatch`). The array route was dry-run on a workstation in the second review round; the other two
  were not run at all. No make target exercises them.
- **Checked by no make target:**
  - README.md, REPRODUCE.md, PROVENANCE.md, REVIEWS.md, data/DATA.md and `slurm/README.md`;
  - `requirements.txt` (the second review round tested its oldest and newest versions);
  - the data scrubs (lane logs, job accounting, ENV.json, the environment blocks of `independent_check/out`);
  - the path generalization in `independent_check/SPEC.md`.

  These were read by the reviewers of §7, nothing more.
- **Release patches checked by the make targets, but by no second AI system:**
  - the regenerated code checksum list (`make test`);
  - the analysis (`estimator.py`, `crosscheck.py`, `build_tables.py`, `make_figures.py`, `note_numbers.py`,
    `check_figures.py`) and the comparison scripts (`make replay` reproduces every released file);
  - `verify/` and the `Makefile` (`make replay`, `make smoke`).

## 9. Reading of the note (2026-10-15)

At the author's request an independent reader without project context reviewed the note for precision and readability
(30 items; coordinated by a separate Claude Code session, which verified one item). The note was revised accordingly.
Applied:
- **The label "not converged in chain depth".** The note now says that it is not an outcome of the estimator: the
  author assigned it after the comparison with the ε series. It also states what the rule alone would give at
  Δσ = 0.225 (0.487529, δ_depth = 2.1e-3) and gives the reasons for the label (note §3.7).
- **Abstract.** The Monte Carlo crossing agreement is quoted over the accepted points only: 1.05 σ_∞, where the old
  1.06 included Δσ = 0.175, which is not used. The error sentence now describes δ_Λ correctly. Two final values were
  added.
- **Cross-check fits.** They are defined once, under two names (late fit, crossover fit), with ranges, end offsets and
  acceptance rules (note §3.8).
- **One-loop test at Δσ = 0.249.** The note derives the one-loop form. With l_0 inferred from the data it predicts
  local slopes 3.1–3.5. The measured slopes, 2.55 to 3.03, are 10–20% lower; "approaches 3 from below" was removed.
- **Crossover fit near s = 1/2.** "Recovers the series" was replaced: at Δσ = 0.24 every accepted fit lies 2e-4 to
  8e-4 above the series.
- **Borel–Padé central value.** It is now called a convention of the 8 October script, without further justification.
  Table 1 marks Δσ = 0.2 as "no test".
- **Monte Carlo comparison.** The sum σ_stat + σ_sys + δ_tot is called a scale, not a test of consistency.
- **Λ = 4.** Its K convergence (only K = 64 was run) is now called assumed in the text, the captions and a figure
  title.
- **Plateau classification.** The dependence on h and on the window width is quantified in the note: at Δσ = 0.15 the
  drift is 6.6e-5 with h = w/2 and 9.3e-5 with 20-site windows.
- **C_7 and C_8.** Their uncertainties are identified as the paper's allowances, together with their effect on the
  Borel–Padé sum.
- **p_edge.** It is defined, and its jumps between items are explained by the side to which the flow leaves the fixed
  point.
- **Bisection width.** It is shown to be at the rounding level.
- **s → 1 table.** δ_tot/δ^{3/2} was added. The coefficient −C^SR_3(1)/2^{3/2} of the remainder and the differences
  from the dual series at Δσ = 0.01 are quoted.
- **Other text fixes:**
  - the unsupported "K ≳ 500" was removed;
  - the rounded-up bounds are stated;
  - the math-mode "and" and a dangling appendix pointer were fixed;
  - the Monte Carlo terms are defined, or the note points to the MC note;
  - Table 1 shows NRG − MC at the accepted points;
  - two referents were made explicit;
  - the campaign name was changed;
  - the old labels of App. E are explained.
- **Notation:**
  - the tunneling amplitude is Ω (as in the paper);
  - the plateau threshold is τ_p;
  - the finite-difference step is η;
  - the detuning amplitude is A_d;
  - the O(𝒩) index and n_fit are distinguished.
- **Voice and organization:**
  - "we" and "the author" are defined;
  - the internal labels were replaced;
  - the HT notes are cited;
  - the review statement was corrected;
  - the timeline of the choices moved to App. C;
  - American spelling is used throughout.

Not changed:
- **Borel–Padé central value.** The upper middle approximant was kept rather than replaced by the median. Changing it
  would change the released comparison; it changes no final value and no decision, and both the convention and the
  median are stated.
- **ω.** It still denotes both a frequency and the correction exponent, as is standard; the glossary says so.
- **Long sentences.** These were shortened only where they were edited for other reasons.
