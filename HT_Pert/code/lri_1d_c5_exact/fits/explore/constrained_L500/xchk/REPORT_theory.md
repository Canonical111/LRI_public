# Independent cross-check (workflow wf_2b5fc5bd-0dd, 2026-10-13), agent report verbatim

**Verdict: SUPPORTED.** The relation c_n(top) = −(w1/(n−2)) c_{n−1}(top), with w1 = +7/2, is justified and has the right sign for the top logarithm Λ^{-1/2} log^{n−2}Λ of C_n(Λ). It covers the top log only, and nothing beyond it.

Closed form (a2 is exact):
- c_n(top) = a2 (−7/2)^{n−2}/(n−2)!, with a2 = −40/(81√π) = −0.2786121.
- c2 = −0.278612, c3 = +0.975142, c4 = −1.706499, c5 = +1.990916.
- For the constrained fit, use c13 = 1.990916 from the closed form. The fitted C4 log² coefficient is only good to about 1%.

**(1) What w1 is.**
- ω(ε) = D6(ε) − 1 = Δ_{φ^6} − d is the exponent of the leading irrelevant operator, φ^6 (`LRI_HT_note.tex` l.139–140 and l.646–658).
- ω0 = 6Δφ − 1 = 1/2. The ε coefficient is ω1 = d1 = −6/4 + 15·g1 = 7/2:
  - Δφ = (1−ε)/4 gives −6/4.
  - The one-loop anomalous dimension is γ_{φ^n} = (n(n−1)/2)·g1 with g1 = 1/3. This gives φ^4: 2ε (Δ_{φ^4} = 1 + ε, so the conventions agree) and φ^6: 5ε.
- So the tail is a(ε) Λ^{-ω(ε)} = Λ^{-1/2} e^{−(7/2)ε logΛ} × …, and w1 multiplies the Λ^{-1/2} tail.
- Mechanism, checked against the data:
  - The tuned bare coupling grows like Λ^ε: from the npz, g2(Λ) increases by 0.2337 between Λ = 1000 and 2000, i.e. a coefficient of about g1·logΛ.
  - So tree-level hard-φ exchange gives ĝ²Λ^{-1/2+3ε/2}, and the one-loop φ^6 renormalisation adds −5ε. The total is −1/2 − 7ε/2.
- Only one channel exists at order ε²:
  - The C2 shell identity (note l.620–628) has the tail −40/(81√π)Λ^{-1/2} with no log. It comes only from the uniform cut n ≤ Λ−2.
  - Reference-energy dependence enters only at Λ^{-3/2}.
  - φ^6 is the only Z2-even local primary with Δ = 3/2 at ε = 0. ∂(φ²) is a total derivative, and (D^sφ)² is proportional to φ^6 by the equation of motion.

**(2) Sign.**
- `eseries` (`analyze_joint.py` l.42–46) computes e_k = [ε^k] exp(+logΛ Σ w_j ε^j).
- The Y targets (l.59–69 and l.89–97) are Y_n = C_n + Σ_j e_j T_{n−j}. They are log-free only if T ∝ exp(−logΛ Σ w_j ε^j); note l.914–927 states the ansatz this way.
- Check at ε^5: [ε^5] of e^{+w1εℓ}·a2ε²e^{−w1εℓ} gives the ℓ³ coefficient a2 w1³(−1/6 + 1/2 − 1/2 + 1/6) = 0. So Y5 is free of log³ exactly when c13 = a2(−w1)³/6.
- The data confirm this sign. My float64 fit of C3(Λ) − C3, even Λ from 400 to 2000, gives a log coefficient of +0.9751441 against a predicted +0.9751425 (1.6e-6 relative). The opposite sign would give −0.975. The note has the same figure (l.1142: 0.97513).
- C2 amplitude from the fit: −0.2786121, matching the prediction.
- The C8 top log uses the same convention (l.1829–1832).

