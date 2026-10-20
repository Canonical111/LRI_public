# HPC campaign report: Hamiltonian-truncation cutoff push on Expanse

The campaign ran from 2026-09-29 to 2026-10-01. Code: `lri_hpc_Hamitonian` (local git). The machine was SDSC
Expanse, account <ACCOUNT>. Most of the campaign ran on the allocation that expired 2026-09-30; the last lanes ran on its
successor.

## 1. Summary

The finite-cutoff solver for the d = 1 long-range Ising Hamiltonian truncation was reviewed and made safe to run on
Expanse. Its cutoff was then pushed as far as single 2 TB nodes allow.

- **111 new cutoffs** were computed, and every one passed the acceptance gates: finite coefficients, independent
  shell residual ≤ 1e-10, tuning residuals ≤ 1e-6. The worst observed values were a shell residual of 9e-14 and a
  tuning residual of 9e-11.

  | task | before (saved data) | after this campaign | largest basis |
  |---|---|---|---|
  | thermal C0…C7 (degree 7) | even Λ ≤ 50 | **every even Λ from 52 to 118** (34 new) | 3,528,133,673 states (Λ = 118) |
  | φ6 gap, degree 5 | Λ ≤ 58 | **all 44 planned cutoffs, 52 to 160** | 4,023,999,219 states (Λ = 160) |
  | φ6 gap, degree 3 | Λ ≤ 128 | **Λ = 136…832** (33 new; 608 not run, §6) | 5,934,061,248 states (Λ = 832) |

- Larger cutoffs do not fit a 2 TB node under the calibrated memory model: thermal Λ ≥ 120, φ6 d5 Λ ≥ 164 and d3
  Λ ≥ 864.
- **Physics, pre-registered protocol** (thermal window starting at Λ = 16): **unresolved.**
  - The fits frozen on Λ ≤ 50 predict every new thermal cutoff to (0.5–2.6)·10⁻⁵ of the remaining distance to
    the limit.
  - However, C5 still drifts with the window and depends on the tail basis.
- **Physics, exploratory** (post hoc; adversarially stress-tested, §7.6):
  - Every calibrated extrapolation puts **C4(∞) of the truncated Hamiltonian 0.18–0.20 % below the exact value**
    (about 45.34 versus 45.42488).
  - This matches the O(ε⁴) scheme defect expected for the two-coupling Hamiltonian.
  - It is strong evidence, not proof, of a genuine matching offset. A near-constant or 1/log Λ tail would remove it,
    and only theory can exclude that.
- **Cost:** about 1,180 core-hours, counted as allocated cores × elapsed time. Of these, about 250 were lost to
  three node failures.

## 2. Setup

### 2.1 What was computed
The package's solver (`lri_hpc/`, Numba float64, exact ranked Fock basis) was used unchanged in its numerics. The
Hamiltonian, tuning conditions, particle caps and float64 arithmetic were not changed. The tasks and caps:
- thermal degree 7: P ≤ 15, Q ≤ 12;
- φ6 degree 5: P ≤ 14, Q ≤ 8;
- φ6 degree 3: P ≤ 10, Q ≤ 4.

All production outputs carry a single solver source fingerprint, `c0c30783db5d…`.

### 2.2 Code changes before production
The changes are listed in `review/CODE_REVIEW.md` and the git history from 67b009f to e1690e8.
- **Result acceptance gates** (`lri_hpc/validate.py`). These are applied before publishing, before reuse with
  `--resume`, when an output is accepted, and on export. The original package published and exported results
  unchecked.
- **Tests.** The full-recursion test now asserts its residuals. New tests cover:
  - the int64 index path for bases above 2³¹ states (needed at thermal Λ ≥ 112);
  - the acceptance gates;
  - campaign planning and status;
  - per-item claim locking under concurrency, including a supervisor killed while its solver runs;
  - extended-analysis merging.
- **Expanse layer** (`cluster/expanse/`):
  - environment, a validation job with a gated summary, a memory-routed submitter and lane runner, a status tool;
  - flock-based locks and per-item claims;
  - accounting-backed failure classification, one bounded retry, persisted exhaustion records.
- **Review.** A Codex plan review (gpt-6-astra, xhigh) took 5 rounds and APPROVED the plan at f0a7084.
  - Two fresh Codex code inspections followed, with 8 findings, all fixed.
  - The second fix round (e1690e8) and everything added afterwards are **not** independently inspected: the data
    refreshes, the exploratory study and this report.
  - Log: `../lri_hpc_Hamitonian_loop/PLAN-REVIEW-LOG.md`.

