# Power sector at eighth order: protocol for C8(2) and C8(3)

Session C63d, 2026-10-03. Shared item (b), LRI_C8_shared/assembly. C62d checks it.

This rule is registered before any C8 production data exist. It must not be changed after production data are seen.

Revision (repair round 1, 2026-10-03, still before any C8 data): §4 corrected a citation (the analytic sixth-order
route was used for C6(2) as well as C6(3)). The rule itself is unchanged.

Revision (repair round 2, 2026-10-03, still before any C8 data: no LRI_C8_D3_HPC or LRI_C8_D2_HPC package or result
exists on this Mac [V]; cluster state not checked, no ssh [I]):
- §2: the order-5 row is split by d. At d=2 the note's MS data give a numerical zero, as at order 6, and a flag there
  now also requires investigation.
- §3: the order-8 Δ_p has the same logical status as the order-7 one (vanishing not proved). Its pull is now
  reported, as a diagnostic only. The earlier text said it had "no null hypothesis"; that was wrong.
- Nothing else changes: the null rows, the flag threshold, and the rule that nothing feeds back into C8.

Revision (repair round 3, 2026-10-03, still before any C8 data: no LRI_C8_D3_HPC or LRI_C8_D2_HPC folder exists on
this Mac [V]; cluster state not checked, no ssh [I]):
- In round 2, §3 and the §3 line of the round-2 revision above (both now corrected) called the vanishing of the
  top-order correction "conjectured", citing N:10220-10221.
- That citation is in the d=1 C7 section (app:C7complete, N:9880), and the sentence there says such a conjecture is
  *not imposed*. For d=2 and d=3 the note states no conjecture; §3 now quotes what it does say.
- Wording and citation only: the rule, the null rows, the flag threshold and the diagnostic-only top-order pull are
  unchanged.

Notation:
- `N:` is a line of `GFF/LRI_condensed_note/long_range_ising_condensed.tex` (md5 85f9a1ec039543e2d7ea70654a1aac10).
- [V] means verified in this folder (by code or a computation cited here). [R] means read in the cited source.

## 1. Definition

- Write f_L = (b_L^pf, c_L^pf) for the power-free jets and p_L = (b_L^p, c_L^p) for the power-containing jets of
  loop L. Both are taken in the same finite zero-momentum prescription and the same mixed local-mass forest kernel.
- Write F8 for the order-8 fixed-point extraction, `order8_assembly.coefficients(·, B2, 8, d/2)`.
- Then

  ```
  C8 = C8^pf + Δ_p C8,      Δ_p = F8(f + p) − F8(f)   (componentwise, orders 0..8)
  ```

- This is the order-8 form of c7d2:difference (N:10398-10400) [R]. Δ_p contains all nonlinear lower-loop changes.
  It is not the simple-pole sum of the eight-loop power graphs (N:10401-10402) [R].
- Covariances follow c7d2:covariance (N:10616-10622), with J_L and J_{f,L} the Jacobians of F8 at f+p and at f:

  ```
  V_C = Σ_L J_L (V_fL + V_pL) J_L^T
  V_Δ = Σ_L (J_L − J_fL) V_fL (J_L − J_fL)^T + Σ_L J_L V_pL J_L^T
  ```

- **Implementation** [V]: `order8_assembly.sector_assembly`.
  - At order 7 it reproduces bit for bit the delivered `calculate`/`combine` fields `coefficients`,
    `standard_errors`, `covariance`, `power_differences` and `power_difference_errors` for both C7 productions
    (test `test_order7_production_reassembly`).
  - The productions are LRI_C7_D3_HPC_production/results_run1-20260930-m4096 and
    LRI_C7_D2_HPC_production/symmetry/c7-d2/run1-20260930-m4096.
  - The delivered code runs from its source on this Mac (bootstrap off).

## 2. Pre-registered null rows: orders 3–7

