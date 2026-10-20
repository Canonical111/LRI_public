# Independent HT check for the d=1 LRI: derivation

This note derives the Hamiltonian that `indep_ht.py` diagonalizes, starting from the definition of the model. It then
lists every point where the derivation agrees or disagrees with the production specification. The specification
consists of `docs/WINDOW.md` §Definition, `docs/ALGORITHM.md` §"Hamiltonian and packed layout", and the description
in the task prompt. No production code, results or other documents were read.

Notation: δ = Δσ, s = 1 − 2δ, ε = 1 − 4δ.

## 1. Generalized free field in radial quantization (d = 1)

- φ is a generalized free field (GFF) of dimension δ, with ⟨φ(x)φ(y)⟩ = |x − y|^(−2δ).
- In d = 1 the conformal family of φ has exactly one state at each level n: |n⟩ ∝ Pⁿ|φ⟩.
  - Its norm follows from [K, P] = 2D and the dimension δ: ⟨φ|Kⁿ Pⁿ|φ⟩ = n! (2δ)_n.
- Normalized single-particle states. Put a_n† |0⟩ = Pⁿ|φ⟩ / √(n!(2δ)_n). Then
  φ(x)|0⟩ = Σ_n xⁿ/n! Pⁿ|φ⟩ = Σ_n u_n xⁿ a_n†|0⟩, with **u_n² = (2δ)_n / n!**.
  - Check: the out-state is ⟨0|φ(x)† = lim ⟨0|φ(1/x̄)… In the radial-quantization inner product,
    ⟨0|φ(y′) φ(x)|0⟩ with y′ = 1/y gives ⟨φ_out(y)|φ_in(x)⟩ = Σ_n u_n² (xy)ⁿ = (1 − xy)^(−2δ). This is
    exactly |1/y − x|^(−2δ) times the conformal factor y^(−2δ) of the inversion, i.e. the two-point function.
  - Hence u_n² is the Taylor coefficient of (1 − z)^(−2δ), as stated. Unit test `test_u_coeffs` checks this, and
    also checks that Σ u_n² (x/y)ⁿ reproduces (y − x)^(−2δ).
- The GFF Hilbert space is the bosonic Fock space over these single-particle states. The dilatation operator is
  D = Σ_n (n + δ) a_n† a_n, with the free vacuum at energy 0.
- On the unit "sphere" S⁰ = {+1, −1}, the operator at |x| = 1 is
  φ(x) = Σ_n u_n (sgn x)ⁿ (a_n + a_n†).
  - Reflection x → −x is the unitary R with R a_n R = (−1)ⁿ a_n.
  - R acts on a Fock state as (−1)^(total level). The zero mode a0 (n = 0) is reflection-even.
- **Split.** φ(1) = q + X, with q = a0 + a0† (u_0 = 1), X = B + B†, B = Σ_{n≥1} u_n a_n.
  - At x = −1: X(−1) = R X R, with B(−1) = Σ (−1)ⁿ u_n a_n. The zero mode q is the same at both points.

## 2. The perturbed Hamiltonian

- **The perturbation.** The perturbation ∫dx [r :φ²: + (g/12) :φ⁴:] becomes, in radial quantization at unit radius,
  a potential summed over the two points of S⁰.
  - Following the specification (the coefficient of g q⁴/12 in H_z is 1), I use the **sphere average**
    V̄ = ½ Σ_{x=±1} V(x), with V = r :φ²: + (g/12) :φ⁴:.
  - A "sum" convention would rescale both r and g by 2. This is a normalization convention for the reported
    couplings, not a physics difference. Δ_ε does not depend on it.
  - The full Hamiltonian is H = D + V̄.
- **Normal ordering.** All normal ordering is with respect to the free vacuum, for all modes including a0.
  - Zero mode: :qᵏ: = He_k(q), the probabilists' Hermite polynomials, since ⟨q²⟩ = 1. So
    :q²: = q² − 1, :q³: = q³ − 3q, :q⁴: = q⁴ − 6q² + 3.
    Unit test `test_zero_mode_normal_ordering` checks He_k(q) = Σ_m C(k,m) a0†^m a0^(k−m) in a large number basis.
  - Bath: :Xᵏ: = Σ_m C(k,m) (B†)^m B^(k−m).
  - q and X act on different modes and are each linear in creation/annihilation operators. Therefore
    :(q+X)ᵏ: = Σ_j C(k,j) :q^(k−j): :X^j:.