### 2.3 Validation on Expanse (job V, AMD EPYC 7742)

| V job | revision | result |
|---|---|---|
| 54519867 | 74b0ac0 | pass |
| 54520113 | 6583645 | pass |
| 54520360 | cd20385 | pass |
| 54520426 | f0a7084 | pass: gate for the production submission |
| 54521491 | e1690e8 | pass: gate for all later top-ups |

Each V runs:
- the full test suite;
- regressions against the saved tables: thermal Λ = 40 and 50 agree to ≤ 1.5e-9, φ6 d5 Λ = 50 to ≤ 2.0e-10, d3
  Λ = 128 to ≤ 5.5e-12;
- calibration runs (thermal 60/70/80, φ6 d5 70/90, d3 200/320).

Measured footprint and speed at 64 threads:

| task | RSS per state | time per state |
|---|---|---|
| thermal | about 400 B (≈ 475 B above 2³¹ states, int64 edges) | about 0.9 µs |
| φ6 d5 | about 330 B | 0.8–1.3 µs |
| φ6 d3 | about 230 B | 0.4–0.5 µs |

The run at 64 threads was no faster than at 32 for thermal Λ = 60. Production therefore used at most 64 threads and
assumed no 128-thread scaling.

## 3. Campaign design

- **Memory model** (`campaign.Model`, from the two largest calibration cutoffs per task):
  - RSS = a + dim · (n + e(Λ)), where the edge bytes per state e(Λ) are extrapolated linearly;
  - an int64 correction (7 → 11 bytes per edge) is applied above 2³¹ states;
  - request = 1.3 × model + 4 GiB;
  - routing: shared if the request is ≤ 240 GiB, otherwise large-shared up to 1950 GiB;
  - items whose request does not fit but whose 1.15 × model + 4 GiB does are best-effort "stretch" items, run last
    in their lane.
- **Model accuracy.** The model was conservative by 0–18 %. For example, thermal Λ = 116 modelled 1373 GiB and
  measured 1159; φ6 d5 Λ = 160 modelled 1600 and measured 1466; φ6 d3 Λ = 832 modelled about 1560 and measured 1454.
- **Lanes.** The QOS allows 4 submitted and 2 running large-shared jobs per user. So each job is a *lane*: a list of
  cutoffs run one after another, each in its own solver process holding a flock claim.
- **Priority.** Thermal first, then φ6 d5, then φ6 d3. Normal-QOS usage was kept within the user's 22-job rule.
- **Wall limits.** 3 × model time + 10 min, at least 1 h, at most 20 h.

## 4. Timeline and incidents (times PDT)

| when | event |
|---|---|
| 09-29 11:47 | Production submitted from the approved f0a7084: 12 lanes (4 large-shared, 8 shared). The two φ6 d3 large-shared lanes were deferred because the QOS submit limit was full. |
| 09-29 11:52 | **Deviation.** The three pending large-shared lanes requested cores ∝ memory (88–126 cores) and could not fit beside other jobs. Each was cancelled while PENDING and resubmitted from the same lane file with 64 cores, which is what its 64 threads use. This was later made the rule in `campaign.resources`. |
| 09-29 12:32 | **NODE_FAIL of <NODE>** after 46 min of thermal Λ = 116, at about 1.2 TiB RSS against a 1950 GiB limit. The requeued job still asked for 126 cores, so it was cancelled while PENDING and resubmitted with 64 cores (54522072). The claim lock had been released by the dead client. |
| 09-29 13:35 | <NODE> returned. Thermal lane A ran there; Λ = 116 resumed from its scalar checkpoint and finished in 15 min. |
| 09-29 13:46 | Thermal lane B completed (114 … 98). The top-up from e1690e8 submitted the first φ6 d3 lane. |
| 09-29 16:38 / 16:46 | Thermal lane A completed, including the **Λ = 118 stretch** (1573 GiB, 74 min). φ6 d5 lane A completed, including the **Λ = 160 stretch** (1466 GiB, 63 min). |
| 09-29 18:01 | **NODE_FAIL of <NODE>** during φ6 d5 Λ = 136 (about 0.4 TiB). Requeued. |
| 09-30 09:13–10:25 | <NODE> returned and **φ6 d3 Λ = 832** finished (1454 GiB). At 10:03 a health check flagged a Lustre I/O error on the node, and it failed at about 10:25 (**third NODE_FAIL**). Requeued; the in-progress Λ = 768 was lost. |
| 09-30 | No large-shared node was usable: 11-01 down, 11-02 drained (failed motherboard), 11-03 and 11-04 fully held by other users. |
| 10-01 06:54–15:59 | On the new allocation, the remaining queued lanes ran on <NODE>: φ6 d3 800/672/544, 736 and 768…512, and φ6 d5 136/128. All passed. |
| 10-01 07:55 | A top-up marked φ6 d3 Λ = 608 "exhausted", because `campaign.EXPIRY` still held 2026-09-30. Revoked 10-02 (`campaign/EXHAUSTED.revoked.jsonl`). The user chose not to run it. |

