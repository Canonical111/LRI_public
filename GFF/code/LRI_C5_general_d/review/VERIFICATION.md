# VERIFICATION: generic-d reduction of L_d and Z_d (LRI_C5_general_d), 2026-10-03

## Overall status: READY FOR THE NOTE AFTER THE LISTED FIXES

- All five reviews ACCEPT.
- No load-bearing statement is false.
- No printed formula in `general_d.tex` or `RESULT.md` §1 and §3 needs to change. Two printed sentences of `general_d.tex` do need rewording: the D_L ≈ P̂′ identification (F20) and the B₋ statement (F21).
- The top-mode theorem (foundation Thm 6, `th:top`) is true.
  - It had one full proof review (FR) and a spot read (ZR).
  - It is confirmed numerically at about 50 digits by independent code (TN).
- One intermediate estimate in its proof (Steps 3–4) is false as written. The corrected estimate gives the same conclusion on exactly the strip b < b_max that the theorem assumes (F1).
- One remark quotes wrong control numbers (F2). Its conclusion, that balance is essential, is confirmed by FR and TN.
- The other fixes concern:
  - rigor gaps for complex b;
  - a missing citation for ∂_bW_3(d;d/2)=0;
  - the D_L vs P̂′ wording;
  - an overcount in the Z inventory;
  - two overclaims in remarks;
  - status labels.
- Merge prerequisite (verifier):
  - The note's `app:generalPeriodization` works at b = d/2 with modes k ≤ r−1 (note ~l.4051).
  - It contains neither the general-b finite Fourier theorem nor c_{r,r−1}=0.
  - `gdr:samples`, `gdr:P4`–`gdr:Z` and `gdr:C5reduced` rest on both.
  - Either add the general-b statements, with the corrected proof of `th:top`, to that appendix, or cite `foundation/general_b_periodization.tex` explicitly as their source.

## Reviews

| key | lens | method | verdict |
|---|---|---|---|
| foundation-rigor (FR) | proofs of the foundation §§1–5, especially Thm 6 | every step rederived by hand; independent double-precision brute-force lattice sums (`brute_xi.py`, 17–25 nodes); direct Taylor residues; Fourier quadrature of eq:Il; b_max residue (symmetry jobs 569242, 569252) | ACCEPT with minor fixes |
| topmode-numeric (TN) | Thm 4(d), Thm 6, Prop 9, numerically | own lattice-sum code (2-D Euler–Maclaurin, tanh-sinh), dps 50; 22 balanced configurations plus controls (jobs 569215, 569260–569313) | ACCEPT |
| L-rigor (LR) | `L/L_general_d.tex`, L part of RESULT §2 | hand rederivation; exact sympy; contour residues; own coefficient code at 11 values of d; AGM quadrature | ACCEPT with minor fixes |
| Z-rigor (ZR) | `Z/Z_general_d.tex`, Z content of general_d/RESULT | exact sympy; own d=1,2,3 codes (spectral, midpoint, Richardson); reviewed code rerun against C63d refs | ACCEPT with minor fixes |
| formula-from-text (FT) | printed formulas of `general_d.tex`, RESULT §1 and §3 | sympy rederivation from W_r = −N^r Res; own samples by exact big-integer convolution plus Richardson (M = 1e5); 16-point b-circles (jobs 569180, 569192) | ACCEPT, no formula changes |

Verdict codes:
- valid
- valid* (valid with minor fixes)
- WRONG
- GAP
- n/c (not checked)

## Load-bearing claims

### A. Foundation (`foundation/general_b_periodization.tex`)

