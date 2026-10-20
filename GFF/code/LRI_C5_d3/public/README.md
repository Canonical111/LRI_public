# LRI_C5_d3: the five-loop coefficient C5(3) and the d = 3 nonprimitive masters

This package evaluates the fifth-order coefficient of the ε expansion of Δ_ε at d = 3, C5(3), from the general-dimension
formula of the note (gs:C5, note Section 1.1) with the d = 3 values of its masters. It also reduces two of the three
nonprimitive masters, L3 and Z3, to parameter derivatives of the primitive two-variable Horn functions, and gives the third,
K3, to 430 digits.
The physics and the proofs are in the note (`GFF/note/`), Sections 1.1, 19.8, 20.4 and 21.8. The package's own `README.md` and `WORKFLOW_RESULT.md` are kept as written on
2026-10-02. This file (`public/README.md`) describes what the public copy contains.

## Results

| quantity | value | status | record |
|---|---|---|---|
| C5(3) | −5.8503514207513272292179442304977443001109973463783… (50 digits) | exact in the six masters; numerical value | `c5_value.json`, `WORKFLOW_RESULT.md` |
| C4(3) | 1.2280635453276230799666561680749… | exact in Q3, P4(3) | recomputed by `make replay` |
| K3 | 1.14859464952717933655664631081067318763… (430 digits) | no closed form known; no relation in the bases tried | `wf_K3/K3_value.json` |
| L3 | −62.7105849683876693472961734335348… (about 158 digits) | reduced to 𝔡_H, 𝔡_a (derived, not a written proof) | `wf_L3/L3_final_values.json` |
| Z3 | 8.82092489306009248553686732817408… (about 250 digits) | reduced to 𝔱₃''(3/2) (derived, not a written proof) | `wf_Z3/Z3_values.json` |
| 𝔡_H, 𝔡_a | 2539.52445251775601935…, 11.38885029910005086619… | new derivative constants | `wf_L3/L3_final_values.json` |

The d = 3 form used everywhere is

    46656 C5(3) = −1536[P5(3) + N3] + 384 A P4(3) − 1728 Q3² + (720A² + 336π² − 4032) Q3 + S(A),
    S(A) = −15A⁴ + (360 − 30π²)A² + (828π³ − 1728 − 21456 ζ(3))A − 83π⁴ + 312π² + 5328,
    N3 = K3 + (3/8) L3 − (149/32) Z3,   A = 2 + 4 log 2 − π.

Q3, P4(3) and P5(3) are the proved rank-two forms of note Section 19; their values come from the research bundle's
package `lri_d3_reduction_update`, of which `inputs/general_d3/` is a byte-identical copy (code and three records). That
package is exported separately as `GFF/code/lri_d3_reduction_update`.

Accuracy. The digits of C5(3) are limited by P5(3), whose independent confirmation reaches about 10⁻⁵³. The other inputs
are good to about 10⁻⁸⁰. The digits of K3, L3 and Z3 rest on two independent evaluations each:
- K3: two Arb runs of the residue series agree to 2.5 × 10⁻⁴³³, and the 100-digit position-space value of `LRI_C5_general_d` agrees to 3.6 × 10⁻¹⁰⁰.
- L3: two Cauchy circles agree to all 165 stored digits.
- Z3: two circles agree to 8.6 × 10⁻²⁵⁴.
- All three agree with independent spectral runs (runs A and B at 43 digits, run C at about 96 digits).

None of these figures is an interval bound.

Status, as in the note (20.8, 21.11) and `WORKFLOW_RESULT.md`. The reduced forms of L3 and Z3 rest on general-b half-shift
steps that are derived, not written out as proofs, and are confirmed numerically to 10⁻⁵¹ and beyond. The 430-digit K3
rests on the mixed-trace step (M) and on taking [τ²] under the trace; the position-space route uses neither. All
statements that a constant does not reduce further are integer-relation bounds in the bases tried, not proofs.

## Layout of the public copy

