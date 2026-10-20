# Amendment P1 to FIT_MODEL_2D and FIT_MODEL_3D: nuisance-aware (profiled-ω′) bootstrap uncertainty

Status: DRAFT revision 4 for independent review (2026-09-25; round 1 → REVISE P1-001…004, round 2 → P1-005/006, round 3 → P1-007; addressed in §3.6, §4 and §7). Applies to both frozen protocols (`LRI_2d_MC/FIT_MODEL_2D.md`, `LRI_3d_MC/FIT_MODEL_3D.md`,
§4.3–4.6, which 3D inherits from 2D) and to their evaluators (`evaluate_2d.py` rev 5, `evaluate_3d.py`). Existing data only; no new Monte Carlo.

## 1. Goal and acceptance criteria
Goal: make the statistical uncertainties that the decision table uses (σ_stat of the quoted value, σ_D of the U4 − Y cross-check, and the
σ compared in the reblocking gate) include the uncertainty of the profiled correction exponent ω′, which the current rule omits.
Acceptance criteria:
1. A calibration on synthetic data (§4) shows that the profiled σ covers the true Δ_ε at close to the nominal rate, while the current fixed-ω′
   σ undercovers; if the calibration does not show this, the amendment is withdrawn and the current evaluations stand.
2. Revised evaluators reproduce the SCIENTIFIC CONTENT of the current evaluations exactly when the new switch is off (P1-004): every per-point
   field (decision, E, series values, σ, ω′ intervals, cross-check, reblocking, precision, quoted block) equal bit-for-bit, excluding only the
   provenance fields that necessarily change (evaluator SHA-256, time, input paths, the new §3.5 fields); and implement §3 exactly when the switch
   is on (unit tests against the reference implementation).
3. New, immutable evaluations of both productions are written next to the existing ones (never overwriting them), each binding the SHA-256 of
   this amendment, of the frozen protocol and of the evaluator, and stating which rule produced which label.

## 2. Why (evidence, disclosed as post hoc)
- The protocols define σ_∞ as the standard deviation of Δ_ε refitted on the bootstrap draws at the CENTRAL ω′* (§4.3), and the cross-check uses
  the same fixed-ω′ refits (§4.5). ω′ is itself fitted (dof counts it), so this is a conditional uncertainty. The ω′-profile half-range Δ_ω′
  enters only σ_sys, and only for the reference series.
- An independent Codex review of the finished productions (2026-09-24, `.claudex_artifacts/review_2d3d_data/reply.md`) identified this as the
  most consequential methodological issue before any reanalysis was run.
- Exploratory reanalysis (`LRI_2d3d_reanalysis/README.md`, `run1/`; the script reproduces all 80 production fits to 2×10⁻¹³): refitting ω′ in
  every draw raises the individual-series σ by factors of 2–10 (3D s = 1.6 U4: 0.0011 → 0.0072; 2D s = 1.05 Y: 0.0018 → 0.0177); the joint
  series J stays tight because two observables pin ω′.
- Disclosure: this amendment is proposed AFTER the production decisions and the reanalysis were seen, and it changes one decision (§5).
  Safeguards: (a) the change is methodological, identical for all 16 points and both dimensions, and was identified by an independent review
  before its effect was computed; (b) the eligibility gates are deliberately left unchanged (§3.3), so the amendment cannot remove a
  disagreeing series; (c) adoption is conditional on the calibration of §4, not on the outcome.

## 3. The change
3.1 σ_∞ (§4.3, used as σ_stat in §4.4 and in the ratio label): for every complete draw i, re-profile ω′ on the SAME grid [0.2, 2.0] step 0.01
    with the SAME covariance C (from all complete draws, as now) and take Δ_ε,i at that draw's own minimising ω′_i; σ_∞ = std(Δ_ε,i).
    Ties are broken towards the smaller grid index; draws whose minimum lies on a grid edge are kept and counted in the record.
3.2 Cross-check (§4.5): σ_D = std over the common complete draws of (Δ_ε,i^U4 − Δ_ε,i^Y) with both series profiled per draw as in 3.1; pass
    if |Δ_ε^U4 − Δ_ε^Y| ≤ 2σ_D (central values unchanged).