| # | claim (label) | verdicts | key evidence | status |
|---|---|---|---|---|
| A1 | Kernel, N_b, multiplicity GF (1+z)(1−z)^{1−d}, \|d_ℓ\| bound, spectral domain eq:bspec | FR valid | rederived; GF coefficients = fp:degeneracy | OK; wording F9 |
| A2 | Lemma 1 lem:reflect (eq:ff, eq:right, eq:middle, eq:left), lattice split | FR valid | by hand; brute force built on eq:right and eq:middle reproduces W_r to 1e-15 | OK |
| A3 | Lemma 2 lem:bounds | FR valid* | correct for real b; for complex b the large-\|y\| bound must avoid Im t = −Im σ | OK after F4 |
| A4 | Lemma 3 lem:count (iff condition, Y-bound) | FR valid | both regions redone | OK; wording F8 |
| A5 | b_max eq:bmax, tab:bmax; centre in strip iff 2/r<d<4 | FR valid | every entry recomputed | OK |
| A6 | Thm 4 th:finite (a),(b): convergence, poles of order ≤ r, Ξ entire, periodic, reflection | FR valid; TN valid | TN periodicity/reflection ≤ 2.2e-50; FR γ_m = γ_{−m}e^{2πimσ} to 1e-11..1e-15 | OK |
| A7 | Thm 4 (c),(d): growth bound, modes \|m\| ≤ r−1, boundary mode absent, c_{r,k} analytic | FR valid*; TN valid | TN boundary modes ≤ 2.1e-49 (balanced) and ≤ 6e-30 (unbalanced, so this holds without balance); off-grid reconstruction ≤ 2.6e-47 | OK after F4 |
| A8 | **Thm 6 th:top: c_{r,r−1}=0 on 0<Re b<b_max, all r ≥ 2, 0<d<4** | FR valid; TN valid; FT indirect; ZR spot read, no gap | see note A8 below the table | **TRUE**; proof OK after F1 |
| A9 | th:top proof Steps 1–2 (half-plane expansion, γ_{1−r} ∝ s_1, unfolding) and Step 5 (phase cancellation from σ+g=d/2; cos(V/2) odd about V=π) | FR valid | rederived | OK |
| A10 | th:top proof Steps 3–4 (eq:laplace, eq:Il, endpoint estimate, dominated convergence) | FR valid* (one false estimate); TN eq:laplace valid | see note A10 below the table | OK after F1 |
| A11 | Remark after th:top: unbalanced control \|γ_{±3}\| = 0.13, 0.020 | FR **WRONG** (numbers only) | for real σ the reflection forces \|γ_3\| = \|γ_{−3}\|; the true value is 0.0506 for both (1.7% of max\|γ\|); the quoted pair are raw DFT outputs at Im t = 0.05 without the node factor; foundation/ has no script for it | F2; conclusion confirmed |
| A12 | Remark after th:top: d=2 square identity Ξ_r = (−1)^r Ω_r(t;b/2)², c_{3,0}=c_{3,1}, r=2 constancy | FR valid; LR valid; ZR valid | rederived by hand; "W_2 elementary" n/c | OK; write proof (F18) |
| A13 | rem:d1: Ξ_r = (−1)^r 2^{−rb} Ω_r(2t;b), mode selection | FR, LR, ZR valid | duplication rederived three times | OK |
| A14 | Prop 9 prop:residue: functional, eq:weights (Bell), eq:elementary, B_{4,k}, eq:explicit | FR valid; TN valid; LR valid | FR Taylor residues to 1e-30 (r=2..5, complex σ); TN Bell form vs own series 1.7e-51..7.8e-49; W vs C63d refs to 47–50 digits; LR sympy exact. Top weights are nonzero (B_{3,2} = 6π²/s², B_{4,3} = −20π³/s³), so th:top is load-bearing | OK |
| A15 | Prop 10 prop:blocks: five blocks, Horn arrays | FR valid; TN | blocks vs brute force 2.5e-16..1.4e-14; TN c_{r,k} vs val50.json 1.4e-50..4.2e-50 | OK; F9 (removable points) |
| A16 | Cor 11 cor:nodes: b-independent nodes, exact DFT, jets | FR valid | aliasing and slopes checked | OK |
| A17 | rem:ranges, rem:sampleradius | FR valid* | σ ∈ Z occurs in the strip iff d > (2r−2)/(r−2) (r=5: d > 8/3), not only r=4; for r=4, d>3 the radius-1/2 jet disc contains σ=1, where the weights ω_{r,j} are singular. No d>3 point is used downstream | OK after F5 |
| A18 | rem:continuation (b_max ≤ b < b_spec, d>2) | FR valid* | not load-bearing; see note A18 below the table | F3 |

