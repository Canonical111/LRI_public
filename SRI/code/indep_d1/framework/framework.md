# Framework: from regulated responses to F, H and the stability invariants

Role: **framework** of the independent C6/C7 re-derivation. This file is the symbolic report.
Every statement below is produced by the scripts in this directory
(`derive_rg.py`, `derive_invariants.py`, `validate_low_order.py`, `tests/`). Their logs are in
`out/*.log`. The note is `LRI_perturbation_compendium.tex`, abbreviated "note", with line numbers.
The compendium was only read.

Conventions are the note's: δ = 1−s, x = Δσ = δ/2, t = √x, Δε = 1 + Σ Cₙ tⁿ, ε is the hard core
on consecutive gaps, ℓ = log ε, and κ = 1. Iₖ := [ε⁰ℓᵏ] I. Products are formed before
extraction. Derivatives at v=1, δ=0 are taken before extraction.

---------------------------------------------------------------------------------------------

## 1. Regulated responses as functions of the auxiliary couplings

The current is resummed exactly (note Sec. 4): b_h = b0 − √2 h, v_h = b_h², and the endpoint
source is η_h = √2 h b_h. Moving the vertex of charge b0 to charge b_h changes its
normal-ordering self-contraction at the cutoff. For each kink this multiplies the weight by

  N(h) = exp[−f_δ(ε)(b0² − b_h²)],  f_δ(ε) = (ε^δ − 1)/δ = Σ_{k≥1} δ^{k−1} ℓ^k/k!

so that the essential fugacity Y = g ε e^{−b0² f_δ(ε)} carries no h (note l.301). The projected,
vacuum-normalized responses at fixed b0 are

  F_G(g,h) = Σ_{n odd} gⁿ N(h)ⁿ C_n(v_h, δ, η_h; ε),
  F_H(g,h) = h + √2 b_h Σ_{n even} gⁿ N(h)ⁿ K_n(v_h, δ, η_h; ε),

where C_n = [Σ A g^odd / Σ Z g^even]_n (C₁ = A₁ = ∫U^odd) and K_n = [Σ Q g^even / Σ Z g^even]_n.

**Check (Part 1A).** With A₁(η) = B(1+η,1+η) and the exact two-kink Q₂, this model reproduces
all three mixed responses that the note displays, including their logarithms (l.2112-2114):
* F_gh = −2√2(ℓ+1);
* F_gh² = 4ℓ²+10ℓ+12−2ζ₂;
* F_hg² = 4ℓ²+10ℓ+10−4ζ₂.

The normal-ordering factor N(h) and the prefactor √2 b_h are both needed for this agreement.

## 2. Renormalization condition and Callan-Symanzik equation

The bare auxiliary couplings carry pure-logarithm counterterms (no finite renormalization,
note l.426): (g,h)_bare = Ψ(g_R,h_R;ℓ), with Ψ(·;0) = id. The condition is that
[ε⁰]F(Ψ(g_R,h_R;ℓ);ε) does not depend on ℓ. Differentiating in ℓ at fixed renormalized couplings
and setting ℓ = 0 gives

  **J₀ β = R₁**,  J₀ = ∂(F_G,F_H)/∂(g,h) |_{ℓ⁰},  R₁ = [ℓ¹](F_G,F_H),  β = −∂_ℓΨ|_{ℓ=0}.

Only ℓ⁰ and ℓ¹ coefficients enter. Because log powers add in products, **only the ℓ⁰ and ℓ¹
coefficients of the raw moments can reach the beta functions.** The higher logs only serve as
checks.

**Explicit check (Part 1A, b0=1, δ=0).** I built the minimal-subtraction counterterms
order by order from the note's displayed responses (C3, K4, C5 logs, F_gh, F_gh², F_hg², F_g³h):
* h_bare = √2g²ℓ + √2g⁴(4/3ℓ³−2ℓ²−4ℓ), which is lo:eq:h4ct exactly;
* g_bare = g + g³(2ℓ²−ℓ) + g⁵[10/3ℓ⁴−22/3ℓ³−(8π²+39)/6ℓ²−b₁ℓ], which is lo:eq:g5ct exactly;
* b₁ = 2F40 − S − 34ζ₂ + 103 = −21+38ζ₂+60ζ₃+32log2−S, which is lo:eq:bperiod.

