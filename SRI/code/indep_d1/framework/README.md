# framework: the response→beta map, the stability invariants, and a reusable assembler

This is part of the independent re-derivation of the C6/C7 inputs of
`LRI_SRI_research_compendium`. That compendium was only read. Role of this directory:
* derive the map from regulated, normalized responses to the essential beta functions F, H
  and to the invariants T, D, from first principles;
* compare that map with the note;
* provide a numerical module that takes raw-moment coefficients and returns all beta inputs
  and C3…C7 (and C8), with error propagation.

The symbolic report is **`framework.md`**. The input contract with the integration agents
(engine, direct) is **`INPUT_FORMAT.md`**.

## Phase 3 (2026-10-03): extension to C8 = 8 T4

The task: extend the framework to the eighth coefficient (note Secs. 14-15, l.1100-1170; appendix
app:C8polynomial, l.2781), in strict mode and with per-replicate errors, and run its old-input
part on our phase-2 production data. Everything here is local; no cluster was used.

**Results.**

| quantity | value | 1 sigma |
|---|---|---|
| B_old (old-input part of C8, our production replicates) | **−861.66357786093882** | 1.16e-5 (rel. 1.3e-8) |
| W (our semi-analytic three-kink integral) | −37.70811151495255511258856000191091523 | ~1e-39 |
| C8_partial = B_old + 4W | −1012.49602392074904 | 1.16e-5 |
| B_done, C8 | MISSING: S, L3, M21, M12, N2 and U, J9, Ndelta, Kv need raw scalars our engine has not computed yet | |

* **σ(B_old).** The three estimators agree: σ_cov 1.04e-5, σ_rep 1.16e-5 (R = 6, 5 dof) and
  σ_pool 1.04e-5. The quoted σ is the largest.
* **Error budget.** By input, J dominates (9.4e-6), then K (4.4e-6) and Ω (3.1e-6). By job, the
  largest are A5_E, Q8, A7 and Z4_E. Tier 1 alone differs from the final input by −4.6e-5 ± 3.1e-5
  (−1.5 σ). This is the A7 group of phase 2.
* **Sealed comparison.** It was run after `out/C8_production.json` existed
  (`compare_c8_production.py`, SHA-256 `0700e9b1…`). The note's B_old is −861.6635672354797792.
  The difference is −1.06e-5, a pull of **−0.92** (rel. 1.2e-8). Our W agrees with the note's 15
  printed digits (−1.1e-16).

**What was built.**

1. **`derive_C8.py` (sympy, about 45 s).** All checks pass (details in `framework.md` §10):
   * J₀β = R₁ through g⁹ gives j₇ = −2∂_vC₇,₀ + (EE C₇)₀ and λ₆ = −2K₆,₀ − 4v∂_vK₆,₀ + 2v(EE K₆)₀.
     h₈ and b₉ equal the note's recurrence.
   * The series division reproduces eq:K8norm and eq:C9norm.
   * The full δ⁴ trace T₄: power counting finds only the 35 named inputs and b₃(0,0). The one-pair
     sector would enter, but it vanishes because h₂ ≡ −1.
   * C₈ = 8T₄ is affine in the ten new inputs, with constant coefficients equal to eq:C8assembly.
   * The remainder B_old (61 terms) equals the appendix polynomial, which the script **parses from
     the note's TeX**, and equals the module's table.
2. **Module.**
   * **C8 two ways.** `res.C[8]` = 8T₄ from the fixed point. `res.c8["C8_asm"]` = B_old +
     eq:C8assembly. They agree to 1e-47 in values and gradients, at any point once the tree data are
     exact; a failure raises.
   * **New outputs.** `B_old8` (also at order D4), `B_done8`, `C8_asm` and `C8_partial`.
     `C8_partial` is B_old plus only the available new terms. An absent input is **never zero**:
     its term is omitted, and the input is listed in `c8_info["partial_missing"]` with the scalars
     it needs.
   * **`c8_combine(res, extra)`** (CLI `--beta-extra`) adds beta-level values of absent new inputs
     from an independent source, such as our W.
   * **Per-replicate errors at C8.** `from_replicates(..., mixed_R="group")` (CLI
     `--mixed-R group`) handles replicate blocks with different R. `merge_inputs(...,
     independent=True)` (CLI `--independent-files`) renames the replicate blocks of independent runs.
     A block id shared by two files is now an error; before, it was silently paired.