- **Zero-mode part.** With p = (a0 − a0†)/i we have [q, p] = 2i and q² + p² = 4 a0†a0 + 2. So
  δ a0†a0 = δp²/4 + δq²/4 − δ/2. The terms with no bath operator are
  δa0†a0 + r(q² − 1) + (g/12)(q⁴ − 6q² + 3) = δp²/4 + A q² + g q⁴/12 + c, where
  - **A = δ/4 + r − g/2**;
  - c = −δ/2 − r + g/4.

  This is the specification's H_z, plus the constant c. I keep c, so that g = r = 0 gives a free vacuum at exactly 0.
  Constants cancel in every observable, including the window (§6).
- **Bath vertices.** Collecting the coefficient of W_k = :X^k::
  - from r :φ²: = r(:q²: + 2qX + :X²:);
  - from (g/12):φ⁴: = (g/12)(:q⁴: + 4:q³:X + 6:q²::X²: + 4q:X³: + :X⁴:).

  The multipliers are:
  - L1 = 2r q + (g/3)(q³ − 3q) = (2r − g) q + (g/3) q³ = (2A − δ/2) q + (g/3) q³;
  - L2 = r + (g/2)(q² − 1) = (r − g/2) + (g/2) q² = (A − δ/4) + (g/2) q²;
  - L3 = (g/3) q;
  - L4 = g/12.

  These are **identical to the specification's L1..L4**.
- **Result.** H = [−δ ∂_q² + A q² + g q⁴/12 + c] ⊗ 1 + 1 ⊗ Σ_{n≥1}(n+δ) a_n†a_n + Σ_k L_k(q) ⊗ W̄_k, where W̄_k is
  the sphere average of :X^k:.
  - The kinetic term follows from p = −2i ∂_q, so δp²/4 = −δ ∂_q².

## 3. Reflection-even sector

- **Claim.** In the reflection-even sector the sphere average equals the vertex at x = +1.
- **Proof.** V(−1) = R V(1) R, so V̄ commutes with R. For R-even states ψ, χ:
  ⟨ψ|V(−1)|χ⟩ = ⟨ψ|R V(1) R|χ⟩ = ⟨ψ|V(1)|χ⟩. Hence ⟨ψ|V̄|χ⟩ = ⟨ψ|V(1)|χ⟩.
- **Consequences.**
  - The even sector is spanned by bath states of **even total level**. The zero mode is R-even.
  - V̄ has no even/odd block.
  - Unit test `test_reflection_average` builds V(±1) on the full truncated Fock space and checks all three
    statements for k = 1..4.

## 4. Product regulator and the truncation-projection claim

- **Bath truncation.** Bath Fock states (partitions, multiplicities k_n of modes n ≥ 1) with total level
  Σ n k_n ≤ N, with no particle-number cap. In the reflection-even sector only even total levels are kept.
- **Zero mode.** a0 is not truncated: it is represented on a converged sinc-DVR grid (§7).
- **Claim.** Normal-ordered products never pass through a level above both endpoints.
- **Proof.**
  - B lowers the level strictly (each a_n with n ≥ 1 removes n ≥ 1 units). B† raises it strictly.
  - In (B†)^m B^(k−m) acting on |χ⟩, the levels first decrease monotonically from lev(χ), then increase
    monotonically to lev(ψ). Every intermediate level is ≤ max(lev ψ, lev χ) ≤ N.
  - So inserting the projector onto level ≤ N between the factors changes nothing. The product of the truncated
    matrices equals the projection of the exact operator.
  - Intermediate states may have odd level, so the products are formed on the full (both reflection parities)
    truncated space and only then restricted to even levels. That is how `Bath` builds W_k.
- **Corollary.** H(L) is exactly the level ≤ L block of H(cut). This is what the window needs.
- **Unit tests.** `test_projection_claim`:
  - :X^k: built at cutoff N agrees bit-for-bit with :X^k: built at N + 4 and projected;
  - an anti-normal-ordered B B† visibly fails the same test, so the claim is specific to normal ordering;
  - B strictly lowers the level.

  `test_window_fixed_point` checks the H(L) block statement.

## 5. Z2 field parity and sector layout

- **Z2 field parity.** q → −q, a_n → −a_n. On a product state (zero-mode parity p, bath with n_b particles) the
  field parity is f = p ⊕ (n_b mod 2).
- **Selection rules.** L1, L3 are odd in q and W1, W3 flip the bath particle-number parity. L2, L4 and W2, W4 are
  even. `Bath` checks these selection rules.
- **Layout.** In sector f, bath states with even particle number carry zero-mode parity f, and odd ones carry 1 − f.
  This is exactly the specification's "p_i = f XOR b_i".

## 6. Tuning, observable and the window