```
README.md, WORKFLOW_RESULT.md   the package's own summary (2026-10-02) and the workflow result cited by the note
hp_masters_d3.py                spectral K3, L3, Z3 at 50-56 digits (runs A, B): finite spins + Stirling-Hurwitz tail, Cauchy derivatives
hp_part.py, hp_combine.py       the same split into one Cauchy circle per job (run C, 110 digits) and their combination
pslq_d3.py                      masters_d3.json (43 established digits from runs A and B) and the integer-relation tests (pslq_d3.log)
compute_c5.py                   c5_value.json: C5(3) from masters_d3.json and the period values
assemble_c5_d3.py               the symbolic d = 3 assembly (needs the research bundle's paths; see REPRODUCE.md)
run_A_dps50.json, run_B_dps56.json, run_C_{b,t,combined}.json, masters_d3.json, c5_value.json, pslq_d3.log
inputs/general_d3/              d3_reduction.py, check_exact.py, verify_d3.py, check_spectral.py; period_values.json,
                                horn_arrays.json, identities.json (byte-identical to lri_d3_reduction_update)
wf_K3/                          K3: k3flint.py (Arb residue series), runs hp1-hp4, K3_value.json (430 digits), K3_results.json,
                                the integer-relation battery (final_battery.py, bases.py, consts.py, lvals.py, irel.py, pslq_K3_*)
                                and the agent's exploratory scripts, kept whole because the note cites the folder
wf_L3/                          L3: pieces.py + gen3.py (Cauchy circles pA/pB at 170 digits), load.py, final_form.py, tdform.py,
                                L3_final_values.json (+ runB), the lattice-reduction battery (battery*.py, lllrel.py, *_dig155.json);
                                kept whole (cited as a folder), with its Slurm script and logs
wf_Z3/                          Z3: zcircle.py + zb.py (circles circA2/circB2 at 260/270 digits), derive.py, derived_circ*.json,
                                Z3_values.json, hp_periods.py + perA/perB.json, the PSLQ battery (pslq_z3.py, pslq_z3_results.json),
                                the d = 4 side check z4check.py
wf_d2check/                     an independent spectral check of the d = 2 closed forms of L2 and K2 (note 17.2), read by
                                LRI_C5_general_d; kept whole
wf_V_L3_b4/, wf_Z3_gamma_verify/  the verifier checks cited by note 20.8: c41(b) = 2 a4(b) b4(b) away from b = 3/2, and the
                                Gamma form of the zero-mode amplitude (also at complex b); each script has an absolute
                                sys.path line to edit before a rerun
public.mk, public/              added for the public release: test, replay, smoke targets, their scripts, this README,
                                REPRODUCE.md, Slurm templates (public/slurm/)
```

`LRI_C5_general_d` reads `wf_K3/K3_value.json`, `wf_L3/L3_final_values.json`, `wf_Z3/Z3_values.json` and `wf_d2check/` through
sibling paths (`../LRI_C5_d3/...`). The two packages must therefore sit side by side under `GFF/code/`.

## Targets (run from this folder)

| target | what | time, node |
|---|---|---|
| `make -f public.mk test` | `inputs/general_d3/check_exact.py` (25 exact identities, 288 Horn coefficients) in a copy, regenerated `horn_arrays.json` compared byte for byte; SymPy check of the d = 3 specialization of gs:C5 and of C4(3) | 2 s, any machine |
| `make -f public.mk replay` | reruns the package's scripts on the shipped records (pslq_d3.py, compute_c5.py, hp_combine.py, wf_L3/final_form.py and tdform.py, wf_Z3/derive.py, wf_d2check/combine_d2.py) and compares their outputs byte for byte; recomputes every quoted number of `../../results/closed_forms_3/LRI_C5_d3_quoted.json`; checks the printed formulas and the accuracy statements. Table: `.work/replay/REPLAY_c5_d3.md` | 4 s, one core |
| `make -f public.mk smoke` | fresh Q3, P4(3), P5(3) at 90 digits and K3 to about 110 digits (Arb), compared with the stored values | 15 s, one core |

Requirements: Python ≥ 3.8 with mpmath (1.3.0 tested) and SymPy; python-flint for `smoke` and for the K3 and lattice
batteries. The production runs (about 120 core-hours) are described in `public/REPRODUCE.md`.

## Not in the public copy

- The 43-digit write-up `C5_d3.tex`/`.pdf` (superseded the same day by `WORKFLOW_RESULT.md` and note 19.8), the root Slurm
  wrappers and logs, `run_dps30.json`, and the raw workflow output `workflow_result_raw.json`. The package `README.md`
  still names some of these.
- The other 38 verifier workspaces of the workflow (`wf_v*`, `wf_*verify*`, `wf_spur*`, ...). `WORKFLOW_RESULT.md` still
  names some of them. Their verdicts are summarized in `REVIEWS.md`.
- `inputs/*.tex`. These copies of the bundle's TeX additions are now note Sections 18 and 19 (one TeX note per
  direction, author rule 2026-10-16). No script reads them. `public/dropped_paths.txt` names them with `C5_d3.tex`/`.pdf`.

Records are released byte-identical. The shipped `wf_*` folders contain Slurm scripts and logs that name the cluster, its
partition and compute nodes. No checksum list or manifest binds any file of this package.