Notes on rows A8, A10 and A18:

- **A8 (th:top).**
  - TN: top modes 2.4e-51..1.6e-49 over 22 balanced configurations (d = 0.8–3.2, r = 2–6, complex b including d > 2), against surviving modes of 1.6e-3..1.
  - FR brute force: 1.9e-15..2.7e-14 in the fast cases. In the slow cases the residual halves when the cutoffs are doubled, so it is truncation error.
  - Controls are nonzero: 6.7e-4..4.6e-2. The δ-scan is linear in δ, so the balanced kernel sits on a simple zero.
- **A10 (Steps 3–4).**
  - eq:Il agrees with Fourier quadrature to 6e-11..1e-5.
  - The parenthetical a(V)a′(2π−V) = O(V^{2rg−2}) is FALSE for rg > 1. This is the generic case: rg = d for r = 4 at b = d/2.
  - The true exponent is rg−1+min(rg−1,0). Integrability then needs 2rg > d AND rg > d−1, which are conditions (i) and (ii) of b < b_max.
  - Verifier check (r=2): a′(2π⁻) = ∫₀^{2π}(2 sin(v/2))^{2g−2} dv = 6.9032 at g = 0.8. This is finite, and multiplied by B(g,g) it gives FR's limit 10.47.
- **A18 (continuation).**
  - FR derived Res_{b=b_max} Ξ_r = −4/(rΓ(d−1)) D_b^r [Φ(−t)+Φ(σ+t)], with Φ(u) = Σ_m [Γ(m+u)/Γ(m+u+g)]^r.
  - The top mode of this residue vanishes, the residual being 2e-18..3e-20 at 20 digits. The functional annihilates the residue, so W_r has no pole.
  - It matches the continued code to O(δ²).

### B. L_d (`L/L_general_d.tex`)

| # | claim (label) | verdicts | key evidence | status |
|---|---|---|---|---|
| B1 | Inputs (F1)–(F3) as quoted | LR valid* | the convergence clause is cited from the wrong lemma | OK after F11 |
| B2 | prop:tau, eq:colid, eq:arrays, eq:fiveCentre | LR valid | line by line | OK |
| B3 | prop:samples (three samples, κ, ρ, signs, eq:rhoid) | LR valid* | the continuity step at t=0 needs one sentence | OK after F12 |
| B4 | (F2) W_3, W_4 mode formulas; B_{4,3} = −20π³/s³ | LR valid; FT valid | sympy exact; contour residues at σ = 0.41 | OK |
| B5 | **th:three: three-node W_4 (eq:threenode, eq:W4five), two-node W_3 (eq:W3three)** | LR valid; FT valid | exact 3×3 solve (det 4 sin²πσ); off-centre W_4 vs C63d at b = 0.43, 0.675, 1.425 to 25 digits; FT off-diagonal W3/W4 to 43.8–53.5 digits | OK (rests on A8) |
| B6 | cor:P4 eq:P4five | LR valid | by hand | OK |
| B7 | prop:dseries | LR valid | slopes ±1/4; Weierstrass | OK |
| B8 | **th:L eq:Lfinal (Theorem 6)** | LR valid | own coefficient functions differentiated at 11 values of d (0.55–3.95, including 4/3, 2, 8/3, 3), worst 1.2e-38; vs C63d refs at d = 0.8, 1.25, 2.75: L to 5e-37..2e-39, P4 to 5e-38..2e-40 | OK |
| B9 | rem:special (d = 4/3, 8/3, 2, 1) | LR valid | exact zeros; fifth-order zero in b confirmed | OK |
| B10 | rem:integer | LR valid* | the d=3 claim "every Horn value is a finite combination of products of single-variable moments" is false for 𝔥_x, 𝔥_{1/2}, 𝔥_1 (nested m ≥ n sums) | F10 |
| B11 | Abstract digamma list | LR | eq:Lfinal uses ψ(q), ψ(q/2), ψ(3q/2), ψ((1+q)/2), ψ((1+3q)/2), not ψ(2q) (verifier confirmed) | F13 |