**Rule.**
- For k = 3..7, report Δ_p[k], its SE √V_Δ[k,k] and pull = Δ_p[k]/SE.
- Flag every row with |pull| > 3 as **"not proved zero"**.
- A flag is a diagnostic: it never changes C8, C8^pf, Δ_p C8 or any reported uncertainty, and nothing is refitted.
- Order 3 is reported as "rounding level" when |Δ_p[3]| < 1e-12 (the LRI_C7_D2_HPC convention,
  `tools/assemble.py:70-75`). Its pull is not computed, because the row vanishes exactly by the weights (below).
- Code [V]: `order8_assembly.power_null_rows(delta, dse, order=8)`.

The row at order k depends only on the slots z^0..z^{k−L} (k ≤ 7), so the rows test the old slots of the new campaign. The
evidence that each row vanishes is not equally strong. The flag wording "not proved zero" covers all of them:

| Order | Status of Δ_p[k] = 0 | Evidence |
|---|---|---|
| 3 | Exact by the weights | The single L3 power graph has ĉ_3^p = b̂_3^p/3 (N:10548, N:10747) [R]. C3 sees loop 3 only through (3c_{3,0} − b_{3,0})/81 (top-slot rule, §5) [V]. |
| 4 | Exact in the MS algebra | The MS Δ_p[4] vanishes identically in A, M, N with d3six:lowerPower (N:8846-8851) [V: `exact_check.power_bookkeeping`]. The d=2 values of done:powerSums (N:8707-8713) are the same formula at M_2 = −4, N_2 = 4 − A_2 [V, 60 digits]. [I] This is the MS Δ_p; it equals the finite-scheme one because the power-free exponent is the same in both prescriptions (N:8916-8922). |
| 5, d=2 | MS numerical zero (numerical check, not a theorem) | 729 Δ_p[5] = [M(57A² + 12AN + 24Q − 3R) + 4(3c5 − b5)^p]/4 identically with d3six:lowerPower (N:8846-8851) and gd:bc3 (N:2273-2275) [V: `exact_check.power_bookkeeping`, sympy]. At d=2 (M_2 = −4, N_2 = 4 − A_2, R_2 = 0, Q_2 of gd:d2exact N:2407; b5^p, c5^p of done:powerSums N:8711-8712) it gives Δ_p[5] = −3.3e-21 [V]: the lower-order part, −1.0775357715447757324…, and the (3c5 − b5)^p/729 part cancel, and the residual is below the 1.8e-20 resolution of the printed b5^p, c5^p digits. Consistent with zero in the C7(2) production [V, table below]. |
| 5, d=3 | Measured only | No physical MS b5^p, c5^p or (3c5 − b5)^p is printed: the individual b5 sums depend on trial core values and "must not be reported" (N:8822-8827) [R]. Consistent with zero in the C7(3) production [V, table below]. Not proved here. |
| 6 | Analytic MS compensation, numerically zero | d=3: higher and lower parts cancel to −1.02e-89 (N:8862-8869). d=2: −8.03e-34 and 6.91e-47 (N:8714-8719). The note calls these numerical consistency checks, not an all-orders theorem (N:8719-8721, N:8876-8880) [R]. |
| 7 | **Not proved** | The note says the C7 measurements "do not prove a cancellation at seventh order" (N:10659-10661, N:10817-10818) [R]. |

C7 production values [V, recomputed from the two `C7_result.json` with `power_null_rows`; they match N:10656-10661 and
N:10812-10818]:

| k | d=3: Δ_p ± SE (pull) | d=2: Δ_p ± SE (pull) |
|---|---|---|
| 3 | −1.1e-16 ± 6.1e-15 (rounding) | −1.1e-16 ± 6.6e-17 (rounding) |
| 4 | 2.017e-6 ± 2.083e-6 (+0.97) | 5.41e-8 ± 1.51e-7 (+0.36) |
| 5 | 3.98e-5 ± 6.44e-5 (+0.62) | 1.103e-5 ± 1.845e-5 (+0.60) |
| 6 | −3.70e-4 ± 1.02e-3 (−0.36) | 3.30e-4 ± 1.18e-3 (+0.28) |
| 7 | 0.01788 ± 0.01565 (top order at C7; diagnostic pull +1.14) | −0.05603 ± 0.04586 (top order at C7; diagnostic pull −1.22) |

