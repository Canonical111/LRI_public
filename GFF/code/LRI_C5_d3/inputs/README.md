# Inputs for the C5(3) workflow (copied 2026-10-02 from ~/Downloads/LRI_complete_research_bundle.zip)

- **`three_dimension_addition.tex`** (= condensed note §19, `td:*`). The d=3 half-shift reduction of the primitive
  wheels:
  - ordinary moments 𝔘_{r,m}^{(ω)}(u);
  - the finite-mode identities for Ψ_{r,m};
  - the two-variable Horn functions 𝔥_r(t);
  - the formulas for Q₃, P4(3) and P5(3).
- **`primitive_periodization_addition.tex`** (= condensed note §18, `fp:*`). The general-d periodization (Barnes
  kernels, finite Fourier modes, samples Ξ_r(t)) and the d=2 factorization.
- **`general_d3/`**:
  - `d3_reduction.py`: evaluators for 𝔘, Ψ, 𝔥_r and the sample formulas;
  - `check_exact.py`, `verify_d3.py`, `check_spectral.py`;
  - `period_values.json`: Q₃, P4(3), P5(3), Ξ samples and the amplitudes 𝔞₃, 𝔟₃, 𝔞₄, 𝔟₄, h at 55 and 90 digits;
  - `horn_arrays.json`;
  - `identities.json`.
