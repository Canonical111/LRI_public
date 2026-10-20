# C5(3): simplest established form and a 43-digit value (2026-10-02, session C63d)

`C5_d3.pdf` contains the result:

  46656 C5(3) = −1536[P5(3) + 𝒩₃] + 384·A·P4(3) − 1728 Q₃² + (720A² + 336π² − 4032) Q₃ + S(A)

  S(A) = −15A⁴ + (360 − 30π²)A² + (828π³ − 1728)A − 21456 ζ(3) A − 83π⁴ + 312π² + 5328

- A = 2 + 4 log 2 − π, and Euler's constant cancels.
- 𝒩₃ = 𝒦₃ + (3/8)ℒ₃ − (149/32)Z₃.
- Q₃, P4(3) and P5(3) are the proved d=3 forms (condensed note §19).

C5(3) = −5.850351420751327229217944230497744300110997. The previous value had an accuracy of about 1e-12.

**Integer-relation tests (`pslq_d3.log`).** 𝒦₃, ℒ₃ and Z₃ do not reduce, within the stated coefficient bounds, to:
- the d=1-type polygamma forms;
- the pieces of P4(3) and Q₃;
- Q₃ times simple constants.

A search with coefficients up to 1e5 found only chance relations; the bounds are now set honestly.

**Files.**
- `assemble_c5_d3.py` is the symbolic assembly.
- `hp_masters_d3.py` computes the high-precision 𝒦₃, ℒ₃ and Z₃ (finite spins plus a Stirling–Hurwitz tail, and
  Cauchy derivatives in b and τ).
- `c5d3_run.slurm` is the job script.
  - Runs A and B: symmetry jobs 567344 and 567345, amdq; outputs `run_A_dps50.json` and `run_B_dps56.json`, logs
    `c5d3-*.out`.
  - `run_dps30.json` is a local validation run.
- `pslq_d3.py` writes `masters_d3.json` and `pslq_d3.log`.
- `compute_c5.py` writes `c5_value.json`.
- `make_c5d3_tex.py` writes `C5_d3.tex`, compiled with SyncTeX.

**Inputs.**
- Archived Q₃, P4(3) and P5(3) (90-digit formula run) from `~/Downloads/LRI_complete_research_bundle.zip`, under
  `packages/lri_d3_reduction_update/verification/general_d3/period_values.json`.
- A copy of the code lives on symmetry in `~/c5d3/`.