### C. Z_d (`Z/Z_general_d.tex`)

| # | claim (label) | verdicts | key evidence | status |
|---|---|---|---|---|
| C1 | **lem:node0, lem:nodeb, th:twonode: W_3 = uR + vM̂ for every b in the strip** | ZR valid | exact sympy solve; second form of F3 to 7e-40; d=1 direct midpoint sum to 1e-37..1e-42; d=3 own R, M̂ vs own spectral W_3(3;1.2) to 1e-16 | OK (rests on A8) |
| C2 | cor:zeromode | ZR valid; FT valid | exact; c_b = 0 allowed | OK |
| C3 | th:jets, eq:uvjets | ZR valid | exact zeros in sympy | OK |
| C4 | prop:first (eq:first, eq:firstzm); readings at d=1 and d=3 | ZR valid | eq:first = 4πs⁴W_3′ exactly; d=3 R′ identity to 1.7e-25 | OK |
| C5 | **th:simplified (eq:simplified, eq:simplifiedQ)** | ZR valid; FT valid | Z_full − Z_simp = −(2πc/(9s))W_3′ exactly; Z_3 from own code to 7e-23; FT Z to 29.5–35.2 digits at 8 values of d | OK given C6 |
| C6 | Input ∂_bW_3(d;d/2) = 0 | ZR valid*; FT valid | the proof is the note's Pattern T (gs:Tjet) with gs:wheelJets; gs:LZspectral only asserts it; numerically 1e-27..1e-38 (FT) | OK after F14 |
| C7 | prop:special(b): M̂(2;b) = 0, c_{3,0} = c_{3,1} | ZR valid | bilateral antisymmetry, 1e-30 | OK |
| C8 | prop:special(b) eq:R2 | ZR valid*; verifier | ZR: R(2;b) = Dixon(b/2)² identically (1e-30 at 5 points, including complex b); verifier: 2π²·₃F₂(½,½,½;1,1;1)² = Γ(1/4)⁸/(8π⁴) = 3Q₂, analytically and to 1e-29 | OK; O1 |
| C9 | prop:special(a), d=1: ĉ0 ≡ 0, R = Dixon, Z_1 = Q_1(2π²/3+8G) | ZR valid; FT valid | own spectral W_3(1;b) vs 6π²·Dixon/s² to about 1e-26, including complex b | OK |
| C10 | prop:special(c), cor:integer at d=3: Gamma form of ĉ0, Z_3 | ZR valid*; FT valid | conditional on C63d's c_{3,0} (derived there, not reviewed; the condition is stated); Gamma form to 3e-30 (b=1.2), 3e-28 (complex b), also holds at b=0.8; FT 31 digits; Z_3 to 28–29.5 digits | OK (conditional); F15 |
| C11 | prop:series (termwise differentiation) | ZR valid* | uniformity in b of the Lemma 2/3 bounds is asserted ("have room"), not stated | OK after F16 |
| C12 | tab:inventory: "4 new numbers beyond Q_d" | ZR **GAP** | Z depends on (R, M̂, R′, M̂′, uR″+vM̂″) with one constraint W_3′ = 0. That leaves 4 independent numbers including Q_d, so 3 beyond Q_d (verifier recount). RESULT and general_d count correctly | F17 |
| C13 | Abstract: "two real sampling nodes ... every b" | ZR valid* | t_b is real only for real b | F15 |
| C14 | Pole-node form for r=3; Z part of gdr:taylorLZ | ZR valid | rederived from F2 and F3; κ′, κ″ checked | OK |

### D. Printed formulas (`general_d.tex` merge fragment; RESULT.md §1 and §3)

