# Reviews: integ_d1

A summary of the reviews of the calculation. The review log itself (prompts, transcripts, reviewer outputs) is not
part of the release.

## Protocol

- The plan fixed the stages (M1: C3; M2: two bubbles, C4 and C5; M3: three bubbles with one logarithm, C6 and C7; M4A:
  f_202; M4B: f_301; then C8), their checks, thresholds and stopping rules before any multi-bubble cluster with
  logarithm insertions was computed. Each stage gated the next.
- Blind records: every flow-coefficient record and the C8 record were written once, hashed and entered in the
  registry (`results/frozen_records.json`) before they were compared with anything. The tools refuse to overwrite a
  frozen record. C3..C7 against their closed forms are checks inside the stages; the C8 comparison is a separate stage
  (`c8_assemble.py --compare`), and it refuses to run unless the C8 record is the current frozen one, bound to the
  current records of its inputs and to a passing confirmatory check.
- Reviewer: OpenAI Codex (model GPT-6 astra, reasoning effort xhigh), a fresh session for each round, given the plan or
  a snapshot of the repository and a short context note; the host (a Claude Code session) decided on each finding.

## Plan review (three rounds, 2026-10-14)

- Round 1, REVISE: raw pole parts not all predicted by lower orders (MSC-001); the continuation to v = 1 unspecified
  (MSC-002); the M1 gate enforced no tolerance (MSC-003). All accepted; plan revision 2.
- Round 2, REVISE: simultaneous disjoint contacts (rho^(-3+4w) at six kinks) need a third-order subtraction (MSC-004).
  Accepted; plan revision 3.
- Round 3: APPROVED, no findings.

## Code inspections (six, 2026-10-14 to 2026-10-17)

| inspection | snapshot | verdict | findings (all accepted and fixed) |
|---|---|---|---|
| 1 | after M3 (437e824) | REVISE | MSC-005..011: gate thresholds not enforced, sector completeness, run fingerprints, batch failures, upstream hashes, an out-of-bounds `-k 2`, and an independent per-sector check of the 63 simultaneous-contact sectors (fix round 1: the sector checker `sector_check.cpp`) |
| 2 | after fix round 1 | REVISE | MSC-012..017: NaN in the checker, fingerprints of checker results and of outputs, a write-once race, `-conj 1` at complex v, `--dry --stage2` (fix round 2) |
| 3 | after the first C8 record (6735a7f) | REVISE | MSC-018 (high): the roundoff part of the f_301 error was not validated; required a third run at another contour radius, a stratified double-double validation sample, and the error |fine - coarse| + |fine - radius| + validated roundoff. MSC-019 (high): the comparison must require a passing confirmatory check bound into the C8 record. MSC-020..025 (medium): record validation, build registry, consumer checksums, sigma(C8) <= 0.3 enforced, distinct complex v, submitter state (fix round 3) |
| 4 | fix round 3 and both amendments (a6a627e) | REVISE | MSC-026..030 (medium): exact key sets of the output records, epsilon from the build precision, design files checked against their pre-data commits plus `--verify` modes, authenticated engine side of the sector checks, the summary's wording. Judged amendments A and B defensible as disclosed (fix round 4) |
| 5 | fix round 4 (e84de6f) | REVISE | MSC-031..034: write safety of the verify paths, completeness of the provenance sidecar, the checker's argument defaults, comparison wording (differences and labelled ratios; no "sigma" or "pull"). Judged the exposure disclosure below adequate for an empirical numerical estimate (fix round 5) |
| 6 | fix round 5 (6d94e80) | APPROVED | MSC-031..034 resolved, no material defect; C8 = 247.381180 +- 0.131 may be quoted as an empirical numerical estimate with the disclosures below |

After fix rounds 4 and 5 every current record was rebuilt byte for byte with the revised checks
(`results/fix4_verification.json`, `results/fix5_verification.json`). No inspection disputed a numerical result.
The inspections read the git history; in particular, that the two design files were committed before the data they
govern (6295185, e49157f) was checked there. The public tree carries the files, not the history: `make replay` shows
that each design file and the provenance sidecar equal the blobs of those commits (git stand-in, public/gitstub.py),
not the order of the commits.

## The two amendments (decided by the author after seeing the data)