I then computed β = −(DΨ)⁻¹∂_ℓΨ with an ℓ-dependent ansatz. The result is **ℓ-independent**,
which is Callan-Symanzik consistency. That consistency checks the displayed higher logs of C5,
K4 and F_g³h against the lower data. The result reproduces the published
β_g = −2√2gh + 2gh² + g³ and β_h = −√2g² + 2hg², and it gives h₄ = 4, so c = −16. The same
counterterms satisfy J₀β = R₁ identically. At h ≠ 0, β_g/g = z_h + g²(1 + a z_h) + … with
z_h = (1−√2h)²−1 and a = −4ζ₂. The auxiliary β therefore depends on h only through the
essential charge.

## 3. The recurrence (Part 1B)

At h = 0 the Jacobian and the residues are (printed by `derive_rg.py`):

```
J0[GG] = 1 + Σ_{n≥3} n C_{n,0} g^{n-1}
J0[GH] = √2 b0 Σ_n j_n g^n ,        j_n = −2∂_v C_{n,0} + E C_{n,0}   (j_1 = E A_1 = −2/(1+δ))
J0[HG] = √2 b0 Σ_n n K_{n,0} g^{n-1}
J0[HH] = 1 + Σ_n λ_n g^n ,          λ_n = −2K_{n,0} − 4v ∂_v K_{n,0} + 2v E K_{n,0}
R1     = ( Σ C_{n,1} g^n ,  √2 b0 Σ K_{n,1} g^n ),    v = b0²
```

* The factor −2 in λ_n comes from ∂_h(√2 b_h) = −2.
* The factors v come from (√2 b0)².
* ∂_ℓN|_{ℓ=0} = 0 at h = 0, so N(h) does not enter J₀ or R₁. It does enter the higher logs.

I solved this system order by order with β_g = Σ b_n gⁿ and β_h = √2 b0 Σ h_n gⁿ, without
assuming which terms vanish. The result is:
* the odd b's and the even h's vanish (parity);
* h₂ = K₂,₁ = [ε⁰ℓ¹]Q₂ = −1 **identically in (v,δ)**. The r⁻¹ log-coefficient of
  r^{1−2v}(1−r)e^{−vδlog²r…} is exactly 1, so there is no zu, δu, … term in H;
* the remaining coefficients are

```
b3 = C3_1 + 2v j1
h4 = K4_1 − 2 Q2_0 b3 + λ2
b5 = C5_1 − 3 C3_0 b3 − 2v j1 h4 + 2v j3
h6 = K6_1 − 2 Q2_0 b5 − 4 K4_0 b3 − λ2 h4 + λ4
b7 = C7_1 − 3 C3_0 b5 − 5 C5_0 b3 − 2v j1 h6 − 2v j3 h4 + 2v j5
h8 = K8_1 − 2 Q2_0 b7 − 4 K4_0 b5 − 6 K6_0 b3 − λ2 h6 − λ4 h4 + λ6
b9 = C9_1 − 3 C3_0 b7 − 5 C5_0 b5 − 7 C7_0 b3 − 2v j1 h8 − 2v j3 h6 − 2v j5 h4 + 2v j7
```

**Comparison:** derived minus note is exactly 0 for every line of eq:subtraction (l.437-444)
and for h₈ and b₉ (l.1149-1155). **No discrepancy.**

## 4. Essential couplings and the role of eq:matching (Part 1C, 1D)