The three node failures all happened while campaign jobs were running, at about 1.2, 0.4 and 1.3 TiB RSS. Memory
pressure therefore looks unlikely as a cause. The 09-30 failure followed a Lustre I/O health-check error. No result
was lost: the lanes were requeued, and per-item checkpoints and claims made the resumptions safe.

## 5. Resource use

The figures below are allocated cores × elapsed time.

| | core-hours |
|---|---|
| shared lanes and V | about 195 |
| large-shared lanes and V (completed) | about 735 |
| lost to the three NODE_FAILs | about 250 |
| **total** | **about 1,180** |

The longest single item was thermal Λ = 118, at 4409 s. Elapsed time for the large thermal items was 0.9–1.25 µs per state at 64 threads, the upper end at Λ = 118,
close to the calibration.

## 6. Data inventory

All 111 per-cutoff outputs are in `results/expanse/{thermal_d7,phi6_d5,phi6_d3}/`, which is git-ignored. Alongside
them are the checkpoints, all Slurm logs, the validation summaries and the campaign journals (`campaign/`: plan, lane
files, SUBMITTED, EXHAUSTED, events). The gated exports are committed in `analysis/extended/*_new.{json,csv}`, exported
with `--source` set to the campaign fingerprint.

Not computed:
- **φ6 d3 Λ = 608.** It was falsely marked out of time and then revoked (§4). It would only fill one hole in the d3
  grid.
- **Memory-rejected cutoffs:** thermal Λ ≥ 120 (model 1887 GiB), φ6 d5 Λ ≥ 164 and d3 Λ ≥ 864.

Per-cutoff tables are in the appendix.

## 7. Results

All fits use the model of REPORT §6 (`analysis/extended/analyze_joint.py`, byte-identical to the original). The
extended gap input is used throughout. The exact C4 = 45.42488010356 and C5 = −731.13947662454, and the
diagrammatic C6 = 14331.8 ± 0.5 and C7 = −322550 ± 41, are **comparisons only**, never fit targets. Ranges are model
spreads, not confidence intervals.

### 7.1 Gap inputs
- ω3: 556.21440 with the cubic window to 128, and 556.20111 with the window to 832. That is a change of −2.4e-5
  relative.
- ω4, ω5: from −13457.69 and 376964.6 (fifth-order window to 58) to −13455.33 and 376987.0 (window to 160).
- Gap-input variations move the thermal limits by < 1e-5 relative (DIAGNOSIS §4). **The φ6 extension does not
  affect the thermal conclusions.**

### 7.2 Reference thermal fits (pre-registered: bases A, B, C, lo = 16, shift 0)

| basis | window | C4 (rel. to exact) | C5 (rel. to exact) | C6 | C7 |
|---|---|---|---|---|---|
| A | 16–50 | 45.34048 (−1.86e-3) | −734.447 (+4.52e-3) | 14359.6 | −323482 |
| A | 16–118 | 45.33604 (−1.96e-3) | −733.838 (+3.69e-3) | 14351.6 | −323242 |
| B | 16–50 | 45.33003 (−2.09e-3) | −733.516 (+3.25e-3) | 14345.9 | −323122 |
| B | 16–118 | 45.33300 (−2.02e-3) | −733.239 (+2.87e-3) | 14342.3 | −322963 |
| C | 16–50 | 45.34913 (−1.67e-3) | −734.046 (+3.98e-3) | 14350.3 | −323010 |
| C | 16–118 | 45.33757 (−1.92e-3) | −733.292 (+2.94e-3) | 14340.7 | −322833 |

- **Held-out test.** The models frozen on 16 ≤ Λ ≤ 50 predict all 34 new thermal cutoffs:
  - max error / remaining distance to the limit: 4.8e-6 (B), 1.7e-5 (C), 2.6e-5 (A);
  - at Λ = 118 the C4 errors are ≤ 1.2e-4 and the C7 errors ≤ 1.3.