3.3 Unchanged: the eligibility gates of §4.3 — (i) χ²/dof ≤ 2, (ii) resolved ω′ interval, (iii) σ_∞ ≤ 5 × σ_stat of the largest pair —
    are evaluated with the CURRENT fixed-ω′ σ_∞ in (iii). Reason: applying the larger profiled σ in (iii) would drop exactly the disagreeing
    U4 series at 3D s = 1.55 and 1.7 (and Y at 2D s = 1.05), turning CROSS-CHECK FAILED into CROSS-CHECK UNAVAILABLE — hiding a discrepancy
    (variant A, computed and rejected: `predict.py`). Central values, E, the reference series, σ_sys (half-range over E + reference Δ_ω′ —
    this now partly double-counts ω′ uncertainty, i.e. is conservative), the decision order and the precision suffix are unchanged.
3.4 Reblocking (§4.6 row 6): the compared quantity becomes the profiled σ_∞ of the reference series at b = 1000 and 4000 (each record
    profiled per draw with its own covariance) vs the primary's profiled σ_∞; tolerance ±30 % unchanged. When no extrapolation is quoted the
    comparison stays σ_U4 of the largest pair, as now.
3.5 Records: the evaluation stores, per series, both σ_∞ (fixed ω′) and σ_∞ (profiled), the per-draw ω′ distribution (median, fraction on a
    grid edge) and, per point, both σ_D values; the label is decided by the profiled quantities only.
