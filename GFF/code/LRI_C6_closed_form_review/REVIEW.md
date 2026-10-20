# Review of `GFF/C6_research_note` (closed form of C6(1))

Reviewed 8 October 2026 by session C71d with three independent check agents. The package was not modified.
Target: `note/C6_progress_note.tex` (28 pages, source sha256 2f6d7f9d…), its claimed values in
`outputs/reassembly.json`, and the package integrity records.

## Verdict

No mathematical error found. The note's value

    C6(1) = 14331.6870327580543204454632552462171183173230619887904582…

is reproduced independently both from the reduced input (eq. 2.7) and from the final nine-value formula (eq. 3.5).
It agrees with our independent six-loop graph sum. The remaining issues are gaps in exposition, unlabelled inputs and
presentation, listed below.

## 1. Agreement with the independent graph sum (most important; not in the note)

| | value |
|---|---|
| note (analytic representation) | 14331.68703275805432… |
| exact all-graph sum, N* = 22 (`LRI_C6_1D_HPC`, condensed note Sec. 1) | 14331.68703276838, allowance 4.9e-7 |
| difference | −1.03e-8 = 0.021 allowance |

The source "repair" (eq. 1.2, R147,−3 = R148,−3 = 2/5) contributes **+659.278983198744** to C6. Without it the note
would give 13672.408. The graph sum is independent of the note, so it confirms the corrected reduced input, including
the repair, to about 3.4e-11 relative. That is numerical confirmation, not a proof of the graph-to-period reduction. The
note says it cannot check its physical input and never mentions this comparison; it should be added (Sec. 1.4 and the
"levels of claims" table).

## 2. Independent numerical checks (all pass)

**Reduced input** (`checks/reduced_input/`, no package code used):
- **Inputs evaluated:** E, B_pol (D3 and D5 from the multiple-polylog sums themselves), U4, U6, U8, H±, H0, Y1, Y7,
  W0, M7 and P_a, each by at least two summation methods.
- **Total:** C6 to about 65 digits; the difference from the claim is 2e-66.
- **Blocks:** all eight blocks of `reassembly.json` agree to 69–81 digits.
- **Inherited identities hold numerically to 1e-63 or better:**
  - eq:Pbseries and eq:B8series;
  - both lines of eq:wheelperiodinputs;
  - both lines of eq:wheel-core, and eq:wheelvanish;
  - the primitive contour relation I22 − 4I12 + 4I02 − 4I00 = 0.

**Final nine values** (`checks/final_values/`):
- **Single values:** L3, C212, G4, G6, G8 and G7 by two or three methods each (Mellin–Barnes line integral,
  mpmath.meijerg, residue series), to 40–64 digits.
- **Two-variable values:** H_W, H7 and H* as genuine 2D Mellin–Barnes integrals in double precision, to 9–14 digits.
  Their 1D reduced forms agree to 40 digits.
- **Reassembly:** eq. 3.5 rebuilt from these values gives the reference value to 4e-50 relative.
- **Definitions:** every parameter list reproduces the kernel the note states, under its convention.

**Algebra and proofs** (`checks/algebra/`):
- Every exact claim in Sections 2–10 and Appendix A was checked, by sympy or by numerics at 30+ digits, including:
  - the slopes of the completed-L symmetry path;
  - all residue polynomials, sine factorizations and the λ* matrix factorization;
  - the wheel certificate constants;
  - the Neumann and tail bounds.
- Implementing the Appendix A recurrence exactly as printed gives P_a(N=48) equal to the table value to 3e-33.

**Package:**
- `audit_package.py` (manifest passed, 31 task records passed) and `audit_final_note.py` (no missing refs, protected
  equations unchanged) both pass. They were run on a scratch copy, because they write into `outputs/`.
- A standalone three-pass pdflatex build gives 28 pages with no warnings.
- Conventions C0 = 1/2 and C1 = −1/6 match the condensed note.
- The arXiv references checked exist: Mishev, arXiv:1008.1011, and Bao, arXiv:2609.34016 (27 September 2026).

## 3. What kind of "closed form" this is

- **What it is:** a finite formula in nine specified values. These are elementary constants (π, log 2, G, ζ(3), ζ(5),
  Γ(1/4)), Ls3(π/2) and Cl_{2,1,2}(π/2), four ordinary Meijer-G values at 1, and three bivariate H values at (1,1).
- **What it is not:** a closed form in standard periods. The three bivariate values hold the wheel W0, the seventh
  sector M7 and the primitive P_a. These are genuine two-dimensional Mellin–Barnes integrals, and the package's own
  attempt (`code/stages/C6_closed_form_attempt_report`) found no reduction of them (PSLQ in three bases, no relation).