| # | claim (label) | verdicts | key evidence | status |
|---|---|---|---|---|
| D1 | gdr:samples (W_3, W_4 in modes; expansion up to k = r−2) | FT valid; LR valid | sympy difference 0; off-diagonal W3/W4 to 43.8–53.5 digits | OK |
| D2 | gdr:samples4 (𝔥_u, 𝔰_u, κ, ρ) | FT valid | own lattice split; through P4 and W4 to 53 digits | OK |
| D3 | gdr:P4 | FT valid; LR valid | difference 0; spectral refs 31.4–39.0 digits; P4(1) 32.1, P4(2) 37.5, P4(3) 33.2 (input-limited) | OK |
| D4 | gdr:L, gdr:frozen (D_L) | FT valid; LR valid | difference 0; L to 30.8–37.6 digits; L_1 32.4 (vs lp:eq:MN), L_2 37.0, L_3 37.3 | OK |
| D5 | gdr:samples3, ĉ0, gdr:Q | FT valid | difference 0; 3Q to 29.4–35.2 digits | OK |
| D6 | gdr:Z (with the u, v statement) | FT valid; ZR valid | difference 0 after eliminating T3′; Z to 29.5–35.2 digits at 8 values of d | OK; citation F14 |
| D7 | gdr:taylorW, gdr:taylorQP (pole-node forms, λ_m) | FT valid | local expansion rederived; sympy difference 0; P4 and 3Q to 24.4–28.3 digits (aliasing-limited) | OK |
| D8 | gdr:taylorLZ | FT valid*; ZR valid (Z part) | product rule and η/θ/μ checked by hand; b-derivatives of the pole-node W give L and Z to 23.5–27.4 digits; the weighted series were not summed literally | OK; open item partly closed |
| D9 | **gdr:C5reduced (C5 assembly)** | FT valid | substituting into the note's gs:C5 gives an exact difference of 0 (negative control nonzero); reduced block vs the reference-master block to 30.4–35.6 digits at 8 values of d | OK |

Row D9 covers k_0, k_{1/2}, k_T, the coefficients 1192, 4768 and 2384/3, and Q_d.

### E. Specializations (`general_d.tex` gdr:special; RESULT.md §2)

| # | claim | verdicts | key evidence | status |
|---|---|---|---|---|
| E1 | d=1 (see the list below the table) | LR valid; FT valid; FR valid | proved by hand (LR); sympy exact; AGM to 30 digits; FT D_L(1) to 33 digits, ĉ0 jets < 1e-46 | OK; F18 |
| E2 | d=2: Ξ_4 = Ω_4², X_T = 𝒜², X_{0,1/2} = (𝒜±𝓑)², L_2 = −16 log2 𝒜𝓑/π = −2 log2 P4(2) | LR valid; FT valid | sympy exact; 37–38 digits | OK; F18 |
| E3 | Landen system gdr:landen; normalization vs PROOF_STATUS's −(10 log2 + 4γ) | LR valid* | consistent: 𝒩_x²-normalized vs raw modes, (𝒩_x²)′(½) = 4γ + 8 log2; FD residuals 4e-15 and 5e-16 | OK; F19 |
| E4 | d=3 dictionary to C63d's L_3 | LR valid* | sympy difference 0, BUT (2/(πS⁷))D_L = P̂′ − 8√2 N⁴c_{4,1} + 32 N⁴c_{4,2} (−1332.48 vs 274.55, verified to 1.2e-46); not literally P̂′ | F20 |
| E5 | Z at d = 1, 2, 3 | ZR valid; FT valid | Z_1 30.7, Z_2 35.2, Z_3 29.5 digits; (4π²/3)·Dixon″ = Q_1H to 50 digits | OK |
| E6 | "at d=3 no analogue of B₋ with elementary coefficients exists" | LR | a numerical (lattice-bound) statement, not a theorem | F21 |

The d=1 claims checked in row E1 are:
- gdr:d12lattice (duplication);
- c_{4,1} ≡ 0, hence X_0 ≡ X_{1/2};
- P4(1) = 32π𝒜 + 40π𝓑 = 13B₋ − 3B₊;
- L_1 = lp:eq:MN = eq:KLpsiReflected;
- the closed form of D_L(1).

The d=1, 2, 3 Z results in row E5 are:
- d=1: ĉ0 ≡ 0 and Dixon;
- d=2: M̂ ≡ 0 and Selberg;
- d=3: the Gamma form of ĉ0, with T3″ the only new number.

### F. Not covered by any review (status unchanged, as the authors label it)