- **Calibration check** (labelled: exact C4 and C5 imposed, window 16–118). The max residuals grow by factors of
  42–238. The free-fit residuals themselves reach about 1e-6 (C4 order), far above the data accuracy of about 1e-9.
  The lo = 16 tail bases are no longer adequate over 16–118.
- **Residual ratio** R4(Λ) = [C4-LHS(Λ) − C4exact]/T2(Λ):

  | Λ | 50 | 70 | 90 | 110 | 118 |
  |---|---|---|---|---|---|
  | R4 | 151.00 | 149.05 | 147.80 | 146.92 | 146.64 |

  It is still drifting, so it is not converged.

### 7.3 Pre-registered criteria (window 50 → 118)

| criterion | result |
|---|---|
| window stability | **no**: C5 drifts up to 1.0e-3 relative; C4 up to 2.5e-4 |
| held-out prediction | **yes**: max 2.6e-5 of distance |
| tail insensitivity of C4 | yes: spread 3.4e-4 against an offset of 1.9e-3 |
| tail insensitivity of C5 | **no**: spread 3.2e-3 against an offset of 2.9e-3 |

**Verdict under the protocol: unresolved. No matching offset is claimed.**

### 7.4 Exploratory, post hoc: raising the lower window edge
The script is `analysis/extended/explore_lower_edge.py`, output `explore_lower_edge.json`; the write-up is DIAGNOSIS
§9. The choice was made after seeing the data, motivated by the growing lo = 16 residuals. The fits use 18 tail
variants: bases A–F, free exponents, the original gap input, z^j/Λ and z^j/Λ^1.5 towers, and an extra Λ^−0.75 term.
They run at hi = 118.

| lo | variants fitting C4 at < 1e-8 | C4 rel. offset | C5 rel. offset | C6 | C7 |
|---|---|---|---|---|---|
| 16 | 1 / 18 | −2.13e-3 … −1.63e-3 | +0.53e-3 … +3.69e-3 | 14302–14352 | −323243 … −321492 |
| 32 | 14 / 18 | −2.01e-3 … −1.80e-3 | +0.67e-3 … +3.21e-3 | 14312–14347 | −323085 … −321957 |
| 40 | 18 / 18 | −1.99e-3 … −1.82e-3 | +0.69e-3 … +3.08e-3 | 14312–14345 | −323041 … −321963 |
| 60 | 18 / 18 | −1.99e-3 … −1.83e-3 | +0.72e-3 … +2.86e-3 | 14313–14343 | −322970 … −321979 |
| 70 | 18 / 18 | −1.98e-3 … −1.84e-3 | +0.79e-3 … +2.79e-3 | 14309–14343 | −322946 … −321527 |

Some of the tail-extension fits are ill-conditioned (condition numbers 1e11 to 1e16), so treat them as indicative
only.

**Reading, corrected by the stress test (§7.6):**
- The table's "fit at < 1e-8" criterion is too loose: the true noise of the C4-order data is about 1e-12.
- The 18 variants are only 10–12 distinct fits at the C4 order.
- Fits that actually reach the noise floor give C4 offsets of **−1.80e-3 … −1.92e-3**, i.e. C4_HT ≈ **45.338–45.343**.
- C5 is offset in the same direction in the fixed-shift variants (+0.07 to +0.31 %), with a basis-dependent size.
- C6 and C7 are not decisive.

### 7.5 Earlier diagnosis on the saved data (Λ ≤ 50)
On the 4032-variant ensemble of the original analysis, no variant has both C4 and C5 within 1e-3 of the exact
values. Imposing the exact C4 and C5 at lo = 16 raised the residuals by 28–170× and moved C6 and C7 *away* from the
diagrammatic values (about 14250 and −321000). See DIAGNOSIS §§1–7.

### 7.6 Adversarial stress test of the exploratory conclusion (2026-10-02)
Five independent analyst lenses tried to refute the C4 offset, each checked by an independent verifier. All key
numbers reproduced. Full details are in DIAGNOSIS §10; scripts and the journal are in `analysis/stress_test/`.