The cutoff-unit couplings are Y = g e^{ℓ+b0²(1−e^{δℓ})/δ} and v_B = (b0−√2h)² e^{δℓ}
(eq:matching with κ=1 and b0 kept variable). At fixed renormalized couplings,

  β_ess = −∂_ℓ(Y,v_B)|_aux + ∂(Y,v_B)/∂(g,h)·β_aux   at ℓ = 0,

which gives β_Y = β_g + g(b0²−1) and β_v = −b0²δ − 2√2 b0 β_h. Hence

  **F = z + b₃u + b₅u² + b₇u³ + b₉u⁴,  H = −δ − 4(h₂u + h₄u² + h₆u³ + h₈u⁴) = −δ + 4u − 4h₄u² − …**

Here u = g², z = v−1, and all b_n, h_n are evaluated at v = 1+z.

* Only the ℓ-linear part of the matching enters β. It produces the tree terms z (from the b0²
  dependence of Y; b0 must stay variable) and −δ.
* The ℓ², ℓ³, … terms of eq:fugmatch (1 − δℓ²/2 + δ²(ℓ⁴/8−ℓ³/6)) change only the bare
  counterterms. For example, g_bare|δg³ = δg³[−ℓ⁴/3+5ℓ³/3+2ζ₂ℓ²−pℓ] becomes
  Y_bare|δg³ = δg³[−4/3ℓ⁴+13/6ℓ³+2ζ₂ℓ²−pℓ], which reproduces lo:eq:physicalDeltaCt.
* The single logarithm is unchanged.
* **Remark (wording only, not a numerical discrepancy).** The note says that eq:fugmatch "is
  needed for p" (l.558). The value p = ∂_δ b₃ is fixed by J₀β = R₁ alone. eq:fugmatch is
  needed for the essential coordinates and for the higher-log checks, but not for the number.

## 5. Derivative dictionary (Part 1E)

The beta inputs are Taylor coefficients of b_n(1+z, δ) and h_n(1+z, δ):
* a = [z]b₃, p = [δ]b₃, A = [z²]b₃, E = [zδ]b₃, V = [δ²]b₃, α = [z³]b₃, β = [z²δ]b₃, γ = [zδ²]b₃;
* b, G, R, Φ, Ψ = [1], [z], [δ], [z²], [zδ] of b₅;
* J, Ω = [1], [z] of b₇;
* c, f, q, L, M, Q = −4×[1, z, δ, z², zδ, δ²] of h₄;
* k, N, P = −4×[1, z, δ] of h₆;
* K = −4[1]h₈;
* for C8: W = [δ³]b₃, S = [δ²]b₅, U = [δ]b₇, J₉ = b₉, L₃, M₂₁, M₁₂ = −4×[z³, z²δ, zδ²]h₄,
  N₂, N_δ = −4×[z², zδ]h₆, K_v = −4[z]h₈.

Converted to derivatives, all 35 entries **agree** with note l.1122-1136, including
L = −2h₄,vv, Q = −2h₄,δδ, L₃ = −(2/3)h₄,vvv, and the mixed first derivatives without a factor ½.

Explicit polynomials for each input in terms of normalized-response coefficients are in
`out/beta_input_formulas.txt`. The symbol X_k_⟨v…d…⟩[E] means ∂_v^i∂_δ^j[E][ε⁰ℓᵏ]X, and
j₁ = −2/(1+δ) is already inserted. Examples:

```
a = C3_1_v − 4        p = C3_1_d + 4        A = C3_1_vv/2        E = C3_1_vd + 4
V = C3_1_dd/2 − 4     alpha = C3_1_vvv/6    beta = C3_1_vvd/2    gamma = C3_1_vdd/2 − 4
c = 8 C3_1 K2_0 − 24 K2_0 − 8 K2_0_E + 16 K2_0_v − 4 K4_1
f = 8 C3_1 K2_0_v + 8 C3_1_v K2_0 − 32 K2_0 − 8 K2_0_E − 8 K2_0_v − 8 K2_0_vE + 16 K2_0_vv − 4 K4_1_v
```