- **Levels.** E_even0 < E_even1 < … and E_odd0 < … are the levels of the reflection-even sector.
- **Tuning conditions.** E_odd0 − E_even0 = δ (σ) and E_odd1 − E_even0 = 1 − δ (shadow χ).
- **Output.** Δ_ε = E_even1 − E_even0.
- **Derivatives.** H is linear in (r, g), so Hellmann–Feynman gives exact derivatives through the operators
  ∂H/∂r and ∂H/∂g (coefficient sets `COEF_DR`, `COEF_DG`).
- **Newton.** Damped Newton on (r, g), stopped at max|F| < 1e-12.
- **First order at weak coupling.** In the zero-mode number basis, ⟨k|:q²:|k⟩ = 2k and ⟨k|:q⁴:|k⟩ = 6k(k−1). So
  E_k = kδ + 2rk + g k(k−1)/2 + O(coupling²).
  - The σ condition (k = 1) gives r = O(ε²).
  - The χ condition (k = 3) gives 3δ + 3g = 1 − δ, so g = ε/3.
  - Then Δ_ε (k = 2) = 2δ + g = 1/2 − ε/2 + ε/3 = **1/2 − ε/6**.
  - Second order brings in the bath (C2(N)).
- **Window.**
  - Ev(L) is the lowest field-even, reflection-even eigenvalue at bath cutoff L, at the same couplings. Ev(0) is the
    zero mode alone, including the constant c.
  - D(N) = Ev(cut) − Ev(cut − N) is added to every bath state of level N in both field parities, with D(0) = 0.
  - Constant shifts of H shift every Ev(L) equally and cancel in D(N).
  - **literal:** Ev(L) = λ_min(H(L)).
  - **consistent:** s_L solves s = λ_min(H(L) + Σ_{N>0} (s − Ev(L−N)) P_N), for L = 2, 4, …, cut in order.
    - λ_min(s) is a minimum of functions linear in s, so it is concave, with slope 1 − p₀ (p₀ is the level-0
      weight of the minimizing vector).
    - F(s) = λ_min(s) − s is concave and decreasing (F′ = −p₀).
    - Newton s ← s + F/p₀ lands at or to the right of the root after one step, then decreases monotonically to it.
    - At L = cut, the main problem's E_even0 equals s_cut. This is checked at every point; |difference| ≲ 1e-13.
  - **Derivatives.**
    - literal: ∂Ev(L) = ⟨∂H⟩.
    - consistent: from s_L = λ_min, ∂s_L = ⟨∂H⟩ + (1 − p₀)∂s_L − Σ_{N>0} w_N ∂Ev(L−N), so
      ∂Ev(L) = (⟨∂H⟩ − Σ_{N>0} w_N ∂Ev(L−N)) / p₀.
    - Main levels: ∂E_k = ⟨∂H⟩_k + Σ_N w_k(N) (∂Ev(cut) − ∂Ev(cut−N)).
    - Unit test: agreement with central finite differences at the 1e-7 level, which is the finite-difference floor.
  - The whole window table is recomputed at every coupling evaluation, including Newton line-search trials.

## 7. Numerical method

- **Zero mode: sinc-DVR.** q_j = j h, |j| ≤ M. Kinetic matrix of −∂² (Colbert–Miller): T_jj = π²/(3h²),
  T_jk = 2(−1)^(j−k)/(h²(j−k)²).
  - Parity-adapted basis: e_0 = |0⟩, e_j = (|j⟩+|−j⟩)/√2, o_j = (|j⟩−|−j⟩)/√2.
  - Even functions of q are diagonal. Odd functions map e_j ↔ o_j with value L(q_j); e_0 maps to 0.
