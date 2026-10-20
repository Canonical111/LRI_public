# C5(2): the two non-scalar masters in closed form (session C62d, 2026-10-02)

## Result

At d = 2 (q = d/4 = 1/2), with a = log 2 and G Catalan's constant:

- **ℒ₂ = −2 log 2 · P4(2).**
- **𝒦₂ = 32 G² − 28 ζ(3) log 2.**

Inserted into the note's eq. gc:d2coefficients and divided by 48:

    972 C5(2) = −32 P5(2) + 56 log2 · P4(2) − 36 Q₂² + (240 log²2 + 596 G) Q₂
                − 1024 G² + 449 ζ(3) log2 − 80 log⁴2,

where:
- Q₂ = Γ(1/4)⁸/(24π⁴);
- P4(2) = (B₋² − B₊²)/(4π³) (note fp:P4two);
- P5(2) is the quadratic form in the five ₉F₈/₈F₇(−1) values X₀, X±, the same values as for P5(1) (note fp:P5two).

So C5(2) needs only Γ(1/4), π, log 2, G, ζ(3), the two ₄F₃(1) values F± behind B±, and the five fixed ₉F₈/₈F₇(−1)
values. These are exactly the scalar values already needed at d = 1, plus G. The non-scalar masters drop out
entirely. In particular the 127 + 163 + 54 Horn values (up to six variables, including a log-divergent endpoint
block) of horn_d2.pdf are not needed.

Numerically (30 digits, P4(2), P5(2) from the note):
- C5(2) = −38.833645896226, as before.
- The non-scalar contribution −1536(𝒦₂ + 3ℒ₂/8)/46656 = +4.17120405869, as before.

## How it was found

1. **Square-lattice factorization (exact).** At q = 1/2 one has:
   - T_{ℓn} = c_m c_n with m = ℓ + n and c_k = (1/2)_k/k!;
   - S_{ℓn} = e_m e_n with e_k = k!/(3/2)_k;
   - every polygamma combination in gs:Lseries / gs:Kseries is a sum of a function of m and a function of n,
     symmetric under m ↔ n;
   - the multiplicities d₀ = 1, d_{ℓ>0} = 2 turn the (ℓ, n) half-lattice into the full (m, n) square (the note's
     §18 "factorization of the wheel lattice").
   Hence every summand is Σᵢ αᵢ Aᵢ(m)Bᵢ(n):
   - ℒ₂: 48 products of 21 absolutely convergent single sums Σₖ cₖ⁴ φ(k);
   - 𝒦₂: 81 products of 27 single sequences with weights cₖ² and eₖ². Here the single sums diverge like
     Σ log^p k/k, and the double series converges only in the note's iterated (diagonal) order.
2. **𝒦₂ strip limit.**
   - The diagonal order equals lim_{θ→0} Σ_{m,n} g(m,n) e^{i(m−n)θ}, and Σ_ℓ |D(ℓ)| < ∞, so this limit is
     legitimate. The sum equals Σᵢ αᵢ Âᵢ(e^{iθ}) conj(B̂ᵢ(e^{iθ})).
   - Each Â(z) = ω Λ_p(z) + C_A + o(1), with Λ_p(z) = Σ z^k log^p k/k = (−1)^p ∂_s^p Li_s(z)|_{s=1}. The
     singular part comes from Li_s(e^{−w}) = Γ(1−s)w^{s−1} + Σ ζ(s−j)(−w)^j/j! with log w = log θ ∓ iπ/2.
   - The θ → 0 finite part is assembled exactly (Γ and Stieltjes coefficients).
   - Checks: the coefficients of log θ and log²θ cancel (1e-36 at 25 digits), the imaginary part vanishes, and the
     result reproduces C63d's spectral 𝒦₂.
3. **Single sums by Euler–Maclaurin at 70–100 digits.** The summand is evaluated with working precision that grows
   with log₁₀ x: tanh-sinh samples x ~ 10³⁰, and fixed-precision Gamma/polygamma differences cancel catastrophically
   there. `mpmath.sumem` gave wrong tails for exactly this reason and is not used.
4. **Identification (PSLQ, small bases, small integer coefficients).** Write a := Σcₖ⁴ and
   b := −(2/π)Σcₖ⁴[ψ(k+½) − ψ(k+1)]. Then:
   - a = (B₋ − B₊)/(4π³) and b = (B₋ + B₊)/(8π³), so P4(2) = 8π³ab;
   - Σcₖ⁴[ψ(k+½) − ψ(½)] = (πb − 2a log 2)/4;
   - 4Σcₖ⁴[ψ(k+½) − ψ(k+1)][ψ(k+½) − ψ(½)] + Σcₖ⁴ψ₁(k+½) = π²a/4 + π b log 2;
   - ℒ₂ = 3π⁴a² − 2π⁴b² + 8π³b·Sy − 12π²a·Sxy, which with the two lines above collapses to −16π³ log2 · ab =
     −2 log2 · P4(2). (Correction, 2026-10-02 proof: this PSLQ form holds only through the two lemmas. The structural,
     lemma-free collapse is ℒ₂ = 2π⁴a² − 4π⁴b² + 16π³b·Sy − 8π²a·Sxy; see proof/PROOF_STATUS.md.)
   - 𝒦₂ = 32G² − 28ζ(3) log2. This used the basis {ζ(3)log2, π⁴, π²log²2, log⁴2, Li₄(½), π²G, G²}; all other
     coefficients came out 0.