- **Outside this work's reduction:**
  - K_d and P5(d), which this work does not change.
  - The full C5(1) = −731.1394766245398258538691. It was not re-run here; per RESULT it agrees with the note's −731.13947662454.
- **Negative results and attempts:** the PSLQ negatives (RESULT §4, gdr:attempts) and the other "what does not work" statements (Gauss-type two-node form, summation theorems, contiguous relations).
- **Z at resonant dimensions:** Z_d at d = 4/3 and 8/3 (Cauchy engine) has no independent check. L at these d is covered by LR.
- **The d=3 zero mode:** C63d's derivation of c_{3,0} has numerical support only. The d=3 Z specialization is conditional on it, as stated.
- **Codes and series:**
  - The accelerated Horn evaluation and the 90-digit Taylor-jet engine, as code. Their outputs were confirmed independently by FT (kron_samples) and TN (xi_direct). There are no interval bounds.
  - Literal summation of the η/θ/μ-weighted series of gdr:taylorLZ.
- **Counts and continuation:**
  - The function-count statements of RESULT §3. ZR finds the Z part consistent.
  - Continuation beyond b_max, which is not load-bearing.

## Fixes

Severity codes:
- [M] must: false or inaccurate as written.
- [S] should: a rigor gap, citation or wording problem.
- [O] optional.

Paths are relative to `LRI_C5_general_d/`, and line numbers are as of 2026-10-03.

### foundation/general_b_periodization.tex

- **F1 [M] Endpoint estimate in the proof of th:top.**
  - Step 3, l.313–314: replace "a(V)a′(2π−V)=O(V^{2rg−2}) and O((2π−V)^{2rg−2})" with "O(V^{rg−1+min(rg−1,0)}) (logarithmic at rg=1), since a′(2π⁻) is finite and nonzero for rg>1; symmetrically at V=2π".
  - Step 4, l.320: replace "integrable because 2rg>d" with "integrable because 2rg>d and rg>d−1 (conditions (i),(ii); for d≤1 condition (iii) suffices)".
  - Add that this is the step where b<b_max, rather than b_spec, enters the proof.
- **F2 [M] Control numbers in the remark after th:top, l.355.**
  - Replace |γ_{±3}| = 0.13, 0.020 with |γ_{±3}| = 0.051 (1.7% of max|γ|).
  - Add the control script and the scripts for the 25-digit r=2 and r=5 checks to foundation/. Alternatively, cite review/foundation-rigor/control_unbalanced.py and review/topmode-numeric, which confirm r=2..6 at 50 digits.
- **F3 [S] Derived pole at b_max.**
  - rem:continuation (l.529) and Open points (l.610–611): replace "expected to have a pole ... / expected but not analysed" with the derived residue Res_{b=b_max} Ξ_r = −4/(rΓ(d−1)) D_b^r [Φ(−t)+Φ(σ+t)], with Φ(u) = Σ_m [Γ(m+u)/Γ(m+u+g)]^r.
  - State that the residue's top mode is ∝ cos(π(rg+2−d)/2) = 0, that its lower modes are nonzero, and that the functional annihilates it, so W_r has no pole. Reference review/foundation-rigor/bmax_*.
  - Phrase the continuation as continuation of each block value at a fixed node.
- **F4 [S] Complex b in lem:bounds and th:finite(c),(d) (l.153–167, 210–235).**
  - For complex b, require |y| ≥ y₀(b) > |Im σ|+1 instead of |y| ≥ 2, and take the line y in (d) depending on the compact set of b.
  - Alternatively, add one line on the joint analyticity of Ξ_r(t;b): Cauchy formula in t on small circles around the pole classes, plus locally uniform convergence in (t,b).
- **F5 [M] Integer σ in the strip.**
  - rem:ranges, l.243: "σ∈Z can only occur for b=2 with d>3, r=4" holds only for r ≤ 4. In general σ ∈ Z occurs in the strip iff d > (2r−2)/(r−2).
  - rem:sampleradius, l.516–523: for r=4, d>3 (and r=5, d>8/3) the radius-1/2 jet disc contains σ=1. There the node weights ω_{r,j} are singular; the samples and W_r are not, and the poles cancel in the sum.