3. **`make_requirements.py`** regenerates the following.
   * `required_inputs_C8.json`: the same 201 scalars; `by_output` gains `B_old8` and `B_done8`. The
     D4 list and the D4 sensitivities are byte-identical.
   * New `out/sensitivities_C8.json`: dC8/dx, dB_old/dx, dB_done/dx and d(new input)/dx for all 201
     scalars, at **our own point**.
     * The point: 116 production means, plus 45 further coefficients our engine already computed
       (production all-log results, poles1, kplus1, validation runs). The 40 not yet computed are set
       to 0, and the exact dependence on them is given.
     * Only 9 gradient entries depend on those 40, all with simple rational coefficients; the
       gradients are exactly linear in them (curvature 4e-37).
     * The note's structure of the four packages is confirmed exactly: for example
       dJ₉/dA9[ε⁰ℓ¹] = 1, dK_v/dQ8_v[ε⁰ℓ¹] = −4 and dK_v/dQ6_vv[ε⁰ℓ⁰] = 16.
   * New `out/C8_new_scalars.json`: the 85 scalars beyond D4, by new input. 45 are computed by our
     engine and 40 are not yet.
4. **`c8_production.py` and `compare_c8_production.py`**: the production B_old and partial C8
   (above), then the sealed comparison.
5. **`tests/test_c8.py`**: ten groups covering the table vs the derivation and the TeX, C8 two
   ways, partial mode at the beta and raw levels, the note's structure, finite differences,
   per-replicate and grouped-R assemblies, block renaming, `c8_combine`, and the CLI. All pass. The
   whole suite passes (`out/tests.log`), and the phase-2 gate probe still passes 11/11.

**Precision needed at C8** (`sensitivities_C8.json`, `precision_plan_C8`).
* The large raw gradients of C8 belong to exact or already-precise low-order scalars:
  * |dC8/dA3[ε⁰ℓ¹]| = 1.3e4, where A3[ε⁰ℓ¹] = 6 exactly (give it as exact);
  * A3_v[ε⁰ℓ⁰] 397;
  * Q4[ε⁰ℓ¹] 331, which is exact.
* The new high-kink single logs enter with O(1) constant coefficients: A9[ε⁰ℓ¹] 1/4, Z8[ε⁰ℓ¹] −1/4,
  A7_d[ε⁰ℓ¹] 3/4, Q6_vd[ε⁰ℓ¹] −1/2, Q8_v[ε⁰ℓ¹] −1/8 and A7[ε⁰ℓ⁰] −2.
* Equal sharing of σ(C8) = 0.025 (1e-4 relative) over the 85 new scalars needs about 1e-2 absolute
  on each of them. If |A9_1| ~ 6e5, that is about 2e-8 relative.

**Update 2026-10-07 (C8 assembly with engine tiers A + B + C, `../RESULTS_C8.md`).** All 201 raw scalars of C8 are now
supplied by the engine; `Framework("C8").from_replicates(strict=True)` on every output gives C8 = 8 T4 = 242.825 +- 2.37
(C8_asm - 8 T4 = 1.7e-13, the tree-data rounding), U = -1296.68755 +- 0.0015, Kv = -1487.005 +- 0.16, J9 = -291.9 +- 9.5.
The note's raw decompositions of U, Kv, J9, Ndelta and C8 (eq:C8short) are reproduced exactly by the gradients. Against
the claim: -1.92 sigma (all in A9[eps^0 l^1]); C8 - J9/4 at -0.20 sigma. The tier-A update below is kept for the record
(`../RESULTS_C8_tierA.md`).