## Status

- **PROVED (2026-10-02).** See `proof/PROOF_STATUS.md` and the merge-ready fragment `proof/proof_d2.tex`. The
  work is the C62d workflow wf_6fd83950-f9b: three routes, each checked by a rigor verifier and an
  independent-numerics verifier, and all six verdicts are ACCEPT.
  - **ℒ₂ = −2 log2 · P4(2).** Two independent proofs, for the series gs:Lseries at d = 2:
    - the two-mode theorem holds for every rim parameter 0 < x < 3/4;
    - the rim-derivative collapse;
    - the elliptic identities (E1) and (E2), each proved twice.
  - **𝒦₂ = 32G² − 28ζ(3) log2.** Proved for gs:Kspectral at d = 2 (input: the note's d=1 Taylor data). It also holds:
    - for gs:Kseries, given the note's per-spin residue identity (S);
    - for gs:Kdefinition, given the mixed-trace identity (T), which the note states but does not prove.
- *Earlier status (superseded):* **Numerical identities, not proofs.** They hold to the precision in §Checks and agree with C63d's independent
  spectral values to their ~1e-12 accuracy. The exactness of the factorization step itself is a derivation, not a
  fit.
- **A structural reason for ℒ₂.** At d = 2 the lattice is square for every rim exponent. The periodized fourth-power
  sum Ω₄(t; x) = sin⁴(π(t+x)) Σ_{n≥0}[Γ(n+x+t)/Γ(n+1+t)]⁴ + (reflected part) is then a two-mode trigonometric
  polynomial A(x) + B(x) cos(2π(t + x/2)). All single sums of ℒ₂ are fixed by A, B and their first x-derivatives at
  x = 1/2. The relations above say that those derivatives are elementary multiples of A and B.
- **A structural reason for 𝒦₂.** Its second-power family is Gauss-summable,
  Σ Γ(n+x)²/n!² = Γ(x)²Γ(1−2x)/Γ(1−x)², which is why only classical constants appear.
- **Not done.** A complete proof of either identity.

## Checks

- **70 digits.** Slurm job 567346 on symmetry amdq node <NODE> computed all 50 single sums in parallel in 31 min
  (`confirm_dps70.json`, `confirm-567346.out`). Residuals:
  - ℒ₂ + 2 log2 · P4(2) (with P4 = 8π³ab): 4.5e-69
  - 𝒦₂ − (32G² − 28ζ(3) log2): 2.0e-70
  - a − (B₋ − B₊)/(4π³): 4.2e-72; b − (B₋ + B₊)/(8π³): 1.2e-71 (B± from the ₄F₃ sums, same Euler–Maclaurin code)
  - Sy and Sxy relations: 5.0e-72 and 7.4e-71
  - log θ coefficients of the 𝒦₂ strip limit: 5.3e-79; Im 𝒦₂: 2.9e-82
  - ℒ₂ = −347.24915312320113105847678307522316920816760199487427083420162434
  - 𝒦₂ = 3.5181091385902522416490901703077395226226728094710360690845577954
- **100 digits.** Job 567347 (<NODE>): see below.
- **Independent cross-check (first pass).** C63d's spectral evaluations (different representation, about 1e-12):
  𝒦₂ = 3.518109138587, ℒ₂ = −347.24915312324. Both agree.
- **Independent cross-check (high precision, C63d, 2026-10-02).** `LRI_C5_d3/wf_d2check`, symmetry jobs
  567514–567517 and 567669–567672, spectral representation, with run-to-run agreement:
  - ℒ₂ = −2 log2 · P4(2) to 70 digits (residual 1.7e-79);
  - 𝒦₂ = 32G² − 28ζ(3) log2 to 59 digits (residual 3.1e-62);
  - gs:C5 at d = 2, evaluated with both identities, equals the 972 C5(2) formula above exactly.

  C63d also corrected an earlier quote. P4(2) = 250.48731558189013 was the archive's 1e-11 spectral value; the true
  value is P4(2) = 250.48731558186728553185175688791…. Nothing here used that number: every evaluation goes through
  the exact form (B₋² − B₊²)/(4π³).
- **Unification (C63d).** K_d = ½[Φ_d + A U], where:
  - Φ₁ = ψ₁(¼)(3ψ₁(¼) − ψ₁(¾));
  - Φ₂ = (ψ₁(¼) − ψ₁(¾))²/4 = 64G².

  This puts d = 1 and 𝒦₂ in one formula; see `LRI_C5_d3/WORKFLOW_RESULT.md` for A and U.

## Files

- `factor_L2.py`, `factor_K2.py`: exact symbolic factorizations, written to `L2_factorized.json` and
  `K2_factorized.json`.
- `emsum.py`: robust Euler–Maclaurin summation.
- `check_L2.py`, `eval_K2.py`: assembly.
- `parallel_eval.py`: all identities at once, run on symmetry; output in `confirm_dps*.json`.
- `idfy.py`: early PSLQ exploration (superseded).