- **F6 [M, after F1–F5] Status labels.** In the status table (l.51–58) and Open points item 1 (l.598–601), Theorems 4 and 6 and Propositions 9 and 10 should read "proved; independently reviewed 2026-10-03 (review/foundation-rigor: proof; review/topmode-numeric: 50-digit probe, r=2..6, d=0.8..3.2, complex b)".
- **F7 [O] Record TN's 50-digit confirmation.**
  - TN's 50-digit run covers r=2 (including the barely convergent point with Re α = 0.7), r=5 and r=6. It supersedes the "25-digit checks".
  - Add TN's methodological caution to the validation section: periodicity, reflection and off-grid checks cannot see reflection-symmetric sample errors of degree ≤ r. Only the top and boundary modes and comparison with independent references test accuracy.
- **F8 [S]** lem:count proof, l.183: "The union of the conditions" should read "Both conditions together (conjunction)".
- **F9 [S] Minor wording.**
  - l.98: "converges absolutely exactly on" should read "represents W_r on".
  - prop:blocks: mention the extra removable singular points of individual blocks.
  - Rename the growth exponent η of th:finite(c), which clashes with the node height η_r.

### L/L_general_d.tex

- **F10 [M]** rem:integer, l.380: restrict "every Horn value is a finite combination of products of single-variable moments" to 𝔰_0 and 𝔰_{1/2}, or to the full samples via C63d's half-shift. 𝔥_x, 𝔥_{1/2} and 𝔥_1 are nested two-index sums.
- **F11 [S]** (F3), l.116: the convergence clause comes from foundation Thm 4(a) and Lemmas 2–3, not Lemma 1.
- **F12 [S]** prop:samples proof (the "by continuity" step, l.~213): add that the left and middle sums have no pole at t=0, since their poles in the class t≡0 lie at t ≥ 1, and that the Stirling bound of Lemma 2 holds uniformly near t=0.
- **F13 [M]** Abstract, l.48–49: the digamma values are at q, q/2, 3q/2, (1+q)/2 and (1+3q)/2 (ψ(q), not ψ(2q)). Alternatively, say "plus log 2 via duplication".
- **Status labels.** Update the status table (l.60) and l.470 as in F6.

### Z/Z_general_d.tex

- **F14 [S] Citation for ∂_bW_3(d;d/2)=0.**
  - At eq:Zdef (l.111–115), in the status table (l.67) and in general_d.tex l.93, cite the note's Pattern T (gs:Tjet: no S5-invariant linear form on the balanced K5 subspace) together with gs:wheelJets as the proof. gs:LZspectral only asserts it.
  - State that eq:simplified and gdr:Z depend on it, and th:jets does not.
- **F15 [S] Wording.**
  - Abstract, l.35: "two real sampling nodes" should read "two sampling nodes, real for real b".
  - l.44 and l.551: "is a Gamma product at d=3" should read "is √2(4π+32G/π) times a Gamma product at d=3".
- **F16 [S]** prop:series proof (l.385) and def:RM: state that the foundation's Lemma 2 and 3 bounds hold uniformly for b in compact subsets of the strip. This gives analyticity of R and M̂ and justifies termwise differentiation.
- **F17 [M]** tab:inventory row "new numbers beyond Q_d" (l.475) and the text at l.487–489: change 4 to 3, for example R (or ĉ0), ĉ0′ and (uR″+vM̂″)/9, consistent with RESULT.md and general_d.tex.
- **Status labels.** Update l.56 as in F6.
- **O1 [O]** prop:special(b): add R(2;b) = [₃F₂(σ,σ,σ;1,1;1)]² = Dixon(b/2)². Then eq:R2 becomes an identity via sin 3πx = sin πx (1+2 cos 2πx), W_3(2;b) = Selberg is derived, and Z_2 = 4G Q_2 follows from Dixon alone.
- **O2 [O]** prop:special(c): the Gamma form of ĉ0 is also verified at b = 0.8, outside C63d's range 1<b<5/3.