**What the order-7 row means at C8.**
- At C7, the order-7 entry was the reported power correction.
- At C8 it becomes a null row. Its pull tests a cancellation that is not proved.
- A flag there means "not proved zero, and the data disfavour zero". It does not mean an error.
- At order 6 (both d) and at order 5 for d=2, a flag would contradict the MS numerical zero: the analytic
  compensation of app:C6d2Complete and app:C6d3Complete at order 6, and the order-5 row above. It must be
  investigated (graph coverage, forest maps), but it still does not change the estimate.

## 3. Order 8: reported, not used

- Δ_p C8 = F8(f+p)[8] − F8(f)[8] and its SE √V_Δ[8,8] are reported, together with C8^pf and the cross term.
  They are the decomposition of the estimate, as at C7 (N:10390-10397; N:10686-10694).
- Δ_p C8 is **not a gate**. Its vanishing is **not proved**, and the note states no conjecture about it for d=2 or
  d=3 [R]:
  - The d=2 and d=3 C7 sections say only that "no power correction is forced to vanish" (N:10655-10656,
    N:10811-10812) and that the lower rows "are consistent with zero but do not prove a cancellation at seventh
    order" (N:10659-10661, N:10817-10818).
  - The only "conjecture" in the note [V, grep] is in the d=1 C7 section (app:C7complete): "Neither C5, C6, nor a
    conjecture that the seventh-order power correction vanishes is imposed as a constraint" (N:10220-10221). It is
    mentioned there as something *not* imposed, and it concerns d=1.
  - The d=1 C8 section (app:C8complete, N:10826-10968) integrates the power sector explicitly (N:10886-10896) and
    says that the references "are checks only and are not imposed" (N:10965-10966). It states nothing about the
    vanishing of an eighth-order power correction.
  - Its pull Δ_p C8 / √V_Δ[8,8] is reported as a **diagnostic only**, with no flag and no threshold. The C7 runs
    reported the top-order correction the same way, with its SE (N:10403-10408, N:10688-10694) [R].
  - It never changes C8. Nothing is refitted, constrained, selected or tuned on it.
  - The C7 practice also compared the top-order Δ_p with the previous campaign's value (0.33 previous SE at d=2,
    N:10663-10665; 1.92 previous SE at d=3, N:10820-10821) [R]. At C8 there is no earlier C8(2) or C8(3) value to
    compare with.
  - Code [V]: `power_null_rows(...)['top']` carries `delta`, `se` and `pull`, and no `flag`.
- C8 itself is F8(f+p). The split never feeds back into it.

## 4. Why there is no analytic eighth-order compensation

**Not needed.**
- C7(2) and C7(3) already integrate the power-containing sector explicitly with the mixed local-mass forest kernel,
  "instead of being taken from an analytic compensation" (N:10392-10395, the d=2 wording); d=3 says the same in
  other words, "the power-containing sector is integrated explicitly" (N:10684-10686) [R].
- The C8 packages do the same at every loop 3..8. So F8(f+p) is the complete coefficient by construction, and Δ_p is
  only a reporting split.
