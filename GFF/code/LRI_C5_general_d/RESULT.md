# C5(d) at generic dimension: reduction of the nonprimitive masters L_d and Z_d (2026-10-02/03)

LaTeX fragment for the note: `general_d.tex` (labels `gdr:`, note macros `\LL \KK \Cat \ii \Res \pA \pD \pU`, no
preamble; the note itself was not edited). It is now the **combined, note-ready general-d statement**: it states and
proves the general-b finite Fourier theorem and the top-mode theorem itself, so it does not rely on the note's
`app:generalPeriodization` (which works only at b = d/2 with modes k <= r-1). Merge notes are in its header comment.

**Joint review applied (2026-10-03).** `review/joint/JOINT_REVIEW.md` (joint review of this fragment, "gdr", and
C63d's K_d fragment, "gdk"): all gdr items G1-G16 and the gdr parts of decisions D1-D6 are applied (see section 6).
Layout D1: in the note, `general_d.tex` is pasted inline as a `\section` at the end of Part III and the gdk fragment
`K_general/note_fragment/K_d_fragment.tex` follows directly as the next `\section`, promoted one level. The HOOK block
is gone (a short MERGE comment for the fallback layout replaces it).

**Not standalone any more.** `general_d.tex` cites gdk labels (`gdk:section`, `gdk:conventions`, `gdk:notation`,
`gdk:Rfamily`, `gdk:topmode`, `gdk:continuation`, `gdk:Kr3`, `gdk:Ksample`, `gdk:KMB`, `gdk:numerics`, `gdk:status`),
so it builds only together with the gdk fragment.

Test builds (rebuilt 2026-10-03 after the joint-review fixes; note labels refreshed from the current note `.aux`, the
08:43 edition with Section 28 = C8(1), 583 labels + 30 citations):
- **`draft/combined_inline_preview.tex` / `.pdf` (the test build; 30 pages):** note preamble, `\input{../general_d.tex}`
  followed by `draft/gdk_promoted_tmp.tex`, a temporary promoted copy of the gdk fragment made by
  `draft/make_combined_inline.py` (the gdk source is not edited). No errors, no undefined or multiply defined
  references, no overfull or underfull boxes (only the usual pdfTeX "dest" warnings for note anchors absent from a
  preview).
- `draft/general_d_preview.tex` / `.pdf` (16 pages): `general_d.tex` alone; the gdk labels are copied from the combined
  build's `.aux` (`draft/gdk_labels_from_combined_aux.tex`). Same clean log.
- `specialize/gdr_test.tex` is the old wrapper (no note labels), not maintained.

Parts: `foundation/` (general-b periodization), `L/` (five-Horn formula for L_d), `Z/` (two-node formula for Z_d),
`specialize/` (integer-d specializations, assembly of C5(d), further reduction attempts). Independent spectral
references: `references/reference_values.json` (C63d). `K_general/` is C63d's K_d work; its note fragment is the
section that follows this one in the note (layout D1), with its own status list.

## Status labels

- **Independently reviewed, 2026-10-03, fixes applied** (`review/VERIFICATION.md`; five lenses, all ACCEPT, no
  printed formula wrong). The fixes of the review are applied in all parts; see "Review and fixes" below.
- **Proved, with written proofs:** the foundation theorems (general-b finite Fourier theorem, top mode
  c_{r,r-1} = 0, residue functional, block decomposition), the d=1 duplication and d=2 square-lattice identities,
  the sample formulas (L Props 1-2, Z Lemmas 2-3, Thm 4), analyticity in b and termwise differentiation.
  - The review found one false intermediate estimate (endpoint exponent in Steps 3-4 of the top-mode proof).
    The corrected proof (in `foundation/` and in `general_d.tex`, Section gdr:top) uses exactly b < b_max.
    The corrected Steps 3-4 were re-reviewed in product form, which contains the wheel case, in
    `review/lemmaG-proof` (ACCEPT; endpoint exponents tested numerically). (An earlier "fix check" by a second
    reader is cited no more: it has no record under `review/`; G10 of the joint review.)
  - **General top-mode theorem (product form; added and independently reviewed 2026-10-03):** foundation
    Theorem 6(a)-(c), labels `th:topG` = `th:top`; fragment `gdr:topG`, `gdr:BC`, `gdr:TG`, `gdr:mixed`,
    `gdr:kernelBalance`. Any product of balanced kernels prod_i f_{g_i}(l+sigma+alpha_i+z) f_{g_i}(beta_i-z) with
    per-factor balance (B) sigma+alpha_i+beta_i+g_i = d/2 and (C) varkappa = sum_i Re g_i > max(d/2, d-1, 1/2) has
    gamma_{1-r} = gamma_{r-1} = 0, i.e. S_T(t) = O(e^{-4 pi |Im t|}); individual Re g_i may be <= 0. It contains the
    wheels (part (d) = the earlier reviewed statement), mixed wheels prod_i g_l(s+delta_i; b_i) (condition: mean
    Re b_i < b_max, shifts free), and C63d's R family of K_d (Re tau > max(0, 2q-1, 1/2-2q)). This is C63d's "Lemma G"
    (lemmaG_statement.md); no change to its statement was needed.
    - *Review scope (decision D6 of the joint review):* the review covered the statement gdr:topG (foundation
      Theorem 6(a)-(d)), including the R-family dictionary (g_i) = (q,q,tau), alpha_i = 0, (beta_i) = (0,0,q-tau) and
      (C) <=> tau in H_q. C63d's own proof text `K_general/note_fragment/topmode/PROOF.md` was not reviewed as such.
      In the case r = 3, Step 0 of the proof gives parts (a) (sufficiency), (b), (c) of C63d's growth theorem; only
      the sharpness of H_q and the explicit constants of `growth/PROOF.md` are unreviewed.
    - *Written proof:* foundation Section 3 (Steps 1-7), restated in gdr:top.
    - *Independent proof review* (`review/lemmaG-proof/`, record `review.json`, Mac scripts t1-t5b): **ACCEPT**, no
      fatal or major issue. Every step rederived by hand; Steps 1-4 tested numerically in unbalanced cases where the
      top mode is nonzero (kappa_+ s_1^+ vs lattice gamma_{1-r}: 2e-13 to 2e-8 for r = 2, 3, 4), lower half-plane
      (Step 6) to 3e-12, Laplace forms to 1e-20..1e-26, endpoint exponents confirmed. Seven minor wording and
      documentation items, all applied (see section 6).
    - *Independent numerical probe* (`review/lemmaG-numeric/`, record `probe_report.json`): **PASS**. Own 48-digit
      lattice-sum code; top modes 2.8e-48 to 4.7e-44 of the largest mode at 12 mixed wheels (r = 3, 4; d = 1.3, 2.4,
      3.1; complex parameters; one with Re g_1 < 0), 6.5e-47 to 5.2e-45 at four R kernels, 3.0e-46 at a wheel; at most
      9.3e-54 in 54-digit reruns; both top modes vanish separately; per-factor imbalance switches them on linearly;
      vanishing also at four analytically continued points outside (C) (< 2e-47 at 54 digits).
    - Quick check: `foundation/check_topG.py` / `.log`.
- **Derived** (exact algebra on the above, rederived by the review): the formulas in sections 1-4; the d = 3
  specializations only given the d = 3 conditional inputs below.
- **Conditional inputs:** gdr:Z and the Z part of gdr:C5reduced use dW3/db(d;d/2) = 0, proved by the note's
  Pattern T (gs:Tjet) with gs:wheelJets. The d=3 Z specialization uses C63d's Gamma form of the zero mode
  (derived there, not a written proof). The d=3 L specialization uses the extension of the half-shift identities to
  every b < 2, c_{4,1}(b) = 2 a4(b) b4(b), derived in LRI_C5_d3 but not written out (confirmed numerically to 1e-51;
  G3). If K_d is taken from gdk:Kr3, C5(d) is conditional on (M), and on (H) when r3 is sampled on the jet circle;
  (J) is the path form of gs:Bjet, on which gs:C5 already rests; with gdk:KMB none of (M), (J), (H) is used (D5).
- **Numerical:** all checks, and every "no further reduction" statement (PSLQ bounds, not proofs).

## 0. Structure of the fragment `general_d.tex`

| section (preview numbering) | label | content |
|---|---|---|
| intro, Status, Notation | `gdr:section`, `gdr:D` | scope (K_d: next section gdk); status summary (the K_d evaluation is gdk's, own status list); notation (σ, g outside gdr:top; S, C, D only in 1.2-1.5; 𝒜/ℬ vs psi-basis A) |
| 1.1 Finite periodization at general b | `gdr:periodization`, `gdr:kernel`, `gdr:Dgen`, `gdr:periodizationDef`, `gdr:bmax`, `gdr:reflected` | kernel, strip b_max, lattice split, estimates |
| 1.1.1 Finite Fourier space | `gdr:finite`, `gdr:finiteFourier` | theorem (a)-(d) with proof sketch, citing foundation Thm 4 |
| 1.1.2 The top modes vanish | `gdr:top`, `gdr:BC`, `gdr:TG`, `gdr:topG`, `gdr:mixed`, `gdr:topless`, `gdr:laplace`, `gdr:endpoint`, `gdr:endprod`, `gdr:Il`, `gdr:kernelBalance` | product form gdr:topG (any product of balanced kernels with (B), (C)) with proof (Steps 0-7; periodization S_T, D_T, Xi_T); mixed wheels; wheel case gdr:topless (the reviewed statement); pointer to gdk:topmode for the R family of K_d (continued points need (H) of gdk:continuation); controls; relation to the note (the only copy of the td correction, D3) |
| 1.1.3 Residue functional, weights, blocks | `gdr:residue`, `gdr:functional`, `gdr:explicit` | general-b functional, explicit W3/W4, top weights B_{3,2}, B_{4,3} nonzero, blocks |
| 1.2 Samples, modes, two masters | `gdr:samples`, `gdr:samples4`, `gdr:Tln`, `gdr:threenode`, `gdr:P4`, `gdr:L`, `gdr:frozen`, `gdr:samples3`, `gdr:twonode`, `gdr:Q`, `gdr:Z` | L_d and Z_d formulas with derivation sketches |
| 1.3 Pole node alone | `gdr:taylor`, `gdr:taylorW`, `gdr:taylorQP`, `gdr:taylorLZ` | residue series one Laurent order lower |
| 1.4 d = 1, 2, 3 | `gdr:special`, `gdr:d12lattice`, `gdr:landen`, `gdr:L1` | identities with proofs; specializations of L and Z |
| MERGE comment | | layout D1: nothing inserted here; the gdk fragment is the next section; notes for the fallback layout (G-H) |
| 1.5 Five-loop coefficient | `gdr:C5`, `gdr:C5reduced` | assembly, inventory; K_d kept as the symbol of gs:Kdefinition, with its evaluations (gs:Kseries, gdk:KMB, gdk:Kr3), the substituted form −1536K_d = 384AU − 576c*U − 384(r3 − s3) and its conditions (M), (H) |
| 1.6 Further reductions tried | `gdr:attempts` | |
| 1.7 Checks | `gdr:checks` | own runs plus the review's independent numbers |
| 1.8 Status, limits, open points | `gdr:status` (= `gdr:open`) | |

The fragment corrects the note's statement after td:sevenOddCoefficients ("These are the precise additional
restrictions special to three dimensions"): c_{3,2} = 0 and c_{4,3} = 0 hold in every dimension (gdr:top). What stays
special to d = 3 is c_{3,0} = -a3 b3, c_{4,1} = 2 a4 b4 and the r = 7 odd coefficients. The replacement sentence
(item N3 of the joint review) is in the fragment's header comment; the "Relation to the earlier sections" paragraph
of gdr:top is written for it and is the only copy of this correction (D3; gdk's Remark (iii) becomes a pointer).

## 1. The formulas (b = d/2, q = d/4, S = sin πq, C = cos πq, D = π cot πq = ψ(1−q) − ψ(q))

**Four-wheel (P4, L).** There are three samples X_i = N_b^4 Ξ_4(t_i; b), at t = 0, at t̃ = 0 (t = −b/4) and
at t̃ = 1/2, with the node variable t̃ = t + b/4 (renamed from τ, D4):

- X_T = (π s_b)^4 h_x
- X_0 = κ0^4 (s_0 + 2 ξ0^4 h_1)
- X_{1/2} = κh^4 (s_{1/2} + 2 ξh^4 h_{1/2})

These involve five two-variable Horn functions. Then:

    P4(d) = (2/(π S^7)) [ (1+C)²(1+2C) X_0 − (1−C)²(1−2C) X_{1/2} − 2C X_T ]
    L_d   = −(1/S^8) [ (1+C)²(4+9C+8C²) X_0 + (1−C)²(4−9C+8C²) X_{1/2} − 2(1+6C²) X_T ] + (2/(π S^7)) D_L
    D_L   = (1+C)²(1+2C) X_0' − (1−C)²(1−2C) X_{1/2}' − 2C X_T'      (one frozen-weight derivative)

**Three-wheel (Q, Z).** The inputs are:

- the residue sum 𝔱3(b) = Σ d_ℓ T_ℓn(b)³ (fraktur t; renamed from 𝒯_3 to avoid the note's 𝒯_d, D4), which is one
  7F6 plus one Horn value;
- the midpoint lattice sum M3(b), which is one 7F6 plus two Horn values. M3 is the bare lattice sum: the factor
  D_b(t_b)³ = (1+ς)³/8 that the sample Ξ_3(t_b) carries is written separately (N_b³ Ξ_3(t_b) = ((1+ς)/2)³ M3);
- the zero mode ĉ0 = N_b³ c_{3,0} = ς(1+ς)²M3/8 − π³ s³ 𝔱3/(1+ς).

Then:

    3Q_d = (6π²/S²) 𝔱3 + (4/(πS³)) ĉ0
    Z_d  = (2π²/(3S²)) 𝔱3'' − π² cos(πd/2) Q_d/(6S²) + (1/9)[π(1+C²)ĉ0/S^5 − 4C ĉ0'/S^4 + 4ĉ0''/(πS³)]

The second derivatives enter only through (u 𝔱3'' + v M3'')/9; the first derivatives only through ĉ0'. The Z formula
uses dW3/db(d;d/2) = 0 (Pattern T, gs:Tjet with gs:wheelJets; gs:LZspectral only records it as a check).

**Pole-node form (new).** This lowers the Laurent order of the note's residue series by one. It uses
κ_b = π cot(πb/2), and λ_m is gs:lambda with the rim and spoke separated:

    W_3(d;b) = Σ d_ℓ T_ℓn³ [2π² − 6 κ_b λ1]
    W_4(d;b) = Σ d_ℓ T_ℓn^4 [4κ_b(4λ1² + λ2 − π²/3) − 8π² λ1]

So 3Q_d = Σ dT³(2π² − 6Dλ1) and P4 = Σ dT^4[4D(4λ1²+λ2−π²/3) − 8π²λ1], compared with F3 (needs λ2) and F4
(needs λ3). L_d and Z_d follow by termwise b-differentiation (gdr:taylorLZ): λ3 and η3 drop out of L_d, and λ2,
η2, θ2 drop out of Z_d.

## 2. Specializations (task 1)

Notation in this section: 𝒜, ℬ are the two mode amplitudes of gc:L2modes; A is always the gs:psiBasis value.

**The common mechanism at d = 1 and d = 2.** Both dimensions sample the same one-variable function
Ω_r(t;x) = sin^r π(t+x) Σ_n [Γ(n+t+x)/Γ(n+t+1)]^r, for r = 4 at the same point x = 1/2. For every b in the strip:

- d = 1, duplication: Ξ_r(t;b) = (−1)^r 2^{−rb} Ω_r(2t; b).
  *Proof.* At d = 1 only ℓ = 0, 1 contribute, 2q = 1/2 and 1 − g = 1/2 + σ. In the reflected form of the kernel,
  Legendre's duplication turns the ℓ = 0 and ℓ = 1 Gamma ratios at z = n + t into 2^{1−2σ}Γ(2z+b)/Γ(2z+1) and
  2^{1−2σ}Γ(2z+1+b)/Γ(2z+2): the terms m = 2n and m = 2n+1 of one bilateral lattice. The prefactor is
  D_b(t) sin π(g−t)/sin πt = (1/2) sin π(2t+b), and the powers of two combine to 2^{−rb}.
- d = 2, square lattice: Ξ_r(t;b) = (−1)^r Ω_r(t; b/2)².
  *Proof.* At d = 2, d_0 = 1, d_ℓ = 2 (ℓ ≥ 1), 2q = 1, g = 1 − σ. With φ(z) = Γ(z+σ)/Γ(z+1), reflection gives
  D_b(t) g_ℓ(a_ℓ+n+t) = −sin²π(t+σ) φ(n+t) φ(ℓ+n+t). With χ_m = φ(m+t)^r the multiplicities turn
  Σ_n Σ_ℓ d_ℓ χ_n χ_{n+ℓ} into the symmetrization (Σ_m χ_m)², absolutely convergent since r Re g > 1 there.

Since Ω_r(t+1) = (−1)^r Ω_r(t) and it grows like e^{rπ|Im t|} times a negative power, its frequencies are in
Z + r/2 with modulus ≤ r/2 − 1. So at d = 1, 2 the top-mode theorem also follows directly, and at d = 1 only modes
k ≡ r (mod 2) occur.

The two amplitudes obey **first-derivative relations at x = 1/2** (not a differential system in x), proved in
gc:L2proof through the elliptic and Landen identities (gc:L2taylor, gc:L2singles):

    𝒜' = 2πℬ − 2 log2 𝒜,   ℬ' = (3π/2)𝒜 − 2 log2 ℬ   at x = 1/2,   𝒜 = 8N_e/π,  ℬ = 8M_e/π

**d = 1.** Here c_{4,1} ≡ 0, so X_0 ≡ X_{1/2}, with c_{4,0} = 2^{−4b}𝒜/𝒩², c_{4,2} = 2^{−4b}ℬ/𝒩². This gives:

- P4(1) = 32π𝒜 + 40πℬ = 13B_− − 3B_+;
- L_1 = −2(π+log2)P4 + 52π²𝒜 + 64π²ℬ = −(96π+512 log2)N_e − (128π+640 log2)M_e, which is lp:eq:MN and
  equals eq:KLpsiReflected, L = −((3𝖠−𝖣)/6)P4 − (2𝖣/3)B_− with the quarter-basis values 𝖠 = π + 4 log 2, 𝖣 = π.

The frozen derivative is elementary: D_L(1) = (√2π²/4)[(31π/2 − 8log2)𝒜 + (19π − 10log2)ℬ].

**d = 2.** The samples are X_T = 𝒜², X_0 = (𝒜+ℬ)², X_{1/2} = (𝒜−ℬ)². Here C = 0, so D = 0 and cos(πb/2) passes
through zero. The motion of the weights gives −(6𝒜² + 8ℬ²). The rotation terms 2πℬ and (3π/2)𝒜 cancel it
exactly, and only the 4^x normalization survives:

    L_2 = −16 log2 𝒜ℬ/π = −2 log2 P4(2)      (gc:L2residue, gc:L2closed)

Read with the general-d values A (gs:psiBasis) and D in place of 𝖠, 𝖣, the d = 1 formula has no B_− term at d = 2
and gives exactly −(A/2)P4(2), A = 4 log 2. At d = 3 no analogue of B_− with elementary coefficients in the samples
was found (lattice bounds of LRI_C5_d3; a numerical statement). In the pole-node form, D = 0 leaves
3Q_2 = 2π² Σ dT³ (the Selberg value) and P4(2) = −8π² Σ dT^4 λ1.

**d = 3.** C63d's half-shift structure gives c_{4,1} = 2 a4 b4, and Dougall's sum puts b4 in Gamma form. The
dictionary is:

- X_T = N^4 X0
- X_0 − X_{1/2} = 4N^4 a4 b4
- dH = (16/π²) ∂_b[N_b^4(4c0+5c2)]
- da = (8/π²) ∂_b(N_b^4 c1)/b4 − (π/2 − log2) a4

With it, the generic formula becomes C63d's
L3 = 4πP4 − 2π²X0 + 6√2π(π−2log2)a4b4 − 2π dH + 12√2π b4 da. The derivative constants occur only in the
combination −2π dH + 12√2π b4 da. It has **the same derivative content as C63d's P̂′, up to value terms**:

    (2/(πS^7)) D_L = P̂′ − 8√2 N_b^4 c_{4,1} + 32 N_b^4 c_{4,2}     (b = 3/2)

with P̂(b) = −2πν_b[4c_{4,0}+5c_{4,2}] + 6√2πν_b c_{4,1} (C63d's wf_L3). Numerically −1332.48 against P̂′ = 274.55;
the identity holds to 1e-57 with C63d's 160-digit values (rechecked 2026-10-03). So D_L is not literally P̂′.
The collapse fails at d = 3 for three reasons:

- the multiplicity 2ℓ+1 gives rank two, not a one-variable bilateral sum;
- only the Dougall factor b4 closes, while a4' and the Horn-sector derivative do not (C63d's lattice bounds at
  155 digits; numerical);
- D = −π ≠ 0.

**Z_d.** The specializations are those of Z/Z_general_d.tex, Cor. 13:

- d = 1: ĉ0 ≡ 0 (Ξ_3 is odd under t → t+1/2 by duplication) and 𝔱3 = Dixon 3F2, so Z_1 = QH.
- d = 2: M3 ≡ 0 and 𝔱3(2;b) = [3F2(σ,σ,σ;1,1;1)]², Dixon squared (= the complex Selberg value), so Z_2 = 4G Q_2
  follows from Dixon's theorem alone.
- d = 3: ĉ0 is a Gamma product (Dixon + Dougall, from C63d), the zero-mode part of Z_3 is
  √2(4π + 32G/π) ĉ0(3/2), and only S''(3/2) = 𝔱3''(3/2) is new, giving C63d's Z3.

**Mechanism table.**

| d | L_d | Z_d |
|---|-----|-----|
| 1 | Ω_4 at x = 1/2; first-derivative relations; residual term ∝ D | zero mode 0; residue sum Dixon |
| 2 | Ω_4 squared; first-derivative relations; D = 0 leaves only −2 log2 | midpoint sum 0; residue sum Dixon squared (Selberg) |
| 3 | rank two; only b4 closes; D_L new | zero mode Gamma; 𝔱3'' new |
| generic | D_L new | ĉ0, ĉ0', (u𝔱3''+vM3'')/9 new |

## 3. C5(d) (task 2; exact algebra, gdr:C5reduced)

    46656 C5(d) = −1536[P5 + K_d] − 1728 Q² + [720A² + 1008R − 1192π² cos(πd/2)/S²] Q
                + k_0 X_0 + k_{1/2} X_{1/2} + k_T X_T − (1152/(πS^7)) D_L
                + (4768π²/S²) 𝔱3'' + (2384/3)[π(1+C²)ĉ0/S^5 − 4C ĉ0'/S^4 + 4ĉ0''/(πS³)]
                − 15A^4 − 90A²R + 414AU − 108AV − 117R² − 75X

with:

    k_0 = (1+C)²[768A(1+2C)/(πS^7) + 576(4+9C+8C²)/S^8]
    k_{1/2} = (1−C)²[−768A(1−2C)/(πS^7) + 576(4−9C+8C²)/S^8]
    k_T = −1536AC/(πS^7) − 1152(1+6C²)/S^8
    Q = (2π²/S²) 𝔱3 + (4/(3πS³)) ĉ0

Here A, R, U, V, X are the gs:psiBasis polygamma values. P5(d) and K_d enter only through −1536[P5 + K_d]. This work
does not reduce P5; K_d stays the symbol of gs:Kdefinition. It is evaluated by gs:Kseries (whose derivation uses the
mixed-trace step (M) and [τ²] under the trace), by the Mellin-Barnes form gdk:KMB (none of (M), (J), (H)), or by
gdk:Kr3 of C63d's fragment (the next section in the note). With gdk:Kr3,

    −1536 K_d = 384AU − 576c*U − 384(r3 − s3),    c* = ψ0(1) + ψ0(2q),

exact given (M) and (J) ((J) = path form of gs:Bjet, on which gs:C5 already rests); with r3 from three-node samples on
the jet circle (gdk:Ksample) also (H). On 2/3 < d < 4 the d ≤ 4/7 caveat of gdk does not arise. (Joint review G2, D5.)

**Inventory.**

| master | before | now |
|---|---|---|
| P4 | 20 complex block values | 3 samples = 5 two-variable Horn values |
| L_d | 244 Horn values, ≤ 6 variables | the same 5 functions plus first b-derivatives, via one combination D_L |
| Q_d | 3 complex samples | 𝔱3 and M3: two 7F6 + three two-variable Horn values |
| Z_d | 318 Horn values, ≤ 6 variables | the same 5 functions plus first and second b-derivatives, via ĉ0' and one second-derivative combination |
| K_d | 386 | gdk (next section): polygamma part + r3, a third-order τ-jet of three-node samples of three two-variable Horn functions (gdk:Ksample), under (M), (H); or one two-fold Barnes integral (gdk:KMB) |
| P5 | finite sample | not treated here |

Total outside P5 and K_d:

- eight hypergeometric functions with ≤ 2 summation indices at unit argument. In split form these are six
  one-variable rows (8F7, two 9F8 and 7F6 for r = 4; two 7F6 for r = 3) plus eight two-variable Horn values;
- their 8 first and 3 second b-derivatives;
- elementary numbers: Γ, ψ, ψ1 at fixed arguments and trigonometric values of πq, πq/2.

Per dimension these are **8 numbers**: X_T, X_0, X_{1/2}, D_L; 𝔱3, ĉ0, ĉ0', and the second-derivative
combination (for Q and Z together 4 numbers, i.e. 3 beyond Q_d). The old route needed 562 six-variable values
(+386 for K).

## 4. Further reductions (task 3)

**What works (exact):**

- *Frozen weights.* L_d needs one derivative constant; Z_d needs one first-derivative and one
  second-derivative constant.
- *Pole node only.* This form needs one Horn family per wheel and drops one Laurent order. It trades functions
  for parameter derivatives, so it is not shorter in the unweighted-Horn count.
- *Explicit mechanism and constants at d = 1, 2, 3.* See section 2.

**What does not:**

- *Node choices.* t = 0 is the unique one-block node. A real Gauss-type two-node form of W_4 exists only for
  |cos(πb/2)| ≤ 1/2, with a moving three-block second node (cos 2πt̃₂ = 3ς/(1+2ς²)).
- *Summation theorems.* The zero-spin rows are well-poised 2rF(2r−1)(1) (a = σ) but not very-well-poised, and
  the centre rows are not well-poised. Dixon and Dougall do not apply for r ≥ 3.
- *Contiguous relations.* None connect the five functions (non-integer shifts).
- *Gamma form of the zero mode ĉ0* (true at d = 1, 2, 3). PSLQ at 80 digits at d = 4/5, 8/5, 12/5, 16/5 tested
  log|ĉ0| against log π, log 2, log 5, log φ, log Γ(1/5), log Γ(2/5). There is no relation with coefficients
  below 10^11. **Negative, numerical.**
- *Elementary closure of D_L* (true at d = 1, 2). PSLQ at d = 4/3 and 8/3 tested L against the three samples
  × {1, √3, log2/π, log3/π, √3log2/π, √3log3/π}. No relation is stable between 70 and 95 digits, and none has
  coefficients below about 10^4. **Negative, numerical.**

## 5. Checks

All runs were on symmetry (jobs 569132, 569133), plus Mac checks at 30 digits. Results are in
`specialize/results/`.

| check | deviation |
|---|---|
| d=1 duplication and d=2 square identities vs five-Horn samples (r = 3, 4; b = 1/2, 0.45; 1, 1.1) | ≤ 1e-44 |
| first-derivative relations and 𝒜, ℬ vs B± | 5e-46 |
| P4(1), L_1, P4(2), L_2 from modes | ≤ 2e-45 |
| d=3 dictionary vs C63d's 160-digit values (c_k, X0, a4, b4, dH, da, P4, L3) | ≤ 1.2e-51 (50 digits) |
| C63d's L3 formula with our dictionary | 5e-64 |
| (2/(πS^7)) D_L = P̂′ − 8√2 N^4 c1 + 32 N^4 c2 at d = 3 (Mac, 60 digits, 2026-10-03) | 7e-57 |
| pole-node form vs multi-node W (d = 1.5, 2.5; b = d/2 and d/2+0.04; r = 3, 4) | 3e-21 – 3e-23 (Cauchy circle limited) |
| compact P4, L, Q, Z forms vs codes at d = 1, 2, 3, 0.8, 1.25, 1.5, 2.5, 2.75 (50 digits) | ≤ 2.1e-48 |
| reduced C5 block vs direct | ≤ 1.2e-48 |
| block vs closed forms (d = 1, 2) | ≤ 4e-50 |
| block vs C63d spectral refs (non-integer d) | ~1e-45 against the earlier 45-digit strings; ≤ 4e-50 against the current 50-digit `references/reference_values.json` with 60-digit samples (joint review, `review/joint/numerics-end-to-end`; G9) |
| block at d = 3 | 6e-34 (limited by the 33-digit Q3 used) |

End-to-end C5(d) (joint review `review/joint/numerics-end-to-end`, quoted in gdr:checks; G8): printed gdr formulas
with 60-digit samples (symmetry job 569478), K_d from gdk:Kr3 with jet r3, P5(d) of the note:

| d | C5(d) | agreement |
|---|---|---|
| 1 | −731.139476624539825853869126582527231 | note's C5(1): 3.2e-34 (all 33 printed digits) |
| 2 | −38.8336458962253605529369824675329232 | independent evaluation of gc:C5twoClosed: 2.0e-50 |
| 3 | −5.850351420751327229217944230497744300111 | `LRI_C5_d3/c5_value.json`: 7.8e-46 (five-node K), 5.2e-45 (three-node K) |

(Earlier own check: C5(1) with P5(1) (30 digits) and the note's K_1: −731.1394766245398258538691.)

Independent review (own codes, `review/<key>/`): top modes 2.4e-51 to 1.6e-49 relative at 22 balanced
configurations (r = 2..6, d = 0.8..3.2, complex b), unbalanced controls 6.7e-4 to 4.6e-2; printed formulas
rederived in sympy with difference 0; off-centre W3, W4 to 44-53 digits; Z_1, Z_2, Z_3 to 30.7, 35.2, 29.5 digits;
reduced C5 block vs reference-master block to 30.4-35.6 digits at 8 values of d.

Product form of the top-mode theorem (`review/lemmaG-numeric`, own 48-digit code, reruns at 54 digits on disjoint
nodes; foundation Table tab:topG):

| case | r | d | kernel | top modes (48 digits) | 54 digits |
|---|---|---|---|---|---|
| A1-A6 | 3 | 1.3, 2.4, 3.1 | mixed wheels, real and complex; A4 has Re g_1 = -0.075 | 2.6e-47 to 4.7e-44 | ≤ 2.7e-54 (A1: 9.3e-54) |
| B1-B6 | 4 | 1.3, 2.4, 3.1 | mixed wheels, real and complex | 2.8e-48 to 1.5e-44 | ≤ 4.3e-54 |
| R1-R4 | 3 | 1.5, 2.5 | R family, real tau inside (C) | 6.5e-47 to 5.2e-45 | ≤ 7.7e-54 |
| W0 | 3 | 2.4 | equal wheel b = 1.1 | 3.0e-46 | 4.8e-54 |
| RC1, RC2 | 3 | 1.25, 1.5 | R family, continued (tau = 0.08i on the boundary of (C); tau = -0.05+0.07i outside) | 1.7e-38 to 3.8e-38 | ≤ 1.1e-47 |
| O1, O2 | 3 | 1.3 | mixed wheels, continued, 2 varkappa - d = -0.06 | ≤ 3.7e-41 | ≤ 6.1e-50 |

Controls: per-factor imbalance delta_bal at fixed total balance gives relative top modes 0.047 → 0.0013 for
delta_bal = 0.15 → 0.0015 (linear onset), boundary modes unchanged at 1e-44; C63d's control C1 reproduced (0.0135, 0.0029);
outside (C) the plain lattice sum diverges (max|c| ~ 1e102 → 1e134 with depth) while the continued sum keeps zero top
modes. Both top modes are reported separately; at complex parameters | |c_{r-2}| - |c_{2-r}| | reaches 79% of max|c|,
yet both top modes vanish. External: TN's 50-digit wheel modes reproduced to 40 printed digits, C63d's R5, G2, C1 modes
to their 1e-15.

## 6. Review and fixes (2026-10-03)

`review/VERIFICATION.md` lists F1-F23 and O1-O3. Where they were applied:

- foundation (`foundation/general_b_periodization.tex`, `validation_section.tex`): F1 (corrected endpoint
  estimate, Steps 3-4 of the top-mode proof), F2 (control numbers), F3 (derived residue at b_max), F4 (complex b),
  F5 (integer σ), F6 (status labels), F7 (validation record), F8, F9; written proof of the d=2 square identity.
- L (`L/L_general_d.tex`): F10, F11, F12, F13, status labels; Pattern T citation; uniformity in b; written proofs
  of the d=1 duplication and the d=2 square identity.
- Z (`Z/Z_general_d.tex`): F14, F15, F16, F17 (3 numbers beyond Q_d), status labels, O1 (R(2;b) = Dixon squared),
  O2 (d=3 Gamma form on the whole strip by continuation).
- fragment and this file (`general_d.tex`, `RESULT.md`): F18 (d=1, d=2 identities with proofs), F19
  ("first-derivative relations at x = 1/2"; 𝒜, ℬ vs A), F20 (D_L vs P̂′ identity), F21 (B_− statement numerical),
  F22 (status labels), F23 (general-b Theorems 4, 6 and Proposition 9 now stated and proved in the fragment, with
  the corrected top-mode proof and explicit citation of the foundation file), O3 (a_ℓ, β_ℓ stated; g vs g_ℓ;
  M3 bare-sum note; "Dixon squared (= Selberg)"); Pattern T citation for dW3/db = 0 (F14 part for gdr:Z).

**Second review: product form of the top-mode theorem (2026-10-03).** Proof review `review/lemmaG-proof/`
(ACCEPT, seven minor items) and numerical probe `review/lemmaG-numeric/` (PASS). The seven items, all applied
(wording and documentation only; no statement, hypothesis or formula changed):

1. foundation Step 3: "a small quarter circle at 0 and small semicircles at 2πk, k ≥ 1" (the points 2πk lie on the
   real side of the rotated contour).
2. foundation Lemma 2 and eq:boundsG: "the finitely many factor values with small arguments are bounded on K one by
   one" (each factor depends on one combination of the indices; a small-argument factor occurs for infinitely many
   lattice points).
3. foundation eq:endpoint/eq:endprod and gdr:endpoint/gdr:endprod: at varkappa = 1 the bound is at most logarithmic;
   for Im Σg_i ≠ 0 the convolutions stay bounded and oscillate.
4. Probe cited in foundation Remark 7 (rem:topcontext), the R-family paragraph, Open points, status table and its
   footnote (new ‡ footnote), the validation section (new paragraph and Table tab:topG), gdr:top, gdr:checks,
   gdr:status, and here; status labels of Theorem 6(a)-(c) changed to "independently reviewed".
5. foundation Remark 7: "five R kernels (0.5 ≤ d ≤ 3.3, real and complex τ)".
6. general_d.tex Step 0: the S bound (S is now written S_T) holds "for 0 ≤ x ≤ 1 and |y| ≥ max(Y_0, 2)".
7. `lemmaG_statement.md`: status line and a pointer to foundation Step 4, where the endpoint integrability condition is
   shown to be exactly (C).

**Third review: joint review with C63d's K_d fragment (2026-10-03).** `review/joint/JOINT_REVIEW.md` (four lenses:
status consistency, conventions, end-to-end numerics, note integration; verdict "ready after fixes", no formula error,
no numerical mismatch). Applied to `general_d.tex` (no printed final formula changed except the D4 renames):

- D1 layout (gdk is the next section; HOOK block replaced by a MERGE comment for the fallback); G1 / D2 (R-family
  paragraph of gdr:top reduced to a pointer to gdk:topmode and gdk:continuation); G2 / D5 (K_d pointers in the intro,
  gdr:C5 text with the substituted form −1536K_d = 384AU − 576c*U − 384(r3 − s3) and its conditions, inventory row,
  status "Conditional inputs", "Ranges" (C5: 2/3 < d < 4), "Outside this section"; optional "Section gdk:section uses
  the product case r = 3 and the case r = 2" added in the Status paragraph and after gdr:topless); G3 (d = 3 half-shift
  extension listed as conditional input, Derived bullet restricted); G4 / D3 (Relation paragraph rewritten for the N3
  sentence; header MERGE NOTES carry the N3 text); G5 (node variable τ → t̃, τ_2 → t̃_2, P_R → P_+, 𝓡 → 𝓡_+);
  G6 (S, C, D scoped to Sections gdr:samples-gdr:C5; generic C in gdr:periodization; gdr:TG objects S_T, D_T, Ξ_T);
  G7 (𝒯_3 → 𝔱_3, all 34 occurrences); G8 (end-to-end C5(1), C5(2), C5(3) in gdr:checks and gdr:status); G9 (spectral
  references 4e-50); G10 ("fix check" replaced by the lemmaG-proof citation, here and in the foundation footnote †);
  G11 (header and this file: builds only with gdk; combined test build; stale rows updated); G12 (c_{r,k}; ω_j in
  Step 1; c_k(1/2) of gc:L2rim; ρ → ξ; ϑ → η; σ, g scope; A_± → a^Y_± (the hat is the Fourier transform there); also
  "continuous at U = 2π" → "at V = 2π"; imbalance ε → δ_bal; 𝒩_x only with argument x, "the N_x of gc:L2rim";
  𝔥_x(d;b); quarter-basis sentence A = 𝖠, U = 𝖴, D = 𝖣 = π; optional h_i^± → 𝗁_i^±); G13 (complex-b reading of the
  eigenvalue); G14 (`LRI_C5_general_d/` prefix on all short paths; the intro sentence that states the base is kept);
  G15 (intro "gives, in place of ..."; gdr:attempts kept, since note item N5 cites it, to be recorded in
  EDITORIAL_MAP); G16 (condition (C) in the intro and at the start of gdr:top); D6 (review scope in the Status
  paragraph and the status bullet). G-H not applied (only for the fallback layout).

## 7. Open

- The corrected Steps 3-4 of the top-mode proof were re-reviewed in product form, which contains the wheel case, in
  `review/lemmaG-proof` (ACCEPT; endpoint exponents tested numerically). No separate fix-check record exists.
- The product form of the top-mode theorem (foundation Theorem 6(a)-(c), gdr:topG) is closed: written proof,
  independently reviewed 2026-10-03 (ACCEPT; minor fixes applied, wording only, not re-read after insertion), and
  numerically probed (PASS). Remaining limits: the probe's error bars are empirical; for the R family on the
  tau-circle around 0 used for K_d, c_{+-2} = 0 also needs the continuation of the regularized samples in tau (stated
  in the K_d work as hypothesis (H) of gdk:continuation, confirmed numerically at d = 1.25, tau = 0.08i and d = 1.5,
  tau = -0.05+0.07i). The d = 2.5 circle, which lies entirely outside H_q and where also varkappa > d-1 fails, was not
  probed by lemmaG-numeric; the joint review's new three-node jets there (symmetry job 569482,
  `review/joint/numerics-end-to-end/k3_jets.json`) give K_d to 5.0e-44 against the Mellin-Barnes value, direct
  evidence that c_{+-2} = 0 continues there (any c_{+-2} would alias into the three-node rule).
- The derived steps are exact algebra, rederived by the review; only sketches are written out in the fragment
  (full derivations in L/, Z/, specialize/).
- K_d is reduced in C63d's fragment, the next section in the note (layout D1), with its own status list; the K_d
  sentences of gdr:C5 and gdr:status quote its formulas and conditions only.
- P5(d) is not evaluated off d = 1, 2, 3, so C5(d) itself is only evaluated there (values in section 5).
- The negative results are bounds, not proofs.
- Ranges: d > 1/2 for L_d and d > 2/3 for Z_d, so 2/3 < d < 4 for C5(d). At d = 4/3 and 8/3 the Z jets need the
  Cauchy engine.
- The differentiated pole-node series (gdr:taylorLZ) were not summed literally; they are confirmed only through
  b-derivatives of gdr:taylorW.
- Merge (for the note turn; JOINT_REVIEW.md section 3): paste inline, not \input (N1); replace the note's sentence
  after td:sevenOddCoefficients (N3) and the two "Scope of the primitive reduction" sentences (N2), as given in the
  fragment header; record gdr:attempts as an EDITORIAL_MAP exception (G15, N12).

## Files

- `foundation/check_topG.py`, `.log`: quick 30-digit check of the product form of the top-mode theorem (kernel identity,
  mixed-wheel dictionary, top modes at four mixed points incl. Re g_i < 0, controls with per-factor imbalance).
- `general_d.tex`: the note fragment.
- `draft/`: `combined_inline_preview.tex`/`.pdf` (the test build, layout D1: `general_d.tex` + `gdk_promoted_tmp.tex`,
  a temporary promoted copy of the gdk fragment written by `make_combined_inline.py`); `general_d_preview.tex`/`.pdf`
  (this fragment alone, gdk labels from `gdk_labels_from_combined_aux.tex`); `note_labels_from_aux.tex` (extracted from
  the note's current `.aux`); `general_d_pre_joint_backup.tex` (the fragment before the joint-review fixes, md5
  33012d95); `combined_general_d.tex`/`combined_preview.*` (the earlier HOOK-layout trial, superseded).
- `specialize/`:
  - `omega.py`: the Ω_r function.
  - `check_special.py`: checks of d=1/d=2 and L1, L2 from the modes.
  - `check_d3.py`: the d=3 dictionary.
  - `sym_taylor.py`, `check_taylor.py`: the pole-node form.
  - `sym_twonode4.py`: the Gauss-type two-node form.
  - `c5_assembly.py`: the C5 assembly and checks.
  - `gamma_c0.py`, `pslq_L.py`: the PSLQ probes.
  - `results/`: logs and json.
  - `gdr_test.tex`/`.pdf`: old test build of `../general_d.tex` (no note labels).
  - Cluster copy: `<SCRATCH>/c5_gend/specialize/`.
- `review/`: VERIFICATION.md, per-lens scripts and logs.
  - `review/lemmaG-proof/`: proof review of the product form (record `review.json`; Mac scripts `t1_laplace.py`
    to `t5b_r4.py`).
  - `review/lemmaG-numeric/`: 48-digit probe of the product form (record `probe_report.json`; code `lg_engine.py`
    md5 9b5d269f, `cases.py`, `run_case.py`, ...; `results/*.json`, `results/summary*.json`; logs of symmetry jobs
    569336-569347, 569461). Cluster copy: `symmetry:<SCRATCH>/c5_gend/lemmaG/`.