These have 101 terms for Ω, 82 for K, 51 for N and 47 for P. The spec agent took eq:subtraction
as its definition and expanded it on its own (`spec/out/input_definitions.json`). All 25 of its
expansions are term-by-term identical to these (`tests/test_vs_spec.py`).

## 6. Fixed point, T, D and power counting (`derive_invariants.py`)

T = 2u_*F_u + (1+z_*)H_z and D = 2u_*(1+z_*)(F_uH_z − F_zH_u) (eq:TD), expanded as
T = δ/2 + T₂δ² + … and D = −2δ + D₂δ² + ….

**Power counting.** I took generic jets with every u^i z^j δ^k, i ≥ 1 and i+j+k ≤ 5, and
exact random rationals, perturbed each coefficient in turn, and recorded which T_m, D_m change.
Every coefficient that enters T₁…T₄ or D₁…D₄ is a named dictionary input.

| invariant | inputs that enter |
|---|---|
| T₂ | p, a, b, c, f |
| D₂ | a, c |
| T₃ | the above, plus V, E, A, R, G, J, q, M, L, k, N |
| D₃ | p, E, A, b, G, c, q, f, k |
| D₄ | p, V, a, γ, A, β, α, b, R, G, Ψ, Φ, J, Ω, c, q, Q, f, M, L, k, P, N, K |
| T₄ | everything in the dictionary through K_v |

Two remarks on this table:
* E does not enter D₄, and W, S, U, J₉ do not enter D₄.
* The weight argument: u_*, z_* = O(δ). A coefficient of degree n enters D at δⁿ and T at δⁿ,
  or at δⁿ⁻¹ if it is a z-term of H.

**Fixed point:**
* u_* = δ/4 − cδ²/64 + (c²/512 + (f−k)/256 − q/64)δ³ + …
* z_* = −δ/4 + ((a−b)/16 + c/64 − p/4)δ² + …

Both agree with l.618-621. The δ³ and δ⁴ terms are in `out/invariant_formulas.json`.

**Assemblies.** Derived minus note is 0 for each of:
* D₂ = 1/2 − a/2 − c/8;
* T₂ = −a/8 + b/4 − c/32 + f/16 + p/2;
* D₃ = (16A − 32E − 8G + 8b + c² + 4f − 4k + 32p − 8q)/64 (eq:D3assembly);
* C₆ = 4T₃ = B_old + 2V + R + 3J/8 − L/8 + M/4 + N/16 with the note's B_old (eq:C6assembly);
* the linear part of D₄ in the new inputs, −3α/32 + β/4 − γ/2 + Φ/16 − Ψ/8 − Ω/32 − Q/8 − P/16 −
  3K/128 (l.1033);
* C₈ = 8T₄: the linear part (eq:C8assembly) and the full appendix polynomial B_old (app:C8polynomial).

The full old-input part of D₄ derived here is

```
B_old^{D4} = −Aa/16 + Ab/16 − Ac/64 + Ap/4 − A/32 + Gc/128 + J/32 − 3L/128 + M/16 + 3N/128 + R/8 + V/2
             + ac²/512 − af/64 − ak/128 − bc/128 + 3bf/128 − 5c³/2048 − c²/512 − cf/64 + ck/64
             + cq/32 + fp/16 − f/128 + k/128
```

It is identical to the archived `derive_D4.py` output (`D4_algebra.json`, `old_D4_symbolic.expr`),
which I read for comparison after deriving it.

**Conversion.** Expanding Δ₋ = 1 + T/2 − √(T²/4 − D) with δ = 2t² gives C₁ = −2, C₂ = 1/2,
C₃ = D₂ − 1/16, C₄ = 2T₂, C₅ = 2D₃ − T₂/2 + C₃²/4, C₆ = 4T₃, C₇ = 4D₄ − T₃ − T₂² + C₃C₅/2 and
C₈ = 8T₄. These are the eq:conversion identities, verified exactly.

**Numerical assembly (comparison only).** I used the closed forms for a, p, A, E, b, c, f and
the ARCHIVED 39-digit values for the rest (`F3_final_100.json`):