**(3) When the recursion holds exactly.**
T = Λ^{-1/2} a(ε) e^{−ℓ(ω−1/2)} + R holds with:
- (a) a single channel whose Λ^{-1/2} amplitude starts at ε². This is shown above.
- (b) a_k and ω_j constants with no log Λ (RG matching at scale Λ).
- (c) R containing no Λ^{-1/2}log^{n−2} term.

Under these conditions:
- ω_{j≥2} enters only at log^{≤ n−3}, because each log costs j ≥ 2 powers of ε. So w2 (−5A + 1/54 in the raw scheme, −5A in the continuum) and ω3 to ω5 cannot affect the top log.
- a_{k≥3} also enters only at log^{≤ n−3}.
- The ratio c_n/c_{n−1} does not change if the cutoff is rescaled or shifted (Λ → cΛ + s).
- Windows carry no top log. Fits to the window differences ΔC = C_Dconn − C_raw:

| Window difference | Λ^{-1/2} top-log coefficient | Compared with | Other result |
|---|---|---|---|
| ΔC4 | −4e-5 / −2e-5 | 1.71 | Λ^0 log = 5.70e-5, i.e. 1/17496 as expected |
| ΔC5 | −1e-3 / −5e-4 | 1.99 | Fits without the log² and log³ terms reach the 1e-13 floor |

So the relation holds equally for the raw and Dconn schemes.

**(4) Can it fail specifically at ε^5?**
- Not for c13. A channel can reach log³ at ε^5 only if its amplitude starts at ε². A channel starting at ε^k reaches at most log^{5−k}.
- The known extra channels all start at ε³ or later:
  - the state-dependent φ² counterterm r ∝ Λ^{1/2} (r2/√Λ → 0.0836)
  - the u_n(ε)² ~ n^{-(1+ε)/2} truncation tail
  - the window and boundary terms; the "spectator-dependent boundary term" exists only for the φ^6-gap reference (note l.662–673)
- These channels do affect the lower logs c12 and c11. That is exactly the open ω3 problem (note l.1617–1628: effective ω3 of 380–430 against 556 from the gap). So it is not justified to tie the log² or log¹ coefficients at order 5 to ω2 or ω3. Only c13 should be constrained.
- A second ε² channel with a different ω1 is ruled out by the ε³ check (1.6e-6). The ε⁴ check (about 1%) leaves only a contrived case: opposite-sign amplitudes that cancel in both the first and second moments, with no operator to produce them.
- The ε⁴ check, from my float64 fits of C4Dconn(Λ) − C4 with the limit fixed, Λ up to 2000:
  - The free log² coefficient is −1.7065 to −1.739 across adequate bases and lo = 60–300.
  - Fixing it at −1.706499 keeps the maximum residual at the 1.1–1.3e-12 floor (rms ratio 1.0–1.2).
  - The earlier exploration fits gave −1.7147 and −1.6971 (`lri_1d_c4_exact/fits/explore/explore_L2000_coef.txt`).
- The ε^5 data, with the limit fixed at C5:
  - The earlier multiprecision M3 fits (`lri_1d_c5_exact/README.md` l.64–69 and l.91–93) gave c13 = 1.945–2.21.
  - In my float64 sanity check, fixing c13 = 1.9909 leaves the maximum residual at the 2.2e-11 floor for both Dconn and raw.
  - The data barely determine c13 by themselves (free values 1.77–2.18), so the constraint adds information without any cost in residual.
- One caveat for the intercept (Λ^0), not the tail: ΔC5 contains about 4.7e-4·logΛ at Λ^0. By analogy with C4, where Dconn has no Λ^0 log, the raw scheme should carry it and Dconn should not. This is not proven separately at ε^5, so the constrained fit should include a free Λ^0 log column as a check.

Files are in `<TMP>/scratchpad/xchk/theory_w1/`:
- `toplog_check.py`
- `c4_log2_scan.py`
- `c5_log3_scan.py`

All are float64 and run in under 1 s locally; nothing ran on the cluster.