- **The count is packaging:** "nine values" is not a count of independent constants. Sine addition merges two G
  values into one with an angle parameter. α4 depends on Γ(1/4), log 2 and π, and η7± on log 2 and π, so G4 and G7 are
  Meijer-G values with transcendental parameters. The note says this (lines 293–296, README), but a reader looking for
  "the closed form of C6(1)" should be told up front.

## 4. Gaps and unclear passages (none changes a result)

Line numbers refer to `note/C6_progress_note.tex`.

- **F1 (gap, 574–580):** U6/(2π) = π⁻⁵ B[K], attributed to the "Bailey–Mishev Barnes and 7F6 representations", is
  used as a black box. It carries all of U6 = 2 g22/π². It should be labelled as an input with a precise statement
  and reference. Numerically true to 1e-31.
- **F2 (scope, abstract and 208–231):** besides eq:baseline, the conversions also rest on several supplied
  identities: eq:ordinaryinput, eq:Pbseries, eq:B8series, F1, the symmetry C, eq:wheelperiodinputs and
  eq:primitive-input. The numerics additionally rest on the 2^(100−N) allowance and the Appendix A recurrence. The
  body flags most of these, but the abstract and setup do not. List them in one place. All hold numerically.
- **F3 (gap, 1448–1452):** the Euler-weight tail allowance 2^(100−N) is asserted without its hypothesis (a moment
  representation with total variation ≤ 2^100). Empirically the error is about 2e4 · 2^−N, so the bound is
  plausible, but it cannot be verified from the note.
- **F4 (gap, 573, 642–647, 677–683, 861–864):** closing the contour to the left is not justified for g13, g22, X35,
  X44, K1–K3 or (8M1+5M2)d; only decay on the initial line is given. The closures are true (O(|s|⁻²) on the left
  lines), and the numerical line integrals match the residue series to 1e-28. Section 7 does this properly for the
  seventh kernel.
- **F4b (gap, 483–500):** no convergence statement for the H* kernel on its own contours Re s = Re t = 1/4. There the
  integrand decays only algebraically, about |uw|^(−7/4) where u and w have the same sign. It is absolutely
  convergent, but slow. The note in effect uses only the 1D equivalent (lines 1512–1513).
- **F5 (unclear, 796–806):** row 3 of the slope table ("half-parameter normalization factors: 2ϱ, 2ϱ²") cannot be
  reproduced as written, because the numerator/denominator signs are lost. The resulting (log l_n)′ and (log l_n)″
  are correct.
- **F6 (unclear, Appendix A):** the appendix gives data, not a derivation (meaning of z_{n,j}, ρ = 3 − 2√2, the
  factor 4, convergence of P_{a,N}). The printed data are correct.
- **F7 (unclear, 1098–1116):** only two entries of the boundary table are argued; the rest rest on "reflection" and an
  unstated connection fact. All eight entries were verified numerically.
- **F8, F9 (unclear, 1428–1430, 730):** the constants 8/9 and 110/189 in eq:wheelcert, and a_n² ≤ 1/(3n+1), are
  stated without derivation. Both are correct.
- **Cosmetic:**
  - "definite pairing" (line 1258) should be "indefinite": M + λ*N has eigenvalues of both signs.
  - The "log² times log²" wording at 1146 is loose.
  - Euler numbers E_{2j} are used (1355) before they are defined (1364).
  - Heavy symbol reuse: M, N, K, L, x, p_0, λ, U, d_7, H_0, β each carry 2–6 meanings.

## 5. Presentation

- **Process language:** the text reads as the output of a supervised editing process. Examples are "supplied",
  "the source proves", "the agreed working formula", "this edition", and many sentences saying what something is not.
  The note has no author, and 16 of its 22 bibliography entries are file paths inside the package.
- **For use outside the package:** the condensed note or the paper would need a short rewrite: the result, its
  transcendental content, the agreement with the graph sum, and a list of inherited inputs.
- **Scope of the physics:** the graph-to-period reduction and the RG assembly (eq. 2.7) are not derived anywhere in
  the package. Section 1 says so honestly. The graph-sum agreement is the only check on them.

## Files

- `checks/reduced_input/`: blocks, inputs and identity tests (assembly.json holds the final numbers).
- `checks/final_values/`: the nine values, kernel and list checks, 2D integrals (assemble.out, h2d_*.out).
- `checks/algebra/`: exact algebra and proof checks (s1–s13, common.py).
- `checks/c6_repair.py`: repair size and graph-sum comparison.
- Python used: `<HOME>/mambaforge/envs/sage/bin/python3` (mpmath 1.3, scipy 1.11, sympy 1.12); all runs local
  and under 2 minutes each.