| quantity | difference from the claim |
|---|---|
| C₆ = −58.665697474225308949717146128… | 3·10⁻³⁹ |
| D₄ = −2.534629799538250115260606412… | 3·10⁻⁴⁰ |
| C₇ = 51.068988612928108831183935979… | 3·10⁻³⁹ |
| B_old(C6) = −48.00036008409774270591275… | matches all 20 digits the note prints |

With the note's 15-digit C8 inputs, C₈ agrees to 2·10⁻¹⁶ and B_old(C8) agrees to 2·10⁻²⁹.

## 7. Validation with closed forms (`validate_low_order.py`)

**(A) The b₃ sector, integrated here from scratch.** Every b₃ input is a single log of a
three-kink derivative minus its two-kink normalization. The cutoff-boundary identity
[ε⁰ℓ]M = −[ε⁰ℓ⁰](−ε∂_εM) (eq:EulerBoundary) reduces each to the one-dimensional integral

  [ε⁰ℓ¹]∂A₃ = −2[G₁ − Σ_m g_m(−1)^m m!],  G₁ = ∫₁^∞[(1+1/s)²P₀(log s, log(1+s)) − g(log s)/s] ds.

Here P₀ is the insertion polynomial (∂_v^i∂_δ^j W)/W on the face r = ε with log r → 0, and
g = ∂P₀/∂L₁ at L₁ = log s. The two-kink part comes from the exact internal sector.

| input | this work | reference | difference |
|---|---|---|---|
| a | −6.5797362673929057458896606665841 | −4ζ₂ (closed form) | 0 |
| p | −9.2494439002931753460808544355376 | closed form | 0 |
| A | −5.8934951847529693660134230462762 | closed form | 0 |
| E | −21.663876674184610081020147908761 | closed form | 7·10⁻⁴⁰ |
| **V** (C6) | −19.518741011574465808242207110132 | archived | 0 at 39 digits |
| **α** (D4) | −1.6576510838700072279237784615761 | archived | 2·10⁻⁴¹ |
| **β** (D4) | −16.027908690418506113987594423041 | archived | 0 at 39 digits |
| **γ** (D4) | −44.009684064767791523714540000681 | archived | 0 at 39 digits |
| W (C8) | −37.708111514952555112588560001911 | note, 15 digits | 1·10⁻¹⁶ |

V, α, β and γ are four of the NEW inputs. They are re-derived here independently, using only
our own integration. The "−4" in V and γ is 2v·∂_δ²j₁/2 from the endpoint source, as stated in
note l.689.

**(B) c, b, f from the displayed expansions.** The inputs were:
* C₃ = 2ℓ²+5ℓ+3−2ζ₂;
* the single log and constant of ∂_vC₃ (l.2231);
* K₄ (l.551) and the C₅ single log (l.555);
* j₃ = F40 (l.2117), which fixes E C₃,₀ = F40 + 2∂_vC₃,₀;
* the Mellin data for Q₄ and ∂_vQ₄ (l.1707-1709), with the closed forms of P₄ and R₄.

From the Mellin data, [ℓ¹]∂_vQ₄ = −4P−R₄+16ζ₂−48, and that data also reproduces K₄,₁ = −8+4ζ₂.
The two-kink pieces Q₂, Z₂, EQ₂ and their v-derivatives are exact. The module gives
**c = −16, b and f equal to eq:oldbetas to 10⁻³⁹**. f also equals the appendix form
16P+4R₄−32+16ζ₂+32ζ₃. All other inputs are correctly reported as *missing*, not as zero.

## 8. Discrepancies

None in the recurrence, the dictionary, the fixed point, the invariant assemblies (including
B_old for C6, D4 and C8) or the conversion identities. Remarks:
1. h₂ ≡ −1 is a theorem of the one-pair integral ([ε⁰ℓ¹]Q₂ = −1 for all v, δ). The note uses
   it implicitly in writing β_h/(√2b₀) = −g² + ….