3.6 Implementation: `evaluate_2d.py` rev 6 and `evaluate_3d.py` rev 2 gain `--sigma-rule {fixed,profiled}` (default fixed = the current
    frozen behaviour) and `--calibration CALIBRATION.json` (required with `profiled`). The rule is applied PER POINT and ATOMICALLY (P1-006):
    a point is P1-CALIBRATED only if every calibration stratum it uses passes with enough samples — the A1 stratum of its reference series (and
    of every series in E, since σ_sys's ratio label uses their σ), and the A2 cross-check of the point when U4 and Y are both in E. A
    P1-CALIBRATED point is evaluated entirely under §3 (σ_stat, σ_D, reblocking, label). Any other point — failed OR UNCALIBRATED — is
    evaluated entirely under the current fixed-ω′ rule (σ_stat, σ_D, reblocking comparison and label identical to the baseline evaluation),
    carries the note "P1 not applied: <stratum, reason>", and its record still lists the profiled σ values for information only. No point ever
    mixes quantities from the two rules. The vectorised per-grid projector of `LRI_2d3d_reanalysis/reanalyse.py`
    is the reference implementation.

## 4. Calibration before adoption (synthetic data, runs in minutes)
Two ensemble types per point, each with an explicit truth that satisfies the model being tested (P1-005):
 (a) single-family ensembles, one per series q ∈ {U4, U6, U8, Y}: truth = q's own recorded fit (Δ_ε^q, c_q, ω′*_q), noise from q's own recorded
     4×4 bootstrap covariance; they calibrate the stratum (point, q) for A1;
 (b) one joint ensemble: truth = the recorded J fit (common Δ_ε^J and ω′*_J, amplitudes c_U4^J and c_Y^J from J), noise from the recorded joint
     8×8 U4–Y covariance; the U4 and Y halves are fitted as individual series AND as J. It calibrates the J stratum for A1 and the point's
     cross-check for A2 (common true Δ_ε by construction). The individual U4 and Y exponents differ from ω′*_J (at 3D s = 1.6: 1.29, 1.21 vs
     1.24), so ensemble (b) is the J-consistent truth; the family-specific truths are ensembles (a). Neither mixes the two.
Per ensemble 2000 synthetic data sets, each with 500 synthetic "bootstrap" draws from N(y, C); the full §4.3 fit, gates and §3 rules run on
each set with both σ rules. Seeds fixed and recorded; `CALIBRATION.json` records per stratum n_eligible, coverages, the cross-check
false-failure rate and PASS / FAIL / UNCALIBRATED.
Calibration provenance (P1-007): `CALIBRATION.json` is written once into a fresh directory (atomic mkdir, immutable) and binds, in a header,
the SHA-256 of this amendment, of the calibration script, of the frozen protocol, of the pinned baseline evaluation and, per point, of the
primary b = 2000 `results.json` and `bootstrap.npy` whose covariances and fitted truths it used, plus the truth parameters (Δ_ε, c, ω′*) and the
§4.3 settings (ω′ grid, gates) of every ensemble. The evaluator, before using any row, recomputes and checks every one of these: amendment
hash = the file it is given, protocol hash = the frozen plan, per-point record hashes = the primary records it is evaluating, truth
parameters = its own fit of those records, settings = its own constants. Any mismatch or a missing header field makes the WHOLE calibration
invalid: every point then falls back to the fixed rule (§3.6) with the note "P1 not applied: calibration not bound to these inputs". The
resulting evaluation records the SHA-256 of `CALIBRATION.json` and the outcome of each binding check.
Adoption rules (all must hold; each stratum judged separately, not only pooled — P1-001):
 A1 per stratum with ≥ 200 eligible synthetic fits: profiled 1σ coverage ≥ 0.60 and 2σ coverage ≥ 0.90 (i.e. at most ~3 binomial σ below
    the nominal 0.683 / 0.954 at n = 200); strata with < 200 eligible fits are reported as UNCALIBRATED;
 A2 per point with ≥ 200 synthetic sets in which U4 and Y are both eligible: false-failure rate of the profiled 2σ cross-check (common true
    Δ_ε) ≤ 0.10 (nominal 0.046); points below 200 such sets are UNCALIBRATED for the cross-check;
 A3 pooled over all eligible strata: fixed-ω′ 1σ coverage < 0.60 (demonstrates the problem the amendment fixes);
 A4 promotion gate: a production point may receive a changed label only if its quoted reference stratum satisfies A1 AND (when the change
    comes from the cross-check) its point satisfies A2; otherwise it keeps its current label even if the amendment is adopted. 3D s = 1.6
    requires the J stratum (A1) and the s = 1.6 cross-check (A2).
A stratum with fewer samples than required is UNCALIBRATED and is treated exactly like a failed stratum: the point is not P1-CALIBRATED and
keeps the complete fixed-rule evaluation (§3.6), including its quoted σ (P1-006); the §5 profiled σ values therefore apply only to points
that turn out P1-CALIBRATED. If A3 fails, the amendment is withdrawn entirely. Also run one misspecified family per point (true sequence with a second correction,
ω₂ = 2ω′*, amplitude chosen to reproduce the recorded U4 − Y difference) and report how often the unchanged gates and the profiled cross-check
still flag it (power; reported, not an adoption rule).

## 5. Predicted outcome (computed on the existing records, `predict_b.py`)
Unchanged: 2D s = 1.05, 1.1, 1.2 CONDITIONAL (quoted σ_stat becomes 0.0177, 0.0101, 0.0018); 2D s = 1.3–1.7 MODEL-LIMITED; 3D s = 1.55,
1.7, 1.85 CROSS-CHECK FAILED (z = +2.49, −4.90, −28.1 with profiled σ_D); 3D s = 1.9 CROSS-CHECK UNAVAILABLE; 3D s = 1.75, 1.8, 1.95
MODEL-LIMITED. Changed: 3D s = 1.6 (Δσ = 0.70) CROSS-CHECK FAILED → ACCEPTED, Δ_ε = 1.47314 ± 0.00118 (stat) ± 0.00230 (sys) from the
joint series J (all five series eligible, U4 − Y = −0.0025, σ_D 0.0055, z −0.45; reblocking 1.02/0.97); the precision suffix
"[σ_stat above target]" remains (σ_U4 of 64→128 = 0.0031 > 0.003). All reblocking ratios stay inside ±30 %.

## 6. Non-goals and risks
Non-goals: new data; changing the correction model, the ω′ grid, the pair list or any gate; promoting CONDITIONAL points. Risks: (R1) per-draw
argmin on a discrete grid makes σ slightly lumpy — mitigated by the 0.01 step and reported edge fractions; (R2) the fixed covariance C is
shared by all draws, as in the current rule; (R3) post-hoc adoption bias — mitigated by §2 safeguards and the §4 adoption rule; (R4) 3D s = 1.6
ACCEPTED rests on four pairs starting at 8→16; the drop-smallest check (U4 1.4724, Y 1.4746 at fixed ω′*) is reported with the label.

## 7. Verification
Baselines are pinned by path and SHA-256 in every script (P1-003): 2D `LRI_2d_MC/prod/evaluation_20260922_083649/evaluation_2d.json`
(fbfc0ef9…), 3D `LRI_3d_MC/prod/evaluation_54387089_20260923_194523/evaluation_3d.json` (ae9cf237…); `reanalyse.py`, `predict.py`,
`predict_b.py` refuse to run on any other file (no "newest evaluation_*" selection).
`python3 -m pytest LRI_2d3d_reanalysis/tests/` (switch-off reproduction of the scientific content of both current evaluations, field list of
§1.2; profiled σ equals the reference implementation to 1e-12; calibration deterministic by seed); calibration record `calibration/CALIBRATION.md`; then the two amendment
evaluations `LRI_2d_MC/prod/evaluation_P1_<time>/`, `LRI_3d_MC/prod/evaluation_P1_<time>/` and an entry in each campaign log.