Both stopping rules were fixed before their data; both fired; the author decided both amendments on 2026-10-17 after
seeing the failing results. They change only error bars and a pass/fail label: the central values of f_301 and C8 are
byte-identical to the first records, which stay frozen and ship (`results/M4B_cx_check.json`,
`results/M4B_flow_coefficients.json`, `results/C8_record.json`).

- **A. Confirmatory check** (J4^(0) at two complex v against the exact Bethe ansatz; threshold 1e-12 relative, fixed
  before the runs). K_A = 0.92 + 0.05i gave 1.69e-14 (pass); K_B = 1.05 + 0.06i gave 1.62e-12 (fail), against that
  run's own first-order roundoff bound 1.69e-9. The remedy fixed in advance, a double-double rerun at K_B (1337
  sectors, about 1.7e4 core-hours: `results/m4_inputs/cx_v2_design.json`), exceeded the 2.5k core-hour cap of the check
  and was not run. Amended criterion: at most 1e-11 and within the run's own roundoff bound; same data, PASS
  (`results/M4B_cx_check_v2.json`, field `amendment`). For scale: the production gate's delta^0 tolerance is 1e-6 and
  the fine level met it at 4.2e-11.
- **B. Roundoff validation** (MSC-018(b)). The rule fixed in `results/m4_inputs/fix3_design.json`: stop if in any
  sampled sector |double - double-double| exceeds 0.1 of the first-order bound eps B; otherwise the roundoff factor is
  max(10 x largest ratio, 0.01), applied to the whole non-sampled bound. The largest ratio was 0.411 (sector 2890),
  with 0.32 and 0.14 in two others, all in bound deciles 1-2, which carry about 4e-8 of the bound. Applied as written
  (ignoring the stop) the rule gives a roundoff estimate of 21.3 and sigma(C8) of about 16 (`results/M4B_gate_v2_dry.txt`).
  Amended rule, fixed in `results/m4_inputs/fix3b_design.json` (commit e49157f) before new data: the same
  max(10 x largest ratio, 0.01), decile by decile, times that decile's non-sampled bound; the 16 sectors ranked 9-24
  by bound are measured in full and enter with their measured differences; a stop only for a ratio above 0.1 in those
  16 sectors or in deciles 9-10. The author also required a fresh held-out sample fixed before its data: 16 sectors
  (random.Random(20261017): 8 from the upper and 4 from the lower half of decile 10, 4 from decile 9). The largest
  decile-10 ratio rose from 7.4e-4 (4 sectors) to 2.5e-3 (16 sectors), inside the factor-ten margin set on the old
  sample. Result: roundoff 0.137 at the fine level (record field `amendment`).

## Disclosures

- **Exposure.** The host session saw the comparison of the first C8 record with the references when that record was
  frozen (2026-10-16), and proposed the amendments with that knowledge. The session that ran the computation (a
  builder subagent) was exposed to the comparison at 2026-10-16 15:43 UTC, through a summary line the host had written
  into a memory index that was loaded into the builder's context when it was resumed. By then the central values of
  f_301 and C8 and the design of the additional error-bar runs (6295185) were frozen; the exposure came 45 s before the
  first record of the confirmatory check was computed (from finished runs, against its fixed criterion, which it
  failed) and before the error bar was evaluated. The builder's later work (the second cx design, the gate's dry run,
  implementing both amendments, the second records, fix round 4) was therefore not blind to the comparison. The
  amendments were decided by the host and the author; the held-out sample was fixed before its data.
- **Order of a check.** The first run of the C8 assembly printed C8 before its C7 check, which failed in that run; it
  was fixed, and the value of C8 did not change (the assembler now prints C8 only after every check has passed and
  the record is frozen).
- **Scope of the uncertainty.** An empirical numerical estimate from three runs and measured roundoff, not a standard
  deviation and not a bound; it cannot exclude an error common to all three runs.

## Comparison (after inspection 6)

`results/C8_comparison.txt` (commit 65d920d): against the compendium's record 247.3812048049935 the difference is
-2.506e-5 (-0.0002 of 0.131); against the independent re-derivation the comparison stage used the rounded
242.83 +- 2.37 (difference +4.551, 1.92 times 2.37); with the unrounded 242.825 +- 2.371 of `indep_d1` the note gives
+4.556, 34.8 times 0.131 and 1.92 times 2.371. `make replay` recomputes all of these.