**Update 2026-10-04 (C8 assembly, tier A; now `../RESULTS_C8_tierA.md`).** Engine tier A supplied the raw scalars of S, L3, M21, M12,
N2 and Ndelta, so B_done and these inputs are now computed. This module ran in strict mode on exactly those outputs,
with three error estimators: B_done = 563.4040557 +- 1.1e-5 and C8_partial = 1334.7958592 +- 1.2e-5. U, J9 and Kv are
still MISSING (tiers B and C), so the paragraph below now applies only to them.

**Not done (needs engine data).** S, L3, M21, M12, N2 (B_done) and U, J9, Ndelta, Kv need the 40
raw scalars listed in `out/C8_new_scalars.json`. Examples: A3_ddd[ε⁰ℓ¹] (W from the engine),
Q4_vvv/vvd/vdd[ε⁰ℓ¹], Q6_vv, Q6_vd, Q8_v, A7_d, A9 and Z8.
* With them, `run_framework.py --raw prod.json --raw c8.json --independent-files --order C8
  [--mixed-R group]` gives C8 strictly, with per-replicate errors.
* Until then, `--allow-missing` gives the partial sums.

## Phase 2 (2026-10-03): fixes of the phase-1 critique

Every item of the critique of `framework` is fixed and covered by a regression test. The
mathematics did not change. On random complete data, the revised module gives values and
gradients identical (difference 0) to the phase-1 module, and the 116/201 required lists are
identical.

| item | fix | test |
|---|---|---|
| **D1** absent scalars silently zero | **Strict mode is the default.** Inputs are validated against `required_inputs()`, not atom windows. Every structural slot is either supplied or a MISSING tag with its own name. An absent required scalar raises `MissingInputError`, which names all of them (CLI exit 2). `null` counts as absent, and `load_spec_raw` keeps it. `strict=False` / `--allow-missing` reports MISSING outputs instead. The spurious "treated as ZERO" warnings are gone. A nonzero coefficient below the structural power is an error. The same rules hold for `from_normalized` and `from_beta`. | `tests/test_strict_missing.py`: dropping **any single** required scalar raises and names it (all 116 at D4, all 201 at C8, every normalized and every beta input). In non-strict mode every dependent output is MISSING and the others are unchanged. |
| **D2** sigmas ignored | `sigmas=` and `cov=` are honoured on `from_raw`, `from_normalized`, `from_beta` and `from_replicates`, and by the CLI flags `--sigmas` and `--cov`, with the derivative-convention scaling. Conflicting, unknown or exact-with-sigma entries are errors. | `tests/test_error_model.py` |
| **D3** outputs not regenerable | `make_requirements.py`, called from `run_all.sh`, writes `out/required_inputs_D4.json`, `out/required_inputs_C8.json` and `out/sensitivities_C6_C7_D4.json`, evaluated at the **engine's own pilot5 data**, not the archive. The archive-point version, labelled COMPARISON ONLY, goes to `tests/archive_comparison/`. | regenerated lists identical to phase 1 |
| covariance / replicates | Covariance blocks, a systematic floor per scalar, and per-block replicate sample covariances, so blocks may have different R. `from_replicates` runs **the full assembly once per QMC replicate** and reports the mean and the replicate standard error next to the linear propagation. Adapters read the engine's v2 `results.json`, a canonical format, and the flat and spec formats. | `tests/test_replicates.py` |
| latent pmax | The internal Z2/Q2 series now have validity pcap. A product that needs a higher order is flagged, and strict mode raises `TruncationError`. | `tests/test_pmax.py` (the phase-1 bookkeeping would have returned a wrong value silently) |
| interface docs | `INPUT_FORMAT.md` states three rules: `d` on an `E` atom also differentiates the f_δ inside the source; `E` is two-sided, U^odd for A and U^even for Z, Q; every required scalar is mandatory, including positive-eps coefficients and structural zeros. | |
| minor | `Framework()` and `closed_forms()` no longer change the global `mp.mp.dps`. The vacuous T4 check is now a real test. `res.normalized` entries that depend on absent inputs are MISSING. | `test_error_model.py` [6], `test_module_vs_sympy.py` |