2. eq:fugmatch: see §4. Its ℓ^{≥2} terms do not affect p or any other single-log β.
3. Requirements. Only [ε^p ℓ⁰] and [ε^p ℓ¹] of the raw moments are needed (§2). With the exact
   two-kink sector built in, the outputs through C7 need **116** raw scalars in 46 raw atoms
   (`out/required_inputs_D4.json`); C8 needs 201. The spec agent's tight list has 122 non-two-kink
   scalars. It contains all of mine, and its 6 extras each multiply an exactly vanishing two-kink
   coefficient, for example [ε¹ℓ¹]Q₂ = 0 and [ε⁻¹ℓ¹]Z₂ = 0.

## 9. Numerical interface (phase 2, 2026-10-03)

The mathematics above is unchanged. The phase-2 revision of `lri_framework.py` reproduces the
phase-1 module exactly: random full data give values and gradients identical to 0, and the
116/201 required lists are identical. What changed is how the module takes its inputs and
reports errors.
* **Strict mode by default.** Every atom carries every structural slot ε^{pmin}…ε^{pcap},
  ℓ⁰…ℓ^{kmax}, either as a supplied value or as a MISSING tag with its own name. An absent
  required scalar raises `MissingInputError`; with `strict=False`, every output that depends on
  it is MISSING.
* **Validity of the internal two-kink series is pcap**, not ∞. A product that needs a higher Z₂
  or Q₂ order is flagged, and in strict mode raises `TruncationError`. The smallest complete cap
  at order D4 is pcap = 3, and pcap = 3, 6 and 8 give identical outputs.
* **Error model.** It combines independent sigmas, covariance blocks, systematic floors and
  per-block replicate sample covariances, and every entry point honours `sigmas=` and `cov=`.
  `from_replicates` runs the full nonlinear map once per QMC replicate. The formats are in
  `INPUT_FORMAT.md`.
* **Three structural zeros.** A3[ε⁻¹ℓ¹], A3[ε²ℓ¹] and Z4[ε⁻²ℓ¹] are required. Both the
  archive-derived raw file and the engine's phase-1 data omit them, so the phase-1 module set them
  to zero silently. Their C7 sensitivities are −0.92, 0.64 and −1.60. A3[ε⁻¹ℓ¹] = 0 follows from
  A3 = Z2 + C3 at order ε⁻¹. The other two rest on the producers' pole analysis, and must now be
  supplied explicitly as exact zeros.
  * Gate review (2026-10-03): the A3 base atom's closed form has log part exactly 2ℓ² + 6ℓ − 6εℓ
    (`review_gate_phase2/check_A3_closed_form.py`), which proves both A3 zeros.
  * Z4[ε⁻²ℓ¹] = 0 by the method of regions. Only the region with both outer gaps O(ε) scales as
    ε⁻², and there the integrand factorizes with no log.
* **Non-finite inputs** (NaN, ±inf) are rejected when the input is parsed (gate review,
  2026-10-03).

## 10. Eighth order: C8 = 8 T4 (phase 3, 2026-10-03; `derive_C8.py`, log `out/derive_C8.log`)

Note Secs. 14-15 (l.1100-1170) and the appendix app:C8polynomial (l.2781). Machine-readable:
`out/C8_trace.json`. Everything below is derived here; the note is used only for the final
comparison, and its eq:C8assembly and appendix polynomial are **parsed from the TeX source**
(no hand transcription).

**A. J₀β = R₁ through g⁹.** The phase-1 derivation (derive_rg Part 1B, from the regulated
responses with the resummed current, N(h) and √2 b_h) is run to order 9. The Jacobian gives

  j_n = [g^n] J₀[GH]/(√2 b₀) = −2∂_v C_{n,0} + (EE C_n)_0,   λ_n = [g^n] J₀[HH] = −2K_{n,0} − 4v∂_v K_{n,0} + 2v(EE K_n)_0