| lens | verdict on the C4 offset (analyst → verifier) | key finding |
|---|---|---|
| data integrity and resampling | supports → supports | Data are clean: no 50/52 or int64 step, no parity structure. Noise is about 1.2e-12, not 1e-9. Resamplings move C4 by ≤ 0.8 % of the offset. Floor-level fits give −1.80 … −1.92e-3. |
| independent extrapolation (validated on C2, C3) | supports → supports | Neville/BST on the e-subtracted sequence: 45.3353–45.3372. No calibrated method returns the exact C4. The evidence comes mainly from lo = 16–24, and the natural tail basis is undetermined at lo ≥ 40. |
| cutoff coordinate | supports → supports | No coordinate choice can make a genuine offset. The exact C4 needs shifts of +6 to +12 with cancelling coefficients, 40–60× above the noise floor, and fails held-out prediction. |
| slow tails | supports → supports, with corrections | Only a near-constant L^−p (p ≤ 0.05) or b/log L (b ≈ −1) term, or unnatural cancelling power towers, admits the exact value. Calibrated Bayesian fits give −1.86 … −1.97e-3, with the exact excluded at \|z\| ≥ 27. |
| higher orders (C5–C7) | weakens → inconclusive | C5 is offset, with basis-dependent size, and its sign is not robust to cutoff shifts. C6 and C7 cannot discriminate: fixed-ω best fits match the diagrammatic values (no offset), while free-ω fits show −1.2e-3 and −1.5e-3 offsets. |

**Net, post hoc:**
- The truncated Hamiltonian's **C4(∞) ≈ 45.34, 0.18–0.20 % below the exact value**. This holds in every calibrated
  method, conditional on standard power-times-log asymptotics.
- It matches the O(ε⁴) scheme defect that the project's own draft anticipates (`EFFECTIVE_HAMILTONIAN_PROPOSAL.md`
  §2.1: descendant spacing 1 + 0.0185 ε², a two-particle shift of −0.13 ε², "the 0.19 % miss of C4").
- This is strong evidence, not proof, of a genuine matching offset. The remaining loophole is a near-constant or
  1/log L tail, which only theory can close.
- C5 is likely offset but not pinned down. C6 and C7 cannot settle it.
- The pre-registered verdict stays "unresolved".
- Corrections to the earlier argument: the true noise is about 1e-12, not 1e-9; there are 10–12 distinct variants,
  not 18; the spread within physical tail classes is 30–40 % of the offset, not 1/10; and inflation factors and
  white-noise z-scores are not calibrated.

## 8. Where everything is

| what | path |
|---|---|
| code review | `review/CODE_REVIEW.md` |
| fit audit (reproduces the original analysis) | `analysis/audit_fits.py`, `analysis/audit_fits.json` |
| diagnosis (pre-registered §§1–8, exploratory §9) | `analysis/DIAGNOSIS.md`, `analysis/diagnosis*.json` |
| extended results (generated) | `analysis/UPDATED_RESULTS.md`, `analysis/extended/` |
| raw outputs, checkpoints, logs, journals | `results/expanse/` (git-ignored, about 2 MB) |
| Expanse copies | `<SCRATCH>/temp_project/lri_ht/{results,campaign,logs,validation,code}` |
| plan and review log | `../lri_hpc_Hamitonian_loop/PLAN.md`, `PLAN-REVIEW-LOG.md` |

To regenerate the analyses:
1. `bash analysis/extended/fetch_results.sh e1690e8`
2. `cd analysis/extended && python run_extended.py && python explore_lower_edge.py`
3. `python analysis/diagnose_systematic.py --thermal-extra analysis/extended/thermal_new.json --phi6-extra
   analysis/extended/phi6_d5_new.json analysis/extended/phi6_d3_new.json --out analysis/diagnosis_extended.json`
4. `python analysis/extended/write_updated_results.py`

## 9. Open items
- Before the submitter is reused, `campaign.EXPIRY` (still 2026-09-30) must be updated and V rerun.
- φ6 d3 Λ = 608 was not run; it is optional.
- The independent inspection of the post-approval edits (e1690e8 onwards) was not done.
- Tests rewrite three files under `benchmarks/` (CODE_REVIEW F7). Restore them with `git checkout -- benchmarks/`.

## Appendix: per-cutoff results (generated from results/expanse/*/*.json)

The columns are: states, solver wall seconds (for an item resumed from a checkpoint, this is the resumed part only), peak RSS, max |shell residual|, max |tuning residual|, and the lane job that produced the accepted output.


### Thermal, degree 7