**The critic's own scripts, rerun** (`out/review_rerun_phase2.log`):
* `check_note_recurrence_direct` gives 1.47e-40 and PASSED.
* `check_required_completeness` finds exactly 116 scalars, as before.
* `check_missing_semantics` finds **0 silent-zero drops** (phase 1: all 7 dropped scalars were
  silently zeroed). It is run non-strict, because strict mode stops at the first drop.
* `check_sigma_keyword` gives keyword = pair form on all three entry points (phase 1: 0 on two of
  them).

**Findings during phase 2:**

1. **Three required scalars were silently zero in phase 1.** They are A3[ε⁻¹ℓ¹], A3[ε²ℓ¹] and
   Z4[ε⁻²ℓ¹].
   * Both the archive-derived raw file and the engine's phase-1 data omit them. Neither has
     such a term.
   * The phase-1 module therefore treated them as zero without saying so. They were also missing
     from the phase-1 sensitivity table.
   * Their sensitivities are not small: dC7/dZ4[ε⁻²ℓ¹] = −1.60, dC7/dA3[ε⁻¹ℓ¹] = −0.92 and
     dC7/dA3[ε²ℓ¹] = 0.64.
   * A3[ε⁻¹ℓ¹] = 0 follows from A3 = Z2 + C3 at order ε⁻¹. The other two rest on the producers'
     pole analysis.
   * **Gate review (2026-10-03): all three are now established independently.** The A3 base atom
     has an elementary closed form (two-gap integral, `review_gate_phase2/check_A3_closed_form.py`,
     checked against 2D quadrature to 1e-31 at four ε). Its log terms are exactly
     2ℓ² + 6ℓ − 6εℓ, so A3[ε⁻¹ℓ¹] = A3[ε^p ℓ¹] = 0 for all p ≥ 2, and A3[ε⁰ℓ¹] = 6,
     A3[ε¹ℓ¹] = −6 (both as in the engine's pilot5 data). Z4[ε⁻²ℓ¹] = 0 by the method of regions:
     ε⁻² comes only from the region where the two outer gaps are O(ε) and the middle gap is O(1),
     where the integrand factorizes to r₁⁻² r₃⁻² (1 − r₂). That gives ε⁻² · ½ with no log, the
     engine's Z4[ε⁻²ℓ⁰] = 0.5. Every other region scales as ε⁻¹ or ε⁰.
   * In strict mode they must now be supplied explicitly as exact zeros. The engine's v2
     `collect` marks them (`zero` flag, `zeros` list, and exact entries in
     `framework_input.json`); for other data, use `--zero`.
2. **The phase-1 sensitivity table had the wrong convention.** It was labelled "derivative
   convention", but its gradients were with respect to the internal Taylor coefficients.
   * Derivative atoms were therefore overstated by a factor i!j!. For example, dC7/dA3_vv[ε⁰ℓ⁰]
     is 8.55, not 17.1, and dC7/dA3_vvv[ε⁰ℓ⁰] is 0.5, not 3.0.
   * The error was conservative for precision planning. The regenerated table is correct, and
     `tests/test_error_model.py` checks it against finite differences.
   * The engine's `py/plan_production.py` read the old table, so its budgets for derivative atoms
     were stricter than needed.
3. **The two error propagations agree.** The engine agent's `tests/e2e_framework.py` is an
   independent implementation of the replicate error propagation that uses this module's
   gradients. On a synthetic v2 `results.json` it agrees with `from_replicates`:
   * σ_rep(C7) is 4.608e-5 in the engine script and 4.61e-5 here;
   * σ_cov(C7) is 4.209e-5 in the engine script and σ_linear(C7) is 4.21e-5 here.

   The engine's own canonical writer (`campaign.framework_input`) and this module's
   `results.json` adapter give the same assembly: C6, C7 and K agree to about 2·10⁻¹⁵ relative
   (the rounding of the means), and their σ to all printed digits.

**Gate review of phase 2 (2026-10-03).** Every must-fix item was re-checked against the code.
The suite and the critic's scripts were rerun, and `make_requirements.py` was rerun in a scratch
copy: it regenerated all four files byte-identically. The reviewer's own probes are in
`review_gate_phase2/`.
* `gate_probe.py`: strict mode on pilot5; derivative-convention gradients against finite
  differences, including the three zeros, A3_vv and A3_vvv; the shipped table equals the live
  gradients; null, alias and NaN inputs; non-strict MISSING; per-replicate assembly; global dps.
* `check_A3_closed_form.py`: the A3 structural zeros (see finding 1).

One change was made to the module. Non-finite numbers (NaN or ±inf, as a value, replicate,
sigma or covariance entry) are now rejected when the input is parsed (`_to_mpf`). Before, a NaN
value propagated into NaN outputs, and C7 showed as MISSING with misleading
`<beta J9 not computed>` tags. The regression check is in `tests/test_error_model.py` [5]. The
suite passes after the change.

## Results in brief (phase 1, unchanged)

* **Recurrence derived.** I set up the projected responses with the resummed current
  (b_h = b0−√2h, η_h = √2hb_h), the normal-ordering factor N(h) and the prefactor √2b_h. The
  renormalization condition (pure-log counterterms, ℓ-independent finite responses) gives
  **J₀β = R₁**. Solving it order by order gives b3, h4, b5, h6, b7, h8 and b9. **They are
  identical to eq:subtraction (note l.437-444) and to its h8/b9 extension (l.1149-1155).**
  The derivation also proves h₂ ≡ −1.
* **Explicit counterterm check.** At b0=1, δ=0, with the note's displayed responses, I built the
  minimal-subtraction counterterms explicitly. They reproduce lo:eq:h4ct, lo:eq:g5ct and b₁, and
  the resulting β is ℓ-independent (Callan-Symanzik consistency).
* **Essential conversion.** F = z + Σ b_{2k+1}u^k and H = −δ − 4Σ h_{2k}u^k come out of
  eq:matching with b0 kept variable. Only the ℓ-linear part of the matching enters β.
* **Derivative dictionary.** All 35 entries (D4 and C8) agree with note l.1122-1136.
* **Invariants.** The fixed point, D2, T2, D3, C6 = 4T3 with B_old, the linear part of D4,
  B_old^{D4} in full, and C8 = 8T4 **all agree** with the note. eq:conversion (C1…C8) is verified
  exactly.
* **Power counting.** Only the named dictionary inputs enter T≤4 and D≤4.
* **Validation with closed forms.**
  * a, p, A and E come from my own three-kink boundary integration and match the closed forms to
    10⁻⁴⁰.
  * c, b and f come from the note's displayed data and match eq:oldbetas to 10⁻³⁹.
* **New inputs re-derived independently (b3 sector),** compared with the archive's 39 digits or
  the note's 15 digits:

  | input | value | vs archive / note |
  |---|---|---|
  | V | −19.518741011574465808242207110132 | 0 at 39 digits |
  | α | −1.6576510838700072279237784615761 | 2·10⁻⁴¹ |
  | β | −16.027908690418506113987594423041 | 0 at 39 digits |
  | γ | −44.009684064767791523714540000681 | 0 at 39 digits |
  | W (C8) | −37.708111514952555112588560001911 | 1·10⁻¹⁶ (the note gives 15 digits) |

* **Comparison only.** The full pipeline on the archive-derived raw coefficients reproduces all
  25 archived inputs to 10⁻⁵⁷, and D4 and C3…C7 to the claims within 10⁻⁵⁶. In strict mode this
  needs the three structural zeros declared explicitly.
* **Discrepancies with the note:** none.

## Files

| file | content |
|---|---|
| `framework.md` | symbolic report (derivation, comparison, invariants, validation; §9 numerical interface) |
| `INPUT_FORMAT.md` | **input contract**: naming, conventions (E, d on E), mandatory list, canonical, flat, engine and spec formats, replicates, outputs |
| `lri_framework.py` | **reusable module** (pure Python + mpmath) |
| `run_framework.py` | command-line driver |
| `make_requirements.py` | regenerates the required lists and the sensitivities (about 10 s) |
| `derive_rg.py`, `derive_invariants.py` | symbolic Parts 1 and 2 (they do not import the module) |
| `validate_low_order.py` | Part 3: three-kink b3 sector and c, b, f (strict on the five outputs it determines) |
| `run_tests.sh` | all tests, logged to `out/tests.log` |
| `run_all.sh` | derivations, validation, regeneration, examples, then `run_tests.sh` |
| `tests/test_strict_missing.py` | D1 regression (about 45 s) |
| `tests/test_error_model.py` | D2, covariance and gradient convention (about 30 s) |
| `tests/test_replicates.py` | per-replicate assembly, canonical and engine-v2 adapters, CLI (about 35 s) |
| `tests/test_pmax.py` | latent pmax issue (about 10 s) |
| `tests/test_module_vs_sympy.py` | jets vs the sympy formulas; invariants; gradients; order bookkeeping |
| `tests/test_normalization.py` | raw→normalized layer vs the explicit eq:normalization products |
| `tests/test_archive_pipeline.py` | end-to-end on archive-derived raw data (**comparison only**) |
| `tests/test_vs_spec.py` | our 25 input expansions vs the spec agent's |
| `tests/test_c8.py` | phase 3: C8 two ways, eq:C8assembly table vs derivation and TeX, partial mode, note structure, grouped-R replicates, block renaming, `c8_combine`, CLI (about 80 s) |
| `derive_C8.py`, `out/derive_C8.log`, `out/C8_trace.json` | phase 3: symbolic C8 (J₀β = R₁ through g⁹; K8/C9 normalization; δ⁴ trace; B_old; eq:C8assembly) |
| `c8_production.py`, `out/C8_production.json` (+ `.sha256`), `out/c8_production.log` | phase 3: B_old on the production replicates (three estimators), W, partial C8, status of the new inputs (archive-free) |
| `compare_c8_production.py`, `out/C8_production_comparison.json` | phase 3: sealed comparison with the note's B_old and W (**comparison only**; refuses to run before the sealed results exist) |
| `out/sensitivities_C8.json`, `out/C8_new_scalars.json` | phase 3: d(C8, B_old, B_done, new inputs)/d(raw) at our own point, with exact point dependence and precision plan; the 85 scalars beyond D4 |
| `out/required_inputs_D4.json`, `out/required_inputs_C8.json` | mandatory raw scalars (116 / 201), flat and spec naming, by output |
| `out/sensitivities_C6_C7_D4.json` | d(C5, C6, C7, D4)/d(raw), derivative convention, at the engine's pilot5 point (`sens` = abs, `signed`) |
| `tests/archive_comparison/` | archive-point results (**comparison only**) |
| `out/beta_input_formulas.*`, `out/invariant_formulas.json` | the 35 inputs and the invariants as formulas |
| `examples/` | partial b3-sector input with σ's (`--allow-missing` demonstration) and its output |
| `review/` | the phase-1 critic's scripts and logs (unchanged) |
| `out/rerun_review_phase2.py`, `out/review_rerun_phase2.log` | the critic's four scripts rerun against the phase-2 module |
| `review_gate_phase2/` | the phase-2 gate reviewer's probes (`gate_probe.py`) and the A3 closed-form proof of the structural zeros (`check_A3_closed_form.py`), with logs |

## How to run

```bash
cd <PROJECT>/LRI_SRI_C6C7_independent/framework
./run_tests.sh                     # all tests, about 4 min in total, each test under 1.5 min (local)
python3 derive_C8.py               # symbolic C8 (about 45 s)
python3 c8_production.py           # B_old on the production replicates + partial C8 (about 15 s)
python3 compare_c8_production.py   # sealed comparison (after c8_production.py)
python3 run_framework.py --raw prod.json --raw c8run.json --independent-files --order C8 --mixed-R group --allow-missing
python3 run_framework.py --raw ../engine/runs/prod_6digit/framework_input_final.json --beta-extra W.json   # B_old, B_old + 4W
./run_all.sh                       # derivations + regeneration + tests (about 5 min, local; derive_*.py
                                   # are unchanged since phase 1 and do not import the module)
python3 run_framework.py --required --order D4 --out req.json
python3 run_framework.py --raw ../engine/runs/prod6/framework_input.json --out result.json      # engine v2 (canonical): per-replicate
python3 run_framework.py --raw ../engine/runs/prod6/results.json --out result.json              # same via the results.json adapter
python3 run_framework.py --raw engine.json --raw own_3kink.json --out result.json               # merged sources
python3 run_framework.py --raw mine_flat.json --sigmas sig.json --cov cov.json                  # flat, with errors
python3 run_framework.py --raw pilot.json --zero "A3[eps^-1 l^1],Z4[eps^-2 l^1]"                # declare proved zeros
python3 run_framework.py --raw partial.json --allow-missing                                     # MISSING instead of stop
python3 run_framework.py --normalized norm.json --sigmas sig.json
python3 run_framework.py --beta beta.json --sigmas sig.json
```

Exit codes: 0 means ok; 2 means required inputs are absent (all of them are listed); 4 means two
--raw files share a replicate block id (use --independent-files); 3 means
pcap is too small.

Requirements: Python ≥ 3.10, sympy 1.12 (tests and derivations only), mpmath 1.3. Nothing here
needs a cluster.

## Using the module

```python
import lri_framework as L
fw  = L.Framework(order="D4", dps=50)          # "C8" adds W,S,U,J9,L3,M21,M12,N2,Ndelta,Kv and T4/C8
fw.required_names()                            # the 116 mandatory raw names; required_inputs() by output
res = fw.from_raw(raw, sigmas=None, cov=None)  # strict; raw = dict, canonical dict, or a file path
res.C[7].v, res.sigma("C7"), res.gradient("C7")   # value, propagated sigma, d C7/d input (input convention)
rr  = fw.from_replicates("results.json")       # per-replicate assembly
rr.stats["C7"]   # value, sigma_linear, rep_mean, rep_se, sigma_extra, sigma_rep_total, nonlinearity, n_rep
data = L.merge_inputs([L.load_inputs("a.json"), L.load_inputs("b.json")], zeros=["A3[eps^-1 l^1]"])
fw8 = L.Framework("C8"); r8 = fw8.from_raw(data, strict=False)   # partial C8: r8.c8, r8.c8_info["partial_missing"]
r8.c8["B_old8"], r8.c8["B_done8"], r8.c8["C8_asm"], r8.c8["C8_partial"]   # eq:C8assembly pieces (Val)
L.c8_combine(rr, {"W": ["-37.70811151495255511258856000191091523", "1e-38"]})   # beta-level extras
```

**Naming and conventions.** The full rules are in `INPUT_FORMAT.md`.
* Raw names have the form `<M><n>[_<deriv>][eps^<p> l^<k>]`.
* `v` is ∂_v at v=1.
* `d` is the plain ∂_δ at δ=0. It is not the Taylor coefficient, and on an E atom it also acts on
  the f_δ in the source.
* `E` is the endpoint-source derivative EE: U^odd for A and U^even for Z and Q.
* `convention="taylor"` accepts Taylor coefficients instead.
* Normalized names have the form `C<n>[_deriv][l^k]` or `K<n>[_deriv][l^k]`.
* Internally every input is a Taylor coefficient. `Val.g` is the gradient with respect to it,
  and `Result.gradient` converts to the input convention.

**What the module does.**
1. It builds jets of Laurent-log series in (z, δ, η). The exact A1, Z2 and Q2 are built in;
   supplied ones are only compared with them.
2. It forms the normalized responses, with products formed before extraction.
3. It extracts [ε⁰ℓ⁰] and [ε⁰ℓ¹].
4. It solves J₀β = R₁ and reads off the dictionary.
5. It solves the fixed point and T, D as δ-series.
6. It computes C3…C7 (C8).

Behaviour along the way:
* **Errors** are propagated linearly in forward mode, with the exact gradients. The error model
  covers independent sigmas, covariance blocks, systematic floors, and the sample covariance of
  each replicate block divided by R_b.
* **Missing inputs.** Strict mode raises. Non-strict mode reports, for each affected output, the
  names it needs. An output can be flagged even though its numerical gradient with respect to the
  absent scalar cancels. This is conservative: the flag is structural.
* **Higher logs.** `Framework(kmax=8)` keeps the higher log powers for the note's higher-log
  checks.

**What the integration agents must supply.**
* All 116 scalars of `out/required_inputs_D4.json`, or all 201 for C8. They are [ε^p ℓ⁰] and
  [ε^p ℓ¹] coefficients only.
* That includes the structural zeros, given explicitly.
* Preferably as replicates (`INPUT_FORMAT.md` §3a/3c), so that within-job correlations are kept.

**Sensitivities and precision budget.**
* `out/sensitivities_C6_C7_D4.json` holds the gradients, which are almost independent of the
  evaluation point: they agree with the archive-point ones to 2·10⁻¹⁰.
* The largest are |dC7/dA3[ε⁰ℓ¹]| = 767 and |dC7/dQ4[ε⁰ℓ¹]| = 191; both scalars are exact (6 and
  4ζ₂−8).
* The largest non-exact ones are |dC7/dA3_v[ε⁰ℓ⁰]| = 82.8, |dC7/dA3[ε⁰ℓ⁰]| = 70.3 and
  |dC7/dA3_d[ε⁰ℓ¹]| = 61.2.
* The hardest scalars enter weakly: dC7/dA7_v[ε⁰ℓ¹] = −1/8, dC7/dQ8[ε⁰ℓ¹] = 3/8, and
  dC7/dA7[ε⁰ℓ¹] = 0.78.
* For a target σ(C7) ≤ T with the error shared equally, scalar i needs σ_i ≲ T / (|dC7/dx_i| √n).
  The three- and four-kink finite parts therefore need about 100× smaller absolute errors than
  the seven- and eight-kink single logs.

## Independence statement

* **Read for definitions:** the note. **Read afterwards, for comparison only:**
  * the archived `derive_D4.py` and its stored output;
  * `F3_final_100.json` and `C7_result.json`;
  * the spec agent's `archive_raw_coefficients.json`, now in `../spec/comparison/`. It is used
    only in `tests/test_archive_pipeline.py` and for the archive-point sensitivity file, which is
    labelled comparison only.
* **Not used:** no archive integration or evaluation code was imported, called or copied, and no
  archived raw integral data was used as an input.
* **The sensitivities** are evaluated at the engine's own pilot5 data.
* **Derived here:** the recurrence, the dictionary, the invariant algebra, the conversion, the
  two-kink sector, and the b3-sector values.
* **Phase 3 (C8).**
  * The note's eq:C8assembly and appendix polynomial are parsed from its TeX, as definitions to
    compare the derivation with. No archive file was opened.
  * The C8 sensitivities are evaluated at our own point: the production means plus our engine's
    other coefficients. The archive's C8 inputs and raw data were not read.
  * The archive's B_old and W (as printed in the note) were compared only in
    `compare_c8_production.py`, after `out/C8_production.json` and its SHA-256 had been written.
  * `derive_invariants.py` (phase 1, unchanged) still contains its labelled comparison-only
    numerical check with the archived inputs.
