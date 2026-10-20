# C5(3): reduction of the nonprimitive masters (workflow wf_d8d88d50-343, 2026-10-02, session C63d)

**Run.** Four research agents (ℒ₃, Z₃, 𝒦₃, d=2 cross-check) and three adversarial verifiers per positive claim,
62 agents in all. **Every positive claim was confirmed 3/3.** Raw results are in `workflow_result_raw.json`; each
agent's code and data are in `wf_*/`.

**Status labels.**
- **Exact** means a derivation that parallels the proved d=3 half-shift steps of the note (§19) but is not yet
  written out as a full proof.
- **Numerical** means an identity found and confirmed to the stated digits, not proved.

## 1. Results at d=3

### Z₃: one new constant
- **Formula (exact):** Z₃ = (4π²/3)·S''(3/2) − (4G + π²/2)·Γ(1/4)¹⁰/(16π^{7/2}). Here G is Catalan's constant and
  S(b) = Σ_{ℓ,n≥0} (2ℓ+1) [ (b/2)_{ℓ+n} ((b−1)/2)_n / ((3/2)_{ℓ+n} n!) ]³.
- **What S is.** S(3/2) = 𝔥₃(0), the two-variable Horn value of the note (td:Hbase). So S''(3/2) is the second
  upper-parameter derivative of 𝔥₃.
- **Equivalent form:** Z₃ = (12G + 3π²/2)·Q₃ + (4π²/3)·𝔰, where 𝔰 = S''(3/2) − (36G + 9π²/2)𝔥₃(0) =
  −9.16451788587850552025…
- **The first derivative reduces (exact):** S'(3/2) = Γ(1/4)¹⁰/(64π^{9/2}) − π𝔥₃(0). This is equivalent to
  dW₃/db = 0 at b = 3/2.
- **Basis of the formula:**
  - **General-b wheel (exact):** for 1 < b < 5/3 and by continuation,
    W₃(3;b) = 6π² S(b)/sin²(πb/2) − π^{11/2} Γ((5−3b)/2)/[2 sin³(πb/2) Γ((3−b)/2)⁶ Γ(b/2)³].
  - **General-b Gamma amplitudes, Dixon + Dougall (exact):** 𝔞₃(b)𝔟₃(b) = π⁵ Γ(1−3β)/Γ(1−β)⁹ with β = (b−1)/2.
- **Accuracy.** Values to about 250 digits (`wf_Z3/Z3_values.json`).
- **Negative results.** S''(3/2) does not reduce to Q₃'s pieces times level-4/8 constants of weight ≤ 2, nor to P4(3)
  pieces (LLL bounds in the raw results).

### ℒ₃: two new derivative constants
- **Formula (exact):** ℒ₃ = 4π·P4(3) − 2π²X₀ + 6√2π(π − 2 log 2)·𝔞₄𝔟₄ − 2π·𝔡_H + 12√2π·𝔟₄·𝔡_a.
- **The two constants:**
  - 𝔡_H = d/db[N(4c₀ + 5c₂)] = 2539.52445251775601935…, from the Horn sector;
  - 𝔡_a = d/db[N^{1/2}·𝔞₄(b)] = 11.38885029910005086619…, from the ordinary sector.
- **Notation.**
  - N(b) = [Γ(3/2 − b/2)/Γ(b/2)]⁴.
  - c_k(b) are the Fourier coefficients of the sample: Ξ₄(t;b) = c₀ + c₁ cos 2π(t + b/4) + c₂ cos 4π(t + b/4).
  - c₁ = 2𝔞₄𝔟₄.
- **Basis of the formula:**
  - **Finite modes for every b < 2 (exact).** The td:momentModes structure persists.
  - **Dougall (exact).** 𝔟₄(b) has a closed form for every b, so (N^{1/2}𝔟₄)' = (π/2 − log 2)𝔟₄.
- **Accuracy.** About 160 digits (`wf_L3/L3_final_values.json`).
- **Negative results.** 𝔡_H, 𝔡_a and ℒ₃ are not in the span of the P4(3) blocks with level-8 weight-≤1 coefficients
  (LLL at 155 digits, confirmed at 125). This is unlike d=1 and d=2.

### 𝒦₃: no reduction found
- **Value.** 𝒦₃ = 1.14859464952717933655664631081067318763384810126431784211170151… to 430 digits, by Arb ball
  arithmetic on gs:Kseries (`wf_K3/K3_value.json`). It agrees with the 100-digit spectral run C to 1.5e-96.
- **Negative results.** No relation exists:
  - with the complete level-4 weight-≤4 basis (32 constants), |c| < 1.3e12;
  - with Q(√2) coefficients, |c| < 1.9e5;
  - with level-8 Dirichlet-type extensions, |c| < 1.25e4;
  - with Γ(1/4)-power or CM-newform L-value extensions, |c| < 2e7;
  - with the new d=3 constants of ℒ₃ and Z₃, |c| < 4.2e6.