| Λ | states | seconds | RSS GiB | shell | tuning | job |
|---|---|---|---|---|---|---|
| 52 | 4,107,636 | 7 | 1.6 | 7.0e-15 | 4.0e-11 | 54521090 |
| 54 | 5,410,687 | 9 | 2.1 | 4.2e-15 | 3.3e-11 | 54521090 |
| 56 | 7,080,064 | 14 | 2.7 | 8.9e-15 | 7.1e-11 | 54521090 |
| 58 | 9,206,453 | 23 | 3.5 | 9.5e-15 | 6.0e-11 | 54521090 |
| 60 | 11,900,137 | 17 | 4.4 | 0.0e+00 | 6.2e-11 | 54521090 |
| 62 | 15,294,671 | 24 | 5.7 | 7.8e-16 | 7.8e-11 | 54521090 |
| 64 | 19,551,130 | 26 | 7.2 | 5.8e-15 | 7.6e-11 | 54521090 |
| 66 | 24,862,964 | 29 | 9.2 | 5.8e-15 | 5.8e-11 | 54521090 |
| 68 | 31,461,720 | 40 | 11.7 | 2.3e-15 | 3.6e-11 | 54521090 |
| 70 | 39,623,469 | 43 | 14.7 | 8.0e-15 | 4.7e-11 | 54521090 |
| 72 | 49,676,246 | 56 | 18.4 | 2.8e-15 | 2.9e-11 | 54521090 |
| 74 | 62,008,566 | 71 | 23.0 | 5.1e-15 | 2.2e-11 | 54521090 |
| 76 | 77,079,088 | 83 | 28.7 | 3.4e-15 | 4.4e-11 | 54521090 |
| 78 | 95,427,565 | 106 | 35.6 | 3.3e-16 | 7.6e-11 | 54521090 |
| 80 | 117,687,411 | 133 | 43.9 | 2.9e-15 | 3.6e-11 | 54521090 |
| 82 | 144,599,740 | 147 | 54.1 | 3.1e-15 | 3.1e-11 | 54521090 |
| 84 | 177,029,321 | 214 | 66.4 | 2.2e-16 | 4.2e-11 | 54521090 |
| 86 | 215,982,567 | 196 | 81.1 | 5.8e-15 | 4.7e-11 | 54521089 |
| 88 | 262,627,727 | 242 | 98.8 | 1.7e-14 | 5.8e-11 | 54521089 |
| 90 | 318,317,481 | 271 | 120.0 | 2.1e-15 | 4.4e-11 | 54521089 |
| 92 | 384,614,460 | 326 | 145.3 | 7.3e-15 | 7.3e-11 | 54521089 |
| 94 | 463,319,538 | 403 | 175.4 | 5.9e-15 | 5.1e-11 | 54521089 |
| 96 | 556,503,524 | 470 | 211.0 | 9.5e-15 | 2.2e-11 | 54522072 |
| 98 | 666,542,536 | 602 | 253.2 | 8.1e-15 | 4.7e-11 | 54521313 |
| 100 | 796,157,247 | 666 | 303.0 | 3.9e-15 | 4.4e-11 | 54522072 |
| 102 | 948,456,427 | 900 | 361.6 | 1.4e-14 | 9.1e-11 | 54521313 |
| 104 | 1,126,985,479 | 951 | 430.5 | 3.8e-15 | 6.2e-11 | 54522072 |
| 106 | 1,335,779,849 | 1185 | 511.1 | 1.0e-14 | 3.6e-11 | 54521313 |
| 108 | 1,579,424,261 | 1333 | 605.4 | 6.8e-15 | 4.0e-11 | 54522072 |
| 110 | 1,863,118,145 | 1708 | 715.4 | 1.1e-14 | 3.6e-11 | 54521313 |
| 112 | 2,192,747,656 | 2199 | 971.4 | 9.5e-15 | 6.2e-11 | 54522072 |
| 114 | 2,574,964,913 | 2555 | 1139.2 | 7.4e-15 | 4.7e-11 | 54521313 |
| 116 | 3,017,275,418 | 891 | 1159.5 | 7.9e-15 | 4.0e-11 | 54522072 |
| 118 | 3,528,133,673 | 4409 | 1573.4 | 2.5e-14 | 7.3e-11 | 54522072 |

### φ6 gap, degree 5