### general_d.tex (merge fragment) and RESULT.md

- **F18 [S]** gdr:d12lattice (l.141–145) and RESULT §2: write out the two-line proofs.
  - d=1: duplication merges ℓ=0 and ℓ=1 into one lattice.
  - d=2: d_ℓ = 1+[ℓ≥1] and x+y = 1 give φ̄ = φ, then symmetrize.
  - The foundation states the d=2 identity at general b only as "confirmed numerically at b=0.8".
- **F19 [S]** general_d l.153 and RESULT l.63: "closed first-order system" should read "first-derivative relations at x=½" (it is not an ODE in x). RESULT §2 uses "A" for both the Landen amplitude and the ψ-basis A; rename one (𝒜, 𝓑).
- **F20 [M]** general_d l.213 ("i.e. the one frozen derivative 𝔇_L") and RESULT l.95 ("Only the one combination D_L (C63d's P̂′)"): replace with "the same derivative content as C63d's P̂′, up to value terms: (2/(πS⁷))𝔇_L = P̂′ − 8√2 N_b⁴c_{4,1} + 32 N_b⁴c_{4,2}".
- **F21 [S]** general_d l.192: "no analogue of B₋ with elementary coefficients in the samples exists" should read "no such analogue was found (lattice bounds of LRI_C5_d3; numerical)".
- **F22 [M, after F1–F5] Status labels.** In general_d l.16–17, gdr:open item 1 (l.330–331), RESULT l.12 and RESULT §6 (l.203), replace "not yet reviewed by a second reader" with "independently reviewed 2026-10-03 (review/)".
- **F23 [S, merge] General-b statements.** Add the general-b Theorems 4 and 6 and Proposition 9 (with the F1 proof) to app:generalPeriodization, or cite foundation/ explicitly as the source of the expansion up to k = r−2 used in gdr:samples. Today the note has the expansion only at b = d/2, with modes k ≤ r−1.
- **O3 [O]**
  - gdr:samples (l.30–36): state a_ℓ(b) = (ℓ+σ)/2 and β_ℓ(b) = a_ℓ+g, and resolve the clash between g = (d−b)/2 and the kernel g_ℓ.
  - Next to gdr:samples3, say that M̂_3 is the bare sum, without the factor (1+ς)³/8; the ĉ0 formula already handles this correctly.
  - Optionally write "Dixon squared (= Selberg)" for T_3 at d=2.

## Caveats on this verification

- **Proof review of th:top.** The proof had one full reader (FR) and a spot read (ZR). The corrected Steps 3–4 (F1) are the reviewer's wording and have not been re-read after insertion.
- **Numerics.** All numerical evidence is empirical (convergence ladders and independent references, no interval bounds). The top mode was tested at about 30 parameter points.
- **Reference file.** references/reference_values.json was reformatted by another session during the review: it now carries 50 significant digits, and the off-diagonal entries were truncated from 56 digits. TN's copy agrees to 50 digits.
- **Reviewer-side bugs, all found and fixed, none in the reviewed code:**
  - TN: log-Gamma series termination at d=2.5;
  - LR: sympy coefficient extraction;
  - FT: gmpy2 sign conversion.
- **Reviewer outputs.** The reviewers could not write REPORT.md files. Their full reports exist only in the workflow output; scripts and logs are in review/<key>/, with cluster copies under symmetry:<SCRATCH>/c5_gend/review/<key>/.
- **Verifier's own checks (Mac, ≤ 30 digits):**
  - Located and confirmed every flagged passage at the line numbers above.
  - F1, r=2 endpoint: a′(2π⁻) = 6.90324… at g=0.8, which is finite.
  - C8: 2π²·₃F₂(½,½,½;1,1;1)² − Γ(1/4)⁸/(8π⁴) = −1e-29. By Dixon, ₃F₂(½,½,½;1,1;1) = Γ(1/4)⁴/(4π³), so gdr:Q at d=2 gives 3Q₂ exactly.
  - Rederived the C12 count and the A11 reflection argument.
  - Confirmed B_{4,3} = −20π³/s³ = −8538 at σ = 0.137, consistent between FR and LR.