for all n. In particular **j₇ and λ₆ are the note's** (eq:b9, l.1156-1157), and h₈ (115 terms) and
b₉ (213 terms, fully expanded) equal the note's recurrence (l.1149-1155) term by term.
J₀[GG] = 1 + Σ n C_{n,0} g^{n−1}, J₀[HG] = √2 b₀ Σ n K_{n,0} g^{n−1}, and R₁ = (Σ C_{n,1} gⁿ, √2 b₀ Σ K_{n,1} gⁿ).

**B. Normalization.** The series division Σ A g^odd / Σ Z g^even and Σ Q g^even / Σ Z g^even gives
eq:K8norm exactly, and eq:C9norm exactly at A₁ = 1. The A₁ term of C₉ is
A₁(Z₂⁴ − 3Z₂²Z₄ + Z₄² + 2Z₂Z₆ − Z₈). The module keeps A₁ as a jet, so EE also acts on it.

**C. The δ⁴ trace.**
* Power counting with generic jets of degree ≤ 5 and exact rationals: 36 generic coefficients enter
  T₄. All of them are named dictionary inputs: the 35 inputs (all 25 old and all 10 new) and
  F₁₀₀ = b₃(0,0).
* The one-pair sector H_{1jk} (u¹ zʲ δᵏ of H) would enter T₄ for 13 (j,k) ≠ (0,0). It vanishes
  because h₂ = [ε⁰ℓ¹]Q₂ = −1 identically (Part 1B). The tree data b₃(0,0) = 1 and h₂ = −1 are the
  two structural facts behind eq:C8assembly; the module checks them at run time.
* T₄ with the prescription eq:C8F/eq:C8H has 71 terms. C₈ = 8T₄ has total degree 1 in the ten new
  inputs, and their coefficients are constants:

  C₈ = B_old + 4W + 2S + ¾U + ¼J₉ + 3/32 L₃ − ¼M₂₁ + ½M₁₂ − 1/16 N₂ + ⅛N_δ + 1/32 K_v,

  which is **eq:C8assembly exactly**.
* The remainder B_old has 61 terms: 12 of degree 1, 38 of degree 2 and 11 of degree 3. All 25 old
  inputs occur. It is **identical to the appendix polynomial** parsed from the TeX (l.2783) and to
  the module's table `B_OLD_C8_TERMS`.
* B_done = B_old + 4W + 2S + 3/32 L₃ − ¼M₂₁ + ½M₁₂ − 1/16 N₂, and C₈ − B_done = ⅛N_δ + ¾U +
  1/32 K_v + ¼J₉ (the note's four packages, l.1404).

**D. Dictionary.** The ten new entries agree with l.1129-1136, including L₃ = −⅔h₄,vvv, and the
mixed derivatives have no ½. Their explicit formulas in normalized-response coefficients
(`out/beta_input_formulas.json`) have 2 (W), 27 (S), 106 (U), 157 (J₉), 10 (L₃), 14 (M₂₁),
16 (M₁₂), 85 (N₂), 121 (N_δ) and 231 (K_v) terms.

**Discrepancies with the note at eighth order:** none.

**Module (numerical).** At order C8 the module evaluates C₈ two ways:
* `res.C[8]` = 8T₄ from the fixed-point series, with the supplied data;
* `res.c8["C8_asm"]` = B_old + eq:C8assembly.

On every C8-order assembly it checks that C8_asm equals 8T₄ recomputed with the exact tree data.
That is an identity, checked for values and gradients at any point; a failure raises.
`tests/test_c8.py` gives:
* 5·10⁻⁴⁸ at random raw points;
* 0 at points with exact tree data;
* 3·10⁻⁴⁸ against the exact rational sympy value at rational beta inputs.

The engine's A3[ε⁰ℓ¹] is 5.999999999999999, not exactly 6. On C₈ that shifts 8T₄ by 1.6e-12 at our point
(`c8_info["8T4_minus_8T4_exact_tree"]`).