- **A pattern that does not extend.** Write 𝒦_d = ½[Φ_d + A_d U_d]. Then Φ₁ = ψ₁(¼)(3ψ₁(¼) − ψ₁(¾)) (proved) and
  Φ₂ = (ψ₁(¼) − ψ₁(¾))²/4 = 64G² (numerical). But Φ₃ = 2𝒦₃ − AU = 10.9457632283938902… is not such a quadratic form
  (bound 1.8e19).
- **Structural reason, a sketch.** At d=3 the 𝒦 summand lives on two lattices offset by ½, with weight 2(x − y). Only
  the antisymmetric part factorizes into single sums.

## 2. C5(3) with the reductions

Exact algebra, checked symbolically and to 1e-119:

    46656 C5(3) = −1536[P5(3) + 𝒦₃] + (384A − 2304π) P4(3) + 1152π² X₀ − 3456√2 π(π − 2 log2) 𝔞₄𝔟₄
                  + 1152π 𝔡_H − 6912√2 π 𝔟₄ 𝔡_a + 9536π² 𝔰
                  − 1728 Q₃² + (720A² + 11064π² + 85824G − 4032) Q₃ + S(A),

with A = 2 + 4 log 2 − π and S(A) as in C5_d3.pdf.

- **The open constants.** Besides the primitive Horn values (𝔥₃(0); 𝔥₄ in X₀, X_h, P4(3); 𝔥₇ in P5(3)), the
  remaining constants are:
  - 𝒦₃;
  - two parameter derivatives of the same two-variable Horn functions (𝔰 from 𝔥₃, 𝔡_H from 𝔥₄);
  - one ordinary-sector derivative 𝔡_a.
- **Count.** This is a structural reduction, not a reduction in count: four open constants (𝒦₃, 𝔰, 𝔡_H, 𝔡_a) replace
  three (𝒦₃, ℒ₃, Z₃). In return it shows that ℒ₃ and Z₃ lie in the derivative closure of the primitive Horn
  functions.

**C5(3) = −5.8503514207513272292179442304977443001109973463783.**
- **Uncertainty.** Shown to 50 digits; the input values are good to about 1e-80, except that P5(3) has been
  independently confirmed only to about 1e-53.
- **Agreement.** The 𝒩₃ form and the reduced form agree to 2e-119.

## 3. d=2 cross-check (C62d's identities)

- **Method.** A spectral representation independent of C62d's factorized single sums (`wf_d2check/`, symmetry jobs
  567514–17 and 567669–72).
- **ℒ₂ = −2 log 2 · P4(2):** run-to-run agreement 70 digits, residual 1.7e-79.
- **𝒦₂ = 32G² − 28ζ(3) log 2:** run-to-run agreement 59 digits, residual 3.1e-62.
- **Algebra.** gs:C5 at d=2 with these identities equals C62d's formula 972 C5(2) = … exactly.
- **Correction.** P4(2) = 250.48731558186728553185175688791…; the value 250.48731558189013 I gave earlier was the
  archive's 1e-11 spectral value. In the same way the exact 𝒦₂ = 3.5181091385902522… (my earlier spectral 3.518109138587
  was good to only 1e-12).

## 4. Side results and tooling

- **d=4 (numerical):** Z₄ = (5/2)ζ(5) = P4(4)/8, to 6.7e-76.
- **By-product identity (numerical):** 4𝔟₄ = (√2 − 1)·𝔘_{4,1}(3/4) + 2(1 + √2)·𝔘_{4,1}(3/8). Residual 3.4e-378 by an
  independent method; probably a Bailey three-term relation, not proved.
- **mpmath 1.3 defect.** `mp.zeta(s, a)` with complex s has an absolute error floor of about 10^−dps. This caps my
  spectral run C (`hp_masters_d3.py` tails) at about 95 digits, consistent with its 1e-93…1e-96 agreement with the
  agents' independent values. The 43–56-digit runs A and B are unaffected. The agents used their own
  Euler–Maclaurin Hurwitz zeta (e.g. `wf_d2check/hp_masters_d2.py: hz()`).

## 5. Open

- Written proofs of the general-b half-shift steps (Z₃ and ℒ₃ formulas). Each step mirrors a proved td step, and they
  are confirmed numerically to 100–250 digits.
- Whether 𝔰, 𝔡_H, 𝔡_a or 𝒦₃ reduce further. All tests so far are LLL bounds, not independence proofs. A complete
  level-8 basis for 𝒦₃ would need about 121 elements and over 1000 digits.
- Proofs of the d=2 identities (C62d).