- The analytic route was used at sixth order at both d: C6(2) (prec:d2production2026, N:9449-9453; "The final
  numbers retain the analytic power-sector compensation", N:9872) and C6(3) (prec:d3production2026, N:9528-9530)
  [R]. Explicit integration in the C7 productions has since tested it at sixth order (d=2: N:10665-10667; d=3:
  N:10821-10823) [R].

**Not available.** The sixth-order MS construction of app:C6d3Complete (N:8450-8887) is:
- 2187 Δ_p = (3c6−b6)^p − 12A b5^p + 30A c5^p + R(b3,c3,b4,c4) − R(b−b^p, …) (done:powerCorrection N:8693-8700;
  d3six:powerCorrection N:8838-8845) [R].

Its order-8 generalization, derived here from ms8 [V, exact sympy identity, `exact_check.power_bookkeeping`], is:

```
3^9 Δ_p = (3c8 − b8)^p − 16A b7^p + 42A c7^p + R8(b3..b6, c3..c6) − R8(b3 − b3^p, …, c6 − c6^p)
R8 := 3^9 ms8 − 82368A^7 − (3c8 − b8) + 16A b7 − 42A c7      (29 monomials; involves A and loops 3..6 only)
```

Using it would need the following MS power sums:
- **individual** b_L^p and c_L^p for L = 3..6, entering nonlinearly in R8 (e.g. 3b3b6, 3b4b5, −5b4c5, −144A²b6 +
  324A²c6);
- b7^p and c7^p separately, since the loop-7 entry is (−16A, 42A), not a multiple of (−1, 3);
- (3c8 − b8)^p.

None of these exists:
- At d=3 even the sixth-order assembly was possible only because the two unknown four-loop core coefficients
  (u_0, u_1) cancel exactly from the sixth-order target (d3six:unknownCancellation, N:8813-8818) [R].
- The individual b5 and b6 sums obtained with trial core values "must not be reported as separately evaluated
  physical MS coefficients" (N:8822-8827) [R].
- No such cancellation is known for the order-8 target, which needs those individual sums.
- At d=2 the MS power sums stop at b5^p, c5^p and the sixth-order combination (done:powerSums, N:8707-8713) [R].
- At neither d are there MS power sums at L = 7 or 8 [I: none found in app:C6d2Complete/app:C6d3Complete, N:8450-8887].

**C7 practice (both d).**
- No analytic seventh-order compensation was attempted. Explicit integration gave Δ_p C7 directly:
  - d=2: −0.0560 ± 0.0459 (N:10403-10408);
  - d=3: 0.0179 ± 0.0156 (N:10688-10694).
- C8 follows that practice. The C6 analytic route survives as a check of the order-6 null row.

## 5. Related exact facts used above [V, `exact_check.py`; tests in `tests/test_order8_assembly.py`]

- **Top-slot rule:** dC8/d(b, c)_{L,8−L} = (−1, +3)/3^{L+1} for L = 2..8, at any point.
  - For L = 2, with c_2 = b_2/6, this gives dC8/db_{2,6} = −1/54.
  - The top slot never enters a lower C_n.
- **Loop-7 entry:**
  - In general: dC8/db_{7,0} = (3b_{2,0} − 2c_{2,0})/3^9 and dC8/dc_{7,0} = −7b_{2,0}/3^9.
  - With c_2 = b_2/6 and b_{2,0} = −6A_d this is (−16A_d, 42A_d)/19683, where:
    - A_d = ψ0(d/2) + ψ0(1) − 2ψ0(d/4) (gd:blocks, N:2247);
    - A_2 = 4 log 2 (N:7822) = 2.7725887222397812377…;
    - A_3 = 2 + 4 log 2 − π (N:8781) = 1.6309960686499879992….
  - Both A_d values are checked against −b_{2,0}/6 of the two_loop inputs to 1e-55.
  - Consequence: the s_G = 4 classes of loop 7 (3w_B = w_A) contribute (−16 + 14)A w_A ≠ 0, so they must be
    integrated at C8.
- **Affinity:** C8 is affine in all loop ≥ 5 jets.
  - All 210 exact second differences over the 20 slots of loops 5..8 vanish (78 at order 7).
  - Loop pairs (3,3), (3,4), (4,4), (4,5), (3,5) and (2,6) do not vanish at order 8 (controls). At order 7 every
    loop-4 × loop-5 second derivative vanishes identically [V, 48 exact slot pairs]; (4,5) first enters at order 8.