| Λ | states | seconds | RSS GiB | shell | tuning | job |
|---|---|---|---|---|---|---|
| 52 | 1,978,554 | 8 | 0.7 | 7.1e-15 | 2.3e-13 | 54521094 |
| 56 | 3,134,157 | 9 | 1.0 | 8.9e-15 | 2.0e-13 | 54521094 |
| 60 | 4,840,468 | 7 | 1.5 | 0.0e+00 | 2.4e-13 | 54521094 |
| 62 | 5,963,681 | 11 | 1.9 | 7.8e-16 | 2.4e-13 | 54521094 |
| 64 | 7,308,225 | 141 | 2.3 | 7.4e-15 | 2.1e-13 | 54521094 |
| 66 | 8,910,412 | 21 | 2.7 | 5.8e-15 | 1.8e-13 | 54521094 |
| 68 | 10,811,389 | 16 | 3.3 | 2.3e-15 | 1.6e-13 | 54521094 |
| 70 | 13,057,619 | 22 | 4.0 | 7.9e-15 | 2.0e-13 | 54521094 |
| 72 | 15,701,446 | 21 | 4.8 | 2.8e-15 | 2.0e-13 | 54521094 |
| 74 | 18,801,641 | 23 | 5.7 | 5.1e-15 | 2.1e-13 | 54521094 |
| 76 | 22,424,048 | 29 | 6.8 | 3.4e-15 | 2.4e-13 | 54521094 |
| 78 | 26,642,224 | 33 | 8.0 | 4.4e-16 | 2.6e-13 | 54521094 |
| 80 | 31,538,165 | 38 | 9.5 | 2.9e-15 | 2.0e-13 | 54521094 |
| 82 | 37,203,044 | 43 | 11.2 | 3.1e-15 | 2.3e-13 | 54521094 |
| 84 | 43,738,037 | 57 | 13.2 | 2.2e-16 | 2.0e-13 | 54521094 |
| 86 | 51,255,147 | 45 | 15.4 | 4.9e-15 | 2.3e-13 | 54521093 |
| 88 | 59,878,156 | 48 | 18.0 | 1.7e-14 | 2.4e-13 | 54521093 |
| 90 | 69,743,552 | 66 | 21.0 | 2.1e-15 | 1.3e-13 | 54521093 |
| 92 | 81,001,581 | 70 | 24.4 | 7.3e-15 | 2.0e-13 | 54521093 |
| 94 | 93,817,312 | 78 | 28.3 | 5.9e-15 | 1.7e-13 | 54521093 |
| 96 | 108,371,811 | 95 | 32.8 | 9.5e-15 | 2.1e-13 | 54521093 |
| 98 | 124,863,318 | 98 | 37.8 | 8.1e-15 | 1.6e-13 | 54521093 |
| 100 | 143,508,569 | 115 | 43.5 | 3.8e-15 | 2.0e-13 | 54521093 |
| 102 | 164,544,114 | 136 | 49.9 | 1.4e-14 | 1.4e-13 | 54521093 |
| 104 | 188,227,764 | 156 | 57.1 | 3.8e-15 | 2.3e-13 | 54521093 |
| 106 | 214,840,071 | 194 | 65.3 | 1.0e-14 | 1.7e-13 | 54521093 |
| 108 | 244,685,938 | 174 | 74.4 | 6.8e-15 | 2.0e-13 | 54521092 |
| 110 | 278,096,228 | 198 | 84.7 | 1.1e-14 | 2.8e-13 | 54521092 |
| 112 | 315,429,559 | 224 | 96.1 | 9.5e-15 | 1.4e-13 | 54521092 |
| 114 | 357,074,092 | 256 | 109.0 | 7.4e-15 | 2.0e-13 | 54521092 |
| 116 | 403,449,473 | 310 | 123.3 | 7.9e-15 | 1.7e-13 | 54521092 |
| 118 | 455,008,817 | 338 | 139.1 | 2.4e-14 | 1.7e-13 | 54521091 |
| 120 | 512,240,846 | 381 | 156.7 | 1.0e-15 | 1.4e-13 | 54521091 |
| 122 | 575,672,044 | 437 | 176.4 | 1.4e-14 | 2.8e-13 | 54521091 |
| 124 | 645,869,007 | 501 | 198.0 | 7.7e-15 | 2.8e-13 | 54521314 |
| 128 | 809,041,515 | 589 | 248.5 | 4.4e-15 | 2.0e-13 | 54521315 |
| 132 | 1,007,186,853 | 769 | 309.9 | 1.3e-14 | 1.4e-13 | 54521314 |
| 136 | 1,246,540,136 | 904 | 384.2 | 1.2e-15 | 2.8e-13 | 54521315 |
| 140 | 1,534,236,271 | 1181 | 473.6 | 4.7e-15 | 3.4e-13 | 54521314 |
| 144 | 1,878,410,904 | 1449 | 580.8 | 6.2e-15 | 2.6e-13 | 54521315 |
| 148 | 2,288,309,690 | 1785 | 831.9 | 6.3e-15 | 2.0e-13 | 54521314 |
| 152 | 2,774,406,248 | 2260 | 1010.6 | 1.6e-14 | 2.6e-13 | 54521315 |
| 156 | 3,348,529,260 | 2731 | 1218.3 | 2.2e-15 | 3.1e-13 | 54521314 |
| 160 | 4,023,999,219 | 3795 | 1466.0 | 1.9e-14 | 3.7e-13 | 54521314 |