- **Grid choice.**
  - A starting grid comes from the 1D Born–Oppenheimer zero-mode problem −δ∂² + V(q) + c + e_bath(q), where
    e_bath(q) is the bath ground energy at fixed q and N_BO = min(N, 10).
  - Code v1, used for 24 of the 38 table points: the lowest 24 1D levels must be stable to 2e-12 under h → h/1.5 and
    Q → 1.5Q.
  - Code v2, used for 14 points, fixed a roundoff runaway of v1 at δ ≲ 0.19:
    - the box Q is the point where the WKB decay integral ∫κ dq beyond the outer turning point of E_top (the 20th
      1D level + 2) reaches 36;
    - h is refined until the lowest 20 levels are stable under h → h/1.5, to max(2e-12, 200 ε_mach ‖H‖).
  - Both versions add a 15% safety margin.
  - The N = 16, 20 points reuse the verified grid of the lower cutoff and are verified again.
  - **Every reported point is then verified in the full problem.** At the tuned couplings the full spectrum (and,
    with the window, the whole window table) is recomputed on a grid 1.5× finer and on a grid 1.5× wider. The
    tuned Δ_ε change is estimated by the linearized retune δΔ − ∂Δ·J⁻¹δF.
  - **Refinement criterion.**
    - v1 refined if that change exceeded 1e-11 or a relative level changed by more than 1e-10.
    - v2 refines above 1e-10 (the task's requirement). It keeps the round with the smallest check differences, and
      stops when refinement does not reduce them; that is the double-precision floor.
    - Every final point passed in its first round, with check differences ≤ 4.4e-11.
  - Two points were also fully retuned on the fine and wide grids (`retune_check.py`). The changes are ≤ 5e-12, so the
    linearized estimate is conservative.
- **Bath.**
  - Partitions with level ≤ N. B is a sparse matrix on all levels ≤ N; :X^k: comes from sparse products, then is
    restricted to even levels and split into particle-parity blocks (dense).
  - The matrix-vector product uses the bath-major layout X[i, a]: dense GEMMs with the W blocks, a small GEMM with
    the DVR kinetic matrix, and diagonal scalings.
- **Eigensolver.** ARPACK (scipy `eigsh`, `which='SA'`, tol 1e-11 on a spectrum shifted so the wanted eigenvalues
  are O(1)). Dense `eigh` is used when the dimension is ≤ 1200. Explicit residual norms are recorded.

## 8. Agreement / disagreement with the specification

| # | Item | Status |
|---|---|---|
| 1 | u_n² = (2δ)_n/n!, the Taylor coefficient of (1−z)^(−2δ) | **agree** (derived §1) |
| 2 | Reflection a_n → (−1)ⁿ a_n; even sector = even bath level | **agree** |
| 3 | Sphere average = vertex at x = +1 projected to the even sector | **agree** (proof §3, unit test) |
| 4 | Normal ordering w.r.t. the free vacuum for all modes; :q^k: Hermite; :X^k: = Σ C(k,m) B†^m B^(k−m) | **agree** |
| 5 | H_z = δp²/4 + A q² + g q⁴/12, A = δ/4 + r − g/2 | **agree** (up to the additive constant c, which cancels) |
| 6 | L1 = (2A−δ/2)q + (g/3)q³, L2 = (A−δ/4) + (g/2)q², L3 = (g/3)q, L4 = g/12 | **agree** |
| 7 | Truncated normal-ordered products equal projected exact operators; H(L) is the N ≤ L block of H(cut) | **agree** (proof §4, unit tests) |
| 8 | Z2 layout p_i = f XOR b_i, no symmetry-allowed state dropped | **agree** |
| 9 | Ev of odd L = Ev(L−1) | **agree** (no odd-level states in the even sector) |
| 10 | D(N) = Ev(cut) − Ev(cut−N) on all bath states of level N, all sectors, D(0) = 0 | **agree** |
| 11 | literal: Ev(L) = λ_min(H(L)) | **agree** |
| 12 | consistent fixed point; Newton with F′ = −p₀; F concave; monotone after one step | **agree** (derived §6) |
| 13 | At L = cut, s = ground energy of the main problem | **agree** (checked numerically at every point) |
| 14 | Tuning Jacobian: literal ∂Ev = ⟨∂H⟩; consistent ∂Ev(L) = (⟨∂H⟩ − Σ w_N ∂Ev(L−N))/p₀ | **agree** (derived independently, FD-checked) |
| 15 | **"Ev(0) = 0"** (WINDOW.md) vs "Ev(0) is the lowest field-even eigenvalue at cutoff 0 (zero mode alone)" (prompt) | **conditional.** These agree only if the spec's energies are measured from the zero-mode-alone vacuum, i.e. the "common scalar removals" subtract w₀. In my convention (free vacuum = 0), Ev(0) = λ_min(H_z + c) ≠ 0 in general. Ev(0) enters only D(cut) = Ev(cut) − Ev(0). If production set Ev(0) to 0 *without* measuring Ev(L > 0) from the same zero, D(cut) would be shifted by −Ev(0)_true on the top level, which changes results. I implement the prompt's definition, which is shift-invariant. |
| 16 | Perturbative branch: g = O(ε), r = O(ε) | **agree, sharper:** g = ε/3 + O(ε²) and r = O(ε²) (first-order r vanishes), confirmed numerically (r/ε² ≈ 0.2 at δ = 0.2499) |
| 17 | Coupling normalization (sphere average, not sum) | **agree** with the spec's H_z coefficient; the sum convention would double r and g |