### φ6 gap, degree 3

| Λ | states | seconds | RSS GiB | shell | tuning | job |
|---|---|---|---|---|---|---|
| 136 | 4,658,985 | 10 | 1.1 | 5.6e-16 | 8.9e-16 | 54521096 |
| 144 | 5,819,359 | 8 | 1.4 | 4.7e-15 | 1.8e-15 | 54521096 |
| 152 | 7,184,072 | 19 | 1.7 | 1.6e-14 | 5.3e-15 | 54521096 |
| 160 | 8,775,812 | 7 | 1.9 | 1.9e-14 | 1.8e-15 | 54521096 |
| 168 | 10,618,462 | 9 | 2.3 | 9.2e-15 | 1.2e-14 | 54521096 |
| 176 | 12,737,099 | 24 | 2.8 | 5.9e-15 | 1.8e-15 | 54521096 |
| 184 | 15,157,995 | 8 | 3.3 | 1.1e-14 | 1.8e-14 | 54521095 |
| 192 | 17,908,617 | 14 | 3.8 | 3.3e-15 | 1.1e-14 | 54521095 |
| 200 | 21,017,626 | 11 | 4.5 | 2.9e-15 | 1.4e-14 | 54521095 |
| 208 | 24,514,878 | 12 | 5.2 | 7.2e-15 | 3.6e-15 | 54521095 |
| 216 | 28,431,424 | 13 | 6.0 | 8.8e-15 | 7.1e-15 | 54521095 |
| 224 | 32,799,509 | 20 | 7.0 | 1.5e-14 | 7.1e-15 | 54521095 |
| 232 | 37,652,573 | 18 | 8.0 | 6.7e-16 | 7.1e-15 | 54521095 |
| 240 | 43,025,251 | 22 | 9.1 | 3.4e-15 | 7.1e-15 | 54521095 |
| 248 | 48,953,372 | 25 | 10.4 | 1.6e-14 | 3.6e-15 | 54521095 |
| 256 | 55,473,960 | 24 | 11.8 | 1.8e-14 | 3.6e-15 | 54521095 |
| 288 | 88,263,277 | 37 | 18.6 | 1.0e-14 | 1.1e-14 | 54521095 |
| 320 | 133,804,601 | 67 | 28.2 | 1.3e-14 | 1.1e-14 | 54521095 |
| 352 | 195,040,908 | 109 | 41.0 | 6.8e-15 | 1.1e-14 | 54521095 |
| 384 | 275,221,009 | 109 | 57.9 | 2.1e-14 | 2.1e-14 | 54521095 |
| 416 | 377,899,549 | 152 | 79.5 | 4.4e-14 | 7.1e-15 | 54521095 |
| 448 | 506,937,008 | 205 | 106.7 | 2.2e-16 | 1.4e-14 | 54521095 |
| 480 | 666,499,701 | 278 | 140.3 | 2.2e-14 | 1.4e-14 | 54521095 |
| 512 | 861,059,777 | 307 | 181.2 | 2.7e-14 | 8.9e-16 | 54524669 |
| 544 | 1,095,395,220 | 398 | 230.6 | 2.2e-14 | 1.4e-14 | 54529459 |
| 576 | 1,374,589,849 | 496 | 289.4 | 2.3e-14 | 4.3e-14 | 54524669 |
| 640 | 2,089,421,112 | 760 | 440.1 | 2.4e-14 | 7.1e-15 | 54524669 |
| 672 | 2,536,754,557 | 931 | 625.0 | 8.7e-14 | 2.1e-14 | 54529459 |
| 704 | 3,052,340,809 | 1128 | 752.2 | 2.0e-15 | 1.4e-14 | 54524669 |
| 736 | 3,642,792,860 | 1361 | 897.9 | 4.4e-16 | 2.8e-14 | 54529497 |
| 768 | 4,315,029,537 | 768 | 935.1 | 2.2e-14 | 4.3e-14 | 54524669 |
| 800 | 5,076,275,501 | 2130 | 1243.8 | 4.9e-14 | 4.3e-14 | 54529459 |
| 832 | 5,934,061,248 | 2803 | 1454.0 | 7.1e-14 | 2.8e-14 | 54524669 |
