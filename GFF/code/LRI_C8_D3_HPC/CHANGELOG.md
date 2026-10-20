# Changelog

## 2026-10-08 — Production support: the production budget line and the conservative tail rule (user decisions 2026-10-08)

**numerical_change: false.** No file under `src/`, `vendor/`, `inputs/`, `reference/` or `benchmarks/`, no
`designs/forbidden_seeds.json`, no Makefile and no assembly arithmetic changed: every native row, merged table, C8 value
and SE is unchanged, and a design bundle frozen without `--pc` is byte for byte as before. The user approved C8(3)
production at target SE 1 with a 20,000 core-h production line on symmetry and "produce with the plan's conservative
rule" for the heavy-tailed graphs (`LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`, "Production decisions"). Changed: the pinned
tools `slurm_submit.py` and `production.py` (`PINNED_TOOLS`: plans made before keep their pins; their merges and
assembles need `--accept-tool-change`, recorded; the production campaign is planned on the new export), the unpinned
`budget.py`, `accounting.py`, `ledger.py` and `design_fallback.py`, tests, `docs/HPC.md`, the new
`docs/PRODUCTION_RUNBOOK.md` and a comment in `slurm/sites/symmetry/env.sh.example`. Mac only; not Codex-reviewed.
`tools/verify_delivery.py --write` must run before the commit.

- **The production line** (`tools/budget.py` `LINES`, `LINE_PREFIX`, `LINE_CAP_ENV`, `line_of`, `base_role`,
  `name_info`, `line_cap`, `other_site`, `carry_line`, `Evaluation.lines`, `report`, `main`; `tools/slurm_submit.py`
  `budget_line`, `check_role`, `Call.check_fault`, `no_merge_check`, `base_role`, `cmd_release`). `C8_BUDGET_LINE=production`
  with the required `C8_PRODUCTION_SU_CAP` (finite, positive; the approved line in the site's unit), mirroring the pilot
  line: every role becomes `prod_<role>`; a caller's `prod_` or `pilot_` role is refused (64) under every line; a job is
  classified by its name (`prod_` production, `pilot_` pilot, else dev; an unparseable `c8d3-` name in all three);
  admission refuses (65) above the cap with the other site's carry, and (64) without a cap; no per-site split
  (`SITE_CAPS['production']` None). `budget.py` prints a `production` row. `C8_OTHER_SITE_SU` gains an optional
  `production=` key (absent: 0, so an older export's carry parses); the printed carry includes it. Intents and `submit`
  records carry `line: production`; `ledger.py rebuild --hold-line production`; `accounting.role_class` and
  `production.parse_queue` (`NAME_RE`, `LINE_PREFIXES`; array-mode `recover`/`resubmit`) strip either prefix;
  `tests/fake_slurm/driver.py` likewise.
- **The conservative tail rule** (`tools/design_fallback.py freeze|report --pc PC`; RECON:1373). `load_pc`
  (`pilot_report.require_subset`: pilot_subset, selection role confirm, subset-check passed) and `bind_pc`: PC's own
  verified selection is a confirm selection of PF's inputs manifest whose screen names PF's identity
  (`pilot_report.bound` on manifest, role, selection and every group's scientific identity; `load_pilot` now computes
  PF's identity as `pilot_report.identity`), and PC has PF's inputs manifest, executable, backend, numerics, MP mode
  and test_only flag (`PC_SAME`); a PC of another pilot is refused (exit 1) before any allocation. `pc_raise`: every
  graph-campaign of PC gets sigma = max(PF's 3%-floored sigma, `sigma_hat(J_8, PC's replicates, 32768)`), `sigma_hat`
  being graph_table's own sqrt(n Var_rep(J_8 . jets)) (factored out, same operations); PC graphs must be L8 at 32,768
  points. `design.json` gains `conservative_tail_rule` (rule, PC identity, `raised` with sigma_before, sigma_pc_32768,
  sigma_alloc and factor, `unchanged`, `monitored` = the graphs `pilot_report.confirm_graph` confirms, `undefined`);
  `design_meta.json` gains `pc` (PC's identity and the PF identity it is bound to) and `monitored_graphs`; the report
  carries the block. Neither `production.py` nor the merge (`assemble.tail_monitor`) takes a monitored list, so the
  bundle (named by the production manifest) carries it. Checked on the Mac: the real `pc.json` (`f9f72144…`, PC's
  manifest selection) binds PF `pilotF-s6-20261007`'s identity recomputed from the copied manifest and merged.json files.
- **Tests.** `tests/test_submit.py` `test_production_line`: classification by name (and `Evaluation.lines` per line),
  admission under each line (roles, intent and record lines; `lanes 1` gives `prod_lane`, `prod_merge`), a prefixed
  caller role refused under every line, a missing or invalid cap refused (64), the cap refusal (95 + 8 > 100, 65) and
  admission at 99, isolation (dev 2,000 and pilot 60 spend outside production; the pilot gate at 68 and the dev gate at
  2,004 without production's 99; budget.py's rows), a production intent in production only, the old carry (production
  0) and the new key (read, malformed values refused), the symmetry joint check through `production=` (refused at 964
  over 950, admitted at 932) and its printed carry, `production.queue_state` on `prod_off5`/`prod_merge`/`prod_lane`,
  `accounting.role_class`, and `ledger.py rebuild --hold-line production` taken by argparse. Updated: the carry text and `site_caps` assertions of `test_sym_su_line` and
  `test_site_subcaps`; `Site.spent` and `carry()` know the line. `tests/design_fallback_test.py`
  `conservative_tail_rule` (a small pilot with PF sigma 1 per free L8 graph and an injected PC): raised (PC sigma 3:
  factor 3 in both campaigns, base count 4,096 -> 8,192, recorded in design.json, design_meta.json and the report),
  unchanged (PC sigmas 0.5, 0.9: counts and design.json as without `--pc`), foreign (another PF's scientific identity
  or manifest in the screen, another executable, a stage-A selection: refused by freeze and report, no bundle).
  `tests/test_pipeline.py` step 7: `freeze --pc` and `report --pc` on the real fake PF and PC (PC's identity recorded,
  the monitored graphs equal to the full report's confirmations), the PA as `--pc` and step 4's `pf_sci` refused.
- **Negative controls** (scratch copies, each with one behaviour changed; all fail the new tests): the old tools;
  production spend leaking into dev; the `production=` key required; no cap refusal for production; `prod_` not
  refused for callers; `prod_` classified as dev; `--hold-line` without production; the raise recorded but not applied; PC's sigma replacing instead of
  the larger; no identity binding (also through `test_pipeline`); PC's sigma at PF's point count.
- **Docs.** `docs/HPC.md`: the budget-line bullet, A1.3's lines and carry, the names, the budget section's lines and
  gate, and a "Production" section. `docs/PRODUCTION_RUNBOOK.md` (symmetry): price and freeze the design with `--pc`,
  the plan(s) through `slurm/plan.sh --design` with fresh seeds, `lanes 8` under the production line and the H11
  production window, 7:30 rounds that backfill, the final merge, combine for K > 1, and `verify_result.py` under
  `OPENBLAS_CORETYPE=Zen`; every flag checked against the tools' argparse. It flags that the pilot's own fallback
  report puts `--target-se 1` at the default margin 1.5 near 26,000 core-h, above the line: a stop-and-ask point.

## 2026-10-08 — tools/margin_probe8.py: the L8 margin re-derivation (RECON (a)–(d); user decision 2026-10-08)

**numerical_change: false.** New files only, plus one Makefile line and documentation. Nothing under `src/`,
`vendor/`, `inputs/`, `reference/`, `benchmarks/` or `gen3/` changed; no pinned tool, plan, campaign, merged table or
C8 value is touched. The tool only reads the inputs; its verdicts are evidence for the user (RECON (e)).
- **Why.** The C8(3) pilot reported 441 of the 710 checked L8 graphs as "possible infinite variance" (two-campaign mean
  ξ̂(32,768) > 0.44), and both sectors are on the pre-registered 3% hold. The user's decision of 2026-10-08: start
  production with a conservative allocation and, in parallel, run the margin re-derivation on the worst flagged
  graphs. A real deficit would lead to a lower proposal rate for those graphs, which the user must approve.
- **`tools/margin_probe8.py`** (new): the package form of `gen3/margin_probe.py` (C7(3), L ≤ 7) for any L ≤ 8. It
  reads every payload through `tools/members.py`.
  - `select`: per sector, the PC-confirmed graphs ranked by variance share (action 3's σ̂√c share, reconstructed from
    the committed `sigma_cost.csv`), the top 12, plus 2 light controls; optionally one representative per double-lift
    class (`--class-reps`).
  - `probe`: RECON (a)–(d) over `--workers` processes, one JSON per graph.
  - `report`: a markdown summary.
  - `estimate`: core-hours per selected graph from earlier runs' timings.
- **Method additions over `margin_probe.py`:**
  - Exact-integer evaluation of the forest sum, with an adaptive fixed-point division and a rigorous error bound.
    margin_probe's fixed 80 digits cancel to exactly zero at some deep points.
  - A depth ladder: every level is also measured with its scale pushed 40, 80 (and 160) decades deeper at fixed other
    scales. Deficits use the asymptotic exponent; shallow-only "dips" are reported apart.
  - Chains in all double-lift subsets, sampled uniformly within a budget, plus "tight" anchors (the smallest
    single-scale margins) for graphs without double-lift subsets.
  - An mpmath cross-check (margin_probe's Kern.f) at adaptive digits.
- **`tools/margin_probe8_job.sh`** (new): the symmetry job template. It is a raw job, `--role margin`, on one whole
  `amdq` node (64 cores), with the evidence under `$C8_ROOT/evidence/<sha12>/margin`; `--skip-existing` makes it
  resumable.
- **Validation (Mac).** The C8 L7 packs hold margin_probe's six graphs byte for byte (all 590 C7(3) power-L7 members are
  identical). Every recorded margin_probe number is reproduced: 228, 1357 and 318 (399 clamped subsets, min(e − α)
  −0.000, max +2.004 / +2.008 / +2.012, 32 equal, none below 0.8α, double-lift exponents 0.500 / 1.500 / 1.500 /
  1.500); 3754 (261, +2.000, 35); the controls 328 (191, +4.000, 19) and 3507 (191, +3.000, 22); the two-scale flags
  (1,984 for 228, 632 for 3754) and 228's 4,620 chains have no level below the proposal rate, with smallest margin
  +0.050. New: (c) on 1357 and 318, and sampled chains in the 8- and 10-edge double-lift subsets, all at asymptotic
  margin +0.050. Two real L8 kernels of `inputs_mini` (power 12211, 12233: 38 double-lift subsets, two at raw −9) give
  no deficit. Details: docs/HPC.md "Margin re-derivation".
- **Tests.** `tests/margin_probe8_test.py` (new; in `make test-python`) covers:
  - the rate recomputation on 49 real L3–L6 members (against the payload, `prepare_inputs.raw_valuations` and
    `g3common.d3_rates`; one changed rate is exactly one mismatch);
  - the integer engine against margin_probe's mpmath f;
  - synthetic forests with analytic exponents, with a no-deficit case and a deficit case (a = 2.67 / 3.5);
  - chain enumeration and sampling, and the flag count 1,984;
  - `select` on the committed pilot report;
  - `probe` end to end, including a deficit planted by an overstated payload rate.
- **Docs.** docs/HPC.md "Margin re-derivation".
- **Not done here.** No cluster run (Mac only), no Codex review. Run `tools/verify_delivery.py --write` before the
  commit.

## 2026-10-07 — Stage 6 results: fix round 2's cluster chain, the refreshed models (data and docs only)

**numerical_change: false.**
- **Final code:** K₆ a914db2. Fix round 2 is K₅ ad983e8, plus the site-aware tests `check_inputs` (R2-S1-02) and
  `cost_refresh_test` (S3-R2-006). On a real site their fake-site cases are refused by design.
- **Symmetry:**
  - val1 and val2 PASS on K₆; val3 PASS on K₅ (PLAN:3932 for round 1's `src/` change).
  - sweep2 570900 gives `cost_models/gmp_symmetry_epyc7543_c8.json` `01b67d0a…` (measured basis, exe e9b6f6c3).
  - J-BLD 570906 PASS.
  - Plans: DL3 and PA2.
  - J-PIL-0: `lanes 1/2 --dry-run` rc 0 under the production-window re-split.
  - The F7 drill passes on the new stop path.
- **Expanse:**
  - The bitwise proof 54709473 PASS (`61d291eb…`, l8self, forced tiers against Stage 3).
  - val1 on K₆ 54712716 PASS. The K₃ run's two failures were corrupted Lustre-to-node copies, caught fail-closed.
  - sweep2 54712666 gives `cost_models/gmp_expanse_epyc7742_c8.json` `d92ebbfc…` (prior_model F = 2 from `56df9d61…`).
  - J-BLD-exp 54716341 on D′₃ PASS (54714801 timed out in its data-only diff on the slow Lustre). G6 closed.
- **Seeds:** the HD6 mirror grows to 164 seeds.
- **Docs:** docs/HPC.md "Stage 6 results", README, cost_models/README.md.
- **Evidence:** `benchmarks/symmetry_2026-10-c8/stage6_*`, `benchmarks/expanse_2026-10-c8/stage6/`.

## 2026-10-06 — Stage 6 fix round 2, host: the H11 production-window re-split (user decision "Raise the cap, use my 3")

**numerical_change: false.**
- `tools/slurm_submit.py` (pinned): a symmetry `C8_RESERVATION` re-split that carries `;until=<UTC>` may reach
  `amd_total` = 12 (`SYM_AMD_WINDOW_MAX`), the agreed C8(2) production window of DECISIONS 2026-10-06 (C62d 9, C63d 3).
  The base split stays at 8; an undated 12 or any 13 is malformed (64); after `until` the total falls back to 8.
- `tests/test_submit.py` `test_sym_admission` has five new cases. The first, 3 of C63d's admitted beside c8d2's 9,
  returns 64 on the old code.
- docs/HPC.md "H11 limitation and its fix", README.
- Not Codex-reviewed: Stage 6 was limited to two inspection rounds by the user.

## 2026-10-06 — Stage 6 fix round 2, group P (S3-R2-001..007, 009)

The accepted findings S3-R2-001..007 and S3-R2-009 of the Stage-6 Codex inspection, round 2
(`LRI_C8_D3_HPC_loop/artifacts/inspect_r2_findings.md`, section S3), fixed in the planner's PC admission, the pilot
selection and report, result verification and publication, and the accounting. **numerical_change: false.** No file
under `src/`, `inputs/`, `vendor/` or `gen3/` changed, nor the Makefile or the assembly arithmetic: every native row,
merged table and batch, and every C8 value and SE are unchanged. Changed: the pinned tool `production.py`
(`PINNED_TOOLS`; S3-R2-001 only), so every earlier plan, J-PIL-0's PA plan included, must be re-planned; the unpinned
`assemble.py`, `combine.py`, `report.py`, `verify_result.py`, `pilot_report.py`, `pilot_select.py`, `accounting.py`
and `budget.py`; tests; `docs/HPC.md` (one paragraph). Every fix has a regression test that fails on the old code (a
negative control in a scratch copy with only that fix reverted). Mac only; `tools/verify_delivery.py --write` must run
before the commit.

- **S3-R2-001 (PC cap at planning).** `production.py plan` of a `confirm` selection recomputes the cost of what it will
  run, priced as its own estimates are (counts, `--replicates` or `--group-replicates`, the basis's seconds per point
  and the MP self-check factor: the sum of the groups' planned seconds), and refuses it above the selection's
  `cap_seconds` before anything is created; a confirm selection on the bootstrap basis (no estimate) is refused.
  Test: `tests/test_pipeline.py` step 4: the runbook's PC selection (priced at 8 replicates, 262.1 of 327.7 s), planned
  through the plan job (`slurm/plan.sh`) at 24 replicates, and with `--group-replicates free:8=24`, is refused naming
  S3-R2-001 and creates nothing; the same selection at 8 replicates is planned as before. Negative control: without the
  check the 24-replicate PC plan is published (its seed reserved).
- **S3-R2-002 (joint quota resolution).** `pilot_select.proportional` draws the same per-stratum random orders as
  before (the rng calls are unchanged), but resolves the first proposals (the same fraction f of every stratum)
  jointly: when they cost more than the budget, f is lowered to the largest common fraction whose proposals fit (exact
  fractions j/n_k, bisection), so no stratum is served before another; then the leftovers of every stratum in one
  random order while they fit. The hard cap, `check_cap` and screened-before-extension (`confirm`) are kept. Test:
  `tests/test_pilot_report.py` `pc_selection_fixes`: identical free and power strata with PC costs 1 and 99 s under a
  100 s cap, 3,000 seeds through `confirm`, and `proportional` with either sector's stratum sorted first: the 99-s graph
  is selected at 0.352 (free) and 0.360 (power) of the seeds, 3/8 each by hand, and the cap holds at every seed.
  Negative control: free 0.500, power 0.254 (Codex's 1/2 and 1/4).
- **S3-R2-003 (non-finite combined statistics).** `verify_result.combined_check` requires a finite `C8_full`, a finite
  per-batch C8, a positive finite per-batch SE, and a finite recomputed and stored chi-square before comparing them.
  `verify` rejects any non-finite number anywhere in a result (results are written with `allow_nan=False`), and
  `verify_result.py FILE` reads with `strict_load`: the JSON constants `NaN`, `Infinity`, `-Infinity` and literals that
  overflow a float (`1e309`) are rejected. Test: `tests/verify_result_tamper.py` (in-process NaN and infinite C8, SE and
  chi-square cases, Codex's 1e309 pair; files with each constant and with ±1e309). Negative control: 13 of the new
  checks are accepted (for example an infinite per-batch C8 with a finite stored chi-square passes, as the tolerance
  scales with the infinite recomputed chi-square).
- **S3-R2-004 (target CPU of the partition).** `budget.partition_cpu`: symmetry's Intel pool (`defq`, `debugq`) runs
  `Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz` (`budget.INTEL_GOLD_6148`, the model string of the Stage-5/6 Intel jobs);
  every other lane partition the site CPU. `pilot_report.target_site` takes the target CPU of the selected lane
  partition, so an AMD PF projected to `-p defq` needs an Intel `--target-cost-model` (an AMD one is refused). Test:
  `tests/test_pilot_report.py` `site_projection` (defq refused without and with an AMD model, scaled x1.5 with an Intel
  one at 80 allocated CPUs per node; amdq keeps EPYC 7543). Negative control: the defq projection is accepted.
- **S3-R2-005 (target MP overheads).** `pilot_report.model_for_ratios(P, explicit, site)`: with target-site
  measurements the off/stride16 columns use the TARGET model's `mp_check_overhead` (read back at its recorded sha256);
  an explicit `--cost-model` for those columns must be measured on the target CPU; without a projection PF's own model
  gives them, as before. The table records the model (`cost_table.mp_check_ratio_model`). Test: `site_projection` (PF
  off/on 0.5, Expanse target 0.9: every row's off SU = 0.9 x on; an explicit model on PF's CPU refused; unprojected 0.5).
  Negative control: the projected table's ratio is PF's 0.5.
- **S3-R2-006 (accounting without scheduling copies).** `accounting.account` reads the campaign with
  `verify_base(scheduling_copies=False)` (D.5), so `design_fallback`'s `eta_node`, `pilot_report`'s eta and queue
  latency never open `prior_cost_model.json` or `synthetic_cost_model.json`. Test: `tests/cost_refresh_test.py`:
  `design_fallback.py report` WITHOUT `--eta-node` on the prior-model sweep (a fake Slurm whose sacct shows one lane job
  of the campaign) opens no scheduling copy (spy) and also succeeds on a copy whose `prior_cost_model.json` was removed.
  Negative control: the spy sees `prior_cost_model.json` opened by the accounting's `verify_base`.
- **S3-R2-007 (scientific identities in results).** `assemble.group_science`: a group's scientific identity is the
  sha256 of each scientific table (`graph_replicates`, `graph_tails`, `graph_promotions`, `graph_prefixes`) and
  `merged_science`, a canonical digest of `merged.json` without its timing and provenance fields (lane, thread and row
  seconds, `max_rss_kb`, the `graph_costs.csv` digest, its payload digest, the units text, accepted tool changes).
  `assemble.evaluate` records it per group (`science_sha256`, beside `merged_sha256`), `combine.py` per batch
  (`combined_from[i].science_sha256`). `publish_result` (`supersede_refusal`) supersedes only when every scientific
  identity is recorded and equal and nothing else but `merged_sha256` changed; it names the groups and tables whose
  science changed, and a result written before this change (no identities) is refused. `verify_result` requires and
  checks the identities (EVAL_PROV; `combined_from` rows), and `bind` (directory mode, `pilot_report.verify_pf`)
  compares them with the campaign's. Test: `tests/lanes_tests.py` `recovery_merge` (unchanged scenario passes: the
  timing-only recovery keeps every identity); new, on a copy: a recovered checkpoint with another positive `tail_sum`
  (jets and top 16 unchanged) re-merges into another `graph_tails.csv` ("SCIENTIFIC TABLE CHANGED"), every assembled
  value is unchanged (an `assemble.py --output` elsewhere equals the published result apart from the two maps), and
  `assemble.py` refuses: "the scientific identity changed for a_free_L3 (graph_tails.csv, merged_science)"; the
  function-level combine fixture carries identities and a changed or missing one is refused. Negative control (the
  four tools at 47ed466): `assemble.py` exits 0, "superseded: scientific content unchanged, merged_sha256 changed for
  a_free_L3".
- **S3-R2-009 (recovery after a completed PC).** Screens and PC selections are bound by scientific identities:
  `pilot_report.identity` records manifest, role, selection sha256, `science_sha256` per group (the ID_KEYS) and the
  `merged.json` sha256s (informative only). `bound` refuses a record without scientific identities (an older screen).
  A timing-only re-merge of PA or PF therefore keeps the screen and selection valid, and the completed PC campaign keeps
  its selection pin; a re-merged PF is re-assembled (its merge job does; `assemble` supersedes), so `verify_pf`'s S3-006
  binding holds. `full` records `pc_cap` (the selection's cap against PF's current L8 row seconds; informative). Tests:
  `tests/test_pipeline.py`: after the completed PA/PF/PC chain, copies of PA (a_free_L8) and PF (a_free_L8) re-merged
  after a recovered index with other row seconds (the scientific tables byte-identical), subset-check and assemble
  supersede, and `full` succeeds on the same PC selection and PC with PA, PF or both re-merged (`pc_cap`: PF's current
  L8 row seconds above the recorded ones, the PC still within the cap); a `tail_sum` change of
  PA's or PF's `graph_tails.csv` (re-pinned) is refused ("another campaign", `science_sha256`); the S3-005 cases now
  tamper a scientific identity, and a screen whose PF identity differs only in a `merged.json` sha256 is accepted.
  Negative control (merged-file ID_KEYS restored; the science-only S3-005 cases disabled so the run reaches the new
  block): `full` on the re-merged PA is refused ("the PC selection ... (its screen's PA) belongs to another campaign
  ... (merged_sha256 differ ...)").

Statistics and records that change: the PC selection drawn from a given registered seed changes only when the first
proportional proposals exceed the cap (S3-R2-002; when they fit, the same graphs as before, up to float rounding of an
exact fit); the pilot report's cost
table for a symmetry Intel partition is refused without an Intel target model (before: projected with PF's AMD costs),
and the off/stride16 SU columns of a projected table follow the target model's overheads (S3-R2-005); results gain
`science_sha256` (and `combined_from[i].science_sha256`), the full report `pc_cap`, the cost table
`mp_check_ratio_model`. Results, screens and selections written by the earlier tools do not verify or bind and are
recomputed (none exists for the pilot yet; the Stage-5/6 evidence results under `benchmarks/` predate the field and
stay as recorded).
## 2026-10-06 — Stage 6 fix round 2, group L (S2-R2-005, S4-R2-001..003)

**numerical_change: false.** No file under `src/`, `inputs/`, `vendor/`, `reference/`, `designs/` or `cost_models/`
changed. Every native row, checkpoint, merged batch and assembled number is unchanged, and so are every verdict and
number of J-SMK-4's re-derivation.

What changed:
- `tools/lanes.py`, a pinned tool. Only its stop path changed: `StopGuard`, the worker's stop branch, `attempt`'s stop
  message and the `--stop-seconds` help. A campaign planned with the earlier tools must be re-planned.
- `tools/thru_report.py` (not pinned).
- `slurm/lane_worker.sh` (a comment only).
- `tests/lanes_tests.py` and `tests/thru_report_test.py`.
- `README.md`, `docs/HPC.md` and `docs/PERFORMANCE.md`.
- One new derived record, `benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6b.json`. The existing
  `thru_report_s6.json` is kept unchanged as fix round 1's record.
- Outside the package: `LRI_C8_D3_HPC_loop/artifacts/G5_TABLE.md`.

These are Codex inspection round 2's findings (`LRI_C8_D3_HPC_loop/artifacts/inspect_r2_findings.md`). Under the
user's decision "Targeted fix, no 3rd Codex" they are tested on the Mac with negative controls and not reviewed by
Codex. `tools/verify_delivery.py --write` must run before the commit, because there is a new file.

- **S2-R2-005 (F7's StopGuard): one shutdown deadline.**
  - The old `drain` waited up to C8_LANE_STOP_SECONDS for the children. Then, one child at a time, it killed a
    survivor and waited another 10 s for it before it looked at the next. A lane delayed in I/O after SIGKILL could
    keep the default worker waiting until 35 s or more, past Slurm's KillWait of 30 s, before its scratch cleanup.
  - Now every wait counts from the stop signal toward one absolute deadline. The handler records the signal's time
    (`StopGuard.t0`), and `drain(seconds, kill)` ends `seconds` after it.
  - `drain` waits for the children until the grace end (the deadline less `REAP_FRACTION` = 0.05 of it). It then
    kills every survivor, all of them before it waits on any, and reaps them until the deadline, never later.
  - The timeline, with S = C8_LANE_STOP_SECONDS (25 s by default):
    - a lane's run has until `LANE_STOP_FRACTION` = 0.7 S (was 0.8), with its session killed at 0.665 S; the lane
      then removes its scratch;
    - the worker kills the lanes still running at 0.836 S and reaps them until 0.88 S;
    - `CLEANUP_FRACTION` = 0.12 S (3 s at the default) is kept for the worker's removal of the lane scratch left
      behind and its exit, so the whole shutdown ends by S = 25 s, 5 s before KillWait.
  - The worker's stop line now gives the kill time, the reap end and the cleanup reserve. The lane's line says
    "its session killed at … s". The module docstring and `slurm/lane_worker.sh`'s comment describe the deadline.
  - Tests, `tests/lanes_tests.py` `lane_sigterm` (in `unit_orchestration.py`):
    - **New `stop_deadline_unit`.** Three real children ignore SIGTERM, and their deaths after the kill are delayed
      1.5 s by a timer (a lane held in I/O). The drain starts 0.5 s after the signal with a 2 s deadline. It must
      return by 2.25 s after the signal, every survivor must be killed within 0.2 s of the others and before the
      deadline, and none may be reaped yet. Measured: 2.006 s, kill spread 0.0002 s.
    - **Tightened bounds.** Every case must exit 143 within the configured S. Before, the allowance was 40 s for
      S = 25 and 12 s for S = 4. Measured: forwarded (25 s) 0.06 s; stuck_native (4 s) 2.73 s.
    - **New case stuck_lanes** (S = 4). Both lanes are frozen with SIGSTOP, so neither acts on the forwarded SIGTERM.
      The worker kills both together at 0.95 × 0.88 × 4 s, removes their two scratch directories itself and exits 143
      in 3.36 s. The claims stay stale, with no failure record, and the same job id then completes the campaign. The
      frozen lanes' orphaned runs are left to Slurm's end-of-job kill; here the test kills them.
  - Negative controls, in a cloned copy with the old `lanes.py`:
    - The unit part fails: the drain took 7.1 s, and the survivors were killed at 2.52, 4.05 and 5.59 s after the
      signal, one at a time.
    - With the unit part skipped, stuck_lanes fails its bound: 4.02 s against 4 s, with "2 lane(s) killed after 4 s".
- **S4-R2-001 (`thru_report.py`): a block without valid timing is never evaluated and never yields PASS.**
  - `timing_problem` requires threads to be a positive integer (not a bool), `integration_seconds` a positive finite
    number and the row seconds a finite number ≥ 0. `efficiency` evaluates only such blocks.
  - `omp_stats` lists the other blocks in `untimed_blocks` with the reason. It computes the time-weighted mean over the
    timed blocks only; the old mean counted an untimed block's row seconds, giving 1.11 in the control below.
  - `omp_part` returns SHORTFALL when a timed block is below 0.95. Otherwise, any untimed block gives INCOMPLETE, with
    `why`.
  - In report mode, a checkpoint's threads, `integration_seconds`, `load_seconds` and row-second sums are taken as
    recorded (`_jnum`: a non-finite or non-numeric value becomes null), so such a checkpoint is reported as untimed
    instead of stopping the tool.
  - `a_perf_3.causes` sums over the timed blocks and counts the untimed ones. `block_detail.omp_efficiency` is null
    for an untimed block.
  - Tests (`tests/thru_report_test.py`):
    - **Pure.** Eleven invalid timings beside passing blocks give INCOMPLETE, with the block listed and the mean
      unchanged: `integration_seconds` 0, None, NaN, inf or −1; threads 0, −8, True or None; row seconds NaN or −1.
      Beside a block below 0.95, each keeps the SHORTFALL and counts the untimed block.
    - **Report mode.** One checkpoint's `integration_seconds` is set to 0 (payload digest renewed) beside blocks at
      1.0: OpenMP INCOMPLETE.
    - **--rederive.** J-SMK-4's record with one other block at `integration_seconds` 0. With the three blocks below
      raised to 1.0 it gives INCOMPLETE, as does A-PERF-3; with them kept, the SHORTFALL stays and the untimed block
      is counted.
  - Negative controls, in a cloned copy with the old `thru_report.py`, the test reaching each case in turn:
    - pure: `PASS` with `untimed` 1 and a mean of 1.11;
    - report mode: `PASS` with `untimed` 1;
    - `--rederive`: `('mixed_pass', 'PASS', 'PASS', 0.955)`.
- **S4-R2-002 (`thru_report.py` cause analysis): possible causes are labelled possible.**
  - Each block below has two lists:
    - `established`: what the records' numbers imply. These are one thread (no imbalance between threads is
      possible), fewer tasks than threads (with the bound tasks/threads) and the longest row's bound below 0.95.
    - `possible`: per-launch overhead and end-of-block imbalance, each marked "not measured". The imbalance is listed
      only with more than one thread.
  - `co_tenancy` is now a dict with three parts:
    - `configured_capacity`: the lanes, their widths and the allocated cores ("capacity, not activity");
    - `observed_concurrency`: "not recorded" with several lanes, since lanes start and finish independently, and for
      one lane "a single lane: no other lane of this job ran beside these blocks";
    - `other_jobs`.
  - The summary adds `untimed_blocks` and `single_thread_blocks_below`. The conclusion names the possible
    explanations as not measured, handles the single-thread and single-lane cases, and states that interference from
    the other lanes can be neither confirmed nor excluded.
  - **Regenerated** on the Mac: `thru_report.py --rederive …/smk4/thru_report.json --hook-dir …/smk4_hook --output
    …/smk4/thru_report_s6b.json` (sha256 `1893d779…`).
    - Every verdict and number equals `thru_report_s6.json`'s: A-PERF-3 SHORTFALL on blocks at 0.916, 0.929 and
      0.936, A-ORC-13 PASS, A-ORC-5 PASS. No block is untimed.
    - Only the OpenMP rule text, the `untimed_blocks` list and the cause analysis differ, besides `rederived`. The
      test checks that against the kept record.
  - Tests:
    - Pure: a 0.92 block on 8 threads has the tail established and two possible causes. A 1-task block on 1 thread
      has the one-thread fact established, overhead as the only possible cause, and no "imbalance" in the conclusion;
      a single lane gives "no other lane of this job". Fewer tasks than threads is established with "efficiency at
      most 0.500".
    - The test pins the committed `s6b` to the fresh re-derivation.
  - Negative control: with the old tool, the test fails at the pure check (`KeyError: 'established'`).
- **S4-R2-003: the docs report the gates consistently.**
  - The README's status now says G5 holds except three items:
    - A-PERF-3 / A-SMK-4: a per-block SHORTFALL, reported with its cause;
    - A-ORC-4 (i): fixed by F8-d3 and passed in J-DRL-5 (570796) and J-DRL-8 (570815) on real Slurm;
    - A-ORC-13: PASS on re-derivation.
  - The README labels Stage 5's verdicts historical and refreshes the pending work against `STAGE6_REVALIDATION.md`:
    Expanse's bitwise proof, val1 and sweep2, then D′₂; fix round 2's cluster chain; the residuals the user accepted.
  - `docs/HPC.md`:
    - The stop-signal bullet gives the new timeline.
    - The throughput report gives the timing rule and the established/possible causes, and points to `s6b`.
    - "Stage 5 results" opens with a list of its historical verdicts and their replacements. Its table rows, the
      F8-d3, F13-d3 and S4-007 findings and its pending list are marked or updated.
    - A new section, "Stage 6 results", has the commits, the symmetry table (bitwise proof, val1, sweep2, J-BLD,
      plans, the S2-001 and F7 drills, J-DRL-5, J-DRL-8, J-PIL-0, the rename probe) and Expanse's state.
    - It also covers the rename probes (BeeGFS and Lustre both take `recheck_rename`), the H11 limitation
      (`amd_total ≤ 8` cannot express the 9/3 production window, so C63d's AMD admissions are refused during it), the
      G5 status, the inspection rounds with the accepted residuals, and what is pending.
  - `docs/PERFORMANCE.md`: the A-PERF-3 section opens with the current verdict and marks the Stage-5 table historical.
    "Where the remaining 6.3% went" no longer calls the idle integration time imbalance. The re-derivation points to
    `s6b` with the possible causes.
  - `G5_TABLE.md`: the rows A-SMK-2, J-DRL-5's window drill, A-ORC-4 (i) (J-DRL-8), A-SMK-4, A-PERF-3, A-ORC-4 and
    A-ORC-13 carry their Stage-6 status first, with the Stage-5 status marked historical. A dated "Stage 6 update"
    note is added.
- **Tests run** (Mac, venv Python 3.10.12, `OPENBLAS_NUM_THREADS=1 C8_ALLOW_NO_L8=1`), all on the final tree:
  - `unit_orchestration.py --only lanes,lanes_submission,done_markers,recovery_merge,arrays_and_recovery,vendor_pin,lane_sigterm`:
    7/7 passed in 248 s. In `lane_sigterm`: forwarded 0.03 s, stuck_native 2.70 s, stuck_lanes 3.37 s; the drain
    2.008 s with a kill spread of 0.0004 s.
  - `thru_report_test.py`: 5/5 passed in 65 s.
  - `ast_scan.py`: 0 findings.
  - `bash -n slurm/lane_worker.sh` (only a comment changed there).
- **Still to do:** `verify_delivery.py --write`. On the cluster chain of fix round 2, re-plan after the pinned-tool
  change and repeat the F7 scancel drill on the new stop path (A-ORC-8a).
## 2026-10-06 — Stage 6 fix round 2, group I (R2-S1-01, -02, -03 (duplicates), -05)

**numerical_change: false.** No file under `src/`, `vendor/`, `inputs/`, `reference/`, `benchmarks/` or `designs/`
changed: the workers, every input, every row and every result are unchanged. Changed: `gen3/size_probe.cpp` (how the
masks output is opened; its CSV and masks bytes are unchanged: old and new binaries give byte-identical outputs on
`classes{3..7}.txt`); the pinned tool `tools/prepare_inputs.py` (`PINNED_TOOLS`: a plan made before must be re-planned);
tests (`gen3/test_gen3.py`, `tests/check_inputs.py`, `tests/c8pkg.py`, `tests/unit_orchestration.py`,
`tests/inputs_l8_test.py`); this entry. A rebuilt `bin/gen3/size_probe` has a new executable sha256;
`inspect/inspect.json`'s `fmax_source` keeps the old one as provenance (nothing compares it with the binary).
`tools/verify_delivery.py --write` must run before the commit. Codex's round-2 findings, accepted; R2-S1-03 in the
host's narrower scope (duplicates only).

- **R2-S1-01 (`gen3/size_probe.cpp`).** A dangling output symlink whose absent target lay in a protected tree
  (`.../LRI_C8_shared/inventory`, the c8d2 prefix) passed both checks (`weakly_canonical` stops at a dangling final
  link) and `ofstream` then created the protected file. Now `under_c62d` follows every final-component link hop (a
  dangling one too, relative targets against the link's directory) and checks each target lexically and resolved; the
  output is then refused (exit 2) when it is a symbolic link at all, and opened with
  `O_WRONLY|O_CREAT|O_TRUNC|O_NOFOLLOW|O_CLOEXEC` (a link swapped in after the check fails with ELOOP, exit 2).
  Test (`test_tool_refuse_c62d`): dangling links to an absent file in the shared inventory (absolute, relative, a
  two-link chain) and under the c8d2 prefix exit 2 "under C62d's tree"; a dangling link into an ordinary directory exits
  2 "is a symbolic link"; nothing is created in either directory. Negative control (scratch copy, old `size_probe.cpp`,
  new test): the old binary exits 0 on the dangling link and creates `LRI_C8_shared/inventory/masks_L3.txt`.
- **R2-S1-02 (`prepare_inputs.plan_inputs`).** The manifest label no longer lifts the completeness check. A manifest
  with a `synthetic` entry (any value, pinned or not) makes a non-test plan test-only (reason `synthetic: ...`); a
  manifest without pins and without it is refused by `inventory_complete` as before. The skip is now reached only
  through `synthetic_seam(env, m)`, which no manifest can switch on: the environment's test seam
  `C8_TEST_SYNTHETIC_INPUTS=1`, honoured only under `C8_SITE=fake` on a host that `ledger.host_sites` finds to be no
  real site (Expanse or symmetry, whatever `C8_SITE` says), and then only for `SYNTHETIC_INPUTS_LABEL` exactly with
  neither pin (the skip recorded as before). Set under another `C8_SITE` or without one it is refused; on a real-site
  host it is refused with ledger.py's text ("this host is <site> but C8_SITE is 'fake'"), which val1 records as
  SITE_REFUSED, like every other Mac fake there. The change to the pinned tool is that branch and the function.
  `tests/c8pkg.py`: `tool()` runs `production.py plan` under an injected validator (`INJECT`: a `-c` driver that
  replaces `prepare_inputs.synthetic_seam` with the label-and-no-pins test, then runs the tool's `main(argv)`; test code
  only, nothing in the package sets it). These plans therefore take their old path under any `C8_SITE`, on the real
  sites too, where val1 runs them (uo_atomic_and_guards, uo_per_index_and_spies and others passed there; not re-run
  here, Mac only). `env()` adds the
  environment's seam to every `C8_SITE=fake` environment (`CLEAN_ENV` drops an inherited one) for the plans that the
  fake Slurm's jobs and the tests' own subprocesses make. `unit_orchestration`'s `seed_logs_two_sites` also checks that
  a non-test plan under `C8_SITE=symmetry` without the validator (`inject=False`) is test-only and skips the mirror
  check. Test (`check_inputs.py`, on the materialized inputs_mini without its marker): twelve variants. Without the
  seam honoured (the label pinned or not, another `synthetic` value, `C8_SITE` empty, fake or symmetry) the plan is
  refused or test-only; the seam under symmetry, without `C8_SITE` and on an Expanse host (`SLURM_CLUSTER_NAME=expanse`,
  with ledger's text) is refused; a tree without the label and without pins is refused, seam or not; only the seam
  under fake on the label with neither pin skips the check. Negative control (scratch copy, old `prepare_inputs.py`
  plus the constant's name): the label without pins gives a non-test plan with the check skipped under every
  `C8_SITE`; the check fails.
- **R2-S1-03, duplicates (`prepare_inputs.inventory_complete`).** Every (sector, loop) of the inventory, L3-L8, must
  hold each graph id once; a repeat is refused naming the ids. The identity check of L3-L6 against C7(3)'s reference
  inventory stays an accepted residual. Test (`check_inputs.py`, the finding's case): free L3 G6 replaced by a second
  G3 row, and power L7's last row by its first; counts, packs and their pins kept, only the manifest's inventory hash
  refreshed; both refused ("free L3: graph ids repeated [3]"). Negative control: the old code accepts the free L3 case
  (L7 was already refused, as "missing").
- **R2-S1-05 (`prepare_inputs` mini, mini-materialize).** `mini` refused only an explicit `--out` and only at its root.
  Now `refuse_mini_targets` checks the destination, the default `tests/fixtures/inputs_mini` included, and every path
  written below it (each directory on the way, each file): one that resolves into the package `inputs/` or exists as a
  symbolic link is refused before anything is read or written, and again before each file is published. The stale-file
  check runs before any write. `mini` builds its files in a fresh private directory (`mkdtemp` under the destination,
  files created with `O_EXCL`), moves each into place with `os.replace` (the entry is replaced, never written through)
  and removes the directory. `materialize_mini` validates `package_files` first, needs a fresh destination (absent or an
  empty directory, not a link), checks every path below it, and creates every file exclusively. Tests:
  `check_inputs.py` on a scratch package whose inputs differ from what `mini` writes (no marker, one byte appended to
  free_L8.pack, re-pinned): A the default destination symlinked to the package inputs, B an `--out` whose `packs/`
  links to `inputs/packs`, C an `--out` holding the old temporary path `.manifest.json.tmp` as a link to
  `inputs/manifest.json`, D/E `mini-materialize` into a destination whose `packs/` links to `inputs/d3` or whose
  `manifest.json` links to `inputs/inventory.json`. Each exits 1 before writing (A, B, D, E naming the overlap; C as
  an unexpected file), with every byte of the package inputs unchanged (content hashes). Positive control: `mini` on a
  fresh `--out` (the mini of the materialized mini) writes the committed fixture's four files byte for byte, removes
  its staging directory, and a second run changes nothing. `tests/inputs_l8_test.py` (the miniature Stage-2b package
  with real L8 packs): A and B, every package input byte unchanged. Negative controls (old `prepare_inputs.py`): each
  check_inputs scenario on its own scratch package, A rewrote `inputs/manifest.json` and `packs/free_L8.pack`, B
  `packs/free_L8.pack`, C `manifest.json`, E `inventory.json`, and D created twelve packs in `inputs/d3/`; B to E
  exited 0. In `inputs_l8_test.py`, A rewrote the package's `inputs/manifest.json` and B exited 0.
- Tests run on the Mac (`OPENBLAS_NUM_THREADS=1 C8_ALLOW_NO_L8=1`): `make gen3` and `make gen3-sanitize` with g++-16
  (no warning); `gen3/test_gen3.py` (24 tests); `tests/check_inputs.py` (65/65; the plan gate through
  `production.py plan` among them); `tests/unit_orchestration.py` (22 tests), `tests/test_submit.py`,
  `tests/test_pipeline.py`, `tests/integration_3a.py`, `tests/inputs_l8_test.py`, `tests/workflow.py --fake`,
  `tests/staging.py --fake`, and the other users of `c8pkg.tool` `tests/cost_refresh_test.py`,
  `tests/thru_report_test.py`, `tests/prefix_check.py`, `tests/members_test.py`: all pass. The negative-control runs of
  `check_inputs.py` on the old `prepare_inputs.py` fail exactly the four new checks (59/63 in a scratch export, whose
  git-only checks are skipped; the same export with the new code passes 63/63).

## 2026-10-06 — Stage 6 fixes: F8-d3, F13-d3, CPU pin (<NODE>, <NODE>)

**numerical_change: false.** No file under `src/`, `vendor/` or `inputs/` changed: the executables, every native row,
every merged batch and the scientific content of every result are unchanged (the recovery test checks the batches and
the scientific tables byte for byte). Changed: the pinned tools `production.py` and `common.py` (`PINNED_TOOLS`), so
every Stage-5 plan, J-PIL-0's PA plan included, must be re-planned; the unpinned `assemble.py`, `combine.py`
(docstring), `pilot_report.py`, `thru_report.py` and `budget.py`; `slurm/native_job.sh` (val1's two lists of
`unit_orchestration` tests gain `recovery_merge`); `slurm/merge.sh` and `slurm/sites/symmetry/{env.sh.example,profiles.sh}`
(comments only); tests; docs; and one new evidence file beside the
unchanged Stage-5 record, `benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk4/thru_report_s6.json`. Also in this
entry: Codex's S4-007 (accepted), A-PERF-3's OpenMP rule per block. Every change was made and tested on the Mac only;
`tools/verify_delivery.py --write` must run before the commit (a new file).

- **F8-d3 (A-ORC-4 (i); port of C62d's F8, `LRI_C8_D2_HPC` 86e15f4).** Symptom (symmetry 570487, 570490): after a
  recovered index the group re-merge stopped at `Checksum mismatch: .../groups/a_free_L3/graph_costs.csv`.
  - `production.py` `_publish_copy`: `merged.json` is a group's commit point. A table without a `merged.json` is
    uncommitted, and a different one is replaced atomically and printed (`graph_costs.csv`: "timing only"; the
    scientific tables `graph_replicates`, `graph_tails`, `graph_promotions` and `graph_prefixes`: "SCIENTIFIC TABLE
    CHANGED"). A committed table must stay identical ("Checksum mismatch"). The EDQUOT fault point and exit 74 of the
    publish path are kept. `merged.json` records the digests of the bytes the merge published (its scratch tables).
  - `common.supersede` (new): the old bytes stay as `<name>.superseded.<sha12>.json` (a hard link), the new bytes
    replace the file atomically, the decision is retaken when the file changed since it was read, and EDQUOT exits 74.
  - `assemble.publish_result` (also behind `combine.py`) supersedes a result whose only change is `merged_sha256`, at
    any depth (`science_of`). `combine.py` records it per batch in `combined_from`, at the top or under
    `partial_values`, and the message names `combined_from[i]:group`. Any other difference is still refused.
  - Beyond C62d: this package's third publisher, `pilot_report.py subset-check` (`publish_summary`), writes
    `subset_summary.json` of a pilot_subset campaign (PA, PC) with the digests of every table. It supersedes a summary
    only when the timing digests (`merged.json`, `graph_costs.csv`) change; a scientific table's digest never.
  - New test `recovery_merge` (`tests/lanes_tests.py`, in `tests/unit_orchestration.py`'s list; 63 s). J-DRL-8 runs
    unattended on the fake Slurm: `lanes 1`, worker, the real `slurm/merge.sh`; one checkpoint and `merged.json`
    deleted; `lanes 1` (marker dropped and logged), a worker at `C8_FAKE_SPP=0.0015`; `merge.sh` again. It hits index
    0 of `a_free_L3`, as on symmetry. The second merge job passes: `graph_costs.csv` replaced (timing only), the three
    scientific tables byte-identical, the batches equal, the result superseded (only that group's `merged_sha256`),
    and `verify_result.py` passes; a third run changes no file. Refusals: a committed table changed, a stale
    uncommitted scientific table (replaced, reported), `_publish_copy` against a committed table, and a result whose
    science changed. Function level: a combine result and a subset summary, superseded and refused.
  - Negative controls (scratch copies): on the Stage-5 code the merge job stops at `C8: merge failed for a_free_L3:
    Checksum mismatch: .../groups/a_free_L3/graph_costs.csv`, the message of 570487 and 570490. With only
    `production.py` fixed it stops at `assemble: .../C8_test_result.json exists and differs from the recomputed
    result; not overwritten`. Both fail at the same assertion, the merge job's exit code.
- **F13-d3 (A-ORC-13).** The hook's rchar is `/proc/self/io` of `production.py run` at its exit. Linux adds a reaped
  child's I/O to its parent's, so the rchar includes each native launch's read of its block's staged copy.
  - `thru_report.py` now counts those reads as own work: `native_staged_reads` = the staged bytes of every block the
    run executed, committed or verified duplicate. The hook gives process totals only, so this is a model, not a
    measurement (C62d's `claim_io` measures each launch); its rule `NATIVE_RULE` is written into the record.
  - Per run: `own_bytes_process` (the Stage-5 own bytes), `native_staged_reads`, `own_bytes` (their sum); `non_own`
    and `non_own_wo_fp` decide; `non_own_raw` and `non_own_raw_wo_fp` (the Stage-5 model) are reported. The group
    comparison also reports the raw medians and whether they agree (`raw_model`, never the verdict).
  - Fits on the staged bytes: rchar (slope near 2) and `non_own` (slope near 0). The schema becomes
    `c8-d3-thru-report-2`.
  - New `thru_report.py --rederive REPORT.json [--hook-dir DIR] --output OUT.json` applies the Stage-6 rules to a
    committed report (see S4-007 for its OpenMP part).
  - **Recomputed on the Mac, J-SMK-4** (R-SMK4 570554's `smk4/thru_report.json` with the 82 hook records of
    `smk4_hook/`; `smk4/thru_report_s6.json`):
    - Every rchar was re-read from its hook record; all 82 equal the report's.
    - Non-own medians: a_free_L3 30,046,840 bytes (1 run), a_free_L8 31,734,238 (11 runs), size ratio 118. They are
      1,687,398 apart, within max(10% = 3,173,424, 2,000,000). Without `fingerprint_bytes` (7,008,499): 23,038,341
      and 24,725,739, within 2,472,574. **A-ORC-13 PASS** (Stage 5: FAIL).
    - The Stage-5 model is reproduced as `non_own_raw`: 30,049,197 and 1,389,313,912.
    - Fits: rchar = 2.001053 × staged + 32,788,697 bytes; `non_own` = 0.00069 × staged + 30,736,551.
  - **Not recomputable on the Mac**, taken from the committed report (computed on symmetry): the own bytes per
    category of each run, the groups' `tasks.sqlite` sizes, the `fingerprint_bytes` part and the hook/idx-log pairing.
    They need the campaign directory (manifest, checkpoints, inventory lengths, idx logs), which is only on symmetry's
    BeeGFS. So `native_staged_reads` of a Stage-5 record is its own `staged_bytes`: the same blocks.
  - The native's other per-launch reads (its copies of the net and gamma, the block's `tasks.txt`, library headers)
    are not modelled and stay in non-own. The residual slope 0.0007 bounds them here.
  - `tests/thru_report_test.py`: the fake hook records now hold the child's reads (rchar = C + own + staged). Every
    run's `non_own` equals C and `non_own_raw` equals C + staged. Negative control: with the Stage-5 model in the new
    tool, the test fails there (non-own C + 58 to C + 372 bytes). Also: the J-SMK-4 re-derivation above, pinned to
    the committed `thru_report_s6.json`; refusals (a changed or missing hook record 65; RUN or another option beside
    `--rederive`, an existing output, no RUN 64); pure `run_bytes` and `raw_model` checks.
- **S4-007 (Codex inspection, accepted): A-PERF-3's OpenMP rule is per block,** as `PLAN.md:3369` states it ("per-block
  OpenMP efficiency ≥ 0.95"). Stage 5 gated the time-weighted mean.
  - Every timed block must be ≥ 0.95. The time-weighted mean, min, P10, median and share stay reported. A block below
    makes the OpenMP and the A-PERF-3 verdict **SHORTFALL**: FAIL outranks it, it outranks INCOMPLETE, and `--strict`
    exits 1.
  - `openmp.shortfall` lists every block below: index, group, graphs, points, tasks, threads, efficiency, wall, idle
    core-seconds, tasks per thread, wall rank and host. From the per-row seconds it adds the longest row's bound on
    balance and the residual. A summary and the node, lane widths and allocation (co-tenancy) follow, then what the
    records can and cannot show. `block_detail` now carries points, the longest row, the host and the graph count.
  - **J-SMK-4 re-derived** (`smk4/thru_report_s6.json`): A-PERF-3 PASS → **SHORTFALL**.
    - Three of 789 blocks are below: b_power_L4 index 58 at 0.916 (24 tasks, wall 63 ms), a_power_L3 index 16 at 0.929
      (8 tasks, 5.5 ms) and b_power_L3 index 57 at 0.936 (8 tasks, 6.0 ms). All ran on 8 threads on <NODE>, the job's
      node (64 of 64 allocated cores in lanes).
    - These are wall ranks 6, 1 and 2 of 789, against a median wall of 26.5 s. Together they hold 1.4e-6 of the
      integration core-seconds and 0.049 idle core-seconds. Every block of 1 s or more is at least 0.9688. The
      time-weighted mean is 0.990, as before.
    - Cause, as far as the records go: per-launch overhead (thread team, scheduling, the final barrier) and
      end-of-block imbalance with 1–3 tasks per thread. The records cannot tell the two apart: there are no per-thread
      or per-block times.
    - The records also cannot exclude interference from the job's other lanes or show OS noise. The longest row's
      bound needs the checkpoints' row seconds, which are not in the committed record.
    - Busy, throughput, speed, sizing, A-ORC-5 and `block_detail` are taken over unchanged.
  - Tests: pure `omp_part` (a block at 0.92 beside a mean ≥ 0.95 is a SHORTFALL with its bound 0.909; PASS;
    INCOMPLETE) and `verdict`. End to end: the fake drill with one checkpoint's `integration_seconds` set for
    efficiency 0.9 (payload digest renewed), mean 0.998. The new rule gives SHORTFALL listing that block with its
    graphs, points, threads, host and bound. `C8_FAKE_OMP_EFF=0.9` gives every block as a SHORTFALL.
  - Negative control: with the Stage-5 rule (the mean) in the new tool, the end-to-end case fails with ('PASS',
    0.99846, 0.9); the Stage-5 `thru_report.py` fails already at the pure checks.
- **CPU pin.** `budget.SYMMETRY.cpu_exclude` gains <NODE> (EPYC 7532: the guard refused J-SMK-3 batch B's merge 570552,
  exit 68) and <NODE> (EPYC 7532: the guard refused re-merge 570589 and report 570591, exit 68;
  `stage5_59d4922/wave45_logs/*_570591.out`).
  - The default token is now `--exclude=cn112,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>`, and an own
    `--exclude=cn[079-087]` becomes `--exclude=cn[079-087],cn112,<NODE>`.
  - Updated to match: `tests/test_submit.py` (`PIN` and the range case), `docs/HPC.md` (the CPU-pin bullet and the
    Stage-5 CPU map, which now records the three 68 refusals), and the comments of `env.sh.example` (no longer needed
    in `C8_AMD_EXCLUDE_EXTRA`) and `profiles.sh`.
  - `budget.py` is not pinned, so the pin change alone would keep plans valid.
- **Docs.** `docs/HPC.md`: "Merge (D.13)" gives the commit point; the throughput report gives the per-block OpenMP
  rule, `NATIVE_RULE`, schema `-2` and `--rederive`; the F8-d3 and F13-d3 findings get their Stage-6 status; there is a
  new S4-007 finding. `docs/PERFORMANCE.md` gets the J-SMK-4 re-derivation; `README.md` the Stage-6 status.
- **Tests run** (Mac, venv Python 3.10.12): `unit_orchestration.py --only recovery_merge`, `thru_report_test.py` (5/5),
  `test_submit.py` `test_sym_resolve`, and `OPENBLAS_NUM_THREADS=1 C8_ALLOW_NO_L8=1 make test-python PYTHON=python3`
  (exit 0 in 26 min 36 s on the final tree, 344 PASS lines, `unit_orchestration` 17/17 with `recovery_merge`). The first full run stopped at `integration_3a`'s check that val1's lists in `slurm/native_job.sh` equal `unit_orchestration.TESTS`; `recovery_merge` was added to both lists and the whole suite rerun.
- **Still to do:** the Codex inspection of these fixes; the symmetry reruns (the J-DRL-5 and J-DRL-8 re-merges, and
  J-SWEEP-2, J-BLD and J-PIL-0 as `PLAN.md:3933-3943` requires after a pinned-tool change); `verify_delivery.py
  --write`; the final val1.
## 2026-10-06 — Stage 6 fix round, group B (S3-001..013)

The accepted findings S3-001..S3-013 of the Stage-6 Codex inspection, round 1
(`LRI_C8_D3_HPC_loop/artifacts/inspect_r1_findings.md`, section S3), fixed in the pilot, design, verification and
report tools. **numerical_change: false** for production numbers: `src/`, `inputs/`, `vendor/`, `gen3/`, the Makefile,
the assembly arithmetic (`assemble.combine`), every merged table and every C8 value and SE are unchanged. The pilot and
design statistics that change are listed under each finding and summarised at the end. Every fix has a regression test
that fails on the old code (a negative control in a scratch clone with only that hunk reverted).

- **S3-001 (PC cap).** `pilot_select.proportional` takes each graph of the first fraction-per-stratum allocation only
  while it fits (the old code added that allocation unchecked), and `confirm` recomputes the selection's cost from its
  rows and refuses to publish above the cap (`check_cap`). `production.read_selection` refuses a `confirm` selection
  without a valid cap record (`pf_l8_seconds`, `fraction` ≤ 0.25, `cap_seconds`, `used_seconds`) or over it. Test:
  `tests/test_pilot_report.py` `pc_selection_fixes` (Codex's 1 s / 99 s / 50 s case at 64 seeds; the read_selection
  refusals).
- **S3-002 (joint allocation).** `confirm` allocates the flagged graphs of both sectors jointly over every stratum
  (sector × T bin × M tertile; no sector first), then the action-2b extension jointly over the triggering sectors'
  strata from what is left, so an extension never displaces screened graphs (E.8). Deterministic from the registered
  seed. Test: `pc_selection_fixes` (10 + 10 equally costly flagged graphs and room for 10: 5 + 5 at every seed, not
  10 + 0; a free 2b extension beside 4 screened power graphs).
- **S3-003 (model identity, MP factor).** `design_fallback.load_pilot` (`model_identity`) and `pilot_select.pc_costs`
  check the model's whole HD11 identity against the campaign (`production.identity_problems`: executable sha256, the
  plan host's CPU model, the MP self-check mode) and multiply every cost by `production.mp_factor` for the campaign's
  mode, as `production.py` plans. The PC selection records its pricing (`pricing`), the bundle's `design_meta.json`
  the model's CPU, mode and factor. Tests: `tests/design_fallback_test.py` `identity_and_imputation`,
  `pc_selection_fixes`.
- **S3-004 (imputation).** `design_fallback.graph_table` imputes only the variance of an unsampled graph (the stratum
  median); its cost is its own measured campaign-keyed cost × the MP factor, and a graph without one is refused. Test:
  `identity_and_imputation`.
- **S3-005 (screen and selection provenance).** `pilot_report.screen` records PF's and PA's identities (`pf_identity`,
  `pa_identity`: manifest, role, selection and every merged.json sha256; `pilot_report.campaign_identity`), and the
  PC selection copies them under `screen`. `pilot_select.py confirm --screen FILE` refuses a screen of another `--pf`
  (or `--pa`, when given) or one without identities; `pilot_report.py full` refuses a PC selection (empty or not)
  whose screen names another PF or PA, or none, or that is not a confirm selection of PF's inputs manifest. Test:
  `tests/test_pipeline.py` step 4 and step 6.
- **S3-006 (result binding).** `verify_result.bind` checks a campaign's result against the campaign: source manifest,
  every merged.json sha256, role, test_only, backend, build, numerics, MP mode, allocation and the two-loop pin of the
  inputs manifest. `verify_result.py RUN` (directory mode) and `pilot_report.verify_pf` apply it; `full` takes C8 and
  its SE from the verified, bound result. Test: `test_pipeline.py` step 6 (a PF copy whose result, still valid on its
  own, names another manifest, merged file or allocation).
- **S3-007 (combined results).** `combine.combine_batches` records the design identity (`batches.design_meta_sha256`)
  and every batch's `campaign_role` and `test_only` (`combined_from`). `verify_result.combined_check` requires them and
  every batch-count invariant: count = per_batch = combined_from ≥ 1, dof = count − 1, count ≤ planned, distinct batches,
  one role (production, or test-only), the chi-square recomputed; a final result needs the planned count of production
  batches. Test: `tests/verify_result_tamper.py` (Codex's promoted one-of-two partial and 12 more cases).
  Consequence: the two Stage-5 smoke combinations archived under
  `benchmarks/symmetry_2026-10-c8/stage5_59d4922/smk3/combine_*/C8_partial.json` (made by the old `combine.py`, test-only,
  never final) no longer verify (no design identity, no roles); `combine.py` re-run on those batches would write them
  with the new fields and unchanged numbers (the combination arithmetic is untouched; not re-run here: the batches
  live on symmetry).
- **S3-008 (error_by_loop).** `verify_result.error_by_loop_of` checks the schema (sectors free and power, loops
  3..order, rows {variance, share, se}) and recomputes every share = variance / Var(C_order) and se = √variance. Test:
  `verify_result_tamper.py` (a changed or deleted share or se, an added row key, loop or sector).
- **S3-009 (report views).** `report.py` writes `C8` and `sampling_standard_error` null for test and pilot campaigns,
  and its `assembly` is assemble.py's `test_partial` / `sizing_only` view. Test: `test_pipeline.py` step 7.
- **S3-010 (target site).** `pilot_report.target_site`: the cost table's allocated units and wall hours are on the
  lane node of C8_SITE's site (`site_shape`: allocated CPUs per node = the node's billing per hour, in which
  `tools/accounting.py` counts eta's allocated core-seconds; Expanse compute 128, symmetry amdq 64). The table records
  the site, its unit, partition, CPUs per node, the target CPU (`budget.SiteProfile.cpu`, new; equal to
  `slurm/site.sh`'s C8_CPU_EXPECT, tested) and the CPU PF was measured on. A projection to a site whose CPU PF was not
  measured on is refused unless `full --target-cost-model T` gives a measured model on the target CPU, which scales
  every per-graph cost by T's seconds per point over PF's own model's (both in PF's MP mode). Not evaluated under
  C8_SITE=fake (the Mac fakes). Test: `test_pilot_report.py` `site_projection`.
- **S3-011 (design view).** `design_adapter.py view` copies (`shutil.copyfile`, a new inode) instead of hard-linking
  before its chmod 0444, so the campaign's and the inputs' files keep their permissions; each copy is checked against
  the campaign's pins. Test: `test_pipeline.py` step 7 (source modes unchanged, new inodes, 0444 copies).
- **S3-012 (prefix_verify).** The expected (replicate, graph, points) rows come from the group's config.json, read
  only at the manifest's sha256 pin: every nested graph × replicate × prefix. Every graph-replicate needs checkpoint
  rows of the configured total covering [0, max prefix] contiguously without overlap; a structural failure is a
  reported problem (verified false), not an exception. Test: `tests/prefix_check.py` part (c) (checkpoints and
  graph_prefixes.csv gone, config.json off its pin, a replicate without rows, a duplicated task).
- **S3-013 (scheduling copies).** `design_fallback.load_pilot`, `design_adapter.view`, `pilot_select` (`pf_l8_cost`,
  `pc_costs`) and `pilot_report` (`Camp`, `subset_check`, `campaign_identity`) read campaigns with
  `production.verify_base(scheduling_copies=False)`, as D.5 ("Never a cost") lists them; `verify_result.py` directory
  mode too. Test: `tests/cost_refresh_test.py` (open spy: design_fallback report with the fresh model, design_adapter
  view and pilot_report subset-check on the prior-model sweep open no `prior_cost_model.json`).

**Changed pilot and design statistics** (no production number changes):
- PC selections (`pilot_select.py confirm`): never above the cap (a selection the old code would have overspent
  changes); when the flagged graphs of both sectors exceed the cap they share it jointly instead of free first; a
  selection with an action-2b extension draws its extension graphs after every screened graph, from a different point
  of the registered seed's stream (same distribution). With the flagged graphs within the cap and no extension the
  selection is unchanged (the random draws per stratum are identical). PC costs carry the MP factor: 1 for the runbook
  (`--mp-check on` with the site models, both measured in `on`).
- Fallback designs (`design_fallback.py freeze/report`): costs × the MP factor when the pilot's MP mode differs from
  the model's (1 for the runbook's PF); unsampled graphs (test-graph subsets, e.g. the J-SMK-3 smoke designs) take
  their own measured cost instead of the sampled median, which changes their Neyman counts, the predicted cost and
  the task-cap predictions. A PF covers every graph, so its design changes only through the MP factor.
- The pilot cost table (`pilot_report.py full`): on symmetry (C8_SITE=symmetry, amdq) the wall hours on 4 and 22
  nodes are allocated core-h / (N × 64), twice the old / (N × 128); on Expanse unchanged; allocated units unchanged;
  new `site` record. With `--target-cost-model` the busy and allocated hours scale with the target model.
- `report.py` on test and pilot campaigns: top-level `C8` and `sampling_standard_error` now null, `assembly` wrapped.
- `verify_result.py` now rejects combined results without design identity and roles (see S3-007).
## 2026-10-06 — Stage 6 fix round, group C (S1-01..07, S4-001..006)

The accepted Codex inspection findings S1-01..S1-07 (native code) and S4-001..S4-006 (inputs and gen3) of
`LRI_C8_D3_HPC_loop/artifacts/inspect_r1_findings.md`, fixed as proposed with the host's notes. **`src/` changed**:
`src/stream.hpp` (S1-04, S1-05) and `src/c8d3_inspect.cpp` (S1-07), nothing else under `src/`. **numerical_change:
false, by argument; the cluster bitwise proof is pending** (the host builds the worker on the clusters and replays it
bit for bit). Why the results cannot change:
- S1-05 replaces `(id+1)` by `(uint64_t(id)+1)` in `stream_seed`. For every int id below INT_MAX both are
  (id+1) mod 2^64 (a negative id included), so every stream seed is the same uint64; the old expression only differed
  at id = INT_MAX, where it was signed overflow (undefined). A Mac scratch check compared both expressions on 430,660
  ids (every id in [-1000, 1000], a stride of 9,973 elsewhere, the edges): equal; UBSan flags the old one at INT_MAX.
- S1-04 adds one start-index check to `Net`'s constructor (`bits < 64 && begin >> bits != 0` throws); no arithmetic
  changed. The worker already refuses every task with total > 2^bits and begin < end <= total, so its tasks never
  reach the new throw.
- S1-07 changes only how `c8d3_inspect sizes` reads its index; the per-member output is unchanged for every valid
  index.
The worker binary's bytes change (a new branch in `Net`), so its sha256 changes: every measured cost model and
baseline record tied to the old executable sha256 needs the usual refresh on the clusters.
`tests/native_static.py`'s C.9 check now expects the new `stream_seed` expression and strips exactly the one guard
line before comparing `Net` with a6ce987's.

- **S1-01 (`gen3/size_probe.cpp`).** The masks output is refused (exit 2, nothing computed or written) under C62d's
  trees, lexically and after resolving existing symlinks (the same rule as `g3common.under_c62d` and
  `regenerate_rates.cpp`), checked first and again just before the file is opened. Test: `test_gen3.py`
  `test_tool_refuse_c62d` now covers size_probe (a symlinked parent into `LRI_C8_shared/inventory`, a symlink to an
  existing file there, which keeps its bytes, the lexical c8d2 prefix; an ordinary path still written).
- **S1-02 (`gen3/regenerate_rates.cpp`).** The job list is refused (exit 2, before any file is read or written) when
  roles collide: outputs and temporaries compared as directory entries with the parent resolved through symlinks,
  existing outputs also by (st_dev, st_ino); every input followed through its symlinks (a dangling one included) and
  compared with the outputs and temporaries by path and identity; an existing `<output>.tmp` is never overwritten.
  Temporaries are created with `O_CREAT|O_EXCL` (the bytes formatted exactly as before, then written through the
  exclusive descriptor) and only those this run created are removed. The 3,512 C7(3) payloads regenerate byte for byte
  as with the old binary (Mac, both builds). Test: `test_gen3.py` `test_collisions` (seven refused job lists, the files
  unchanged; on a case-insensitive file system two outputs differing in case fail at the exclusive creation).
- **S1-03 (`tests/forced_tiers.{cpp,py}`, `tests/record_compare.py`).** `forced_tiers points` emits `breach_counts`
  (ld_scaled, quad_scaled, mp_scaled, quad_conversion, mp_conversion; their sum is `breach_count`) from its 450-digit
  comparisons, and per tier `full_precision` maxima with 17 significant digits. `forced_tiers.py` takes the status only
  from those counts and the decision mismatches (`contract_breaches`; the findings' wording unchanged) and merges maxima
  at full precision; the six-digit maxima are display values. `record_compare.py --kind forced_tiers` compares the two
  new fields when both records hold them and ignores their absence from a Stage-3 record made before them. Tests:
  `forced_tiers.py --selftest` (new, in `make test-python`), `test_opt.py` compare.
- **S1-04 (`tests/forced_tiers.cpp`, `src/stream.hpp`).** `points` checks every task row's end, `--point` every index
  and `--scan` its end against the net period 2^bits after reading the net and before any point is computed; `Net`'s
  constructor refuses a start index outside the period. Tests: the tool checks below (`range_beyond_period`,
  `point_beyond_period`, `scan_beyond_period`).
- **S1-05 (`src/stream.hpp`).** `stream_seed` uses `uint64_t(id)+1` (above).
- **S1-06 (`tests/forced_tiers.{cpp,py}`).** The task file is parsed explicitly: an optional worker header (C8D3TASKS1
  <order> <L> <nt> or C7D3TASKS1 <L> <nt>, first non-blank line only; its L must be the run's and nt the row count),
  then rows of exactly six unsigned integers with begin < end <= total, a new uid and graph <= INT_MAX; anything else
  exits 2 naming the line. The summary reports `rows`; `run_points` requires exactly the rows and points it asked for.
  `forced_tiers.py` runs these tool checks on the built executable before sampling (recorded as `tool_checks`) and with
  `--selftest --exe`.
- **S1-07 (`src/c8d3_inspect.cpp`).** `sizes` reads one complete four-field record per non-blank line (a missing,
  malformed or trailing field is an error, also in the last line) and refuses an empty index. Test:
  `tests/inspect_check.py` `index_part` (cluster, with `bin/c8d3_inspect`).
- **S4-001 (`gen3/g3common.py`, `gen3/gates_d3.py`, `gen3/run_d3.sh`).** Before anything of an H1 copy runs, the
  package's own `g3common.h1_code_snapshot` authenticates its code: MANIFEST.json at the external pin, SHA256SUMS at the
  MANIFEST's `sha256sums_sha256`, every file under `src/` at its SHA256SUMS row (equal to `gen_sources_sha256`), no
  unlisted file, directory, link or special file there (a module next to the verifier would be imported first); then
  `src/gen/` is copied into a private snapshot whose bytes are checked again, and only the snapshot runs. `h1-copy`
  does this for a new and for a reused copy (`h1_code_authenticated` in `h1_copy.json`); the new `gates_d3.py h1-auth`
  does it for `run_d3.sh` (verify step: snapshot into `$WORK/h1gen/src`, the verifier run from it; builders step:
  `--check`, then the build from the snapshot). The real H1 tree (46341a3c…) authenticates (28 code files). Tests:
  `test_tool_h1_copy` (a replaced verifier in a reused copy and in the source, a module beside the verifier: refused,
  nothing run; `run_d3.sh` stops at its verify step; `h1-auth --check` refuses an extra or changed snapshot file);
  the fake H1 trees of the tests now carry H1's checksum chain (`fake_h1_tree`).
- **S4-002 (`gen3/gates_d3.py`).** `run_tool` (gates 2, 4, 5, 7) gives each invocation a unique temporary `--output`;
  only a fresh JSON object with a boolean `passed` is published (one rename) and read; otherwise a record left by an
  earlier invocation is set aside as `<name>.superseded`. Every gate-5 check requires exit 0 and that fresh record. (A
  failing supplementary (e) makes forest_check exit 1, so (c), (d) and the certificate now also read false; before,
  the gate record already failed in that case.) Test: `test_tool_gate5_logic` (Codex's case: `L8_summary.json`
  missing after a passing run).
- **S4-003 (`tools/prepare_inputs.py`, `tests/c8pkg.py`; test inputs never pass as production inputs).**
  `prepare_inputs.verify()` turns a manifest's `test_inputs` marker into a test-only reason wherever the tree lies.
  `plan_inputs()` requires `inventory_complete()` for any plan that stays non-test: the inventory must hold exactly H1's
  `selection.json` kernels at L7 and L8 (H1's own pin, each row at its `MEMBERS_d3.sha256` hash, the primitive flags),
  C7(3)'s L3-L6 at a6ce987's pack pins, and the manifest's counts. The only exception is tests/c8pkg.py's synthetic
  scratch inputs (manifest `synthetic` exactly `prepare_inputs.SYNTHETIC_INPUTS_LABEL`, neither the H1 nor the d3 pin):
  they skip the check so the orchestration suites can still make non-test plans, and the skip is recorded in the gate
  result. `prepare_inputs.py mini --out` and `mini-materialize --to` refuse a destination overlapping the package
  inputs/ (equal, inside, containing or symlinked) before anything is read or written. Tests: check_inputs.py (five
  checks, the synthetic exception's bounds among them), inputs_l8_test.py (`mini --out inputs` with the L8 packs
  present). tests/plan_gate.py's Stage-2b simulation keeps the real L8 rows so it stays a complete state.
- **S4-005 (`tools/benchkit.py`, `tools/opt_speed.py`, `tools/prepare_benchmarks.py`; benchmark inputs verified first).**
  New `benchkit.verified_inputs` runs `prepare_inputs.verify` (every pinned file, the Stage-2b chain, the vendored pins)
  and parses the inventory from the bytes checked against its pin. `opt_speed.py` calls it before creating, selecting
  or running anything (exit 65 on failure), records `inputs_verified` (manifest, inventory and gamma hashes, skipped
  packs, test-only reasons), and marks inputs with a test-only reason as smoke. `prepare_benchmarks.build_fixtures8`
  verifies before any selection and writes the verified hashes as the fixture pins; the committed fixtures8 still
  rebuild byte for byte. Tests: test_opt.py and test_profiling.py `inputs_verified` (a gamma changed by one digit or an
  edited inventory is refused); their mini inputs are now materialized with `materialize_mini`.
- **S4-004 (`gen3/gates_d3.py`).** `replace_if_unchanged` is gone. `decisions-ack` makes the duplicate check, then one
  `O_APPEND` write of the new line while the file still holds exactly the bytes read (checked through the descriptor),
  and requires old + line afterwards (else exit 1; the line is never repaired). `handoff-gate6` swaps by take-aside
  compare-and-swap: `rename(p, aside)`, compare the aside bytes with the bytes read, `link(new, p)` (fails if p was
  recreated), `unlink(aside)`; on a mismatch or failure the aside is restored only while p is absent, a newer p is never
  overwritten (the aside is then kept and named), exit 1. The HANDOFF is absent for an instant between the rename and
  the link (documented in the module text). Test: `test_tool_report_back_concurrent_owner_writes` (in-process owner
  writes at the tool's own write; temporary directories only).
- **S4-006 (`gen3/check_dimension8.py`).** Every number a comparison reads (the B2 strings of the three files, the
  gamma rows' tokens 2..9) must be a finite decimal string (`g3common.NUM_RE`); every recomputed reference value must
  be finite (and non-zero where it divides); every difference must be finite and within its tolerance. A non-finite
  or malformed value is an explicit failure of its check, never a traceback. The package inputs still pass (worst
  differences unchanged). Test: `test_tool_check_dimension8_lengths` (Codex's case: the seventh B2 string "nan"; also
  "inf", "-Infinity", "abc", "1e", a historical "nan", gamma tokens 2, 3 and 9).

Also: `docs/HPC.md` (J-H1-COPY and the gen3 tool list: the S4-001 authentication and `h1-auth`); the Makefile's
`test-python` runs `tests/forced_tiers.py --selftest`. `DELIVERY_MANIFEST.json` and `SHA256SUMS` are not regenerated
here (`tools/verify_delivery.py --write` after the merge).
## 2026-10-06 — Stage 6 fix round, group A (S2-001..006, F7)

**numerical_change: false.** No file under `src/`, `inputs/`, `vendor/`, `reference/` or `cost_models/` changed: every
native row, checkpoint, merged batch and assembled number is unchanged. Changed: `tools/` (`slurm_submit.py`,
`production.py`, `common.py` and `lanes.py` are pinned tools, so a campaign planned with the earlier tools must be
re-planned; `budget.py`, `seeds.py`, `sweep.py`), `slurm/` (`site.sh`, `common.sh`, `plan.sh`, `lane_worker.sh`,
`native_job.sh`), `tests/`, `docs/HPC.md`. Codex inspection round 1, section S2
(`LRI_C8_D3_HPC_loop/artifacts/inspect_r1_findings.md`), with the host's dispositions, and C62d's F7. Mac only;
`tools/verify_delivery.py --write` must run before the commit.

- **S2-001: one CPU vendor per campaign, durable.** A campaign's first work admission (`lanes N`, `lanes 0`, `submit`,
  `window` or `resubmit`, past every check, before its first `sbatch`; never a dry run) writes `RUN/cpu_vendor.json`
  (schema `c8-d3-cpu-vendor-1`: `amd` or `intel`, the command, time, host, manifest sha256) under the session lock,
  exclusively (`O_EXCL`, fsynced). Every later admission refuses (64, nothing submitted) new jobs, or live jobs of the
  campaign in its snapshot, of another vendor: also a `resubmit` that brings only its merge on live elements (the
  finding's case); an unreadable pin 69 (`slurm_submit.py` `campaign_vendor`, `vendor_check`, `pin_vendor`, the
  `pin` hook of `Call.run`). Job side: `slurm/site.sh` `c8_vendor_guard`, run by `slurm/common.sh` right after the CPU
  pin, exits 68 on a node of another vendor than the pin (`vendor_id`), before any scratch, claim or output.
  Checkpoints record their CPU (`runtime.fingerprint.cpu_model`), so `production.py merge` refuses checkpoints of
  several vendors before anything is published (parallel: across every group it merges; `--serial`: all groups
  checked first). Tests: `lanes_tests.py` `vendor_pin` (entry points on the fake Slurm; the mixed-vendor merge),
  `integration_3a.py` `test_vendor_guard` (lane_worker.sh, merge.sh, run_array.sh), `test_submit.py`
  `test_vendor_rule`.
- **S2-002: seeds reserved before publication (HD6).** `production.py plan --reserve-seed LOG` re-reads the seed log
  under its own lock (the session lock; on symmetry the NFS home's) after every check and before anything is built or
  published, and appends an entry keyed by the campaign's resolved directory (`seeds.reserve`). A retry of that
  directory is idempotent (`present`); a plan that checks seeds (`--forbid-seeds-from`: every non-test plan and sweep)
  refuses (65) a seed the log holds for another directory, or a derived-seed collision; the entry is never removed.
  `slurm/plan.sh` passes `$C8_SEEDS` (and no longer runs `seeds.py add` afterwards), `tools/sweep.py --reserve-seed`
  passes it to its plan, and `native_job.sh`'s `sweep1`/`sweep2` pass `--reserve-seed $C8_SEEDS`. The mirror rule is
  unchanged (`designs/forbidden_seeds.json` untouched). The reservation is **required wherever seeds are checked**:
  `production.py plan` with `--forbid-seeds-from` and without `--reserve-seed` naming one of those logs is refused
  (65) before anything is read or built (every non-test plan, every sweep), and so is `tools/sweep.py`;
  `tests/argmax_run.py` passes `--reserve-seed $C8_SEEDS` and no longer runs `seeds.py add` after its plan;
  `tests/plan_gate.py`'s hermetic request drops `--forbid-seeds-from` (its children cannot take the session lock, and
  every scenario stops at the input gate or is made test-only by it); `unit_orchestration.Env.plan` reserves in a
  per-call copy of the log it checks, so the shared test logs never grow; `test_seed_logs_two_sites`'s symmetry plan
  now passes the mirror check and stops at symmetry's lock (69 on the Mac). **Deviation:** a test-only plan that
  checks no seed (no `--forbid-seeds-from`: the J-SMK-1 twins, `prefix_check.py --real`) neither checks nor needs to
  reserve (through `plan.sh` it registers its seed without the exclusive recheck), because those drills reuse one
  seed on purpose. Tests: `lanes_tests.py` `seed_reservations` (two concurrent `plan.sh` of one seed publish one
  campaign; an interrupted plan keeps its reservation; twins; a sweep) and `reserve_required` (a plan or sweep that
  checks without reserving, or reserves in another log, refused 65; argmax_run reserves in its plan; twins
  unaffected).
- **S2-003: `--time` in whole minutes.** `slurm_submit.resolve` normalizes the limit up to the minute (what Slurm
  reserves) before the partition check, the pricing and the intent, and submits a request with a seconds part as that
  value (`--time=<D-HH:MM:00>` after the user's tokens); elapsed-time parsing is unchanged. Test: `test_submit.py`
  `test_time_minutes` (the finding's 1-s compute job at a joint 4,999.90 is refused: 2.13 SU, not 0.0356).
- **S2-004: hard per-site sub-caps.** `budget.SITE_CAPS` (one place): the dev line's 5,000 is 2,500 on Expanse and
  2,500 on symmetry, enforced by each site's admission as a hard limit on its own projected total (its ledger and
  scheduler, no carry; `budget.gate(..., own=, prof=)`, `site_cap`); `C8_SU_APPROVED` does not lift it. The joint
  4,000 ask and the joint cap stay through `C8_OTHER_SITE_SU` and are labelled soft. The pilot line has no value yet
  and so no split. `budget.py` reports `site_caps`. Test: `test_submit.py` `test_site_subcaps` (the sum equals the
  joint cap; the finding's two-site race refused at 2,528 own); `test_su_gate_thresholds`, `test_n`, the `su`
  interleaving scenario and the requeue cases now reach the joint thresholds through the carry or bind at the
  sub-cap.
- **S2-005: plan staging.** The staging copy is `<dir>.tmp.<host>.<pid>[.<SLURM_JOB_ID>]`; another attempt's is listed
  on stderr and never removed; publication is `common.rename_noreplace` (`renameat2(RENAME_NOREPLACE)`,
  `renamex_np(RENAME_EXCL)`; where the flag is unsupported, `recheck_rename`: a recheck and `rename(2)`, which fails on
  any non-empty target), and a target created meanwhile ends the plan (1) with only the own staging copy removed. No
  mkdir claim (A-ORC-17 (k)). Test: `lanes_tests.py` `plan_staging`.
- **S2-006: held jobs released at most once.** `slurm_submit.py release` refuses a missing ledger or an unusable intent
  state (69) before any scheduler command, appends and fsyncs `release_attempt` before the scontrol `release` command
  (a failed append: 74, nothing released), records an ambiguous outcome as `release_unknown` (69; it counts as the
  attempt) and reconciles with `squeue` (`released` or `release_unconfirmed`); any later hold is cancelled. The fake
  Slurm's `scontrol release` now clears a hold. Tests: `test_submit.py` `test_held_release_once`;
  `lanes_tests.py` `lanes_submission` (actions `release_attempt`, `released`, `cancelled`).
- **F7 (ported from C62d 86e15f4): stop signals in lane mode.** `lanes.py` `StopGuard`: the worker forwards SIGTERM
  (SIGINT, SIGHUP) to its lanes and each lane to its `production.py run`, started in its own session, which stops its
  native worker and removes its runtime; the lane removes its scratch and exits 143, its claim left stale and no
  failure record. Bounded waits: `C8_LANE_STOP_SECONDS` (25 s, below KillWait 30 s) for the worker, 0.8 × that for a
  lane, then the run's session or the lane is killed and the worker removes any lane scratch of its job. The fake
  worker takes `C8_FAKE_IGNORE_TERM`. Test: `lanes_tests.py` `lane_sigterm` (exit 143 in 0.05 s; with a native that
  ignores SIGTERM, killed after 3.2 s).
- **Tests registered:** `unit_orchestration.TESTS` gains `vendor_pin`, `seed_reservations`, `reserve_required`,
  `plan_staging`, `lane_sigterm` (and `native_job.sh` val1's two lists); `test_submit.py` gains the four functions
  above.
- **Owed on the clusters:** a cross-vendor refusal drill on symmetry (an amd-pinned campaign's job on `defq`: 68; an
  Intel `lanes 0` against an amd pin: 64); `rename_noreplace` on BeeGFS and Lustre (which method each takes); a
  scancelled lane-worker drill (F7, A-ORC-8a); val1 on the fixed commit.

## 2026-10-06 — C8(3) Stage 5 on symmetry and Expanse: results, the pilot runbook, the refined pre-pilot table (docs)

The Stage-5 docs (PLAN "Stage 5", G5; Amendment A1). This is a docs-only change: **numerical_change: false**. No file
under `src/`, `tools/`, `slurm/`, `tests/`, `inputs/`, `vendor/`, `cost_models/` or the Makefile changed. The changed
files are all in the carry set that J-BLD's data-only check allows (`docs/`, `README.md`, `CHANGELOG.md`).
`docs/PILOT_RUNBOOK.md` is new, so `tools/verify_delivery.py --write` must run before the commit. Every number cites a
committed record under `benchmarks/symmetry_2026-10-c8/stage5_*/`, `benchmarks/expanse_2026-10-c8/stage5_*/` or
`cost_models/`, or a line of `LRI_C8_D3_HPC_loop/PLAN-REVIEW-LOG.md`. Numbers derived from those records are marked [M]
with their rule.

- **`docs/PILOT_RUNBOOK.md`** (new; A-SMK-5). The symmetry form of PLAN "Pilot (Stage 7)":
  - J-PIL-0's PA plan (570565: 2,733 L8 graphs, selection sha256 `225e0d62…`, 21 jobs, 32.13 busy core-h, measured
    basis, `cost_identity` ok);
  - the expected spend on the symmetry model: default 217.99 busy core-h, 441.43 with every branch;
  - the exported submit lines: `slurm_submit.py lanes 3/4/2` for PA/PF/PC under the H11 window's `amd_nodes=5`, plans
    through `slurm/plan.sh`, and the `pilot_report.py` and `pilot_select.py` lines verbatim from
    `tests/fixtures/runbook_stage7_pilot_tools.txt`;
  - the gates A-PIL-1..6 and G7, with the F25 thresholds and the stop rules.

  Still to be agreed: the H11 window and the pilot core-h line; and the PA re-plan that Stage 6 forces once F8-d3's
  fix changes `production.py`. J-PIL-0's `lanes 2/3 --dry-run` passed.
- **`docs/HPC.md` "Stage 5 results (2026-10-06)".**
  - What ran where, with jobs, nodes, verdicts and evidence, on both sites.
  - The drills J-DRL-1..9 and their outcomes, and the real parts of A-ORC-9 and A-ORC-14.
  - Findings F8-d3 (the re-merge after a recovered index; J-DRL-5 570487, J-DRL-8 570490) and F13-d3 (A-ORC-13's
    own-bytes model omits the reaped native child's reads; rchar = 2.001 × staged + 32.8 MB).
  - The symmetry facts learned in Stage 5: `/bin/sh` is bash; BeeGFS hard links across directories; BeeGFS's lazy
    directory `st_size`; the CPU map of the evidence; Slurm refusing a user requeue of a `--no-requeue` job.
  - The dev line at its last committed snapshot: 2,441.06, of which symmetry's own is 1,180.93 and Expanse's carry
    1,260.13.
  - The pending list. The "Operations" stub now points to this section.
- **`docs/PERFORMANCE.md` "C8(3) Stage 5".**
  - J-L8SELF-sym: ×1.366 at 8 x 8 on EPYC 7543 (free ×1.461, power ×1.227; rows equal to Expanse's).
  - J-SMK-4's A-PERF-3 table: busy 0.937, OpenMP 0.990, throughput ×1.005 of the J-L8SELF reference, L8 speed ×0.994
    of the sweep's, sizing 115.47 core-h; A-ORC-5 PASS, A-ORC-13 FAIL.
  - A-PERF-4: both refreshes; κ measured from the models (symmetry free 3.91 / 3.92, power 3.66 / 3.50, inside the
    RECON's bands) [M]; the refined pre-pilot table from J-SMK-3a's `design_fallback.py report` (19,391 allocated
    core-h at target SE 1.5 with the 1.5 margin, 689,352 at 0.216), beside J-DES-5's freezes and the RECON's
    projection.
  - A-PERF-5 per site: symmetry ×1.366 on the L8 sample. Expanse ×1.718 (G4b), and per (sector, L) from the two
    Expanse sweeps [M]: L8 free ×1.65 / ×1.58, power ×1.29 / ×1.25; L7 free ×1.34, power ×1.10 / ×1.07.
- **`README.md`.** The status of Stage 5, the pending items, and the new doc and evidence folders.
- **Completed after the draft (2026-10-06):**
  - J-SMK-3 batch B 570551 and R-SMK3 570595 (A-SMK-3 pass). Batch B's merge first stopped at the CPU guard (68) on
    <NODE> (570552) and <NODE> (570589), both EPYC 7532 not yet listed, and passed on <NODE> (570593).
  - J-PIL-0's `lanes 2/3 --dry-run` (pass).
  - J-DRL-10 and its close by the user decision PLAN-REVIEW-LOG.md:667 (A-ORC-17 real pass).
- **Open for Stage 6** (`LRI_C8_D3_HPC_loop/artifacts/G5_TABLE.md`): the fixes of F8-d3 (A-ORC-4 (i)) and F13-d3
  (A-ORC-13), <NODE> and <NODE> into `budget.SYMMETRY.cpu_exclude`, and the final val1 on the last code commit.

## 2026-10-06 — The Stage-4a fixtures keep their own Stage-3 cost model

Stage 5's Expanse calibration refresh (`native_job.sh sweep2` on Expanse, then a data-only commit) replaces
`cost_models/gmp_expanse_epyc7742_c8.json` with the final binary's model. `benchmarks/fixtures8` (the Stage-4a profiling
fixtures of the Stage-3 baseline) named that live path for its cost model (sha256 `fc78fc8f…`, executable `24adff54…`),
so `tests/test_profiling.py` `fixtures` (pin) and `determinism` (rebuild) and `prepare_benchmarks.py --order 8 --check`
would have failed after the refresh: `make test-python` red. **numerical_change: false**: `src/`, `inputs/`, `vendor/`,
the Makefile and every fixture task and net file are unchanged; no tool computes anything differently.

- `tools/prepare_benchmarks.py`: `FIX8['cost_model']` is J-SWEEP-1's committed evidence copy
  `benchmarks/expanse_2026-10-c8/stage_3b/8b8778273bd9/sweep1/gmp_expanse_epyc7742_c8.json` (the same bytes, sha256
  `fc78fc8f…`; the folder of `FIX8['promotions']`), so a rebuild never reads `cost_models/`. Not a copy inside
  `benchmarks/fixtures8`: the 2.17 MB model would break the folder's committed size bound (< 2 MiB, `fixtures`).
- `benchmarks/fixtures8/manifest.json`: `cost_model.path` names that file; no other byte changed. Its sha256 goes from
  `becacd70…` (the Stage-4a manifest that the Stage-4a profiling records cite) to `dedc515f…`; `--check` rebuilds it byte
  for byte (scipy 1.11.1, nets compared).
- `tests/test_profiling.py` `fixtures`: also asserts that the path is `FIX8['cost_model']` and not under `cost_models/`,
  that the model's sha256 is `fc78fc8f…` (a literal pin; before, only the manifest's own value), and that the manifest
  with the old path put back hashes to `becacd70…` (every other byte is the Stage-4a manifest's). `determinism` is
  unchanged (byte-identical rebuild).
- Readers of `cost_models/gmp_expanse_epyc7742_c8.json` kept as the live site model, unchanged: `tools/opt_speed.py`
  `DEFAULT_MODEL` (lane LPT of the A-PERF-2 speed runs), `tests/test_opt.py` `sample`, `tests/drill_select_test.py`,
  `tests/integration_3a.py`, `slurm/site.sh` and `slurm/native_job.sh` (`C8_SITE_MODEL`, sweep2's PREV fallback), and the
  fake packages of `tests/c8pkg.py` and `tests/check_inputs.py` (copy `cost_models/`). `tools/benchmark.py`,
  `tools/perf_profile.py` and `tools/thru_report.py` use the seconds per point stored in the fixture manifest, not a
  model file.
- Checked on the Mac in scratch copies whose `cost_models/gmp_expanse_epyc7742_c8.json` was replaced by another valid
  model (symmetry's final-binary model, executable `8f3a36aa…`, relabelled EPYC 7742 as an Expanse refresh would be;
  sha256 `bc6d7c84…`): before this change `fixtures` (model pin) and `determinism` (16 differences) failed and
  `prepare_benchmarks.py --order 8 --check` exited 1; after it all 16 `test_profiling` tests, `--check` (identical, nets
  compared), `test_opt` `sample`, `drill_select_test` and `integration_3a` pass. `docs/HPC.md` "Stage 5" notes the rule.

## 2026-10-05 — C8(3) Stage 5 package support for symmetry

The user's Stage-5 decision of 2026-10-05 ("Fix package first", PLAN-REVIEW-LOG.md:488-504): native support for the
calibration refresh and the campaign build on either site, a 7543 node pin, J-SMK-4's report and J-DRL-9's selections,
before the Mac tests and the final J-VAL-1/3 and J-RUN1 rerun on this commit. **numerical_change: false (A-PKG-2)**:
`src/`, the Makefile's build rules, `inputs/` and `vendor/` are unchanged, so the rebuilt binaries keep their sha256 per
toolchain; no tool that computes a number changed what it computes.

- **1a, the CPU pin at submission (`tools/budget.py`, `tools/slurm_submit.py`).** `budget.SYMMETRY.cpu_exclude` lists
  the AMD nodes known not to be EPYC 7543 (<NODE>, <NODE>–<NODE>, <NODE>, <NODE>: EPYC 7532, each with its source;
  `budget.EXPANSE.cpu_exclude` is empty). `slurm_submit.amd_exclusions(prof, env)` returns cn112, then those, then
  `C8_AMD_EXCLUDE_EXTRA` (a comma list of `cnNNN`; malformed items and any value under the Expanse profile refuse, 64).
  `resolve(..., exclude=)` merges every excluded node the job's own `--exclude` does not name into its token
  (`--exclude=cn112,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>,<NODE>` by default) and refuses a `--nodelist` naming one ("<node> is
  not AMD EPYC 7543 ..."; cn112 keeps its AVX-512 text). raw, array mode (`array_vendor`, `array_specs`) and `lanes N`
  (workers and merge) compute the list before the session lock, so a refusal writes no intent. Intel and every Expanse
  partition resolve as before (no token). `slurm/sites/symmetry/{profiles.sh,env.sh.example}` document the pin and
  `C8_AMD_EXCLUDE_EXTRA`. Unknown nodes (<NODE>, <NODE>–<NODE>, <NODE>, <NODE>, <NODE>–<NODE>) stay admissible: the job
  guard catches a non-7543 among them. The pool (`sinfo`, the draft Stage-5 runbook): `amdq` = <NODE>–<NODE> and cn112,
  `amddebugq` and `amdpreq` add <NODE>–<NODE>; known EPYC 7543: <NODE>–097, <NODE>–102, <NODE>–<NODE>.
- **1b, the CPU guard in the job (`slurm/site.sh`, `slurm/common.sh`, `slurm/native_job.sh`).** `c8_site_cpu` sets
  `C8_CPU_EXPECT` and `C8_SITE_MODEL` from `C8_SITE` inside the job (symmetry `AMD EPYC 7543 32-Core Processor` and
  `gmp_symmetry_epyc7543_c8.json`, Expanse `AMD EPYC 7742 64-Core Processor` and `gmp_expanse_epyc7742_c8.json`, empty
  elsewhere; an inherited value is overwritten). `c8_cpu_guard` compares the first `model name` of
  `${C8_PROC:-/proc}/cpuinfo`, whitespace collapsed as `production.norm_cpu`, exactly with it (Intel passes on
  symmetry) and otherwise exits **68** (EX_NOHOST; new in the package) with one line naming the host, both CPUs and the
  remedy. `common.sh` runs it before the scratch (lane workers, array tasks, plans, merges, the scratch probe);
  `native_job.sh` after its argument checks and before the toolchain, scratch and evidence, and records `cpu_expect`
  and `site_model` in `environment.txt`. On Expanse every recorded CPU is EPYC 7742; a node of another class stops at
  68 (fail-safe) and is excluded with `-x`.
- **2a, `native_job.sh` mode `sweep2` (J-SWEEP-2, D.14).** In the L8 work copy: the builds, `check_build.py`,
  `sweep.py --choose-only` (`basis.log`), `sweep.py --refresh PREV --output $EV/$C8_SITE_MODEL --report
  refresh_report.json` (PREV: `C8_SWEEP_PREV`, else the export's site model, else J-SWEEP-1's; lanes `C8_SWEEP_LANES`,
  else Expanse 16 and symmetry `numa`; an inherited `C8_LANES` is ignored), `seeds.py add`, `cost_identity.py check
  --host-cpu --mp-check on`, `refresh_record.json` (both executables, PREV, the basis; fails unless plan, manifest and
  model agree), `assemble.py`, `cost_summary.py`; nothing to `$C8_STORE/baseline`; evidence `sweep2_<jobid>` (a repeat
  never overwrites). `tools/cost_identity.py check` gains `--host-cpu` and `--mp-check MODE` (HD11's three fields,
  `production.identity_problems`); without them its records and exit codes are unchanged.
- **2b, `native_job.sh` mode `bld` (J-BLD), in place.** `cost_identity.py data-only --base <code export> --data
  <export>` first (every file by sha256; only `cost_models/`, `benchmarks/` and the carry set of the user's decision
  (`docs/`, `README.md`, `CHANGELOG.md`, `designs/forbidden_seeds.json`, `DELIVERY_MANIFEST.json`, `SHA256SUMS`) may
  differ; `bin/`, `bin.bld_failed_*`, the two L8 pack links and caches are skipped), then `make link-l8`, `make
  verify-inputs`, the workers, `check_build.py`, `cost_identity.py check --model cost_models/$C8_SITE_MODEL --host-cpu
  --mp-check on`, `model_record.json`, optionally the sweep's accounting and `cost_summary --accounting`. A failed build
  or check step (`link_l8` … `model_record`) moves `bin/` to `bin.bld_failed_<jobid>` (no plan or lane uses an unchecked
  binary; PLAN risk 32); a failure of the optional bookkeeping alone keeps `bin/` (F5 below). Every other mode
  copies a built export without `bin/` and the L8 links (`copy_export`; a pristine export is `cp -a`, as before).
- **2c, site-named models.** `sweep1` writes `$EV/$C8_SITE_MODEL`, `argmax` and `argmaxre` read
  `cost_models/$C8_SITE_MODEL` (on Expanse the same paths as before); `tools/cost_summary.py` labels its busy
  core-hours with the model's own CPU (`cpu_label`: EPYC 7742 as before, EPYC 7543 on symmetry); no number changes.
- **3, `tools/thru_report.py` (J-SMK-4: A-PERF-3, A-ORC-13 real Slurm, A-ORC-5).** Read-only on a lane campaign's
  manifest, measured model, checkpoints (validated), lane and idx logs, `accounting.py --json`, an optional `--sweep`
  and node-throughput reference (a P4 record, an `opt_speed.json` for D9, or a given value) and the external hook's
  records (schema `c8-d3-host-io-hook-1`, user decision D7; the hook stays outside the package). Rules and thresholds as
  PLAN A-PERF-3/A-ORC-13/A-ORC-5, with J-SMK-4's 64-core sizing of ≥ 72 busy core-h (A1 deviation, user decision
  2026-10-05). The OpenMP rule gates the time-weighted mean of the per-block efficiencies (all and L8 blocks; the
  distribution is reported). `tests/fake_worker.py` gains `C8_FAKE_OMP_EFF` (default 1: nothing else changes).
- **4, `tools/drill_select.py drl9` (J-DRL-9).** The stage_a selection of 4 L8 graphs (per sector the cheapest
  non-zero-channel graph at 1,024 points nested at [256] and the second at 512) and the empty confirm selection, both
  self-checked with `production.read_selection` (test-only only; the empty one 65) and never overwritten.
  `tools/pilot_select.py` is untouched.
- **5, `tools/verify_delivery.py`** skips any `.pytest_cache/` component like `__pycache__/` (only that exact name),
  so `--strict` passes on a Mac tree after pytest ran and `--write` neither lists nor refuses one.
- **Review fixes (the two reviews of this change set; F1–F7).**
  - F1 `tools/cost_identity.py data-only`: `designs/forbidden_seeds.json` (the HD6 mirror, symmetry's plan floor) may
    only grow: the data tree's file must be a `c8-d3-seeds-1` log whose entries begin with every entry of the base's,
    exactly and in order (`tools/seeds.py mirror`'s rule); a removed file, a dropped, changed or reordered entry, a
    symlink or a non-log is class `refused` (listed in `refused` with the reason) and fails the check; the added seeds
    are recorded (`seeds_added`).
  - F2 `native_job.sh bld`: `C8_BLD_BASE_PKG` equal to the data export's own sha12, or a path to the same directory,
    refuses (64: a tree compared with itself passes anything), as does a base whose `tools/cost_identity.py` has no
    data-only check; the comparison runs the **base export's** `tools/cost_identity.py`, so a data export's changed
    copy of that tool cannot approve itself.
  - F3 `native_job.sh`: `opt`'s variant copy of `$C8_PACKAGE`, its copy of `C8_OPT_PREV_PKG` and `basestore`'s copy of
    `C8_BASE_PKG` use `copy_export` too (now the script's only `cp -a`), so none carries a built export's `bin/` (which
    make would take as up to date) or its L8 pack links.
  - F4 `tools/thru_report.py`: busy = Σ row seconds / (the node's **allocated** cores × W) as the PLAN defines it, the
    cores from the accounting's new `alloc_cpus` (sacct's AllocTRES cpu; one value per job, else 65) or, without it,
    the lane log's node CPU count (the widths' sum, refused after a memory-guard cut); the widths' sum is reported as
    `lane_cores` with a note when it differs. Without `--sweep` (the PLAN's comparator) the speed, so A-PERF-3, is
    INCOMPLETE, never PASS; `a_perf_3.references` records the throughput, speed and core sources. Sizing moved into
    `sizing_of` (unit-tested: 140 busy core-h on 128 cores, 72 on 64). `tools/accounting.py` attempts gain `alloc_cpus`
    (nothing else changes; not a pinned tool).
  - F5 `native_job.sh bld`: only a failed build or check (`link_l8` … `model_record`) moves `bin/` aside and prescribes
    the risk-32 loop; when only the optional sweep bookkeeping (`sweep_accounting`, `cost_summary`) failed, `bin/` stays,
    the job still exits 1 and its log names the two commands to rerun (no second J-BLD, which would refuse).
  - F6 docs: J-DRL-9's commands name the site's model file (`$C8_SITE_MODEL` exists inside jobs only); the unknown-CPU
    AMD nodes are <NODE>, <NODE>–<NODE>, <NODE>, <NODE>, <NODE>–<NODE> (`tools/budget.py`'s comment, `docs/HPC.md`, above).
  - F7 `slurm/site.sh c8_cpu_guard`: a set `C8_PROC` (the Mac tests' seam) prints one `C8: WARNING: C8_PROC=... is set
    ... TEST SEAM` line on stderr (the job's log) and the guard exports `C8_CPU_SOURCE` (marked "TEST SEAM") and
    `C8_CPU_READ`, which `native_job.sh` records as `cpu_source:` and `cpu_read:` in `environment.txt`; behaviour is
    otherwise unchanged and the tests keep their seam.
  - Tests: `tests/cost_refresh_test.py` (the seed mirror's growth rule against `seeds.py mirror`), `tests/integration_3a.py`
    (the seam warning and record, the self-base and alias refusals, the base's tool judging a tampered data export,
    the bookkeeping-only failure keeping `bin/`, basestore's and opt's PREV copies of a built export, the single `cp -a`),
    `tests/thru_report_test.py` (allocated vs lane cores, the no-`--sweep` INCOMPLETE, sizing thresholds, the core
    source refusals), `tests/test_pipeline.py` (`alloc_cpus` equals the fake's AllocTRES cpu). Negative controls in
    APFS clones (the package never reverted), each fix undone in turn: the seed rule off or its refusal dropped, the
    self-base refusal off, the data export's own tool, `cp -a` for opt's PREV, basestore's BASE and opt's variant copy,
    the lane widths as busy's cores, the speed passing against 1.0, no `alloc_cpus`, any failure moving `bin/`, no seam
    warning, no `cpu_source`/`cpu_read` record: each makes its test fail at the assertion named for it.
    `OPENBLAS_NUM_THREADS=1 C8_ALLOW_NO_L8=1 make test-python` passes again on the Mac (342 PASS lines, 21.5 min);
    `bash -n` of every changed script; `ast_scan` and `native_static` clean (A-ORC-17 (k)'s scan keeps the word
    `sbatch` out of the guard's warning).
- **PINNED_TOOLS.** Only `tools/slurm_submit.py` changes (production.py, common.py, prepare_inputs.py and lanes.py are
  untouched): a campaign planned from an export before this commit refuses submission from this one, as designed; no
  live Stage-5 campaign exists. `tools/budget.py`, `tools/cost_identity.py` and `tools/accounting.py` are not pinned,
  so a later `cpu_exclude` addition keeps existing plans valid.
- Tests (Mac): `tests/test_submit.py` (resolve and admission with the pin, the extra list and its refusals),
  `tests/integration_3a.py` (`test_cpu_guard`, the 7543/7742 cpuinfo of `test_native_job_symmetry`,
  `test_native_job_stage5`: sweep2, bld, copy_export, the site model of sweep1/argmax/argmaxre),
  `tests/cost_refresh_test.py` (`--host-cpu --mp-check`, data-only, cost_summary's label), the new
  `tests/thru_report_test.py` and `tests/drill_select_test.py` (Makefile `test-python` and `val1`'s third stream),
  `tests/test_pipeline.py` (the drl9 scenario), `tests/test_delivery_verifier.py` (`.pytest_cache`). Docs:
  docs/HPC.md ("CPU pin", the Stage-5 sections, the Stage-3b rows), README.md, cost_models/README.md.
  `OPENBLAS_NUM_THREADS=1 C8_ALLOW_NO_L8=1 make test-python` passes on the Mac (Python 3.10, about 26 min); `bash -n`
  of every changed script. Negative controls in a scratch copy (the package never reverted): with HEAD's
  slurm_submit/budget, an empty `cpu_exclude`, the exclusions computed inside the lock, C8_AMD_EXCLUDE_EXTRA ignored by
  raw, HEAD's site/common/native_job, a substring CPU match, an overridable `C8_CPU_EXPECT`, common.sh or native_job.sh
  without the guard, HEAD's native_job.sh, `copy_export` as plain `cp -a`, `bld` keeping an unchecked `bin/`, `sweep2`
  inheriting `C8_LANES`, sweep1's hard-coded model, HEAD's cost_identity/cost_summary/verify_delivery, drill_select
  without the zero-channel filter, an unweighted OpenMP mean and a 2.2 MB tolerance, each new test fails.
- Not in this commit (the host's): the Stage-5 runbook rewrite, PLAN deviation lines, `docs/PERFORMANCE.md`'s tables,
  the probe of the unrecorded AMD nodes, and the Expanse consequence of replacing `cost_models/gmp_expanse_epyc7742_c8.json`
  by J-SWEEP-2-exp (`tools/prepare_benchmarks.py` FIX8 and `benchmarks/fixtures8/manifest.json` pin J-SWEEP-1's
  model; decide before that data-only commit). After the commit, `DELIVERY_MANIFEST.json` and `SHA256SUMS` need the
  usual data-only regeneration (`tools/verify_delivery.py --write`).

## 2026-10-05 — C8(3) Stage 4b complete (G4b passed)

- G4b (Expanse 54681801, `C8_OPT_STEP=final` on 02963bc) passed every exact gate: validate_full, l8self,
  thread_identity, first_error, quaddiff, and same_binary. The final binary is J-OPT-4's (`c8d3_gmp` b7db88c1…).
  Cumulative ×1.718 over the Stage-3 baseline on the L8 sweep sample (free ×1.970, power ×1.397), with the same rows.
- Kept: R5a (parallel NUMA-local graph load) and #4 (inline binary128 add/sub/mul).
- Reverted or not merged: R5b, #6 and #8.
- The opt-in #7 (`-O3 -march=x86-64-v3`) is exact and ×1.023. It stays off.
- `benchmarks/expanse_2026-10-c8/stage_4b/derive_stage4b.py` reports G4b on its own (final vs last kept, cumulative,
  #7). Before, it ran the step rule on it.

## 2026-10-05 — C8(3) Stage 5 on symmetry: J-E0-sym repairs

J-E0-sym (`C8_JOB=val1` of `slurm/native_job.sh` on export 02963bc, symmetry `amddebugq` <NODE>, job 570281; evidence
`benchmarks/symmetry_2026-10-c8/stage5_02963bc/val1/`) failed 11 steps in four classes; its 10 `SITE_REFUSED` steps are
the expected Mac fakes. Every safety check stays as strict (the HD6 seed rule, the site refusals, the session lock, the
fail-closed input pins, the vendored files); no tool, worker, input, binary or number changes.

- **The L8 packs (`check_inputs`, `class_b`, `workflow`, `staging`).** Latent since Stage 2b: `val1` built in the
  node-local copy of the export, which holds no L8 packs (not in git), while `inputs/manifest.json` pins them since
  b558898, so the fail-closed rules refused (`check_inputs`' "the L8 packs are present … or C8_ALLOW_NO_L8=1",
  `members.extract_to` on `free_L8.pack`, `verify()`'s "free_L8.pack: missing (pinned by …)"). Stage 3b (d730046)
  closed the Stage-2b open item for its own jobs only; no Expanse `val1` ran after Stage 2b, so Stage 5's final J-VAL-1
  would have failed the same way there. `slurm/native_job.sh`: `val1` joins the L8 work-copy jobs, like `val2` (which
  ran the same four tests with the packs on Expanse): its copy is `$C8_ROOT/work/val1_<id>`, `make link-l8
  STORE=$C8_STORE` runs before the builds (`packs_listing.txt` to the evidence), and the copy is kept when a step fails
  and removed after a full pass. On symmetry the store must hold the two pinned blobs and BeeGFS must allow a hard link
  across directories (a probe before the rerun: docs/HPC.md "Before Stage 5 on symmetry").
- **The HD6 mirror in the tests' scratch packages (`uo_allocation`, `uo_selection_files`, `uo_atomic_and_guards`,
  `prefix_check`, `test_pipeline`).** A symmetry node is symmetry for `production.py` and `seeds.py` by its BeeGFS
  mount whatever `C8_SITE` says, so the scratch packages' non-test plans ran A1's mirror check, and `tests/c8pkg.py`
  copied no `designs/` ("the package mirror …/pkg/pkg/designs/forbidden_seeds.json is missing"; `pkg/pkg` is
  `unit_orchestration.Env`'s layout); `test_pipeline`'s `seeds.py init` without `--from` was refused (64) before its
  first fake-site call. Tests only: `c8pkg.make` copies `designs/forbidden_seeds.json` as every export carries it;
  `unit_orchestration.Env` and `test_pipeline.Pipe` start their seed logs with `seeds.py init --from` the mirror (as A1
  requires of symmetry's `$C8_SEEDS`); `seed_logs_two_sites` gives its gap and Expanse plans an explicitly empty log.
  `production.py`'s and `seeds.py`'s rules are unchanged, and the HD6 refusal is not a `SITE_REFUSED` text.
- **`integration_3a`'s mkdir shim (`test_native_job_symmetry`).** The shim refused every `/local1` and `/scratch` path,
  and on a node the test's own temporary tree lies under the job's `TMPDIR` there (`/local1/<USER>/job_570281/tmp/…`;
  on Expanse `/scratch/$USER/job_<id>/tmp`, so every Expanse `val1` since 36a13a9 would have failed too): case (2) died
  at 74 creating its own fake scratch. The shim now exempts the test's own tree by name (`C8_TEST_OWN`; `..` refused;
  unset refuses everything) and still refuses and logs `/local1/$USER/job_4242` and `/scratch/$USER/job_4242`. The fake
  job's environment also drops `BASH_ENV`/`ENV`, exported shell functions, `CPATH`, `PYTHONPATH`/`PYTHONHOME` and
  `MAKEFLAGS`/`MFLAGS`, and its `PATH` is the shims plus `/usr/bin:/bin` (no real Slurm client). Case (2) now also checks
  the `val1` work copy: `make link-l8 PYTHON=python3 STORE=$C8_ROOT/store` before the builds, `link_l8` PASS,
  `$C8_ROOT/work/val1_4242` kept (a step fails) and no node-local copy.
- **Tracked bytecode (`vendored_isolated`, 14/15).** 03e1e7e committed `tools/__pycache__/{benchkit,common}.cpython-310.pyc`
  (Mac bytecode; the repository had no `.gitignore`), so every export since carries them and `vendored_isolated`'s
  after-check ("no bytecode" anywhere in the export) failed, with a detail that did not name them. The two files are
  deleted (the fix commit must stage the deletion), a root `.gitignore` keeps `__pycache__/`, `*.pyc` and
  `.pytest_cache/` out, and the check's detail now lists the bytecode paths (the condition is unchanged). Because
  `.gitignore` is a new payload file, `DELIVERY_MANIFEST.json` and `SHA256SUMS` need the usual data-only regeneration
  (`tools/verify_delivery.py --write`) after the commit.
- Docs: docs/HPC.md (the `val1` row, the Stage-3a and Stage-3b work-copy paragraphs, where the test campaigns' scratch
  lives, the symmetry native-jobs bullet, J-E0-sym's preconditions, the vendored paragraph).
- Tests (Mac, Python 3.10): `make test-python` (with `C8_ALLOW_NO_L8=1`) passes (about 21 min); `check_vendored.py
  --no-review-record` 24/24; `vendored_isolated.py --in-place` on an export of HEAD with these changes 15/15. The
  symmetry conditions were emulated in scratch copies: `integration_3a` with `TMPDIR` under an emulated `/local1` (and
  an emulated Expanse `/scratch`) passes 5/5; with `ledger.host_sites` reporting a symmetry host, `uo_allocation`,
  `uo_selection_files`, `uo_atomic_and_guards` and `prefix_check` pass and `test_pipeline` ends with the
  `SITE_REFUSED` text. Negative controls, all failing: HEAD's tests under the same emulations, with <NODE>'s messages
  (the mirror "pkg/pkg/designs/forbidden_seeds.json is missing", the `init` refusal, the mkdir shim's 74); the new
  `integration_3a` with HEAD's `native_job.sh` (no `make link-l8`, the node-local copy); `vendored_isolated` on HEAD's
  export (14/15; the new detail names `tools/__pycache__/{benchkit,common}.cpython-310.pyc`).

## 2026-10-05 — C8(3) Amendment A1 addendum L: the symmetry session lock on the NFS home

User decision 2026-10-05 (PLAN-REVIEW-LOG, "Amendment A1, addendum L"). BeeGFS on symmetry checks `flock()` on the
local node only (`tuneUseGlobalFileLocks = 0`), and the session lock is also taken inside jobs on compute nodes, so
it moves to the NFS home.

- `tools/ledger.py`: on a symmetry host the lock is `SYMMETRY_LOCK_DIR/c8d3.lock` (`<HOME>/c8d3/locks`);
  `C8_LOCK` may name only that. `mount_check(site='symmetry')` requires NFS (`nfs`/`nfs4`) with `local_lock=none` and
  without `nolock`, and refuses (69) BeeGFS and everything else; the BeeGFS client-configuration reader is gone. On NFS
  `flock()` is a per-process POSIX lock, so `SessionLock` refuses (69) a second acquisition in one process while the
  first holds it (symmetry only). The lockprobe records the `/mnt/beegfs` and `/home` mount lines.
- Tests: `test_ledger.py` `mount_check_symmetry_lock_on_nfs_home_beegfs_refused_one_holder_per_process_…` (fails with the
  guard removed) and `lockprobe_symmetry_mount_step_refuses_beegfs_and_passes_on_the_nfs_home`; `test_submit.py`'s
  symmetry site locks on a fake NFS mount, and `symmetry_admission_refused_at_the_lock_when_it_is_on_beegfs`.
- Docs: docs/HPC.md "Session lock" and "Before Stage 5 on symmetry", `slurm/sites/symmetry/env.sh.example`,
  `slurm_submit.py`'s docstring.

## 2026-10-05 — C8(3) Stage 4b decisions and F12 (exact pack-member reads)

- **Stage 4b, J-OPT read back** (Expanse, after the maintenance): R5a (parallel NUMA-local graph load, 36ec1c1/81238c8)
  exact, 1.186x, kept; #4 (C62d's R3a inline binary128, 9fa9421) exact, 1.452x, kept; #6 (lock-step first pass,
  33f4661) exact, 1.021x < 1.03, reverted (46475ca). R5b (lane shape 16 x 8) timed out in its export copy (Lustre
  after the maintenance: 36 min for a copy that took 51 s that morning) and was resubmitted; #8 (uint8 rates, branch
  `opt-8`) submitted. Records: `benchmarks/expanse_2026-10-c8/stage_4b/`.
- **F12, ported from LRI_C8_D2_HPC d5dfd38** (C62d's finding on symmetry's BeeGFS): every reader of pack members,
  `production.stage_members`, `stage_runtime.stage`'s member copy, `members.extract_to` and `benchkit.stage_members`,
  read through Python's buffered reader, whose buffer is st_blksize (524,288 bytes on BeeGFS) and which refills one
  whole buffer after each seek, so it read up to 512 KiB of neighbouring pack data per member (0.7 bytes per staged
  byte at L8 on symmetry). Now `common.read_member` reads exactly the member with `os.pread` in a loop over short
  reads; the staged bytes and their sha256 checks are unchanged. New `tests/pack_reads_test.py` (in `make
  test-python`): counted `os.pread` on a fake pack with members around and above 512 KiB, short reads, a truncated
  pack (refused, no descriptor left open), EOF, the pack never opened with `open()`, and C62d's buffered-reader control
  (the pre-fix read of the same members reads 1.24 bytes extra per member byte); `tests/staging.py` runs
  `stage_runtime` under the same read spy. Each check fails on the pre-fix reader. No src/ change; no output changes.

## 2026-10-05 — C8(3) Amendment A1, repair round 2: native jobs on symmetry, the per-site baseline, the carry's asof, Intel arrays

Fixes of the A1 review (round 2). Code, Mac fakes and docs; no symmetry job (the BeeGFS lock still refuses: <NODE> reads
`tuneUseGlobalFileLocks = 0` at 18:28 UTC).

- **Native jobs on symmetry** (major; `slurm/native_job.sh`, new `slurm/site.sh`): the script that runs J-E0-sym (`val1`),
  J-E1-sym (`run1`) and the exact gates was Expanse-only. It computed its scratch as `/scratch/$USER/job_<id>` (symmetry
  sets no `SLURM_TMPDIR`, and `/scratch` there is root's), expanded `$C8_GMP` under `set -u` (unset on symmetry: "C8_GMP:
  unbound variable" before any build), passed check_build Expanse's toolchain (g++ 13.3.0, a Spack GMP RPATH) and
  matched the SITE_REFUSED text "this host is Expanse" (which A1's ledger message, "this host is expanse", no longer
  matched on Expanse either). Now every job script takes the site's rules from `slurm/site.sh`: `c8_set_scratch`
  (`$SLURM_TMPDIR`, else `/local1/$USER/job_<id>` on symmetry, `/scratch/$USER/job_<id>` on Expanse; 74 when it cannot
  be made; used by `common.sh`, `native_job.sh`, `inputs_job.sh`, `gen_d3_0.sh`, `gen_d3.sh`, `h1_copy.sh`;
  `scratch_probe.sh` states the expectation itself), `c8_toolchain_args` (symmetry: g++ 11.4.0, Boost 107700, the system
  GMP 6.2.1 in `/usr/lib/x86_64-linux-gnu`, `--gmp-search system`; Expanse unchanged and `$C8_GMP` required with a
  message; any other site 64) and `c8_site_refusal`. `tests/check_build.py --gmp-search system` (and
  `libprobe.gmp_problems(search=)`) drops only the RPATH requirement; ldd and the loader must still resolve the expected
  file at the expected version. `val1` now also runs `unit_orchestration`'s `seed_logs_two_sites` (missing from its
  stream and from its completeness list since repair round 1, so `uo_list_complete` would have failed).
- **The c8-stage3 baseline per site** (`tools/baseline.py`, `native_job.sh`): `--site`/`C8_SITE` picks
  `reference/baseline_c8_stage3.json` (Expanse) or `reference/baseline_c8_stage3_symmetry.json` (symmetry; not yet
  recorded, so every reader refuses 65); `baseline.py sha` gives the profile and speed jobs their B0 (no more literal
  24adff54 in `native_job.sh`), `baseline.py val3` the site's J-VAL-3 record for the `forced_tiers` gate; `record --site
  symmetry` needs that record. New `C8_JOB=basestore` (J-BASE-sym): the c8-stage3 commit's export (`C8_BASE_PKG`) built
  and check_build-checked with the site's toolchain, stored read-only in `$C8_STORE/baseline/<sha12>/`. docs/HPC.md
  documents the symmetry store's staging (run1 archive, c7d2_frozen, H1 copy, d=3 payload, L8 packs, baseline).
- **The carry's asof** (`tools/budget.py`): stamped at the reader's first read (the intent-file scan) instead of the
  snapshot, so an admission missing from `own` (intent appended after the ledger read, job accepted after the
  unfiltered sacct) always postdates `asof` and the refresh rule covers it; `carry_asof_utc` in `--json`.
- **Intel arrays** (`tools/slurm_submit.py` `array_vendor`): on symmetry array mode (`submit`, `window`, `resubmit`)
  refuses (64, before the lock) windows or a merge on `defq`/`debugq` unless the plan's `plan_role` is `campaign`.
- **Decisions before Stage 5 on symmetry** (docs/HPC.md): the lock options now include (d), C62d's mkdir lock
  directory, with its trade-off against D.11 and J-LOCK-0 (iv); the work list (J-LOCK-0-sym, J-SCRATCH-sym, the store,
  J-E0/E1-sym, J-BASE-sym and the symmetry J-VAL-3) and the array-mode limit under H7.
- **Tests (Mac)**: `test_submit.py` `carry_asof_is_the_readers_first_read_…` (fails on the old stamping);
  `unit_orchestration.py` `arrays_and_recovery` with a validation plan on symmetry (`-p defq`, `-p debugq`, an Intel
  merge: 64 in submit, window and resubmit; amdq and a campaign plan pass); `integration_3a.py`
  `native jobs on symmetry` (native_job.sh with symmetry's variables, fake lscpu/g++/make/python3 and a mkdir that
  refuses the node disks; fails on the old script); `check_build.py --selftest` symmetry cases; `test_opt.py`,
  `test_profiling.py` and `gen3/test_gen3.py` follow the per-site B0 and `slurm/site.sh`.

## 2026-10-05 — C8(3) Amendment A1, repair round 1: the joint line on both sites, the pilot's symmetry prices, merges, Intel, the seed log

Fixes of the A1 review (round 1). Code, Mac fakes and docs; still no symmetry job (the BeeGFS lock blocker stands).

- **The joint line (A1.3) on both sites** (`tools/budget.py`): `C8_OTHER_SITE_SU` is now required under
  `C8_SITE=expanse` as well as `symmetry` (64 while unset; explicit zeros allowed; only `C8_SITE=fake` treats it as 0),
  so an Expanse admission can no longer gate on Expanse SU alone (the review's case: Expanse at 3,990 with symmetry's
  carry now projects 4,090 + 8 and asks). A carry older than 24 h or more than 10 min in the future is refused (64).
  `budget.py` reports `own` (spent + live + intents, without the carry) beside `total` per line and prints the
  `carry` line to paste on the other site (rounded up to the cent; `carry` in `--json`), so the carry procedure is
  defined and never double-counts. The Expanse env template documents the variable.
- **The pilot's re-projection on symmetry** (`tools/pilot_report.py`): the PF/PC lane steps use the site's lane
  shape (`slurm_submit.lane_shape` of `C8_SBATCH_ARGS`, falling back to the site's lane default when it names no lane
  partition: amdq 64 cores, f_class 1, 64 core-h per node-hour; defq 40 cores, f_class 1.5, 80; at most 23:30:00) and
  the runbook's jobs are priced as whole nodes (512 core-h for the six jobs, against 168 SU on Expanse; merges on the
  lanes' vendor). Expanse's numbers are unchanged. `lane_step` reports `capped_at_tmax` and `T_lane_max` (was
  `capped_at_47h30`).
- **Merges take the node** (`budget.SYMMETRY.merge_args`, `profiles.sh`): `-p amdq -c 64 --mem=240G -t 02:00:00`
  (Intel: `-p defq -c 40 --mem=180G`), so `slurm/merge.sh` runs 64 (40) workers instead of 4; every `c8_profile`
  branch sets `C8_MERGE_SBATCH_ARGS` itself (an `intel` profile's defq merge no longer leaks into a later `lanes`).
- **Intel and the bitwise gates** (`tools/slurm_submit.py`): on symmetry `raw` admits a job on `defq`/`debugq` (AVX-512,
  like cn112) only under an `intel_*` or `drill_*` role; a campaign's merge must be on its workers' CPU vendor
  (`lanes N`, `lanes 0` against the live workers, array mode; 64 otherwise).
- **The seed log on two sites** (`tools/seeds.py`, `tools/production.py`): `add` (and the new `merge`) refuse a missing
  log instead of creating an empty one; on symmetry `init` needs `--from` a seed log that holds every seed of the
  package mirror; `merge COPY... --log FILE` folds another site's entries in (verbatim, in order, once, under the
  lock); a non-test plan on symmetry refuses a forbidden set that lacks a mirror seed. Sync procedure in docs/HPC.md.
- **Tests (Mac)**: `test_submit.py` `symmetry_core_hours_…_carry_required_on_both_sites_at_most_24h_old`,
  `symmetry_intel_admits_only_intel_and_drill_roles_merges_on_the_workers_vendor_merge_takes_the_node`;
  `test_pilot_report.py` A-PIL-2 on symmetry; `unit_orchestration.py` `seed_logs_two_sites`; the seed concurrency
  test now `init`s its log first.
- **Still blocked**: symmetry's BeeGFS clients run with `tuneUseGlobalFileLocks = 0` (re-read on <NODE>, 2026-10-05
  17:26 UTC), so no symmetry admission, J-LOCK-0-sym or symmetry baseline can run; the user decides between enabling
  global locks (the administrators), a plan revision for the lock, or Expanse only.

## 2026-10-05 — C8(3) Amendment A1: symmetry site support (`C8_SITE=symmetry`); BeeGFS refuses the session lock

Amendment A1 (`LRI_C8_D3_HPC_loop/artifacts/AMENDMENT_A1_site.md`; the user's rule "symmetry is back, so for the moment
only use expanse if symmetry is not enough"). Code, Mac fakes and docs; no symmetry job was submitted (see the end).

- **Site detection** (`tools/ledger.py`): a BeeGFS mount at `/mnt/beegfs` makes a host symmetry, whatever `C8_SITE`
  says; there every tool refuses (64) unless `C8_SITE=symmetry` and `C8_ROOT` resolves to `<SCRATCH>/c8d3`
  (`SYMMETRY_ROOT`), as on Expanse. A host that looks like both sites refuses.
- **Session lock on BeeGFS**: the mount check of every acquisition requires a BeeGFS mount whose client runs with
  `tuneUseGlobalFileLocks = 1`, read from `/proc/fs/beegfs/<client>/config` (the one client whose `cfgFile` is the
  mount's); otherwise 69. `lockprobe` records the BeeGFS version, the mount lines and the client's lock mode.
- **Admission** (`tools/slurm_submit.py`, `tools/budget.py`; one `SiteProfile` per site): symmetry admits `amdq`,
  `amddebugq`, `defq`, `debugq` (one partition per job); refuses `longq` always, `preq` and `amdpreq` (preemptible with
  requeue, every job carries `--no-requeue`), `sharedq` and the rest; `-A` absent or `<USER>`; every AMD-pool job gets
  `--exclude=cn112` merged into its own `--exclude` (a `--nodelist` naming cn112 is refused). H7 caps from
  `C8_RESERVATION="mode=reservation;id=H7;amd_nodes=4;amd_total=8"`: live `c8d3-` nodes on amdq + amddebugq + amdpreq
  (pending included) + intents + k ≤ `amd_nodes` (`C8_COMPUTE_CAP` only lowers it) and, with the live `c8d2-` AMD-pool
  nodes, ≤ `amd_total`; the pilot window's re-split (5 / 3, total 8) needs its DECISIONS id and `until`. Intel is
  outside the cap. Snapshots `squeue --all -u <USER>` (both) and `sacct -u <USER>`, in the Expanse formats (checked
  against Slurm 21.08.8's output on 2026-10-05); the state-selected `sacct` carries `-E now` there, because 21.08
  returns no row for `-s <states> -S <start>` without an end time (0 rows, against 476 with `-E now`).
- **Accounting (A1.3)**: allocated core-hours (whole nodes: 64 per AMD node, 80 per Intel node as `AllocTRES cpu=80`, or
  a record's allocated cpu when larger; a pending exclusive job's `tres-alloc` `cpu=1` is priced at the node), 1:1 with
  Expanse SU in the same dev line (ask at 4,000, cap 5,000) and pilot line. `C8_OTHER_SITE_SU="dev=;pilot=;asof=;ref="`
  carries the other site's line totals: required on symmetry, optional (0) on Expanse. Intents and `submit` records
  carry `site` and `unit`; `budget.py` prints the carry.
- **Lanes**: site defaults (`-p amdq`, merge `-p amdq --mem=240G -t 02:00:00`), auto lane time at 64 cores per AMD
  node (f_class 1) or 40 per Intel node (1.5), at most 23:30:00; drills on amddebugq/debugq. The jobs that source
  `slurm/common.sh` (lane workers, array tasks, merges, plans) use `/local1/$USER/job_$SLURM_JOB_ID` as scratch on
  symmetry. *Corrected in repair round 2:* the native, input and generation jobs (`native_job.sh`, `inputs_job.sh`,
  `gen_d3_0.sh`, `gen_d3.sh`, `h1_copy.sh`) and `scratch_probe.sh`'s expectation still used `/scratch`, so this entry's
  "Jobs use /local1" held for those four scripts only.
- **Templates**: `slurm/sites/symmetry/env.sh.example` (GCC 11.4, `boost/1.77.0`, GMP 6.2.1, `python/3.11` venv,
  `C8_SITE=symmetry`, H7 reservation) and `profiles.sh` (lanes 8 × 8 on AMD NPS4 nodes, Intel 2 × 20), replacing the
  inherited C7(3) files.
- **Tests (Mac)**: `test_ledger.py` `mount_check_beegfs_global_file_locks_only_symmetry_detection_fail_closed`,
  `lockprobe_symmetry_mount_step_…`; `test_submit.py` `symmetry_option_resolution_…`, `symmetry_admission_h7_…`,
  `symmetry_core_hours_…`, `symmetry_admission_refused_at_the_lock_…`; the fake Slurm has a symmetry mode.
- **Blocker found (STOP per the task):** symmetry's BeeGFS 7.4.5 client runs with `tuneUseGlobalFileLocks = 0` (the
  default; `/etc/beegfs/beegfs-client.conf` and the login node's runtime configuration), so `flock()` excludes only
  within one node. The package therefore refuses every symmetry admission at the session lock (69), J-LOCK-0-sym cannot
  be submitted, and the symmetry baseline (J-E0-sym/J-E1-sym) was not run. Evidence: `benchmarks/symmetry_2026-10-c8/`.

## 2026-10-05 — C8(3) Stage 4a: J-PROF-1/2/3 on the c8-stage3 baseline, the Stage 4a performance section, decisions for 4b (G4a)

Jobs (Expanse; each checks that `bin/c8d3_gmp` rebuilds to the baseline `24adff54…` before any profile): profbuild
54677088 (tool check on the export of 6593ea8, shared), then J-PROF-1 54677131, J-PROF-2 54677133 and J-PROF-3 54677135
(compute, exclusive, on the export of 03e1e7e); 163.2 SU (dev line 287.5 → 450.7). Evidence `benchmarks/expanse_2026-10-c8/stage_4a/` (README there);
numbers and decisions in `docs/PERFORMANCE.md`, "C8(3) Stage 4a".

- **P1** (perf + per-graph tier timers, re-weighted to the population): all of L8 is first pass 9.3%, binary128 60.1%, MP
  30.2%. The kernel's binary128 add/sub/mul are 89-92% of the L8 binary128 tier; divisions are 1.0-2.1%, so #4 covers
  add/sub/mul only. `calculate_reference<ld>` and the shift loop: 0 (no shifted point). MP temporaries 0.2-1.0%.
- **MP self-check**: `on` costs 1.09% more than `off` at L8, so production keeps `on`. Mode factors for E.7: `off` 0.989,
  `stride16` 0.992.
- **P2**: first-pass IPC 1.01-1.05 (latency-bound), promoted tiers 2.4-2.5; interleave probe x1.10 (promotion-free x1.04,
  heavy x1.16-1.19). #6 is a go by the IPC rule, expected <= 2.2%.
- **P3**: promotion rates as J-SWEEP-1; MP evaluations below 1e-63 are 1.8-3.1% at power L8; deepest 1e-200.
- **P4**: 16x8 best (113.4 cost-model s per node-second), 8x16 0.986, 4x32 0.979, 1x128 0.943, 2x64 0.941; rows identical
  across shapes; loading + staging 0.9% (16x8) to 6.4% (1x128).
- **f_E** = 0.96-0.99 isolated core for core against symmetry's EPYC 7532; a loaded 64-core socket adds 8-10%.
- **Clean merge**: phase 1 435,984 rows/s (16 processes), phase 2 55,105-55,975 rows/s, against the planner's 60,000 for
  phase 2. 4b lowers `MERGE_PHASE2_ROWS_PER_S` to 50,000.
- **Decisions for 4b**: R5a go (low priority); R5b `C8_LANES=16`, `--threads 8`; #4 go (add/sub/mul; projected x1.43-1.49
  at L8); #5a not attempted unless time allows (bounded near 1%); #6 go by rule, revert likely; #8 as planned (small); #7
  optional.
- `docs/PERFORMANCE.md`'s Stage 3b merge paragraph points to the clean rates.

## 2026-10-05 — C8(3) Stage 4a: profile tooling (fixtures8, perf_profile, lane shapes, interleave probe, per-graph tier timers)

PLAN "Performance plan", Profiling first (P1–P4), A-PERF-1. Tooling commit; the profile runs, `docs/PERFORMANCE.md`'s
Stage 4a section and the decisions for 4b follow in the evidence commit. Nothing on the default path changes:
`bin/c8d3_gmp` must rebuild to the c8-stage3 baseline `24adff54…` in every profile job, which checks it before any run.

- **`tools/prepare_benchmarks.py --order 8`** → `benchmarks/fixtures8/` (14 blocks and the P4 workload, < 1.2 MB;
  `manifest.json` pins the inputs, the J-SWEEP-1 cost model and the sweep's per-graph promotion counts): the plan's P1
  blocks (`strat_*`: 120 graphs drawn within 8 equal-count T bins plus the 8 heaviest, with stratum weights; L7 1,024
  tasks, L8 256 nominal), `heavy_*_L8`, `nopromo_free_L7/L8` (P2), `random_*` (P3), `p4_{free,power}_L8` (P4, production's
  60 s chunking, ~330 s of ideal node time). `--order 7` now verifies C7(3)'s committed fixtures (`benchmarks/fixtures`,
  the f_E basis) instead of calling the refusing `prepare_inputs.prepare()`.
- **`tools/benchkit.py`**, **`tools/perf_profile.py`** (`p1`, `p2`, `p3`, `mpcheck`, `fe`, `p1-reparse`) and
  **`tools/benchmark.py --lane-shapes / --interleave-probe`**: ports of C62d's Stage-4a tools (LRI_C8_D2_HPC@651c56f /
  2083d84) to d=3: c8d3 names, `--mp-check on` in every run, the d=3 ratio-histogram keys, sqrtq/sqrtl shares,
  production's two-maxima blocks in P4 (`production.cut_blocks`), the passive OpenMP wait policy in P1, the population
  re-weighting of the stratified blocks, the MP self-check overhead (PLAN C.4) and f_E (A-PERF-1) modes.
- **`benchmarks/probes/interleave_probe.cpp`**: the P2 lock-step probe with the d=3 term denominator U·sqrt(U); built by
  `benchmark.py --interleave-probe` into `bin/diag/` with the worker's command; never a worker.
- **`src/diagnostics.hpp`** (diagnostic builds only, `make profile`): the tier timers also per graph id
  (`tier_timers.per_graph`). The in-tier sub-timers of C.5 are not built (perf is available on Expanse; instrumented
  tier loops would change `src/kernel.hpp`).
- **`slurm/native_job.sh`**: `C8_JOB=profbuild|prof1|prof2|prof3` (J-PROF-1/2/3; `docs/HPC.md`).
- **`tests/test_profiling.py`** (16 tests, in `make test-python`) and **`tests/fake_perf.py`**.

## 2026-10-05 — C8(3) Stage 3b: J-VAL-2/3/4 with L8, the L=2 control, J-SWEEP-1 and the first measured cost model, J-ARGMAX, tag `c8-stage3` (G3b)

PLAN Stage 3b (needs G2b): J-VAL-2/3/4 with L8, the L=2 control, J-SWEEP-1, then J-ARGMAX on the binary J-SWEEP-1
measured, with its model; tag `c8-stage3` and `bin/baseline/`. Commits: d730046 (drivers, jobs, seeds), 8b87782 (job
tweak), 83c07fb (data only: the model and the baseline record), e72fa54 (argmax `--reinspect`), 361716f
(`cost_summary.py` eta), then this evidence commit and a data-only commit (`verify_delivery.py --write`), which carries
the tag `c8-stage3`. `src/` is unchanged since Stage 3a: `bin/c8d3_gmp` is `24adff54…` and `bin/c8d3_decimal`
`5a4d4088…` in every job. Evidence: `benchmarks/expanse_2026-10-c8/stage_3b/` and `benchmarks/expanse_2026-10-c8/argmax_L7/`
(READMEs there).

### What was built

- **`tests/thread_identity.py`** (new; A-RPL-6; the native track had not written it): an L8 free and an L8 power block
  (64 tasks × 256 points, 32 drawn kernels × 2 replicates) at 1, 16, 64, 128 threads and as 8 × 16, 4 × 32, 2 × 64
  NUMA lane processes (`tools/lanes.cpu_lanes`; 32 × 4 not applicable, no 4-core domains), each process pinned and
  writing a fresh output, both backends; chunk splits (23 points) and layouts 0/1/2 at L7 and L8 against whole tasks.
- **`tests/forced_tiers.{cpp,py}`** (A-RPL-4): each maximum carries its point (graph, replicate, index); every breach is
  listed with tier, value, evaluate()'s level, moderate/direct, the 450-digit value and err450; per-tier histograms of
  floor(log10 s); per-graph evaluate() levels. The counts now take the MP points from the points evaluate() hands to MP
  (the old stopping rule compared the MP *evaluations*, i.e. every point); "points per graph double until met" doubles
  the graphs that produce points of a short tier and evaluates only the new index range; a time budget per (sector, L)
  and a recorded shortfall.
- **`tests/point_checks.cpp`, `tests/check_points.py`** (A-RPL-5): in L8 contract mode an MP breach is recorded too (any
  A-RPL-5 bound at L8 is a finding), one JSON line per breach, kept in the record (`contract_breaches`); the binary128
  sharing identity stays hard. `tests/sanitize.py` runs the L8 point checks in contract mode.
- **`tests/class_b.py`**: part (f) (A-KER-6 (f): tail_top[0] × |norm (3 w_B − w_A)| = max_abs to 1e-18 at L8) and L8 in (a).
- **`tests/prefix_check.py --real`** (A-DES-8 (e)) with the real worker; **`tests/argmax_run.py`** (A-DES-6; `--reinspect`);
  **`tools/cost_summary.py`** (per-group cost, promotion rates and the pilot cost a model implies);
  **`tools/baseline.py`** and **`make baseline STORE=…`** (bin/baseline/, A-RPL-8's c8-stage3 baseline).
- **`slurm/native_job.sh`**: `smoke3b`, `val2`/`val3`/`val4` with L8, `sweep1`, `argmax`, `argmaxre`; the L8 jobs work in a
  Lustre copy of the export with the store's L8 packs hard-linked (`make link-l8`), which resolves the Stage-2b open item
  on node-local copies.
- **HD6**: the Stage-3b test seeds registered before use (17; `stage_3b/seeds/`), the call-site fixture extended
  (`tests/fixtures/stage3a_test_seeds.json`, `thread_identity.py` in `NET_TESTS`; a seed may serve two sites, 9907);
  the sweep, argmax and prefix_check --real seeds registered after their plans; the mirror refreshed (126 entries).
- **Docs**: `docs/HPC.md` "Stage 3b", `docs/NUMERICS.md` (the accuracy contract with its measured column),
  `docs/PERFORMANCE.md`, `cost_models/README.md`, `README.md`.

### Results (Expanse; 98.3 SU, dev line 189.25 → 287.54)

- Every gate job (J-VAL-2/3/4, J-SWEEP-1, J-ARGMAX) passed. The smoke3b tool check (54676968) ended in Slurm state
  **FAILED** on class_b --parts f (missing notail build, fixed in 8b87782; (f) passed in J-VAL-2).
- **smoke3b** 54676968 (debug, d730046; Slurm state FAILED): the new drivers on small samples pass; the class_b_f step
  failed with rc=1 because `bin/diag/c8d3_gmp_notail` was missing (the smoke built no test-builds), and `native_job`
  reported "FAILED steps". Fixed in 8b87782 (smoke3b builds test-builds); not rerun, because A-KER-6 (f) passed in
  J-VAL-2 54676971.
- **J-VAL-2** 54676971 (8b87782; shared 64 c, 28 min): all steps passed. G-C7 (A-RPL-1) on the L2 graph and all 3,773
  L ≤ 7 kernels, 40,296 rows per backend bitwise, the shift case; **G-JET (A-RPL-2) on 3,773 kernels + L2, the 262 new
  L7 included**; class_b (a)–(f) ((e) on the new zero-channel free L7 G37; (f) 64 L8 rows, max 6.2e-20); inspect_check;
  **check_points (A-RPL-5) L3–L7 hard, L8 contract mode: no breach**; check_inputs 57/57 with the L8 packs; workflow and
  staging with the real workers; compat_run1.
- **J-VAL-3** 54676975 (compute, 15.5 min): all steps passed. **forced_tiers (A-RPL-4): every count met, no breach**
  (worst at L8: ld s 4.7e-18, binary128 s 1.3e-33, MP 1.7e-366, conversions ≤ 5.41e-20, no decision mismatch;
  `docs/NUMERICS.md`); thread_identity (A-RPL-6) identical at every thread count and lane split, chunks ≤ 1.3e-18;
  G-BK8 (A-RPL-3) at L7 and L8: counters identical, rows identical; **the L=2 control (A-IN-6)**: all pulls within 4 SE
  (largest |pull| 2.31), wb/wa = 1/6, the b − 6c bound; merge_scale at 1.25 million rows (A-ORC-6: byte-identical,
  RSS 46/81 MB, phase 1 268,650 rows/s with 16 processes, phase 2 49,083 rows/s, both measured while forced_tiers ran
  128 threads and thread_identity ran too, so not clean rates (see Open); the 500-shard bounded fan-in);
  assembly_checks --exact and compat_run1 (A-ASM-3/4); prefix_check --real (A-DES-8 (e), 4.8e-21).
- **J-VAL-4** 54676973 (shared 32 c, 10.6 min): sanitize.py --selftest --parsers --runs --max-loop 8 passed (A-KER-4: 288
  sanitizer worker runs on 45 kernels L2–L8, the parser corpus, the unguarded-index self-test at kernel.hpp:148).
- **J-SWEEP-1** 54676977 (compute, 11 min): the bootstrap sweep (612 indices, 868 blocks, 8 × 16 lanes, 578 s; 7.20 busy
  core-h) → **the first measured cost model** `cost_models/gmp_expanse_epyc7742_c8.json` (48,346 keys, sha256
  `fc78fc8f…`, executable `24adff54…`, scheduled_with bootstrap); test assembly with **A-IN-7**: b_3^p(0) =
  −3.2351 ± 0.0472 against −16π/15, pull +2.46 (not flagged); the binaries stored as the c8-stage3 baseline.
- **J-ARGMAX** 54677001 (83c07fb; shared 32 c, 6 min): the rebuilt binary equals the model's executable and the stored
  baseline; `make baseline` installs and verifies `bin/baseline/`; the argmax run (A-DES-6) is recorded in `argmax_L7/`;
  `accounting.py` on the sweep. 54677011 (debug, e72fa54) re-inspected the same points with y and jac.

**The measured cost model** (`stage_3b/cost_summary_stage3b.json`; busy seconds per point, a/b): free L8 0.438/0.523 ms,
power L8 0.944/1.100 ms, free L7 0.099/0.122 ms, power L7 0.272/0.333 ms. Promotion per point at L8: binary128
0.33/0.38 (free), 0.85/0.89 (power); MP 0.022/0.039 (free), 0.29/0.37 (power); no MP self-check alarm at any of the 4.33 million MP-tier points of the 49.5 million-point sweep (worst log10(|v|/err): -191.7 power L8 b, -165.1 power L8 a, -92.4 free L8 b, -147.3 power L7; alarm at -320); at
L7: MP 0.009/0.017 (free), 0.18/0.24 (power). At L ≤ 7 order 8 costs 0.97–1.02 × C7(3)'s order-7 symmetry model.
**The first cost estimate it implies** (busy core-hours on EPYC 7742): PF (R = 8) 230.4 (L8 221.2), the R = 16 branch
+221.2, PA 39.5, PC cap 55.3; default pilot 269.9 and every branch 546.4 busy core-h, i.e. 1.01 × (PF) and 0.95 × (PA)
the plan's symmetry-basis figures; at the plan's allocated/busy 1.2 that is 276 SU (PF), 47 SU (PA), 324 SU (default
pilot) and 656 SU (every branch), against the plan's 302/55/356/718 SU central (which assumed f_E = 1.1). The sweep job's own allocated/busy was
3.26 (612 indices of a few seconds each; about 3.5 s per index outside the blocks), an artefact of the sweep's index
size and not a lane-mode figure; the pilot's stage-A report measures η. The worker's peak RSS in the sweep, 1.01 GB, is
0.66 × the plan's largest est_peak_bytes (1.57 GB).

**The argmax run** (`argmax_L7/README.md`): all 64 argmax points of graphs 228, 1357, 318, 3754 (both campaigns, R = 8,
2^18 points) are direct, moderate, long-double points with |t| = |y| (no grid); only 3 have a single scale step above
5 in log (median largest step ≈ 2, depth ≈ −9), and 10 of the 53 flag sets with a step above 2 lie inside or contain
a double-lift subset. This favours a peaked bounded weight and multi-scale chains over a single small-margin face; it
is reported to the user and C62d (the `LRI_C8_shared/PERF_NOTES.md` entry is left to the host; this workflow writes
nothing there).

### G3b checklist

| Item | Evidence |
|---|---|
| A-KER-4 | J-VAL-4 54676973 (`stage_3b/8b8778273bd9/val4/`) |
| A-KER-6 (f) | J-VAL-2 54676971 class_b (f): 64 L8 rows, max relative 6.2e-20 ≤ 1e-18 |
| A-RPL-2 (the 262 new L7 kernels) | J-VAL-2 G-JET on all 3,773 L ≤ 7 kernels + L2, both backends |
| A-RPL-3 | J-VAL-3 54676975 G-BK8 at L7 and L8 (400 kernels per sector) |
| A-RPL-4 | J-VAL-3 forced_tiers: counts met, **no precision-contract finding** |
| A-RPL-5 (L8) | J-VAL-2 check_points, L8 contract mode: **no breach** (L ≤ 7 hard gates pass) |
| A-RPL-6 | J-VAL-3 thread_identity |
| A-IN-6 (the L=2 control) | J-VAL-3 validate --l2-control |
| A-IN-7 | J-SWEEP-1 test assembly: pull +2.46, not flagged |
| A-ASM-3/4 (cluster) | J-VAL-3 compat_run1, assembly_checks --exact (also compat_run1 in J-VAL-2) |
| A-ORC-5 (fakes) | Mac `make test-python` on d730046 (exit 0: `unit_orchestration` lanes and array-mode memory suggestion) |
| A-ORC-6 (cluster) | J-VAL-3 merge_scale --rows 1000000: byte-identical, RSS and bounded fan-in pass; its phase rates were measured on a loaded node and are recorded as lower bounds only (Open) |
| A-DES-8 (e) | J-VAL-3 prefix_check --real |
| A-DES-6 (recorded) | J-ARGMAX 54677001 (+ 54677011), `argmax_L7/` |
| The first measured cost model | J-SWEEP-1 54676977, `cost_models/gmp_expanse_epyc7742_c8.json` (83c07fb) |
| Results first obtained on the provisional sample | none: H1 was delivered before Stage 3a; every Stage-3a/3b result is on the H1 payloads |
| Tag `c8-stage3`, `bin/baseline/` | the tag on the data-only commit after this one (src/ and Makefile of 8b87782); `reference/baseline_c8_stage3.json`, `$C8_STORE/baseline/8b8778273bd9/`, `make baseline` verified in J-ARGMAX |

No precision-contract finding at L8: nothing waits for the user at Stage 5 on A-RPL-4/5.

### Repair round 2 (docs only, 0 SU, no job rerun)

| # | Finding | Fix |
|---|---|---|
| 1 (minor) | The A-ORC-6 merge rates of J-VAL-3 were measured while forced_tiers (128 threads) and thread_identity loaded the node, yet `docs/PERFORMANCE.md` concluded that phase 2 is about 20% slower than projected, and the Open list carried 60,000 vs 49,083 rows/s as a planner issue | `docs/PERFORMANCE.md`, `stage_3b/README.md`, the Results bullet, the checklist row, the `val3` row of `docs/HPC.md` and the Open item now say the rates come from a loaded node (timeline from the job log and `merge_scale.json`) and are lower bounds only; the 20% conclusion is withdrawn; `MERGE_PHASE{1,2}_ROWS_PER_S` unchanged until merge_scale's scale part is re-measured alone (Stage 4a J-PROF, or ahead of the forced_tiers stream in the Stage-5 J-VAL-3) |
| 2 (minor) | The caption of the accuracy contract's measured column in `docs/NUMERICS.md` said the values were measured on `bin/c8d3_gmp` 24adff54…; `forced_tiers.py` and `check_points.py` compile their own test executables | The caption names them (`forced_tiers_gmp` `e01ffd5a…`; `point_checks` gmp `c828394b…`, decimal `61cb8449…`), built in the jobs from the same `src/kernel.hpp` with the Makefile's strict flags as `bin/c8d3_gmp` 24adff54… and `bin/c8d3_decimal` 5a4d4088…; `stage_3b/README.md` says the same in its header and the val2/val3 rows. No number changes |

### Open

- The `LRI_C8_shared/PERF_NOTES.md` entry for A-DES-6 (report to C62d) is not written by this workflow.
- **The merge rates are not clean measurements** (repair round 2). J-VAL-3's merge_scale (A-ORC-6) measured phase 1 at
  268,650 rows/s with 16 processes (16,790 per process) and phase 2 at 49,083 rows/s. All three val3 streams started
  together at 03:44:34, and the scale merge is merge_scale's first step: the parallel merge ran from about 41 s to 75 s
  after the start and the serial reference until about 140 s. Throughout, forced_tiers ran 128 OpenMP threads on the
  node's 128 cores (831 s), and thread_identity ran at up to 128 threads and as 8 × 16 lane processes (until 03:48:02),
  so the node was oversubscribed by up to about 2×. The rates are therefore at best lower bounds. Phase 1 still beats
  the planner's 4,000 rows/s per process. Phase 2 runs as a single process and can easily lose 20% to that contention,
  so the measurement does not show that the planner's 60,000 rows/s is too high (the "about 20% slower than projected"
  conclusion of the first Stage-3b text is withdrawn). `tools/production.py`'s `MERGE_PHASE1_ROWS_PER_S` and
  `MERGE_PHASE2_ROWS_PER_S` are unchanged. Before either is changed, merge_scale's scale part is to be re-measured
  alone on the node: in Stage 4a's J-PROF, or by running it before the forced_tiers stream in the Stage-5 J-VAL-3.
- The tail monitor of the sweep's test assembly flags several power L8 graphs (512 points × 2 replicates; a test
  result with no physical number): pilot material, not a gate.

## 2026-10-05 — C8(3) Stage 2b repair round 1: the A.5 report-back under DECISIONS A3, the Stage-1b records

Two minor findings of the Stage-2b inspection. Commits: 5e05096 (the report-back tools, their test, the docs), then
this evidence commit and a data-only commit (`verify_delivery.py --write`). Evidence:
`benchmarks/expanse_2026-10-c8/stage_1b/` (README there) and `benchmarks/expanse_2026-10-c8/stage_2b/repair1/`.

### Dispositions

| # | Finding | Disposition | Fix | Test |
|---|---|---|---|---|
| 1 (minor) | After G2b the HANDOFF's `c63d` block still said gate "6": "pending (Stage 2b, with the C8 packs)", and `docs/HPC.md`, the Stage-2b CHANGELOG open item and the `gates_d3.py` docstrings said C62d would copy the addendum's `handoff_c63d_update`, contrary to DECISIONS A3 (agreed 2026-10-04: C63d writes `pin_recorded`, `gates_1_7` and `gate_5_forest_certificate` into the `c63d` block and nothing else) | fixed | The docs, the docstrings (`report`, `addendum`, the module text, `g3common`) and the open item now follow A3. New `gates_d3.py handoff-gate6` makes exactly that one write: only for a passed gate-6 addendum whose `addendum_to` sha256 is the gate record's bytes, with the pins agreeing and the `c63d` block equal to the record's `handoff_c63d` apart from gate 6, on the canonical `json.dumps(indent=1)` text of C62d's `handoff_inventory.py`; the structural difference must be exactly `c63d.gates_1_7["6"]`; the bytes are re-read just before the one rename (a concurrent edit is refused); mode kept; old bytes kept as evidence; idempotent; `--dry-run`. Run on the Mac: HANDOFF sha256 `0e2cdd4a…` → `8ee6bb42…`, a one-line diff | `test_gen3.py` `test_tool_report_back` (Mac and Expanse) |
| 2 (minor) | G1b's paperwork was incomplete: no DECISIONS log line carried the d3 pin `70af9d22…` (A.2 step 6), no Stage-1b NOTE, and no Stage-1b evidence or CHANGELOG entry for J-H1-COPY 54661740 and J-GEN-D3 54666138 | fixed | `benchmarks/expanse_2026-10-c8/stage_1b/`: the J-H1-COPY, J-GEN-D3-0 (54661738, G1a) and J-GEN-D3 evidence from `$C8_ROOT/evidence/{d455db3f9123,4540d525be91}/`, the three Slurm logs, their ledger lines and sacct, a copy of the A.5 gate record; the large J-GEN-D3 files are listed by sha256 with the published file each is byte-identical to (`large_files.sha256`, checked with `cmp` on Expanse). New `gates_d3.py decisions-ack` appended the one acknowledgment-log line carrying the d3 pin (DECISIONS.md `0036106b…` → `1b4af6b2…`, only after the HANDOFF holds gate 6; one line, the old bytes a prefix of the new) and `gates_d3.py note` wrote `LRI_C8_shared/assembly/NOTE_C63d_to_C62d_2026-10-05.md` (`943946c4…`) from the records (only after both; never over an existing NOTE) | `test_tool_report_back`; second runs on the real files changed nothing (`stage_1b/report_back/rerun_idempotent.log`) |

The two inventory files, by exact name, are the only paths under C62d's trees that a gen3 tool writes;
`g3common.refuse_c62d` still refuses every other one (`test_tool_refuse_c62d` unchanged). The A.5 gate record
(`81fc4b17…`) and the gate-6 addendum (`f3c69eda…`) are unchanged. The writes into `LRI_C8_shared/` went through these
documented package tools (this workflow's rule for that tree), under DECISIONS A3 and the log's append-only grant to
C63d; `stage_1b/report_back/handoff_gate6/HANDOFF_inventory8_d2.before.json` restores the HANDOFF byte for byte if
wanted.

### Results

- **Mac** (5e05096, personal desktop arm64, g++-16, Python 3.10.12): `gen3/test_gen3.py --only tools` 18 passed in 27 s
  (`stage_2b/repair1/mac_5e05096a506e/`).
- **Expanse**: J-IN-1 in1check, inputs part (`C8_JOB=in1check C8_PHASE=inputs`, `debug -c 16 --mem=32G`) on the
  export of 5e05096 with the L8 packs linked from the store: job 54676920 (<NODE>, 10 min 22 s), every step passed:
  `make link-l8`, `verify`, `tests/check_inputs.py` 58/58 with the L8 packs (A-IN-1..5; the gate record compared),
  `members_test`, gate 6, `make inputs` and `make inputs-mini` changed nothing, `gen3/test_gen3.py --only tools` 18
  passed on x86-64 (`test_tool_report_back` included). 2.76 SU (dev line 186.49 → 189.25; this workflow 18.32 SU)
  (`stage_2b/repair1/5e05096a506e/in1check_inputs/`). The kernels part (A-KER-5) was not rerun: no input, worker or
  inspector byte changed.
- **Stage 1b (recorded now).** J-H1-COPY 54661740 (55 s), J-GEN-D3-0 54661738 (G1a: 3,512 / 3,512 C7(3) payloads
  byte-identical on x86-64; 6 min 22 s) and J-GEN-D3 54666138 (17 min 49 s; every gate passed; d3 pin `70af9d22…`):
  22.46 SU charged on 2026-10-04 (dev line).

### G2b / G1b checklist (after this round)

| Item | Evidence |
|---|---|
| G1a (A-INV-2(a), A-INV-1 sanitizer part) | J-GEN-D3-0 54661738, `stage_1b/d455db3f9123/gen_d3_0/` |
| G1b (A.2 steps 0-6, gates 1(b)-7, A.4) | J-H1-COPY 54661740, J-GEN-D3 54666138, `stage_1b/` |
| A.5 gate record | `LRI_C8_shared/assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates.json` (`81fc4b17…`; copy in `stage_1b/`) |
| Gate 6 | the addendum (`f3c69eda…`, Stage 2b) and now the HANDOFF's `c63d.gates_1_7["6"]: true` (A3) |
| The d3 pin's DECISIONS line (A.2 step 6) | DECISIONS acknowledgment log, 2026-10-05 (`stage_1b/report_back/decisions_ack/`) |
| NOTE to C62d (A.5) | `LRI_C8_shared/assembly/NOTE_C63d_to_C62d_2026-10-05.md` (copy in `stage_1b/report_back/`) |
| A-IN-3..5, A-KER-5 on all 24,173 kernels | unchanged from the Stage-2b entry below (54676856, 54676858); the inputs part rerun on 5e05096 (54676920, 58/58) |

## 2026-10-05 — C8(3) Stage 2b: the complete inputs (L7 complete, the L8 packs in the store, inspect fields, inputs_mini), J-IN-1, gate 6 (G2b)

PLAN.md Stage 2b (needs G1b and the Stage-3a inspector): `make inputs-l8` with the A.5 gate record's D3PIN, the L8
inspect fields, `inputs_mini`, J-IN-1. G2b = A-IN-3..5 and A-KER-5 on all 24,173 kernels. Gate 6 (pack identity), which
the A.5 gate record left "pending (Stage 2b)", is recorded in an addendum next to it. Commits: code 02858a2, 540b6b3,
5859e63, 429ea42, 9db882f, f499d5a; seed registration 782b0cb; generated data b558898; README/docs 3aa57cd; then this
evidence commit and a data-only commit (`verify_delivery.py --write`). Evidence:
`benchmarks/expanse_2026-10-c8/stage_2b/` (README there).

### What was built

- **`make inputs-l8 D3PAYLOAD=… D3PIN=… STORE=$C8_STORE [H1=…] [GATE_RECORD=…]`** (`prepare_inputs.py l8`; A.2 step 6,
  the Stage-1a host note deferred to Stage 2b). The Makefile, then the tool, refuse without D3PIN (exit 2). With
  GATE_RECORD the pins must equal the record's. `gen3/verify_d3.py TREE --pin D3PIN` runs first; on a failure nothing is
  read from the payload's tars and nothing is written. Then:
  - the Stage-2b small files are copied as bytes (`selection.json`, `h1/{MANIFEST.json,SHA256SUMS}`,
    `d3/{MANIFEST_d3.json,SHA256SUMS,MEMBERS_d3.sha256,rate_audit_L7.json,rate_audit_L8.json}`) and their chains checked
    to the two pins (`prepare_inputs.Stage2b`); `selection.json` must hold H1's counts and primitives;
  - L7: the C7(3) members from `reference/inputs/` (their concatenation in id order must reproduce a6ce987's pack, each
    must equal the payload's member byte for byte and its `MEMBERS_d3.sha256` hash) and the s_G = 4 members from the
    payload's tars (by offset);
  - L8: the selected members from the tars, each at its member hash, published as the read-only, content-addressed
    blobs `$C8_STORE/packs/<sha256>.pack` (never overwritten; HD3) and hard-linked into `inputs/packs/`;
  - double_lift: numpy at L ≤ 7, equal to `rate_audit_L7.json` (the C++ count) for every L7 kernel; the audit's count at
    L8.

  **Host decision (HD3 naming):** the plan names the store directory `$C8_STORE/packs/<inputs-manifest sha12>/`. The
  inputs manifest changes whenever the inventory does (the inspect fields arrive after the packs), so the blobs are
  keyed by their own sha256 instead; the manifest pins them, `make link-l8` links the pinned ones, and every reader
  verifies them by hash, as HD3 requires.
- **The Stage-2b `make inputs`** (mode 2b-carry, once the manifest carries the d3 pin): rebuilds everything from the
  package's own copies; the new L7 members come from the committed L7 pack at their committed rows, each checked
  against `MEMBERS_d3.sha256`; the L8 rows are re-derived from the L8 packs when present (each member split by its
  header's T, the pack at its pin), or carried forward (the Mac) after checking each row's id, primitive flag, sha256,
  double_lift and offset against the selection, the member list and the audit. The L8 packs are never written. The
  Stage-2a output is byte-identical to before.
- **`verify()`** also checks the Stage-2b chain when the d3 pin is set. **`make link-l8 STORE=…`**,
  **`make inputs-mini`** and `prepare_inputs.materialize_mini` / `members.py mini` / `members.mini_inputs()` (PLAN B
  `inputs_mini`: the 8 smallest L8 kernels per sector, the package's L3–L7 rows, a manifest pinning the package's other
  inputs; any plan on it is test-only).
- **`tools/members.py`**: the member list is the inputs' `d3/MEMBERS_d3.sha256` (checked against its manifest pin,
  loaded only for L ≥ 7); a listed L7/L8 member must be listed and match.
- **`gen3/gates_d3.py`**: `gate6` (every C7(3) member of the C8 packs, read at the C8 offset, has a6ce987's row
  sha256; the PINS digest; the L3–L6 packs; every L7 member at its member hash; 143 + 119 new s_G = 4 kernels; L7
  totals) and `addendum` (gate 6 next to the A.5 record, which `report` writes once; refuses an existing output, a
  failed gate6, another inputs manifest or other pins; C62d's HANDOFF is not touched). Gate 5(a) now lists a builder
  binary whose sha256 differs from H1's MANIFEST under `warnings` and prints it (the Stage-1a host note: "passes with
  a warning"); this changes no published record (in J-GEN-D3 every binary was equal).
- **`tests/check_inputs.py`** follows the live state (Stage 2a or 2b); at Stage 2b: A-IN-3 (counts, flags, the chain,
  the gate record's pins, the inventory on loops 3–8 with every L7/L8 row at its member hash and the audit's
  double_lift, the C7(3) L7 members reproducing a6ce987's pack, 143 + 119 new s_G = 4 kernels, 248 L8 primitives, the
  L8 members read from the packs when present, numpy against the C++ audit on the smallest L8 kernels, inputs_mini),
  A-IN-4 (the gate not test-only with the L8 packs; one-byte changes to the Stage-2b files; with the L8 packs, a
  one-byte change to `packs/free_L8.pack` refused by the gate and by `production.py plan`, non-test, creating
  nothing), A-IN-5 (the regeneration byte for byte). `tests/plan_gate.py`: `flip_large` (a streamed flipped copy; the
  store blob's hard link set aside and put back) and `run_live_flip`.
- **Tests:** `gen3/test_gen3.py` (inputs-l8 refusals without and with a wrong or malformed pin, an audit-hook spy
  showing no tar opened; the gate-5 warning; the addendum: 17 tests), `tests/inputs_l8_test.py` (new; the whole
  Stage-2b path on a miniature payload with the real C7(3) members: 8 checks, about 2 min; in `make test-python`),
  `tests/members_test.py` (the inputs' member list and inputs_mini).
- **`slurm/inputs_job.sh`** (J-IN-1): `in1build` (code commit) and `in1check` (data commit), each optionally in two
  parts for debug's 30-minute limit (`C8_PHASE=l8|inspect`, `C8_PHASE=inputs|kernels`); work copies on Lustre so the
  store's blobs can be hard-linked.
- **Docs:** `docs/HPC.md` "Inputs" and "Stage 2b", `README.md`, `tests/fixtures/README.md`.

### Results

- **J-IN-1 in1build** on 5859e63: 54676620 (`make inputs` unchanged; `make inputs-l8`: verify_d3 four steps PASS;
  3,511 C7(3) members, all 10 a6ce987 packs reproduced, 2,888 L7 members equal to the payload's; 262 new L7 members;
  L8 packs `d60ccb8c…` 7,121,248,655 bytes and `92b70b36…` 1,674,690,805 bytes in the store) and 54676810 (`make
  inputs-inspect` over 24,173 kernels in 140 s, `make inputs-mini`, gate 6 PASS, verify PASS). The generated files are
  the data commit b558898 (inputs manifest `ece2e4a4…`, inventory `e0f16f00…`, L7 packs `b5bd6c12…` / `0e5c6eab…`,
  `inspect/inspect.json` `04470217…`).
- **J-IN-1 in1check** on f499d5a (the final code and data): 54676856, every step passed: `check_inputs.py` 58/58 with
  the L8 packs (A-IN-1..5; gate record compared), `members_test`, gate 6, `make inputs` and `make inputs-mini` changed
  nothing, `test_gen3 --only tools` 17; 54676858: `inspect_check.py` (A-KER-5) on all 24,173 kernels and its worker
  part on 100 graphs (10 per sector at L8). Two earlier in1check attempts failed in the tests themselves and are kept
  as evidence: 54676834 (429ea42; EXDEV when hard-linking from the Lustre work copy into node-local TMPDIR; fixed in
  9db882f) and 54676849 (9db882f; 57/58, the gate's no-change snapshot saw the bin/ the live plan flip had added;
  fixed in f499d5a). Their kernels parts (54676836, 54676851) passed.
- **Gate 6:** PASS (3,511 C7(3) members at a6ce987's row sha256, digest `baa6203a…` = PINS, the L3–L6 packs a6ce987's,
  2,441 + 709 L7 members at their member hashes, 143 + 119 new s_G = 4). The addendum
  `LRI_C8_shared/assembly/H1_gates/inventory8_d2_46341a3c0f11_C63d_gates_addendum_gate6.json` (sha256 `f3c69eda…`)
  records it from 54676856's `gate6.json`; the A.5 record (`81fc4b17…`) and `HANDOFF_inventory8_d2.json` are unchanged.
- **Mac** (9db882f): `C8_ALLOW_NO_L8=1 check_inputs.py` 57/57, `check_vendored` 25/25, `members_test` 2,
  `inputs_l8_test` 8, `test_gen3 --only tools` 17; `make -k test-python` on 429ea42: exit 0.
- **Observations.** double_lift totals: power L7 247 subsets in 71 kernels (C7(3)'s 106 in 42, unchanged), power L8
  1,882 in 380 (the pre-pilot prevalence, F25), none in the free sector.
- **HD6:** the L8 net seed 5563 of `inspect_check.py` registered before use (782b0cb).
- **Expanse use:** 15.56 SU (dev line 170.93 → 186.49), all on `debug` (one `shared` submission cancelled while
  pending before the 2026-10-05 maintenance, 0 SU).

### G2b checklist

| Item | Evidence |
|---|---|
| A-IN-3 (packs and inventory) | L3–L6 packs at a6ce987's sha256; L7 2,441 / 709 and L8 16,064 / 4,336 members at `MEMBERS_d3.sha256`; every row with the inspect fields (products, addends, kernel_bytes > 0), `inspect_complete: true`; `inputs_mini` verifies: check_inputs 58/58 (54676856) and 57/57 (Mac), gate6 |
| A-IN-4 (manifest) | the 12 packs, the small inputs, the order-7 files, the H1 and d3 pins (equal to the HANDOFF's and the gate record's) and the vendored pins; a one-byte change to `packs/free_L8.pack` refused by the gate and by `plan` before creating anything (54676856); a foreign `C8_INPUTS` refused; `l7_complete: false` plans test-only (plan_gate's fixed state) |
| A-IN-5 | `tests/check_inputs.py` passes on Expanse with the L8 packs present (54676856, 58/58) |
| A-KER-5 on all 24,173 kernels | `tests/inspect_check.py` (54676858): products and addends = `gen3/opcount.py`, M and T = headers, every row inspected; the worker part on 100 graphs (L8 included) |
| Gate 6 | `gates_d3.py gate6` PASS (54676810, 54676856, Mac); the addendum next to the A.5 record |
| A-INV-5 (`make inputs-l8` refuses without the pin; verify_d3 first) | `gen3/test_gen3.py` inputs_l8 refusals (Mac, 54676856); 54676620's `verify_d3.json` |

### Open

- **Stage-1b records** (resolved in the repair round above). The Stage-1b evidence (J-H1-COPY 54661740, J-GEN-D3
  54666138) was on Expanse only, no DECISIONS log line carried the d3 pin `70af9d22…` (A.2 step 6: "the A.5 gate
  record and its DECISIONS log line") and no Stage-1b NOTE existed. This entry also said that C62d may copy the
  addendum's `handoff_c63d_update` into the HANDOFF; that was wrong: under DECISIONS A3 (agreed 2026-10-04) C63d
  writes the `c63d` block, now through `gates_d3.py handoff-gate6`.
- Jobs that read L8 data on an export need `make link-l8 STORE=$C8_STORE` first; `slurm/native_job.sh` copies its
  export to node-local scratch, so with the L8 packs linked it would copy 8.8 GB (Stage 3b's J-VAL jobs should link or
  copy the packs into their node-local copy deliberately).

## 2026-10-05 — C8(3) Stage 3a repair round 3 (the residual issues of the Stage 3a workflow)

Commits 44e1c9c (code and tests) and 0325f1c (the HD6 seed registration and its mirror), then the evidence commit
ee73fca and the data-only commit 750e397 that regenerates `DELIVERY_MANIFEST.json` and `SHA256SUMS`. Follow-up for
the verifier's item-5 residual (below): 16ae9b7 (the net seeds registered, the mirror, the fixture and its test), then
an evidence commit and a data-only commit. `src/` is unchanged. No Slurm job; two Expanse login-node sessions
registered seeds (HD6 permits it for the seed log).

### Dispositions

| # | Finding | Disposition | Fix | Test |
|---|---|---|---|---|
| 1 (major) | `pilot_report.py stage-a` always said GO (A-PIL-2, E.6) | fixed | `stage_a` now reports every A-PIL-2 field: the MP self-check histogram and alarm, the stage-A screen, P1c, action 4, alpha and skewness from P1c (graph bootstrap), eta (allocated/busy) from `accounting.py`, f_E = PA's measured busy / its measured model's prediction, queue latency, the worker failures (`groups/*/logs/*.failure.*`, `lanes/failures/*.json`, work attempts sacct shows in FAILED, NODE_FAIL, OUT_OF_MEMORY, BOOT_FAIL, TIMEOUT, DEADLINE or PREEMPTED), and the re-projection of PF and every pre-registered branch (PF at R = 8, PF with R = 16 at L8, action 4's mixed R when it is mixed, each followed by PC at its 25% cap) as expected spend and as peak reservation: the line's committed SU (`budget.py`) + the branch's earlier spend + the step's N x 128 x T_lane (`slurm_submit.auto_lane_time` on max(model, f_E x model)) + its merge, with the runbook's shared jobs at their F39 reservations. GO needs no `mp_alarm`, no worker failure and every branch's peak within `C8_PILOT_SU_CAP` (or `--line-cap`); otherwise NO-GO with the reasons (stderr and `go_reasons`), and a branch above the line is named ("the pilot stops and the user is asked"); a line or committed SU that cannot be read is NO-GO ("not evaluated") | `test_pipeline` stage_a_checks on the fake PA: the runbook line gives GO with every field; f_E, the PF busy hours, lane times, reservations and peaks equal hand values; NO-GO with its single reason on a copy with one injected `mp_alarm` (graph_promotions.csv re-pinned), on a copy with one lane failure record, naming every branch below a too-small line, and "not evaluated" without a line. `test_pilot_report` reproject_hand: busy hours, T_lane 1:15/2:00, peaks 708.5/1,092.5 SU by hand; a line between them leaves only the R = 16 branch outside |
| 2 (major) | E.7 outputs missing from `cost_table`; `band68` values computed and unused | fixed | every row: F and the realistic cost at the central alpha and P8_hat; F at both ends of the pooled P8_hat band (action 5's band now passed in); the optimum at both ends of the alpha band (item 10's band, now passed in); for relative targets the SE at both ends of the |C8| band (|C8| -+ PF's sampling SE; a band reaching 0 is marked unbounded above); the row band = the envelope over all corners in busy core-h, SU and wall hours on 4 and 22 nodes; a Gaussian-kappa column; SU per MP self-check mode from `mp_check_overhead` of `--cost-model` or PF's own measured model ("pending P1" when not measured); queue latency per step (PA, PF, PC) apart from eta; the measured/projected statement kept. `full`'s usage line is now true (`--cost-model` accepted) | `test_pilot_report` cost_table_bands: all 17 rows (6 relative) against an independent water-filling at any alpha and `realism`: central, Gaussian kappa, P8 band, alpha band, |C8| band, envelope (9 or 27 corners), SU per mode (x0.8/x0.9; a stride16-measured model: 0.72/0.8; none: pending), unbounded case; `test_pipeline`: every SU inside its band, latency for PA, PF and PC |
| 3 (minor) | the PLAN's Stage-7 runbook lines did not run against the CLIs | fixed (tools follow the read-only PLAN) | `pilot_report.py stage-a RUN --output FILE` (`--out` kept as alias); `full ... --output FILE --markdown FILE` (`--out DIR` kept; `growth_c63d.csv` and the new per-graph `sigma_cost.csv` beside the JSON; `PILOT_REPORT.md` written by a new markdown view); `pilot_select.py confirm --screen <PF run> --pa <PA run> --seed S --out FILE` computes the screen itself and takes the PC costs from PF's pinned measured model (`--screen SCREEN.json --pf PF [--cost-model M]` kept; the selection records the screen it used); `--output` also accepted where `--out` was | `tests/fixtures/runbook_stage7_pilot_tools.txt` is a verbatim copy of the PLAN's lines (checked line by line against PLAN.md when reachable: `C8_PLAN_MD` or `../LRI_C8_D3_HPC_loop/PLAN.md`); `test_pipeline` runs stage-a, confirm, count, both `PC_ARGS` branches and full verbatim in bash from the package directory (placeholders `<date>`, `<registered>` filled); the old forms give the same selection |
| 4 (minor) | the item-10 alpha band and the item-9 pooled P8_hat band resampled graph-campaign entries | fixed | `boot_band` resamples units (optionally within strata); `alpha_p1c` and `action5` pass one unit per graph holding both campaigns' entries; the central alpha of E.7 gets a graph band stratified by sector | `test_pilot_report` graph_bootstrap: the reviewer's 40-graph case (graph band 1.48 x the graph-campaign band, equal to the one-entry-per-graph band); spies show one unit per graph with campaigns a and b of that graph (alpha_p1c and action5, hand values); stratum sizes kept |
| 5 (minor) | HD6: the L=2 control's seeds and the other Stage-3a test seeds were not in `$C8_SEEDS` | fixed in two steps: base and native seeds (0325f1c), then the net and `random.Random` seeds (follow-up, 16ae9b7) | registered on the Expanse login node with `seeds.py add --seed S --label ...`. 0325f1c, 16 entries: the control's base 6602215, natives 6602267/6602275 and nets 220052/220060 of val3a 54668918 and 54669734; the base and native seeds of the Stage-3a runs with the real workers: validate.py 7738251, 741987; class_b.py 6619043-6619045; forced_tiers.py 4401; sanitize.py 4242, 1; inspect_check.py 1; workflow.py 7611826; staging.py 816615, 816616 (`seeds_r3/`, mirror sha256 0afcb6b1...). 16ae9b7, 85 entries: every net seed the same runs passed to `nc.net` and the two `random.Random` seeds (below; `seeds_r3b/`, mirror sha256 fcd8c178..., 102 entries). Scope (host decision, below): the seeds of runs that sample the integrand with the real workers; fake-worker test plans are not registered | `unit_orchestration` seeds_and_nets: the committed mirror holds the 16 and `seed_refusal` refuses the control's seeds; `tests/fixtures/stage3a_test_seeds.json` lists every `nc.net` call site of the five real-worker tests (the test fails on an unlisted or changed site), each seed is recomputed from the file's own expression at its binding and is in the mirror and refused as a plan seed (87 seeds, the control's two nets included); the zero-channel nets equal those of the pinned repair3b rows; `seeds_r3/` and `seeds_r3b/forbidden_seeds.json` (the log read back) each equal the mirror of their commit byte for byte |
| 6 (minor, host decision) | zero-channel graphs with heavy t tails (power L7 G1601) would take PC budget although they carry no C8 variance | fixed as a host refinement (below) | `pilot_select.zero_channel` (s_G = 4); `screen_graph` never flags and `confirm_graph` never confirms an L8 zero-channel graph and both report it as "zero-channel heavy tail, not confirmed"; `pilot_select.confirm` drops one from a screen file (recorded under `zero_channel`) and never draws one for 2b; `action3_hold` does not count it; the reports list them (`zero_channel_heavy_tail`) | `test_pilot_report` zero_channel_actions (the vendored C8 Jacobian row at L8 is (-1, 3) x const; s_G = 4 vs 6 on the same heavy graph; the real G1601 rows flagged without the rule and reported with it; confirm's drop and 2b exclusion; action 3 hand shares; action 5, alpha_p1c, item 12); `test_pipeline`: the heavy L8 graph 3 (s_G = 4 in `tests/c8pkg.py`) is reported and never flagged or selected, graph 5 is |

**Host refinement (zero channels; recorded as a host decision of this round).** An L8 graph with s_G = 4 (3 w_B =
w_A) has an identically zero C8 contribution: the C8 Jacobian row at L8 is proportional to (-1, 3) (checked on the
vendored `jacobians`), so 3 jet_1 - jet_0 vanishes for every replicate, while its t = v_0 jac tail is weight-free and
can be heavy. Such a graph is reported as "zero-channel heavy tail, not confirmed" and is excluded from PC selection
(screen and 2b), from the 3% hold test and, since its replicate values are the rounding noise of a zero channel, from
the C8-variance statistics: the P8_hat pools of actions 4 and 5, alpha_hat (item 10) and item 12. L <= 7 graphs are
unaffected (their C8 Jacobian rows are not proportional to (-1, 3) in the old slots, and the actions act on L8 only).
The pre-registered thresholds are unchanged. A reviewer may prefer to keep the P8_hat/alpha/item-12 exclusion apart
from the PC/hold exclusion that the finding named; it is one rule here because a zero channel's Q values would
otherwise enter Var(Q) at full weight.

**Follow-up: the net seeds of the test runs (the verifier's item-5 residual).** The verifier found that 0325f1c
registered the net seeds of the L=2 control only. The round-3 report had left the other runs' net seeds out under a
rule of its own, and neither the PLAN nor this CHANGELOG recorded that rule. 16ae9b7 registers them (85 entries, one
per seed, each label naming the file, part, expression, binding and jobs):

| File | Part | Net seed expression | Values |
|---|---|---|---|
| validate.py | G-C7, G-JET (`net_for`) | 983507 + L + 11255[power] + 101 layout + bits | 30: free L2; both sectors L3-L6 at layout 0, L7 at layouts 0-2; bits 52 and 60 |
| validate.py | G-C7 shift path | 1201 + L | 1204, 1206, 1208 |
| validate.py | bad inputs | 5150 + L | 5153, 5158 |
| validate.py | L2 at both orders | 4242 | 4242 (already present as sanitize.py's native seed; added with its own source) |
| validate.py | random access and threads | 273845 + layout | 273845-273847 |
| validate.py | G-BK8 | 81113 + L | 81120 (L7) |
| class_b.py | (a); (b)(c)(d); deep fixture | 7700 + L; 8800 + layout; 3131 | 7702-7707; 8800, 8802; 3131 |
| class_b.py | (e) inventory; (e) new L7 | 9900 + L; 9907 | 9903, 9906; 9907 |
| class_b.py | zero-channel tails | 9950 + 100 off + L | 10053, 10056, 10057, 10153, 10156, 10157 (= the pinned repair3b rows) |
| forced_tiers.py | A-RPL-4 smoke | SEED + L = 4401 + L | 4408 |
| inspect_check.py | order trace | 5555 + L | 5558-5562 |
| sanitize.py | worker runs; targeted cases | 6060 + L + 7 layout; 3030 | 6062-6067, 6069-6074, 6076-6081; 3030 |

Also registered: the `random.Random` seeds 81113 (validate.py's G-BK8 kernel draw) and 8814 (validate.py's synthetic L8
G-file; also gen3/test_gen3.py's `SEED` and sanitize.py's parser mutants). The values are those the Stage-3a runs
reached. The inventory has L <= 7, and the records confirm the L, kernel and case sets: the (e) picks, the shift cases,
G-BK8 at L7, and the 30 bad-input cases with the single L8 one. Values a formula did not reach are not seeds of any run
and stay accepted. For example 5157 (= 5150 + 7, the verifier's instance) is accepted, because the bad-input cases use
L3 and L8 only. Stage-3b runs at L8 will add their own values.

**Host decision (HD6 scope for test runs).** Every seed a test run with the real workers used is registered: its base,
native and net seeds, and the `random.Random` seeds that draw kernels or generate inputs. Not registered:
- the seeds of the fake-worker test plans (`tests/c8pkg.py`, `C8_SITE=fake`: `workflow.py`/`staging.py --fake`,
  `integration_3a.py`, `check_vendored.py`, `merge_scale.py`, `cost_refresh_test.py`, `unit_orchestration.py`,
  `test_pipeline.py`). They sample no integrand, and every Mac suite run repeats them.
- the numpy RNG seeds of Mac-side analysis tests.
- the C7(3) seeds replayed by `run1_replay.py`, `archived_replay.py` and `archived_stream_replay.py`. They are covered
  as far as HD6 lists them: C7(3)'s `USED_BASE_SEEDS`, the archived records' base seeds, and run1's group seeds.

The workflow.py and staging.py validation plans with the real workers are covered by their registered base seeds, from
which `seed_refusal` derives every group seed. `docs/HPC.md` states this rule.

**Not addressed (outside this round's list):** the nits of the same review, `heldout_by_sector` taking only the label
`stratified` (P1c graphs drawn from the stratified part are left out of item 12; about 1/32 of its sample) and
`seeds.py mirror` validating a COPY less strictly than `production.read_seed_file` (a non-object COPY crashes; a
malformed entry is accepted).

### Results

- **Mac** (`benchmarks/expanse_2026-10-c8/stage_3a_integration/mac_0325f1c8c09e/summary.txt`, `git archive` of
  0325f1c): unit_orchestration 15, test_pipeline 9, prefix_check 3, test_pilot_report 16, assembly_checks --exact 3,
  design_fallback_test 5 passed; ast_scan 0 findings. `verify_delivery --strict` passes on the data-only commit that
  follows.
- **Expanse:** this round submitted no job; the seed registration ran on the login node (`seeds_r3/`, README there).
- **Follow-up** (`mac_16ae9b72cf42/summary.txt`, `git archive` of 16ae9b7): unit_orchestration 15 (seeds_and_nets with
  the 87 fixture seeds), test_pipeline 9, prefix_check 3, test_pilot_report 16, assembly_checks --exact 3 passed;
  ast_scan 0 findings. Expanse: no job; `seeds_r3b/` holds the registration script, its log (85 added) and the log read
  back (102 entries, sha256 fcd8c178..., = `designs/forbidden_seeds.json`). `verify_delivery --write` follows in a
  data-only commit.

## 2026-10-05 — C8(3) Stage 3a repair round 2 (the G3a review's 5 minor findings)

Commits 2040715 (data only: the seed-log mirror), b61ea23, c583543, be73870, 592fb7f, 239613f (code, tests and the
pinned fixture), then this evidence commit and a data-only commit that regenerates `DELIVERY_MANIFEST.json` and
`SHA256SUMS`. `src/` is unchanged: `bin/c8d3_gmp` is `24adff54…` in both jobs.

### Fixes

| Finding | Fix | Test |
|---|---|---|
| A-DES-3's zero-channel sub-item on real tail fields untested (it was deferred to G3b, which does not list it) | `tests/class_b.py --parts e --zero-channel-tails FILE` integrates every zero-channel kernel of (e) in the pilot shape (campaigns a/b, 8 replicates × 32,768 points nested at 4,096, the tasks [0, 4096) and [4096, 32768) as `task_bounds` cuts them, `--mp-check on`); `tests/test_pilot_report.py --zero-channel FILE` builds the full-stream and 4,096-point prefix rows by the merge's rules and feeds them to `tail_stats` (both lengths, both campaigns), `screen_graph`, `confirm_graph` (alpha unknown and ½), `split_q` and σ; the rows of job 54672564 are pinned as `tests/fixtures/zero_channel_tails.json` and checked in the default (Mac) run; `pilot_report`: a non-finite `tail_sum` is "undefined", `confirm_graph`'s supporting values are finite or None (`fin`), a non-finite two-campaign mean is "undefined" | Expanse repair3b 54672564: power L3 G7, free L6 G26, free L7 G1487, power L7 G1601, every row max_abs 0; 16 of 16 tail statistics finite, no NaN or infinity anywhere, flags booleans; Mac: the pinned fixture, `zero_channel_synthetic` (inf/NaN `tail_sum` or top value → "undefined", an overflowing variance → V ratio None) |
| `designs/forbidden_seeds.json` (HD6 mirror) missing | 2040715 commits the byte copy of `$C8_SEEDS` (sha256 8b983e32…, the single 20261004 entry); `tools/seeds.py mirror --log COPY` refreshes it append-only (64 for a copy that drops or changes an entry); `docs/HPC.md` states the per-evidence-commit procedure; repair3b copies the log into its evidence | `unit_orchestration` seeds_and_nets: byte copy, identical rerun, dropped entry and non-log refused with the mirror unchanged, appended entry taken; the committed mirror holds 20261004; repair3b's copy equals the mirror byte for byte (no seed was registered in this round) |
| Phase 2 kept every pass level on scratch; D.7 projected the largest group only | `_phase2` deletes each batch of F runs once its merged run is complete and the group's last runs after the final pass; `_final_pass` deletes the group's scratch tables after publishing (body unchanged, in `_final_pass_files`); `plan` compares the campaign's merge scratch peak, Σ_groups rows × 900 B × 2 (phase 1 leaves every group's rows; merge.sh runs up to `C8_MERGE_JOBS` groups in passes at once), with 0.8 × the merge node's `/scratch`, prints it, and records `merge_scratch_bytes_peak` | `merge_scale` scratch (spies on the real merge, fan-in 2, 16 runs, 4 passes): peak 1.50 copies, 1.00 at the final pass (4.00 before), nothing of the group left after phase 2, byte-identical to the serial merge (Mac and Expanse); `atomic_and_guards`: a `/scratch` that holds the largest group's two copies but not the campaign's peak is refused, one that holds the peak is accepted; the reviewer's reproducer now ends with 2 files = 1.00 copy |
| `combine.py` mixed a test-only batch into a final production result (order-dependent) | `SAME` includes `campaign_role` and `test_only`; a final combination needs role production in every batch; test-only batches give a partial result; any other role is refused; `batch_of` records `campaign_role` | `verify_result_tamper` (94 checks): [prod, test] and [test, prod] refused, a role-only difference refused, `pilot_full` refused, two test-only batches partial and verified |
| Item 12 pooled both sectors under the first row's c4(R_PF)² | `pilot_report.heldout_by_sector`: per sector, that sector's PF L8 replicate count (both campaigns must agree, else refused), keys sorted; `cost_table` takes `{sector: corrected}` into that sector's L8 P̂ only; the report's `design_penalty_heldout` is per sector with `R_PF` | `heldout_per_sector`: free R = 8 and power R = 16 against hand values (c4² 0.931284 and 0.967240), key order irrelevant, mixed R in a sector refused, cost_table per sector; the reviewer's pipeline reproducer now gives free R_PF 8 (c4² 0.93128) and power R_PF 16 (0.96724) |

Observation (no change): the zero-channel kernel power L7 G1601 has a heavy tail of t = v_0·jac (ξ 0.77/0.69 at
4,096 points, two-campaign mean 0.54 at 32,768). t is weight-free, so a zero-channel **L8** graph with such a tail would
be screened and confirmed although its C8 contribution vanishes. Action 3 and the cost table use σ on the C8 Jacobian,
which is 0 for such a graph, so they are unaffected; only the PC budget could be spent on it.

### Results

- **Expanse** (`benchmarks/expanse_2026-10-c8/stage_3a_integration/{592fb7f2aa4f,239613f7192d}/`, README there):
  repair3b 54672564 on 592fb7f passed (the zero-channel rows and their pilot_report check; the seed log copied);
  J-VAL-1 54672581 on 239613f passed (37 PASS, 10 SITE_REFUSED, 0 FAIL). 6.39 SU; dev line 163.47 → 169.86 SU
  (155.43 after round 1; 8.04 SU of intent de7f01e5a086 between the rounds were not this round's).
- **Mac** (`git archive` of 239613f; `mac_239613f7192d/summary.txt`): PLAN's Mac list and `make test-python`, all
  green except `verify_delivery --strict`, which passes on the export of the data-only commit that follows.
- **Seed mirror at this evidence commit:** `seeds.py mirror --log` repair3b's copy → "identical" (sha256 8b983e32…,
  equal to `$C8_SEEDS` read on the login node); no seed was registered in this round, so 2040715 stays current.

### G3a checklist after repair round 2

| Item | Evidence |
|---|---|
| Mac suite | `mac_239613f7192d/summary.txt` (+ `verify_delivery --strict` on the data-only commit) |
| A-KER-1..3 | J-VAL-2 54669728 and repair3a 54672309 (`src/` unchanged since); J-VAL-1 54672581 (check_build, bad inputs) |
| A-KER-5 (L ≤ 7) | J-INSPECT 54670914; repair3a 54672309 (100 graphs) |
| A-KER-6 (a)–(e) | J-VAL-1 54672581 class_b (a)–(e); repair3a 54672309 and repair3b 54672564 (e) with the new zero-channel L7 kernels G1487/G1601 |
| A-KER-7 | J-VAL-2 54669728, J-VAL-1 54672581 (class_b deep fixture) |
| A-RPL-1 | repair3a 54672309 (all 3,511 + L2, both backends, nondirect totals, the shift case on the A-L18 hunk) |
| A-RPL-2 (3,511 C7(3) kernels) | repair3a 54672309 G-JET (3,512 with L2) |
| A-RPL-5 (L ≤ 7) | J-VAL-2 54669728 check_points |
| A-RPL-7 | J-RUN1 54669730 (G-RUN1 T1–T5, test-replay); the selection seed 20261004 registered (54672281) and mirrored (`designs/forbidden_seeds.json`) |
| A-ASM-1 | Mac (`check_vendored`, `vendored_isolated`), J-E2 54659017, J-VAL-1 54672581 |
| A-ASM-2..7 | Mac (`assembly_checks --exact`, `compat_run1`, `verify_result_tamper` 94/94 with combine's role checks, `test_pipeline`); J-VAL-1 54672581 |
| A-ORC-1..5, 7, 10..17 (fakes) | Mac (`unit_orchestration` with the seed mirror and the merge scratch projection, `lanes_tests`, `test_submit`, `test_ledger`, `cost_refresh_test`, `blocks_test`, `test_pipeline`); A-ORC-13's Linux platform class in J-VAL-1 54672581 |
| A-ORC-6 (Mac part) | `merge_scale` (with the scratch case; also J-VAL-1 54672581) and `unit_orchestration` merge_and_safety |
| A-ORC-9 (fakes) | `test_pipeline` accounting_checks |
| A-DES-2..4 | `design_fallback_test`, `test_pilot_report` (Mac oracles; actions 1/3/5 hand values; item 12 per sector; the zero-channel synthetic rows and the pinned real rows; `--run1` in 54672309; `--zero-channel` in 54672564), `test_pipeline` |
| A-DES-7 (a)–(e), A-DES-8 (a)–(d) | `test_pipeline`, `prefix_check` |
| A-EXP-1 | J-E0/J-E1 records (`stage_0/`), check_build in every build job, the Boost < 1.70 refusal (`native_static`), the scratch probe 54672283 |
| A-EXP-2, A-EXP-4 | Mac (`unit_orchestration`, `lanes_tests`, `test_submit`) |

**Still open (G3b and later, as PLAN stages them):** A-RPL-2 on the 262 new L7 kernels, every L8 item, the benchmark
tools' D.1 port (Stage 4a), C.6's R5a (Stage 4b). A-DES-3 has no open part at G3a any more.

## 2026-10-05 — C8(3) Stage 3a repair round 1 (the G3a review's 15 findings)

Commits c1f0533, 2f42a0c, 4d7870a, b349a0b, 5aaa0e2, 3e4b973 (code and tests), then this evidence commit and a
data-only commit that regenerates `DELIVERY_MANIFEST.json` and `SHA256SUMS`. `src/` is unchanged: `bin/c8d3_gmp` is
`24adff54…` in every job, as before.

### Fixes

| Finding | Fix | Test |
|---|---|---|
| A-DES-3's Expanse part missing (major) | `tests/test_pilot_report.py --run1 [--archive --sha256]`: the pinned run1 archive's power-L7 block maxima (xi_sd over 64 replicate maxima of the checkpoint rows' `max_abs`) and `pilot_report`'s P8_hat (split_q, p8_pooled) on the eight L6/L7 groups, projected on the old slots of the vendored C8 Jacobian at run1's means | 590 graphs; 34/37/33 > 0.38, 33/28/27 > 0.42 (27 of 590); graph counts, Var(Q) and P8_hat equal `tail_calib.log` to its decimals, 1.078–1.103; on Expanse in repair3a (and the `run1` job of `native_job.sh`) |
| A-ORC-9 untested (major) | `tests/test_pipeline.py` `accounting_checks` on PF | `accounting.py --json` = the hand F39 sum over every `sacct -X --duplicates` attempt (a requeued lane worker NODE_FAIL + COMPLETED; a `c8d3-` lane job of the campaign without a ledger record, cpu=4,mem=12G = 6 SU/h); eta_node = the hand ratio; a checkpoint naming a job id `sacct` does not show exits 69 "allocation unknown"; `pilot_report full` and a `design_fallback` freeze without `--eta-node` take eta from the accounting |
| Action 3 ignored PA's 32,768-point sigma (major) | `pilot_report.action3_hold`: sigma_hat = max(PF's 4,096-point value, every 32,768-point estimate from PA (P1c) and PC) | hand values with no 32,768-point rows, with an empty PC (the P1c graph's PA sigma 2 lifts its share from 2.5% to 4.9%: hold), and with a PC |
| A-KER-6 (e) new L7 kernel | `tests/class_b.py --parts e --d3-payload TREE --d3-pin SHA`: one zero-channel new L7 kernel per sector from the published d=3 payload (pin of the A.5 gate record), verified along its checksum chain | Expanse: free G1487 and power G1601 (header 3 w_B = w_A), `max_abs` 0, `tail_top[0]` and `tail_sum` positive and finite |
| A-KER-5 checked 79 graphs | `tests/inspect_check.py` `allocate()` hands small groups' slots to larger ones | Expanse: 100 graphs |
| `verify_delivery --strict` red | `tools/verify_delivery.py --write` in the data-only commit after this one | `--strict` on that commit's export |
| Seed 20261004 unregistered | `$C8_SEEDS` created (`seeds.py init`) and the seed added in the repair3a job | `forbidden_seeds.json` in the evidence |
| A-EXP-1 untested parts | `slurm/scratch_probe.sh` (submitted with `C8_SCRATCH=/tmp/login-value`; Mac part in `tests/integration_3a.py`); the J-LOCK-0, J-E0, J-E1 records copied to `benchmarks/expanse_2026-10-c8/stage_0/` (README: job ids, the C7(2) binary's `/lib64/libgmp.so.10`, the RPATH build's Spack GMP) | Expanse job 54672283 |
| A-ORC-6 collision branch not forced | `unit_orchestration.py` merge_and_safety: a race driver hooks `production.dump_point` so another publisher's `merged.json` lands first | identical: "identical merged.json published concurrently; kept"; different (valid checksum): "a different merged.json was published concurrently" |
| `workflow.py`/`staging.py` env update inside a comment | the `e.update(...)` is a statement again; `tests/ast_scan.py` flags `;stmt` inside comments in tools/, tests/, gen3/ | ast_scan reports both lines on the old tree |
| A-DES-3 actions 3, 5 and L8-only untested | `pilot_report` actions 1, 3, 5 as functions; `test_pilot_report.actions_hand`; `test_pipeline` heavy L7 graph (`C8_FAKE_HEAVY 7:2`) | hand values; the heavy L7 graph (xi > 0.38) in no action's output |
| G-C7 blind to the A-L18 hunk | `tests/validate.py`: the G-C7 record holds the nondirect totals; `part_c7_shift` (rate .02 one-point tasks, L3/L5/L7 both sectors and the deep-cancellation fixture, c7ref against C8 order 7, `--mp-check off` and `on`) | Expanse: exact, 1,389 rows per backend whose MP point has shift ≠ 0 (nondirect 0 in all 37,152 rows of the A-RPL-1 configurations) |
| `pilot_report` screen suppressed a defined flag | `screen_graph` ORs the defined campaigns; the undefined one is listed | the mixed case flags (and a light defined campaign does not) |
| `verify_result` copied the campaign coverage record; PROV optional (A-ASM-7) | the campaign record recomputed (null for test; 24 groups, 2 × the tail monitor's graphs, source = campaign_role); assemble.evaluate's provenance and tail monitor required, the role matching the label; combine's batches/combined_from required; tail-monitor flags from its listed rows | 27 new tamper cases (89/89); the pipeline's real results verify |
| The S/2 refusal named no graph (D.6) | `production._lpt_blocks` refuses naming group, graph, replicate and points before anything is created | `blocks_plan_level`: the message and no directory |

Found on the way: the first repair3a job (54672281 on 5aaa0e2) stopped with a NameError after its gates passed (the
G-JET record had landed inside the new `part_c7_shift`); 3e4b973 fixes it, and `tests/ast_scan.py` now reports reads
of undefined globals in tools/, tests/ and gen3/ (it names `do_jet` and `full` on 5aaa0e2's `validate.py`).

### Results

- **Expanse** (`benchmarks/expanse_2026-10-c8/stage_3a_integration/{5aaa0e20960f,3e4b973bb591}/`, README there):
  repair3a 54672309 on 3e4b973 passed every step (check_build; identity, G-C7 + shift case, G-JET; inspect_check 100;
  class_b (e) with the new L7 kernels; test_pilot_report --run1; seed present); the scratch probe 54672283 passed.
  21.37 SU; dev line 134.06 → 155.43 SU.
- **Mac** (`git archive` of 3e4b973; `mac_3e4b973bb591/summary.txt`): PLAN's Mac list and `make test-python`, all
  green except `verify_delivery --strict`, which passes on the export of the data-only commit that follows.

### G3a checklist after repair round 1

| Item | Evidence |
|---|---|
| Mac suite | `mac_3e4b973bb591/summary.txt` (+ `verify_delivery --strict` on the data-only commit) |
| A-KER-1..3 | J-VAL-2 54669728 (551e63e; `src/` unchanged since) and repair3a 54672309 (identity, check_build, bad_inputs in J-VAL-1 54672098) |
| A-KER-5 (L ≤ 7) | J-INSPECT 54670914; repair3a 54672309 (100 graphs) |
| A-KER-6 (a)–(e) | J-VAL-1 54672098 class_b (a)–(e); repair3a 54672309 (e) with the new zero-channel L7 kernels G1487/G1601 |
| A-KER-7 | J-VAL-2 54669728, J-VAL-1 54672098 (class_b deep fixture) |
| A-RPL-1 | repair3a 54672309 (all 3,511 + L2, both backends, nondirect totals, the shift case on the A-L18 hunk) |
| A-RPL-2 (3,511 C7(3) kernels) | repair3a 54672309 G-JET (3,512 with L2) |
| A-RPL-5 (L ≤ 7) | J-VAL-2 54669728 check_points |
| A-RPL-7 | J-RUN1 54669730 (G-RUN1 T1–T5, test-replay); the selection seed 20261004 registered (54672281) |
| A-ASM-1 | Mac (`check_vendored`, `vendored_isolated`), J-E2 54659017, J-VAL-1 54672098 |
| A-ASM-2..7 | Mac (`assembly_checks --exact`, `compat_run1`, `verify_result_tamper` 89/89, `test_pipeline`) |
| A-ORC-1..5, 7, 10..17 (fakes) | Mac (`unit_orchestration`, `lanes_tests`, `test_submit`, `test_ledger`, `cost_refresh_test`, `blocks_test`, `test_pipeline`); A-ORC-13's Linux platform class in J-VAL-1 54672098 |
| A-ORC-6 (Mac part) | `merge_scale` and `unit_orchestration` merge_and_safety (forced collision, both branches) |
| A-ORC-9 (fakes) | `test_pipeline` accounting_checks |
| A-DES-2..4 | `design_fallback_test`, `test_pilot_report` (Mac oracles, actions 1/3/5 hand values; `--run1` in 54672309), `test_pipeline` |
| A-DES-7 (a)–(e), A-DES-8 (a)–(d) | `test_pipeline`, `prefix_check` |
| A-EXP-1 | J-E0/J-E1 records (`stage_0/`), check_build in every build job, the Boost < 1.70 refusal (`native_static`), the scratch probe 54672283 |
| A-EXP-2, A-EXP-4 | Mac (`unit_orchestration`, `lanes_tests`, `test_submit`) |

**Still open (G3b and later, as PLAN stages them):** A-RPL-2 on the 262 new L7 kernels, every L8 item, A-DES-3's
power-L3 real-tail part (J-VAL-3), the benchmark tools' D.1 port (Stage 4a), C.6's R5a (Stage 4b).

## 2026-10-04 — C8(3) Stage 3a: the native kernel and worker, the orchestration and statistics, and their integration

Stage 3a ran as two tracks from `c8` at 4540d52 (after G2a), then an integration on `c8`:
- **Track N (native, PLAN C; branch `c8-3a-native`, 9 commits 97d181d..cb07dfc).** The kernel and worker
  generalization, the inspector, the Makefile and build records, the native test drivers and the inspect data for
  L ≤ 7; validated on Expanse (`debug`, nine jobs, 38.0 SU).
- **Track P (Python, PLAN D, E, F; branch `c8-3a-python`, 10 commits 4518fd7..da22d8d).** The C8(3) orchestration,
  statistics, design fallback and pilot tools, and their tests; Mac only, no SU.
- **Integration** (merge commits 7bb512a and efc35df, then the commits below). The tracks' notes,
  `docs/STAGE3A_NATIVE.md` and `docs/STAGE3A_PYTHON.md`, are folded into this entry, `docs/NUMERICS.md` and
  `docs/HPC.md`, and removed.

### Track N: native kernel and worker (PLAN C)

#### Native kernel and worker (C.1, C.2, C.3, C.4, C.7, C.9)
- `src/kernel.hpp`: the C.1 constants (`LMAX 8`, `ORDER_MIN/MAX 7/8`, `EMAX 16`, `KMAX 6`, `NLOGS 7`, `NVALUES 14`,
  `DIMMAX 31`, `MAXMASKS 16384`, `MAXTERMS 10000`, `TAILK 16`) and their `static_assert`s replace every literal size
  (`Scratch`, `PromotedScratch`, `sample()`); no literal array size 6, 12, 14 or 28 remains (A-KER-1 grep,
  `tests/native_static.py`).
- **Checked G-file reader** (C.2, round-1 R11): `read_graph(istream, path, scale)` / `load_graph(path, scale)`. One
  extraction helper (`<path>: truncated or malformed <field> (end of file|malformed)`), every check before any resize
  or index use (magic `C7D3GRAPH1`; L in [2,8]; id >= 0; wa, wb finite; M in [1,16384]; T in [1,10000]; each mask
  < 2^E with popcount L as read; per term n in [1,M] before the resize, each index in [0,M) as read, exactly E
  coefficients; the rate count 2^E, then 2^E values, then nothing). `rates()`/`prepare()` errors carry the path. The
  extractions read the same types in the same order as a6ce987's reader, so valid files load to the same values.
  Tokens echoed in messages are printable ASCII with `\xHH` escapes (`printable`).
- The A-L18 hunk `exponential(T(T(logx[j])-T(shift)/g.L))` in `calculate_shared` (F4; Boost >= 1.86 compiles).
- `src/c8d3_integrate.cpp` (`git mv` of `c7d3_integrate.cpp`): one binary, two orders. `C8D3TASKS1 <order> <L> <nt>`;
  C7(3)'s `C7D3TASKS1 <L> <nt>` is read as order 7 (HD3, input only); `K = order - L`; gamma rows with labels
  `order - l`, exactly `order - 1` logs, nothing after the last row (B1); every task, net, gamma, grid and graph error
  names its file (exit 2); `--mp-check on|off|stride16` after the 11 positional arguments; native schema
  `c8-d3-hpc-native-1` (`order`, `task_magic`, `numerics`, `mp_check`, `max_rss_kb` = VmHWM with `max_rss_source` and
  `rusage_maxrss_kb`, the `gmp` block, `libraries`); `--describe` schema `c8-d3-build-1` (orders [7,8], lmax 8, kmax 6,
  emax, dimmax, numerics `exact`, `diagnostic`, Boost, the backend-specific `gmp` block, `libraries`, C7(3)'s fields).
- **Class-B row fields** (C.3): with t = v_0·jac (v[0] after the Jacobian, before norm, weights and the jet),
  `tail_top` (16 largest |t|, descending, an equal value never displacing an earlier one), `tail_sum` (Σ|t| in point
  order), `tail_argmax` (global index of the first largest); `nondirect`, `nonmoderate`; with `--mp-check on` or
  `stride16`: `mp_checked`, `mp_hist` (18 bins: x >= −20, [−40,−20), …, [−340,−320), x < −340; the plan's last bin
  "< −320" read as "< −340", since [−340,−320) is already a bin), `mp_min_log10`, `mp_alarm` (x < −320).
- **MP self-check** (C.4): the checked MP evaluation is `calculate_shared<MP,true>` (same value operations; A-KER-7).
- `src/stream.hpp`: the net, the stream seed, the checked net and grid readers and the grid arithmetic (moved verbatim),
  shared by the worker and `c8d3_inspect --point`. `src/identity.hpp`: `--describe` and the runtime library identity
  (`dl_iterate_phdr` on the address held in `gmp_version`; `--describe` exits 3, and the worker refuses to run, when
  `gmp.h` and the loaded libgmp differ in version). `src/diagnostics.hpp`: the C.5 tier timers and ratio histograms
  (C62d's design, re-implemented).
- `src/c8d3_inspect.cpp` (C.7): `sizes PACK INDEX [THREADS]` (pack members through `read_graph`: masks, terms,
  products, segments, addends, numerators, kernel_bytes), `files GFILE...` (`load_graph`; the parser corpus entry),
  `--point GRAPH REP INDEX... -- ROOT L NET SEED LAYOUT RATE GRID` (lx, jac, y, t, |t| of a worker point). Built with
  the gmp backend so `--point` reproduces a gmp row's `tail_top[0]` bit for bit.
- Unchanged on the default path (C.9; checked by `tests/native_static.py` against `reference/src`): `rates()`,
  `prepare()` (apart from the `#ifndef C8_TEST_UNGUARDED_INDEX` pair), `calculate_reference`, `calculate_products`,
  `calculate_shared` (apart from the hunk), `sample()`'s arithmetic, every arithmetic statement of `evaluate()`, the
  stream mixing, the Kahan step, `max_abs`, the value assignment and the in-block order by points × addends.
- **Deferred to Stage 4b (as the plan stages it):** C.6's parallel NUMA-local graph load (R5a, class B, measured by
  A-PERF-2). Stage 3 keeps the serial load (PLAN C.2 ":36 ... Stage 3 keeps it serial").

**Makefile and build records (C.8).** `bin/c8d3_{gmp,decimal}` keep a6ce987's command lines token for token apart
from file names; `make c7ref` (`bin/ref/c7d3_*` from `reference/src`), `make inspect`, `make profile`, `make ratiohist`,
`make test-builds` (`bin/diag/c8d3_gmp_{notail,ordertrace}`), `make sanitize` (`bin/c8d3_{gmp,decimal,inspect}_san`,
`bin/test/point_checks_{gmp,decimal}_san`, `bin/selftest/c8d3_inspect_unguarded_san`), `make inputs-inspect`,
`make test-native` / `test-native-full`. The Boost probe refuses < 1.70 and requires 107700 unless
`BOOST_ACCEPT=<version>` (kept in the record). `NUMERICS=<profile>` is refused (no profile exists, A-FLAG).
`tools/buildinfo.py` writes `bin/<binary>.buildinfo.json` (schema `c8-d3-buildinfo-1`: `backend` from the command,
cross-checked against `--describe`'s `mp_backend`; `boost_accept`; `libprobe`). `tools/libprobe.py` (Linux): readelf,
`env -i ldd`, the `LD_DEBUG=libs` loader trace, the libgmp file's own version. `tests/check_build.py` applies A-KER-3's
backend-specific rules (and `--selftest` on canned outputs). The Makefile test of `tests/unit_orchestration.py` moved
to `tests/native_static.py`.

**Inputs: the inspect fields (B, A-KER-5).** `make inputs-inspect` = `tools/inspect_inputs.py build` (c8d3_inspect over
every packed kernel; fmax from gen3's size probe, because the maximal forest size is a property of the class, not of
the payload: terms with equal monomial lists are merged) writing `inspect/inspect.json`, then `make inputs`, which
merges the fields into the inventory rows whose member sha256 the file records (a stale row is refused) and sets
`inspect_complete`. Without `inspect/inspect.json` the inputs are byte-unchanged. `tests/check_inputs.py` (Stage 2a's
"inspect fields null" checks) must be updated with the generated-data commit (see "Merge notes").

**Native test drivers (F).** `tests/validate.py --bk8 --l2-control` (A-RPL-3, A-IN-6; the J-VAL-3 parts, run here at L7 as a tool check).
`tests/native_common.py` (shared helpers), `tools/members.py` (pack members by inventory
offset and sha256 into a private temporary tree; the L2 graph by its pinned sha256), `tests/validate.py` (identity,
G-C7, G-JET, bad_inputs, both orders at L2, random access), `tests/class_b.py` (A-KER-6 (a)–(e), A-KER-7),
`tools/tails.py` (the `graph_tails.csv` / `graph_promotions.csv` merge of C.3, for `production.py merge`),
`tests/check_points.py` + `tests/point_checks.cpp` (A-RPL-5; `--contract` for L8; `--deep` for A-KER-7),
`tests/forced_tiers.cpp` (A-RPL-4 measurement, `--point`, `--scan`), `tests/sanitize.py` (A-KER-4),
`tests/run1_replay.py` (A-RPL-7 G-RUN1), `tests/archived_stream_replay.py` (the C8 worker in order-7 mode),
`tests/inspect_check.py` (A-KER-5), `tests/native_static.py` (Mac). `slurm/native_job.sh` runs J-INSPECT, J-VAL-2,
J-VAL-4, J-RUN1 and the L7 tool check of the J-VAL-3 parts (`C8_JOB=inspect|val2|val4|run1|val3a`) in a node-local
copy of the export.

#### Evidence (track N)

`benchmarks/expanse_2026-10-c8/stage_3a_native/` (README there: one row per job). Mac: `tests/native_static.py`,
`tests/check_build.py --selftest`, `tests/inspect_check.py --no-worker`, `tests/check_inputs.py` (the Stage-2a checks
with the inspect data), `tests/unit_orchestration.py` (without its Makefile test) and `gen3/test_gen3.py` (19) pass.

**G3a native criteria.**
- A-KER-1: the grep and the constants (Mac); every bad-input case exits 2 naming its file (J-VAL-2, both backends;
  J-VAL-4 under the sanitizer builds); L = 2 at both orders; C7D3TASKS1 and C8D3TASKS1 7 give identical rows.
- A-KER-2: both orders, order 7 with L = 8 refused, widths 2(order + 1 − L), the native JSON identity fields.
- A-KER-3: `--describe` of both backends; `check_build.py` on the four records (gmp: the Spack 6.2.1 library through
  the RPATH, self-report equal to the probe; decimal: no libgmp); `--selftest` (Mac); the reference probe at use time
  in validate.py and run1_replay.py. **Open (orchestration track):** `plan`/`run` refusing a GMP worker whose runtime
  gmp block differs from its build record, and diagnostic, sanitizer and self-test executables.
- A-KER-5 (L ≤ 7): all 3,511 kernels (opcount re-derivation, M and T), and on 79 kernels the inspector's `files` path
  and the worker's ordering key (order-trace build).
- A-KER-6 (a)–(e): exact values, counters and max_abs across mp-check off/on/stride16 and the no-tail build; chunked
  tail fields; `--point` reproduces tail_top[0]; graph_tails.csv equals a hand merge; zero channel on power-L3 G7 and
  free-L6 G26. **Open:** (e) on a zero-channel NEW L7 kernel (Stage 2b packs); (d) inside `production.py merge`
  (the merge functions are `tools/tails.py`).
- A-KER-7: the deep fixture raises mp_alarm at every point (on) and at the 8 stride16 points; real rows: histograms
  sum to mp_checked, mp_checked = mp (on), stride16 counted by one-point tasks.
- A-RPL-1: G-C7 exact on the L2 graph and all 3,511 C7(3) kernels, both backends.
- A-RPL-2: G-JET on the 3,512 L ≤ 7 graphs, both backends. **Open (G3b):** the 262 new L7 kernels.
- A-RPL-5 (L ≤ 7): the hard gates pass, both backends.
- A-RPL-7: G-RUN1 T1–T5 and `make test-replay` with the C8 worker in order 7.
- J-VAL-4 (L ≤ 7) is green; A-KER-4 itself is G3b (with L8).

**Left for G3b (native):** L8 in J-VAL-2/3/4 (A-KER-4, A-RPL-5 L8 in `--contract` mode, A-RPL-3 at L8, A-RPL-4 with
`tests/forced_tiers.py`, A-RPL-6 with a `thread_identity.py` that this track has not written), A-KER-6 (f), A-KER-5
on all 24,173 kernels (J-IN-1: `make inputs-inspect` after `make inputs-l8`), A-RPL-2 on the 262 new L7 kernels, the
L2 control (A-IN-6) as J-VAL-3 evidence, the zero-channel new L7 check of A-KER-6 (e).

### Track P: orchestration, statistics and tests (PLAN D, E, F)

| Commit | Content |
|---|---|
| 4518fd7 | Component D: `tools/production.py` rewritten for C8(3) (order 8, 24 groups, HD5 allocation sources, the D.2/D.3a roles, D.5 cost bases, D.6/R10 blocks, per-index task and blocks files, D.4 atomic plan, D.7 Lustre guard, D.13 parallel merge, R06 prefixes); `tools/lanes.py` port; `slurm_submit.py` campaign entry points; `slurm/` templates and `slurm/sites/expanse/profiles.sh`; `make_cost_model.py`, `cost_identity.py`, `sweep.py`, `seeds.py`, `members.py`, `accounting.py`, `stage_runtime.py`, `bootstrap_proxy.py`; `c7_legacy/` removed; the plan input gate wired (`tests/plan_gate.STAGE3A`) |
| 8f6fc63 | Component E: `assemble.py` (order 8 on the vendored assembly), `verify_result.py`, `combine.py`, `report.py`, `design_fallback.py`, `design_adapter.py`, `pilot_select.py`, `pilot_report.py`, `prefix_verify.py`; `references/lower_order_d3.json` (C3..C7) |
| e8cf8a5 | `tests/test_pipeline.py`: the fake pipeline end to end (A-DES-7 (a)-(e)) |
| 1c72815 | `tests/unit_orchestration.py` rewritten and `tests/lanes_tests.py` added (A-ORC-1..16 fakes); `tests/assembly_checks.py` (A-ASM-2/4/5); tool fixes found by the tests |
| b7a563d | `compat_run1.py` (A-ASM-3), `verify_result_tamper.py` (A-ASM-6/7), `test_pilot_report.py` (A-DES-3/4), `prefix_check.py` (A-DES-8 (a)-(d)); tool fixes |
| d1f07c5 | `merge_scale.py` (A-ORC-6 Mac part), `cost_refresh_test.py` (D.14), `members_test.py`, `ast_scan.py`, `design_fallback_test.py` (A-DES-2); tool fixes |
| 631ce25 | `workflow.py` and `staging.py` ported (`--plan-role validation`, `--fake`); `verify_delivery.py` with R16 and its test; the plan/run read-rule spies in `check_vendored.py`; `tests/c7_view.py` and `tests/legacy_seeds.py` removed; `make test-python` |
| e785776 | A-ORC-5 memory assertions; the A-ORC-7 zero-task group test |
| 6891eb9 | the A-DES-3 design cross-check in the pipeline; `tools/reassemble_reference.py` dropped (D.1) |

#### Component D (orchestration)

- **Roles and bases.** Campaign roles: `test`, `pilot_subset`, `pilot_full` and `production` (D.3a). Plan roles:
  `campaign`, `cost_sweep`, `cost_refresh`, `flag_check` and `validation` (D.2). Cost bases (D.5):
  - `measured`, with the HD11 identity: executable sha256, CPU model and `mp_check` mode;
  - `bootstrap`: the preliminary proxy `tools/bootstrap_proxy.json`, which is never used as a cost;
  - `prior_model` (×F), for `cost_refresh` only;
  - `synthetic`: the labelled fixture, for `validation` only.

  Each campaign stores a copy of the scheduling model that planned it (`prior_cost_model.json` or
  `synthetic_cost_model.json`). Cost consumers never open that copy: `make_cost_model.py` calls
  `verify_base(scheduling_copies=False)`, and a spy checks this in `cost_refresh_test.py`.
- **Blocks (D.6, R10)** are frozen in the per-index task files, as a seventh column. The per-block records (W(B), φ,
  est_peak_bytes, the small_block record) are in `groups/<g>/tasks/s<shard>.blocks.json`, pinned by sha256 in each job
  entry. This keeps the manifest size independent of the task counts: a claim reads a fixed number of bytes whether
  the other indices hold 10^3 or 10^6 tasks (A-ORC-13).
- **The input gate** is wired. `plan` calls `prepare_inputs.plan_inputs()` first. A request that the gate makes
  test-only, for example because `l7_complete` is false before Stage 2b, is planned test-only and recorded that way.
- **Merge (D.13).**
  - Phase 1 runs in parallel over shards. Phase 2 is an external merge with fan-in F = min(--fan-in, RLIMIT_NOFILE − 32);
    it refuses when F < 2.
  - The final pass is the unchanged 50-digit Decimal summation.
  - It writes `graph_replicates`, `graph_tails`, `graph_promotions` and `graph_costs`, plus `graph_prefixes` for nested
    graphs (jets on the full-stream scale, total/P, R06).
  - `--serial` is the SQLite reference merge.
  - Quota errors stop with exit 74 in the parallel path too, because `Refuse` is picklable.
- **Lanes** (`tools/lanes.py`) follow C62d's designs (H8):
  - NUMA lane shapes come from sysfs (`numa`, `numa:k`, `socket`, n), with the `C8_SYSFS`/`C8_PROC` test overrides;
  - done markers are hints, and the lane view does bounded scans;
  - a memory guard at 0.85, the CPU-class deadline factor and the time policy;
  - drill mode, and held jobs (`launch failed requeued held`: released once, then cancelled);
  - `attempt()` runs one index.
- **Submission** (`tools/slurm_submit.py`) has the entry points `lanes N` (`--dry-run` anywhere), `submit`, `window`,
  `resubmit` and `release`, all on the Stage-0 admission engine.
  - Drill mode never uses `--exclusive` and needs 2..16 CPUs on `shared` or `debug`.
  - The merge defaults are `-A <ACCOUNT> -p shared -c 24 --mem=48G -t 02:00:00`.
  - `slurm/merge.sh` dispatches on `production.py role`: `pilot_subset` runs `pilot_report.py subset-check`; `test`,
    `pilot_full` and `production` run `assemble`; any other role exits 64.
- **D.14.** `sweep.py` picks the basis from PREV's identity:
  - the same executable sha256: measured;
  - only the sha256 differs: `prior_model` at F = 2, with the fit check before any index;
  - otherwise, or with `--refresh-bootstrap`: bootstrap.

  `make_cost_model.py` writes `scheduled_with` and `refresh_report.json`. `cost_identity.py check` compares a model
  with an executable, or the published plans with their pinned models.

#### Component E (statistics)

- **`assemble.py`**
  - `combine(order=8)` calls the vendored `campaign_moments`, `sector_assembly` and `power_null_rows`, after the
    `vendored()` sha check.
  - Before any gate it asserts coverage: loops 3..8 in both sectors and both campaigns.
  - After the gates it asserts that the top-slot rows are exactly 3..8 and the affinity loops exactly 5..8.
    `loop7_gate` runs only at order 8; at order 7 the result records "not applicable at order 7".
  - The `power_null_rows` input guards are: length, finite values, a positive SE at orders ≥ 4, and a finite pull at
    orders 4..8 (naming the row).
  - The PP8 marker is set on an order-6 flag, with a FLAG line.
  - It reports:
    - the lower-order pulls C3..C7 against `references/lower_order_d3.json`;
    - the b̂₃ᵖ(0) control pull;
    - the a/b pull and the bootstrap/covariance ratio flags;
    - `error_by_loop`, the half streams and the bootstrap (seed 70530413);
    - the tail monitor.
  - Test, pilot and partial results hold no physical number at the top level.
  - The power-protocol and assembly pin blocks come from `protocol_block()` and `assembly_block()`.
- **`verify_result.py`** recomputes the following from the result's own fields:
  - the coefficients, the gates, the null rows (with PP8), the pulls and the consistency flags;
  - the coverage records;
  - the pin blocks;
  - the variance identities: SE_i = √V_ii, and V_nn = power_free_se² + power_correction_se² + 2·cross.

  A changed value, an added key or a deleted key is rejected.
- **`combine.py`** combines batches only when they share the same bundle, inputs manifest, numerics and rates
  identity. The rates identity is read from the group configs (`default` = a .8, b .7). Seeds must be distinct, and
  the batch count must equal the plan's, or be fewer with `--partial`. It reports the inter-batch χ².
  `coverage_guard` names a missing bundle counts file.
- **`pilot_select.py` and `pilot_report.py`** (E.6–E.8, RECON 6.3.6).
  - Every tail row goes through `rows_at()`, which asserts the length rule (R06).
  - `tail_stats` adds the excess Hill index, using the replicate mean |t| = tail_sum/n.
  - `confirm_graph(alpha=)` adds the variance ratio normalized by 8^−(2α̂−1). `full()` therefore computes α̂ before
    the PC confirmations.
  - The cost table applies the realism factors F_G = P_G κ_G ρ.
  - Item 12 is the c4(R_PF)²-corrected held-out penalty.
- **`design_fallback.py`** is labelled `fallback` throughout, and a non-test plan from it needs `--approved-fallback`.

#### Component F (tests, Mac)

| Test | Criteria |
|---|---|
| `unit_orchestration.py` (+ `lanes_tests.py`) | A-ORC-1, 2, 3, 4, 5 (fake part), 6 (Mac), 7, 10, 13, 14, 15, 16; D.3 selection files; HC1/HC5 roles; first-sweep bootstrap; zero-task groups |
| `blocks_test.py` | D.6 `cut_blocks` (A-ORC-3, R10) |
| `test_pipeline.py` | fake end to end; A-DES-7 (a)-(e); design batches and combine |
| `test_submit.py`, `test_ledger.py` (Stage 0) | A-ORC-9, 11, 12, 17 |
| `cost_refresh_test.py` | D.14 X → Y → Z, HD11, `cost_identity.py`, the never-a-cost spy |
| `prefix_check.py` | A-DES-8 (a)-(d) (`--real` = (e), Expanse) |
| `merge_scale.py` | A-ORC-6 (Mac sizes; record `benchmarks/expanse_2026-10-c8/stage_3a/merge_scale_mac.json`) |
| `assembly_checks.py [--exact]` | A-ASM-2, 4, 5 (PP1–PP10) |
| `compat_run1.py` | A-ASM-3 (record `benchmarks/expanse_2026-10-c8/stage_3a/compat_run1_mac.json`) |
| `verify_result_tamper.py` | A-ASM-6, A-ASM-7 |
| `test_pilot_report.py` | A-DES-3 (Mac part), A-DES-4 |
| `design_fallback_test.py` | A-DES-2 (with the A-DES-1 list on 24,173 synthetic graphs) |
| `members_test.py`, `ast_scan.py`, `test_delivery_verifier.py`, `archived_replay.py` | F rows |
| `workflow.py --fake`, `staging.py --fake` | the inherited workflow and staging tests, ported (real worker without `--fake`) |
| `check_vendored.py`, `check_inputs.py`, `exact_keys.py` | A-ASM-1 and the plan/run read-rule spies; A-IN-*; the exact-check keys |

`make test-python` runs this set.

**Mac results, 2026-10-04** (Apple M1 Max, Python 3.10.12, numpy 1.24.4, `LRI_C8_D3_HPC_loop/venv_mac`;
`C8_ALLOW_NO_L8=1`):

| Test | Result | Seconds |
|---|---|---|
| `unit_orchestration.py` | passed (15 items) | 315 |
| `test_pipeline.py` | passed (7) | 135 (150 with the A-DES-3 design cross-check, re-run after 6891eb9) |
| `test_submit.py` / `test_ledger.py` | passed (42 / 22) | 68 / 14 |
| `cost_refresh_test.py` / `prefix_check.py` / `members_test.py` | passed (5 / 3 / 1) | 71 / 34 / 1 |
| `assembly_checks.py --exact` / `compat_run1.py` | passed (3 + exact keys) / passed | 14 / 0.5 |
| `verify_result_tamper.py` / `test_pilot_report.py` / `design_fallback_test.py` | passed (62 checks / 8 / 5) | 2 / 22 / 12 |
| `blocks_test.py`, `ast_scan.py` (0 findings), `archived_replay.py`, `test_delivery_verifier.py`, `exact_keys.py` | passed | ≤ 1 each |
| `workflow.py --fake` / `staging.py --fake` | passed (gmp and decimal fakes) | 19 / 19 |
| `merge_scale.py` | passed | 254 |
| `check_vendored.py` | 24 / 25 | 35 |
| `check_inputs.py` | 49 / 50 | 51 |

The single failure in each of the last two is the plan_gate "untouched" scenario. The wired `plan` refuses the live
inventory because its L ≤ 7 rows have no inspect fields (`products`, `segments`, `addends`, `numerators`,
`kernel_bytes`, `fmax`); `make inputs-inspect` (track N) fills them. Every other wired scenario passes. So do the plan
and run read-rule spies, and plan_gate on simulated post-Stage-2b inputs.

### Integration on `c8` (merge commits 7bb512a, efc35df; then 9f14cf8, 551e63e, b335aeb, a372664 and the evidence commit)

- **Merge conflicts.** `Makefile`: `test-python` is track P's list plus `tests/integration_3a.py`,
  `tests/native_static.py` (the C8(3) Makefile test that moved out of `unit_orchestration.py`) and
  `tests/check_build.py --selftest`; `test-native`/`test-native-full` are track N's; `test-full` runs
  `tests/compat_run1.py` in place of the dropped `tools/reassemble_reference.py`. `tests/unit_orchestration.py`: track
  P's rewrite. `tools/members.py` (added on both branches): one module with both interfaces (track N's
  `extracted([(sector, L, id)])` and `inventory()` with the pinned L = 2 graph; track P's `extract([(sector, L, [ids])])`
  context manager, the `C8_INPUTS` default and the L ≥ 7 `MEMBERS_d3.sha256` check); the CLI takes either form and
  exits 1 on a refusal.
- **The worker contract (9f14cf8).**
  - `tests/archived_stream_replay.py` rebuilds C7 with `assemble.combine(order=7, bootstrap=0)` (A-RPL-7); the
    pre-merge `assemble.calculate` no longer exists, so `make test-replay` would have failed. On the Mac, the archived
    rows give C7 to 1.6e-15 relative.
  - `production.py describe()`: the build record keeps the `gmp` block under `describe.gmp` (`tools/buildinfo.py`), so
    A-KER-3's runtime-versus-record comparison never ran on a real record; it now reads that block. A GMP worker
    without the block and a decimal worker whose `gmp.applicable` is not false are refused.
  - `production.py validate_checkpoint()`: `run` and `merge` refuse a block whose worker reports a runtime `gmp` block
    other than the planned build's (A-KER-3's "plan and run refuse"; track N's open item).
  - Under `--mp-check off` the native worker omits the MP self-check fields (C.3); `validate_checkpoint` rejected
    every such row as "invalid class-B fields" and the run files needed the fields. Both now read them as 0/null.
    `mp_min_log10` `"-inf"` (an exact zero at the MP tier) is accepted; it was rejected as non-finite.
  - `graph_tails.csv`'s `tail_sum` is the exact `Decimal` sum of C.3 (precision 2000, `Inexact` trapped), not a
    50-digit sum.
  - `tools/tails.py` writes `production.py merge`'s layout of `graph_tails.csv` and `graph_promotions.csv` (the one the
    statistics tools read; track N's layout differed) and is the independent merge the tests compare with:
    `tests/workflow.py` now requires every group's two files to equal it byte for byte (A-KER-6 (d) inside
    `production.py merge`, track N's open item), and runs its decimal campaign with `--mp-check off`;
    `tests/class_b.py`'s hand merge follows the layout. `tests/fake_worker.py` omits the MP fields under `off` like the
    native worker, and `C8_FAKE_RUNTIME_GMP_LIBRARY` reports another loaded libgmp.
  - `tests/integration_3a.py` (new, in `make test-python`): the A-KER-3 refusals at plan and run time and the C.3 row
    forms.
- **Found by the Mac suite on a git-archive export of the merge.**
  - `tests/unit_orchestration.py` `first_sweep_bootstrap` ran `git archive` on the package, so it failed on any export
    (J-VAL-1 runs on one); without `.git` it now copies the same three paths.
  - `tests/check_vendored.py`'s read-rule scratch package lacked `inspect/`, so `make inputs` there rebuilt a manifest
    without the inspect fields and "its manifest equals the package's" failed once the inspect data was committed.
  - `tests/merge_scale.py` takes `--many-shards N` (default 500), the option PLAN's Mac command line uses.
- **`slurm/native_job.sh` `C8_JOB=val1`** (J-VAL-1 on the cluster export, step by step; `docs/HPC.md`).
- **Docs.** `docs/NUMERICS.md`: order modes, class-B fields and the merge layouts, the MP self-check, identity
  (A-KER-3), the Stage-3a gates; stale C7(3) references corrected. `docs/HPC.md`: "Campaigns" (track P's component D
  text), "Stage-3a validation jobs", the Mac test list, the Stage-3 stub closed, the C7(3) runbook marked as a record.
  `README.md`: the C8(3) state, build and test targets.
- **Found by J-VAL-1 on Expanse (b335aeb, a372664).**
  - Test campaigns planned in node-local scratch inherited `C8_SITE=expanse` from `~/c8d3/env.sh`, so D.7's Lustre file
    guard ran `lfs quota` on a non-Lustre path and refused every plan (69): `plan_gate` (via `check_inputs`),
    `check_vendored`'s plan spy (which then crashed on a missing `procs` key), `workflow` and `staging`. These harnesses
    no longer pass `C8_SITE` to their scratch plans.
  - The `C8_SITE=fake` Mac fakes of the admission engine are refused on an Expanse node by A-ORC-17's site detection,
    by design. `slurm/native_job.sh` val1 runs `unit_orchestration.py` one function per step and records exactly that
    refusal as `SITE_REFUSED` (Mac evidence), never as a pass.
  - `common.io_fault` ignores `C8_TEST_IO_FAULT` on Expanse, so `atomic_and_guards` runs the EDQUOT injection only
    where it is honoured and otherwise checks that a requested fault is inert.
  - `tools/profile.py` dropped (D.1); the J-E2 records (job 54659017 on 8250107, numpy 2.3.5, passed) copied into
    `benchmarks/expanse_2026-10-c8/stage_v/expanse_e2_8250107f3f58/`.

#### Results (evidence: `benchmarks/expanse_2026-10-c8/stage_3a_integration/`)

- **Mac** (`git archive` of a372664; M1 Max, Python 3.10.12, numpy 1.24.4, `C8_ALLOW_NO_L8=1`): all 30 commands of
  PLAN's Mac list and `make test-python` pass (unit_orchestration 15, test_pipeline 7, test_submit, test_ledger,
  cost_refresh_test, blocks_test, prefix_check, test_pilot_report, design_fallback_test, members_test, workflow and
  staging `--fake`, integration_3a, native_static, check_build `--selftest`, ast_scan, archived_replay,
  test_delivery_verifier, exact_keys, check_inputs 50/50, check_vendored `--standalone` and full 25/25,
  vendored_isolated `--in-place`, assembly_checks `--exact`, compat_run1, verify_result_tamper, gen3/test_gen3,
  inspect_check `--no-worker`, merge_scale `--rows 20000 --many-shards 500`), except `tools/verify_delivery.py
  --strict`: `DELIVERY_MANIFEST.json` is still C7(3)'s (it failed at 4540d52 too) and is regenerated at delivery
  (A-PKG, Stage 5).
- **Expanse** (shared/debug, EPYC 7742, GCC 13.3.0, Boost 1.77, Spack GMP 6.2.1, Python 3.11.9, numpy 2.3.5;
  `bin/c8d3_gmp` 24adff54…, identical to track N's):
  - J-VAL-1 on a372664 (54672098): 37 PASS, 10 SITE_REFUSED, 0 FAIL; check_inputs 49/49, check_vendored
    `--no-review-record` 24/24, vendored_isolated `--in-place` (30 / 21 + 9 skipped; `:134` 0 ulp), compat_run1 0 ulp,
    unit_orchestration's `per_index_and_spies` on the Linux path (A-ORC-13 platform class), workflow and staging with
    the real workers.
  - J-VAL-2 (L ≤ 7), J-RUN1, J-VAL-4 (L ≤ 7) and the J-VAL-3 tool check on 551e63e (whose native drivers and `src/`
    a372664 keeps unchanged): all passed. J-RUN1: G-RUN1 T1–T5 as track N; test-replay 168,528 rows, 162,044 bitwise,
    max 1.01e-11, C7 rebuilt by `assemble.combine(order=7)` to 1.0e-15 relative.
  - J-INSPECT on b335aeb: `make inputs-inspect` reproduces the committed inspect data, inventory and manifest byte for
    byte.
  - 44.95 SU (dev line 83.64 → 128.59); with track N, Stage 3a used about 83 SU.

#### Open after Stage 3a

- A-KER-6 (e) on a zero-channel **new** L7 kernel, A-RPL-2 on the 262 new L7 kernels and every L8 item: Stage 2b/3b
  (G1b, G2b, G3b).
- **A-DES-3's Expanse part is missing:** `tests/test_pilot_report.py` has no `--run1` mode (PLAN's J-RUN1 row runs
  `tests/test_pilot_report.py --run1`: run1's 27 of 590 power-L7 graphs and P̂8 1.078–1.103 reproduced from the
  archive). Neither track wrote it; it is a G3a item still to do (its power-L3 real-tail part needs J-VAL-3, G3b).
- `$C8_SEEDS` does not exist on Expanse yet (Stage 0 item); the G-RUN1 selection seed 20261004 is registered with
  `tools/seeds.py add --seed 20261004 --label ...` when it does, before any non-test plan.
- `tools/benchmark.py`, `prepare_benchmarks.py`, `benchmark_production.py` and `benchmark_memory.py` are still C7(3)'s
  (`bin/c7d3_gmp`, `C7D3TASKS1`); their D.1 port belongs to Stage 4a (P1–P4).
- C.6's parallel NUMA-local graph load (R5a) is deferred to Stage 4b, as the plan stages it.
- `DELIVERY_MANIFEST.json`/`SHA256SUMS`: regenerated with `tools/verify_delivery.py --write` at delivery.

## 2026-10-04 — C8(3) Stage 2a repair round 2: `plan_gate` on a fixed input state, not the live inputs

- **Finding.** `tests/plan_gate.py` (repair round 1) ran its scenarios on the live inputs. Its `untouched` case
  expected `test_only` true from them, and `_run` stripped `C8_ALLOW_NO_L8`. That works only while the live inputs
  stay in the Stage-2a state. Nothing in the plan's stage order guarantees that: Stage 2b needs only G1b and the
  Stage-3a inspector, so it can land before or after `plan` calls `plan_inputs`. After Stage 2b:
  - on Expanse, with L8 present, a correct wired `plan` is rightly not test-only, so `untouched` failed. That would
    turn `check_inputs.py` red against A-IN-5 at G2b and in J-VAL-1/2;
  - on the Mac, with L8 pinned but absent, `verify()` refused the missing `free_L8.pack` because `C8_ALLOW_NO_L8` was
    stripped, so `untouched` and `vendored` failed.

  Both failures were reproduced in a scratch package with the correct fake wired planner (see the evidence README).
  The repair-round-1 claim that Stage 3a is "the only window" for these checks rested on an ordering the plan does
  not impose. It is corrected below.
- **`tests/plan_gate.py`.**
  - **The fixed state.** `fixed_inputs()` first puts the scratch package's `inputs/` into a fixed input state,
    whatever the live stage:
    - the live manifest, with `l7_complete` and `l8_present` false;
    - no pin, count or inventory row of a loop above 7, and any L8 pack removed from the scratch package;
    - the kernel total recounted, and the inventory repinned when rows were dropped.

    Every other pin and file stays the live one. At Stage 2a the live inputs are already in this state, so nothing is
    rewritten. The function refuses to run on the checkout.
  - **A new precondition check (`fixed-state`).** The scratch package's own gate (`prepare_inputs.py gate`, a
    non-test request) must pass the fixed state, skip nothing and make the plan test-only because of `l7_complete`.
    If a later `verify()` refuses the fixed state, this check fails with the gate's message, and `fixed_inputs()` is
    the thing to adapt.
  - **`untouched`** expects `test_only` true from the fixed state.
  - **Environment.** `_run` now passes `C8_ALLOW_NO_L8` through when the caller sets it, as the plan's Mac command
    does. It still strips `C8_INPUTS`, `PYTHONPATH` and `PYTHONPYCACHEPREFIX`.
  - **Check labels.** Every check carries a `scenario` name: `fixed-state`, a scenario, or `obligation`.
  - **Self-test helper.** `fake_stage2b_inputs()` simulates the post-Stage-2b inputs: `l7_complete` and `l8_present`
    true, synthetic L8 packs pinned (present or absent), their counts and inventory rows.
- **`tests/check_inputs.py`.**
  - It passes `C8_ALLOW_NO_L8` to the runner as the caller set it.
  - The self-test reads failures by scenario name.
  - A new self-test check runs the correct fake wired planner on simulated post-Stage-2b inputs. Each simulated
    state is first confirmed by the real gate:
    - Expanse (L8 present): the gate no longer makes a non-test plan test-only;
    - the Mac (L8 absent): the gate refuses without `C8_ALLOW_NO_L8` and skips with it.

    In both cases the runner must reach the fixed state and the planner must pass every scenario.

  Result: 50 checks, 50 passed.
- **`tests/check_vendored.py`** (b) runs on the fixed state and records it in its notes. Result: 23 checks, 23 passed.
- **Docs.** `docs/HPC.md` "Inputs", the Stage 2a "Deferred" entry (corrected), and the evidence README
  (`benchmarks/expanse_2026-10-c8/stage_2a/README.md`, new `repair2_mac/`).
- **Unchanged.** The tools, the generated inputs, and every other check. Mode at this commit: transitional. Stage 2b
  need not retarget `plan_gate`. Its `check_inputs.py` changes (`EXPECTED_FILES`, the L8 part) are its own work.

## 2026-10-04 — C8(3) Stage 2a repair round 1: A-IN-4 and A-ASM-1(b) through the real `plan`, a Stage-3a obligation

- **Finding.** A-IN-4 and A-ASM-1(b) say that `plan` refuses or becomes test-only. Stage 2a checked these clauses only
  on `prepare_inputs.plan_inputs()` and `verify()`, because `production.py plan` is still the C7(3) planner and its
  `prepare()` refuses every request. No gate re-ran them on the real `plan` after Stage 3a wires the gate in:
  - G3a does not list A-IN-4;
  - check_vendored's carry-forward note covered only the read-rule spies;
  - at G2b, `l7_complete` is already true.

  So a Stage-3a port that ignored the gate's `test_only`, or created the campaign directory before calling the gate,
  would have passed every listed gate.
- **`tests/plan_gate.py`** (new). This runner sends four non-test `production.py plan` requests in a scratch package
  with the real `l7_complete: false` inputs, each into a fresh campaign path:
  - the untouched package, which must come out test-only (`manifest.json` `test_only` true);
  - a one-byte change to `inputs/packs/free_L7.pack`, refused with the gate's `Checksum mismatch` naming the file;
  - a one-byte change to `vendor/c8_assembly/order8_assembly.py`, refused the same way;
  - a foreign `C8_INPUTS`, refused.

  After every refusal there must be no campaign directory, nothing beside the campaign path (no plan temporary
  directory), nothing in the child's `TMPDIR`, and no package file created, removed or changed.
  - **Modes.** The mode is *transitional* if `tools/production.py` does not name `plan_inputs` (ast) and the untouched
    request is refused with `prepare()`'s Stage-3a message. In that mode every scenario must be refused that way,
    creating nothing. Otherwise the mode is *wired* and the expectations above apply. A port that drops `prepare()`
    without calling the gate is classed as wired and fails.
  - **The obligation.** In wired mode the runner needs `plan_gate.STAGE3A`: the ported plan's non-test arguments, the
    package paths `plan` needs (`bin/`, …) and the key of the test-only flag. While it is `None`, the wired check
    fails and names the obligation.
- **`tests/check_inputs.py`.** It runs all four scenarios, replacing the single transitional planner check. A
  self-test runs fake wired planners through the same runner in a copy of the scratch package:
  - a correct planner passes;
  - planners that ignore the gate's `test_only`, create the campaign directory first, create a `TMPDIR` entry first,
    or never call the gate (wired by behaviour) fail exactly the expected scenarios;
  - a correct planner with `STAGE3A` unset fails, naming the obligation.

  Result: 48 checks, 48 passed.
- **`tests/check_vendored.py`** (b) also runs the untouched and vendored-flip scenarios through `production.py plan` in
  its `git archive` export (22 checks, 22 passed). Its notes record the G3a obligation beside the read-rule spies
  still to come.
- **Docs.** `docs/HPC.md` "Inputs", the Stage 2a "Deferred" entry below, and the evidence README
  (`benchmarks/expanse_2026-10-c8/stage_2a/README.md`, new `repair1_mac/`).
- **Unchanged.** The tools, the generated inputs and every other check. Mode at this commit: transitional.

## 2026-10-04 — C8(3) Stage 2a: the C8(3) inputs (component B; G2a = A-IN-1, A-IN-2, A-IN-4 for L ≤ 7, A-ASM-1(b))

- **`tools/prepare_inputs.py`** (rewritten; `make inputs` = `build`, `verify`, `gate`):
  - **Low-loop files.** `inputs/two_loop.json` (7 B2 strings, order 8) and `inputs/gamma_d3_8.txt` are byte copies of
    the vendored `inputs_d3/` files. They are read only after the HANDOFF copy and every vendored file have matched
    their pins (HD4). The vendored `prepare_low8.py --d 3` then runs in compare mode as a separate `python -B`
    process with the fixture `LRI_ROOT`. Exit 0 with three files identical is required and recorded.
  - **Order-7 files.** `inputs/order7/{two_loop.json,gamma_d3_7.txt}` are C7(3)'s.
  - **Packs.** The L3–L7 packs are rebuilt from `reference/inputs/` and checked against a6ce987's sha256. L7 still
    holds 2,298 + 590 kernels, and `l7_complete` is false.
  - **Inventory.** The rows have the PLAN B fields: `s_G` from the header weights, `wa`/`wb` as header text, and
    `double_lift`, the subsets with raw p4 ≤ −5, from a numpy port of `regenerate_rates`' valuation. The inspect
    fields are null and `inspect_complete` is false until Stage 3a. One row per line.
  - **Manifest** `c8-d3-hpc-inputs-1`. It records the 15 pinned files, the counts, `l7_complete`, `l8_present` and
    `inspect_complete` (all false), the H1 and d3 pins (null until Stage 2b) and the vendored pins from
    `tools/VENDORED.json`.
  - **Build.** The build is deterministic and staged. It leaves unchanged files alone and never touches the Stage-2b
    L8 packs.
  - **`verify()`** checks the schema (a C7(3) manifest and a dimension-2 manifest are refused, HD7), every pinned
    file and the vendored files. It skips missing L8 packs only under `C8_ALLOW_NO_L8=1`, printing `SKIPPED`.
  - **`plan_inputs(test_only)`** is the plan's input gate. A non-test plan with a foreign `C8_INPUTS` is refused.
    `l7_complete`/`l8_present` false, a skipped L8 pack or a foreign `C8_INPUTS` make the plan test-only.
  - **Transitional.** `prepare()` refuses: the unported C7(3) planner now stops before creating anything. Its wiring
    to `plan_inputs` is Stage 3a.
- **`tools/common.py`**: `verified_bytes` (the bytes whose sha256 was checked, read once); `read_verified` uses it.
- **Generated data.** `inputs/` is rebuilt by `make inputs`:
  - new files: `two_loop.json` (order 8), `gamma_d3_8.txt`, `order7/`, the new inventory and the new manifest;
  - removed: `gamma_d3_7.txt` (now `order7/`) and `primitive_reference.json` (HD5);
  - the packs are unchanged.
- **`tests/check_inputs.py`** (new; `make check-inputs`, part of `make test-python`) checks:
  - the byte-identical regeneration of every tracked input, with no stale file;
  - the manifest;
  - A-IN-1 (vendored bytes and HANDOFF sha256s, the gamma rows, the L = 8 norm to 60 digits);
  - A-IN-2 (lengths and prefixes, and `gen3/check_dimension8.py` on the package inputs);
  - the inventory against a6ce987 and gate 6 for L ≤ 7 against `gen3/pins/PINS.json`;
  - `double_lift` against `gen3/g3common.d3_rates`;
  - A-IN-4 for L ≤ 7 on the gate in scratch packages.
- **`tests/check_vendored.py`.** The read-rule spy now covers `prepare_inputs.verify()` (vendored files hashed only
  through `common.digest`, no process) and `make inputs`:
  - vendored files are opened only through `digest`/`verified_bytes`, the latter for the HANDOFF copy and the two
    copied `inputs_d3/` files;
  - exactly one process runs, `prepare_low8.py --d 3` under `-B`;
  - the scratch build's manifest equals the package's.

  The negative control now also opens a vendored file directly and starts a process.
- **The inherited C7(3) tests** run in scratch packages on the C7(3) input view of `tests/c7_view.py` until their
  Stage-3a port. That view has a6ce987's manifest, inventory and primitive reference in `tests/fixtures/c7_inputs/`,
  the order-7 files, hard links to the unchanged packs, and a6ce987's `prepare_inputs.py`.
  - `unit_orchestration.py` imports the campaign tools of its scratch package (`pkg_module`).
  - `assembly_checks.py` runs the C7(3) `assemble.py` from such a package. Its output is unchanged.
- **Makefile**: `inputs` runs `prepare_inputs.py build`. New targets `verify-inputs` and `check-inputs`.
  `test-python` runs `check-inputs` instead of `inputs`.
- **Docs**: `docs/HPC.md` "Inputs", `docs/NUMERICS.md`, `README.md`, `tests/fixtures/README.md`.
- **Deferred.**
  - To Stage 2b: L7 complete, the L8 packs (`make inputs-l8`), the H1/d3 pins, `selection.json`, `inputs_mini`, and
    `check_inputs.py`'s L8 part.
  - To Stage 3a: `make inputs-inspect`, `production.py plan` calling `plan_inputs`, the plan and `run --index` spies,
    and the port of the C7(3) tools and Expanse tests that still read a6ce987's layout (`validate.py`, `workflow.py`,
    `staging.py`, `check_points.py`, `archived_stream_replay.py`, `stage_runtime.py`, the benchmark tools).
  - **Test obligation with that wiring** (added in repair round 1; corrected in repair round 2). Once `production.py
    plan` calls `plan_inputs`, `tests/check_inputs.py` and `tests/check_vendored.py` (b) repeat their checks through
    `production.py plan`. They run in scratch packages on `plan_gate`'s fixed input state (`l7_complete` false, no L8
    pin), whatever the live stage, so before or after Stage 2b. The checks are:
    - the one-byte flips of a pinned L ≤ 7 input (`packs/free_L7.pack`) and of a vendored file, refused;
    - a foreign `C8_INPUTS` on a non-test plan, refused;
    - `l7_complete: false`, which makes a non-test request a test-only plan.

    Each refusal must leave no campaign directory and no plan temporary directory. These runs are G3a evidence, under
    A-ASM-1 (Mac) and A-IN-4 (L ≤ 7). G3a does not list A-IN-4, so `tests/plan_gate.py` enforces them: see the
    repair-round-1 and repair-round-2 entries above. Repair round 1 said that Stage 3a was "the only window" for these
    checks, because at G2b `l7_complete` is already true. That was wrong: the plan does not order Stage 2b after the
    Stage-3a wiring. Since repair round 2 the checks do not depend on the live stage, and they hold at G3a whether
    Stage 2b has landed or not.

## 2026-10-04 — C8(3) Stage 1a: host notes after verification

- Deferred to Stage 2b (J-IN-1), with gate 6: the `make inputs-l8 D3PAYLOAD=… D3PIN=…` target, which refuses to run
  without `D3PIN` and runs `verify_d3.py --pin` before reading any member, and its `test_gen3.py` cases (no pin, wrong
  pin; PLAN A.2 step 6, A-INV-5).
- To do in Stage 1b: gate 5(a) records a binary sha256 that differs from the MANIFEST only as `equal: false`. The plan's
  gen3 F row asks for a printed warning flag ("passes with a warning"); add a `warnings` list and assert it in
  `test_tool_gate5_logic`.
- docs/HPC.md: a missing required job-script variable exits 1 (bash `${VAR:?}`), not 64.

## 2026-10-04 — C8(3) Stage 1a repair round 1 (review of the Stage 1a build)

- **Publication (A.2 step 5, A-INV-5).** `publish_d3.py` no longer requires `"passed"` in every `gates/*.json`: the
  seven gate records (`g3common.H1_GATES`) must be present and pass; their supporting records
  (`g3common.GATE_SUPPORT`) must be present and, carrying `passed`, say true; H1's raw `check_edge_forests` outputs
  (`gate3_edge_forests_L{7,8}.json`, no `passed`) are published unchanged, `gate3.json` being their verdict. Before,
  J-GEN-D3 would have run its two hours and failed at publication. The four builder side files of A.2 step 2a are
  published under `d3_payload/gates/gate5/` (new required `--side`; listed in `SHA256SUMS` and `MANIFEST_d3.json`).
- **Gate 1(a) platform rule (A-INV-2(a)).** `a_inv_2a` is true only for a full pass on Expanse x86-64 (machine
  `x86_64`, a numeric `SLURM_JOB_ID`, `C8_SITE=expanse`); any other run is `run_class: "rehearsal"`.
  `gates_d3.py summary-gen-d3-0` writes `jgen_d3_0.json` (G1a only on Expanse; an off-Expanse dry run exits 0 only
  with `C8_GEN3_REHEARSAL=1` and still says `passed: false`), and `gates_d3.py report` re-derives the rule and refuses
  a rehearsal, including the committed Mac dry run of `1289f3a`.
- **Job scripts (D.10).** `slurm/h1_copy.sh` (J-H1-COPY) and `slurm/gen_d3.sh` (J-GEN-D3): the D.10 preamble, inputs
  as environment variables (`C8_PACKAGE`, `C8_H1_PIN`, `C8_H1_SOURCE`, `C8_H1_BEFORE`), every path computed inside the
  job, start checks (exit 64). `docs/HPC.md` "Stage 1b" gives their `slurm_submit.py raw` lines.
- **Scratch.** All three job scripts export `TMPDIR=$C8_SCRATCH/tmp`, so g++ and `test_gen3.py --sanitize` no longer
  write to the node's `/tmp`.
- **Tests** (`gen3/test_gen3.py`, 19 on the Mac): the publication of the real gate-file set and the side files, the
  platform rule, the summary, the report's refusals, and the three job scripts on a fake package export.

## 2026-10-04 — C8(3) Stage 1a: the regenerate_rates port, the gen3 gate tools, J-GEN-D3-0 (component A)

- **`gen3/regenerate_rates.cpp`** (A.1, round-1 R11). The rate formula, the header copy and the printing are
  unchanged, so L <= 7 outputs keep their bytes. New: no `num_threads(3)`; L <= 8 with uint64 ids and size_t 2^E
  arrays; the checked reader (each check before the allocation or index it guards; canonical integers; finite decimal
  weights; masks < 2^E, popcount L, strictly increasing; term lengths in [1,M], indices in [0,M) strictly increasing,
  exactly E coefficients; the input's rate block read to EOF); a checked job list (even, non-empty, no repeated output,
  nothing under C62d's trees); per-job error slots, `.tmp` outputs renamed only after every job succeeded, exit 2 with
  `<path>: <field> <reason>` and no stdout otherwise; the record adds `raw_histogram`, `min_raw`,
  `double_lift_subsets`. Test-only `C8_TEST_UNGUARDED_INDEX` for the coverage self-test (C.7).
- **Makefile**: `make gen3` (A.1's exact command; `size_probe`) and `make gen3-sanitize` (the sanitizer build and the
  self-test build); a compiler warning fails the build; `<binary>.build.txt` per binary.
- **Gate tools** (A.2-A.4): `gates_d3.py` (gate1a; h1-copy, source-unchanged, split-audit, gate1b, gate2, gate3,
  gate4, gate5, gate7, determinism), `opcount.py` (vendored recon script, split whole at L8), `weights_check.py`,
  `kirchhoff3.py`, `forest_check.py` (ported to H1's side files, strict reader, own memoized recursion),
  `check_dimension8.py` (port to order 8: lengths 7/6/5 asserted per file, prefixes through `zip(strict=True)`, the
  independent b_{2,0..6}(3) recomputation, 42 gamma comparisons), `publish_d3.py`, `verify_d3.py`, `g3common.py`,
  and the driver `run_d3.sh` (`--pre-h1`, `--h1`). Every writer refuses C62d's trees.
- **Pins**: `gen3/pins/c7d2_frozen_d2.sha256` (the 3,774 frozen C7(2) d=2 payloads; the Stage-0 Expanse copy
  `$C8_STORE/c7d2_frozen/` has the same list digest, 26b44747…) and `gen3/pins/PINS.json`.
- **`gen3/test_gen3.py`**: A-INV-1 (targeted cases, mixed list, 2,000-mutant corpus seed 8814, idempotence and
  records against a Python recomputation, the self-test with `--sanitize`), the gate tools on miniature fixtures
  (A-INV-5's one-byte changes at every level, gate 2's alterations, gate 5 (a)-(d) logic, check_dimension8's
  lengths), A-INV-6's refusal and intake, and the injected failing gate in `run_d3.sh` (no publication).
- **`slurm/gen_d3_0.sh`**: J-GEN-D3-0 (G1a). `docs/HPC.md` "d=3 payloads" gives the submission and the Stage-1b jobs.
- **Mac evidence** (`benchmarks/expanse_2026-10-c8/stage_1a/`): gate 1(a) 3,512 / 3,512 byte-identical (arm64,
  g++-16), test_gen3 plain and under the sanitizers, and read-only pre-checks on H1's L7 data and inventories.
- **Observation** (not a gate): the 119 power L7 kernels with s_G = 4 that C7(3) never integrated carry 2 subsets
  with raw p4 = -9 (a triple lift, rate 3/4); the 590 C7(3) ones reproduce RECON's 42 double-lift graphs (106 raw -6).

## 2026-10-04 — C8(3) Stage V: the assembly HANDOFF f5ff6a353371, vendored (component E.1, A-ASM-1)

- **Delivery.** `LRI_C8_shared/assembly/HANDOFF_assembly.json` (sha256 `f5ff6a353371…`, 2026-10-03) passed C62d's
  H2 review (`LRI_C8_shared/inventory/reviews/order8_assembly_f5ff6a353371.json`: ACCEPT_WITH_MINOR, no required
  change; step-0 decision `accepted_documentation_only_minor_fixes`, for this HANDOFF version only) [F11, F12].
- `vendor/c8_assembly/`: the 13 files the HANDOFF lists, byte-identical at its sha256s (md5 and sizes checked too),
  and the HANDOFF copy. No vendored byte differs from the delivery.
- **Read set** (C63d's own measurement). `tools/vendor_assembly.py` ran the HANDOFF's tests (30 passed),
  `exact_check.py` and `prepare_low8.py --d 3` on a temporary copy outside <PROJECT> with `LRI_ROOT=<PROJECT>`,
  under an open-audit hook in every Python process. It measured 50 files, 555,995 bytes, under `LRI_ROOT`. That is
  the same set at the same sha256 as C62d's `handoff-tests/external_read_set.json` (E.1's stop rule did not
  trigger). Evidence: `benchmarks/expanse_2026-10-c8/stage_v/read_set_measurement.json`.
- `vendor/c8_assembly_fixtures/`: the 50 files as regular-file byte copies, each from a pinned source.
  - 21 are `reference/c7d3_run1_results/` copies at their `reference/SHA256SUMS_c8` entries.
  - 3 are `git show c8-base` (= `LRI_C7_D3_HPC@a6ce987`), and 4 are `git show LRI_C7_D2_HPC@a55958f`.
  - 22 are `git show LRI_C8_D2_HPC@1769abc` of C62d's fixture tree: the C7(2) production records and the RECON.md
    that C62d's review measured.
  - Each copy equals the live file this measurement read.
- **`tools/VENDORED.json`** (written by `tools/vendor_assembly.py`, which refuses an existing vendored set) holds:
  - the HANDOFF and file pins, and the review verdict with the step-0 decision and its scope;
  - the fixture provenance and the measurement summary;
  - the run rules of the H2 record;
  - the interface signatures and constants, read with `ast` without importing the vendored module;
  - F12's wording: `loop7_gate` is an order-8 gate, `jacobians` takes float or complex means only, and
    `power_null_rows` is compared on its numeric fields, not on its layout.
- **`tests/fixtures/exact_check_keys.json`** classes the 40 leaves of `exact_check_results.json`: 33 exact, 6 float
  diagnostics with bounds, and 1 provenance pattern (the live-RECON md5 key). It is identical to C62d's committed
  classification. It differs from C62d's draft only in `module_md5`, which is exact here. `tests/exact_keys.py`
  holds the gate: unclassified, new or missing keys fail, and `lri_root_dependent` names the two keys that
  `exact_check.py` drops without `LRI_ROOT`.
- **`tests/check_vendored.py`** checks A-ASM-1(a) with `--standalone`:
  - the pins, the complete set, the F12 wording, the fixtures and their source pins, and no tracked symlink;
  - the review record, the interface (`inspect` against the recorded `ast` signatures), and the key classification;
  - the read rule: a static allowlist scan, plus an open/import spy on `prepare_inputs` with a negative control.
  - Without `--standalone` it also checks A-ASM-1(b), the `inputs/manifest.json` pins. That waits for Stage 2a (G2a).
- **`tests/vendored_isolated.py`** runs A-ASM-1(a) on a `git archive` export outside <PROJECT>, or with
  `--in-place` on an Expanse export.
  - It runs the vendored tests with and without `LRI_ROOT=fixtures` (30; 21 + 9 skipped), with the `:134`
    disposition (`--asm3-record`).
  - It runs `exact_check.py` through the classified keys and asserted float bounds, and `prepare_low8.py --d 3`
    in compare mode.
  - It records an order-7 ulp diagnostic and checks the open-audit logs, an unchanged export, the vendored set
    afterwards, and numpy, Python and the CPU.
- `docs/NUMERICS.md` starts with the pins. `README.md` lists the vendored trees.
- The HANDOFF precedes Stage 2a, so `inputs/manifest.json` is unchanged. A-ASM-1(b), and the full A-ASM-1 re-run,
  wait for G2a (C62d's R15).

## 2026-10-04 — C8(3) Stage 0, repair round 3 (minor issues of the Stage-0 verification)

- **A launch wrapper that never started** (`timeout` missing from `PATH`, not executable, a failed fork) is recorded
  `not_submitted` with `launched: false`: no process ran, so no `sbatch` exists, and T resolves at zero cost (HD17
  (b)). `budget._run` raises `NotStarted` for a start failure only; an OS error after the start stays ambiguous.
- **Rule (c) from the user snapshot alone** needs the line to prove "no other attempt": `RestartCnt` 0 and
  `SubmitTime` equal to `EligibleTime` (or no eligible time). A line whose `RestartCnt` shows a requeue rules (c) out.
  The user snapshot gains `RestartCnt`, `SubmitTime` and `EligibleTime` (still `squeue --all`).
- **Charges.** An earlier attempt that `RestartCnt` shows and `sacct` lacks is charged its full reservation until
  `sacct` delivers it, also while the job is live again; evidence (a) waits for it.
- **`lockprobe --side login --job ID`** polls `squeue` in the scheduler environment (`SQUEUE_*` removed), and refuses a
  `--job` that is not a job id (64).
- **Finite numbers.** `rebuild --hold-su`, `lockprobe --interval` and `--wait`, `C8_LOCK_WAIT` and
  `C8_PILOT_SU_CAP` refuse `nan`, `inf`, `1e999` and values out of range (64), before anything is written. `--interval`
  is in [0, 60] s, `--wait` in (0, 600] s and at least 4 × `--interval`.
- **Tests.**
  - New in `test_submit.py`: rule (c) and the charges under a requeue, with the reviewer's two reproducers on the
    stateful fake; the launch wrapper that cannot be started (real processes and in process).
  - New in `test_ledger.py`: the login side's RUNNING gate with a fake `squeue` (PENDING, then RUNNING, with
    `SQUEUE_STATES` exported), and the finite-number refusals.
  - `test_lockprobe` waits for the ready marker in the run directory and checks the handshake's marker order.
  - The fake Slurm prints `RestartCnt`, `SubmitTime` and `EligibleTime`, models a requeue's new submit and later
    eligible time, and reads `SQUEUE_STATES`.

## 2026-10-04 — C8(3) Stage 0, repair round 2

- **The C7(3) campaign code is quarantined in `c7_legacy/`.** This covers `submit`, `window`, `resubmit`, `lanes N`,
  their plain `sbatch` launch, the mkdir campaign lock, and `slurm/submit.sh` and `resubmit.sh`.
  - It sits outside `tools/` and `slurm/`, refuses (64) on Expanse, and only the inherited Mac tests run it.
  - `tools/slurm_submit.py` refuses the unported entry points (64) everywhere.
  - A-ORC-17 (k)'s negative scan holds as written, and its test can fail.
- **`lanes.py queue` and `release-stale` take the session lock** in place of `.c7_submit.lock` (D.11). They stay
  refused on Expanse until their Stage 3 port.
- **`raw` refuses the campaign roles** `lane`, `merge` and `off<N>`.
- **The campaign option sets** (`C8_SBATCH_ARGS`, `C8_MERGE_SBATCH_ARGS`) take the campaign allowlist. It has no
  `--wrap`, `-o`, `-d`, `-N`, `-n` or `--exclusive`.
- **The node cap** is min(`C8_COMPUTE_CAP`, the reservation's `dev_nodes`), and the base split's after `until`.
- **Requeued jobs.** A finished `squeue` line is matched to its own attempt by its start. Its charge and evidence rule
  (a) no longer take an older attempt's `sacct` row as the last one.
- **Lock-free readers** (`budget.py`, `ledger.py check`) scan the intent files before they read the ledger. A
  concurrent submitter can no longer cause a false repair alarm.
- **`lockprobe`.** The holder keeps the lock for `--interval` after the waiter's NB-failed marker. The waiter checks
  causally that the release marker exists when its acquisition returns.
- **The session lock** is released when its acquisition `fsync` check fails.
- **The exec guard** must be executable before any intent is written (64). A `timeout` that cannot start it is
  `launched: false`.
- **No traceback on OS errors.** `rebuild` re-writes an intent file the OS cannot read. Stray OS errors exit 69 or 74
  with the path.
- **`docs/HPC.md`** states the residual race bound (D.11) and documents each change above.
- **Tests.**
  - New in `test_submit.py`: the requeue whose last attempt lags in `sacct`, the reader race, the exec guard and the
    docs.
  - Extended in `test_submit.py`: the literal (k) scan with mutation cases, roles and campaign options, and the cap.
  - New in `test_ledger.py`: the early-grant lockprobe, the acquisition-check release, and rebuild with an unreadable
    file.
  - New in `unit_orchestration.py`: the session lock of `lanes.py queue` and `release-stale`.

## 2026-10-04 — C8(3) Stage 0, repair round 1 (review of the submission, budget and ledger tools)

- **No append after a failed one.** A failed or short ledger append, a failed `fsync`, or a failed lock-descriptor
  check ends every further append of that call, in every job of a multi-job call (`lanes N`, `submit`). The ledger
  then ends in the torn bytes, which the next admission truncates. The jobs already submitted are adopted, never
  recorded after the torn bytes (D.11 step 5).
- **A missing ledger stays a repair block.** Only admission's first use on a new root and `rebuild` create the
  ledger. `register` and `resolve` refuse (69).
- **Standalone `budget.py`** applies the evidence rules (a) and (c) in memory and lists those intents as resolved
  by evidence now; it still records nothing (HD17).
- **`rebuild`:**
  - it blocks on a token with resolving records but no intent copy, as admission refuses;
  - the decision's hold lists the tokens it covers, whose leftovers then block nothing;
  - unreadable intent files leave `intents/` only after the new ledger with the hold is installed;
  - G runs from the current blocking conditions, and write failures exit 74.
- **Create-time failures** (EDQUOT from the file quota) exit 74 everywhere, never with a traceback.
- **`C8_RESERVATION`:**
  - a malformed value refuses normal-QOS jobs (64) and still admits `shared` and `debug` jobs (A-ORC-11);
  - only the H7E-R base split may omit `until`;
  - after `until`, the `shared` share falls back to at most 32.
- **The re-snapshot:** a failed `scancel` or re-query exits 69, naming the jobs that may still be pending.
- **Batch scripts** are read as `sbatch` reads them (directives at column 0). `#SLURM`, `#PBS` and `#BSUB`
  directives are refused (64), and so are non-UTF-8 scripts, a missing `#!` and DOS line breaks.
- **Decoding.** Scheduler output is decoded with replacement. The decision reference hashes the raw line bytes.
- **`lockprobe`:**
  - each run has its own marker directory;
  - a lock or mount failure on one side is recorded by both sides (the host STOPS), never as an expired handshake.
- **The Stage 0 fence** now also covers `lanes.py queue` and `release-stale` (the inherited mkdir lock).
- **Tests.**
  - New in `test_ledger.py`: the resolved-intent loss, `--user-decision` killed or failing at every step, the block
    clock, the decision-reference bytes, and lockprobe failures and repeats.
  - New in `test_submit.py`: multi-job append failures, the standalone budget with evidence, re-snapshot query
    failures, missing-ledger writers, script directives and decoding.
  - Changed: (m) and (n) run over the four shares, (i) uses `lanes 2`, (e) and (p) assertions are strengthened, and
    the open spy and three other weak assertions were fixed.
  - `test_ledger.py` and `test_submit.py` together take about 75 s.

## 2026-10-04 — C8(3) Stage 0: submission, admission and budget tools (plan "Staged plan", Stage 0)

These tools are written and tested first, so that every Expanse job of the C8(3) plan is admitted, gated and counted
from the first submission onwards.

- **`tools/ledger.py`** (D.11, D.12):
  - the session lock (`flock` on `$C8_ROOT/locks/c8d3.lock`), with its Lustre `flock` mount check and the fsync check
    on the lock descriptor;
  - the checksummed record framing and the record check (a torn tail is kept as evidence, then truncated);
  - intent records and intent files;
  - the commands `register`, `resolve --user-decision`, `rebuild` (it restores every intent or stays blocked until
    the user decides), `lockprobe` (J-LOCK-0) and `check`.
- **`tools/budget.py`** (HD17):
  - the billing function and its option resolution;
  - per-attempt and per-task charges from `squeue` (first) and the two `sacct` queries since `BUDGET_EPOCH`;
  - the intents, counted by the union of their two copies, with resolution only on evidence (H-g) and the one slot
    rule (H-h);
  - attribution and adoption.
- **`tools/slurm_submit.py raw`** with the admission engine (D.11 steps 1–7):
  - the H7E-R shares from `C8_RESERVATION`, the node cap, the detectors and the SU gate;
  - the intent written twice before every `sbatch`, the 60 s age check and the launch through
    `timeout -s KILL 120 slurm/exec_guard.sh … sbatch`;
  - `submit` records and the re-snapshot;
  - spec builders for the campaign entry points.
- The inherited C7(3) campaign entry points are unchanged but refused on Expanse until Stage 3 ports them.
- **Also new:** `slurm/exec_guard.sh` and `slurm/sites/expanse/env.sh.example`.
- **Tests (Mac):** `tests/test_ledger.py`, `tests/test_submit.py` (A-ORC-11, A-ORC-12, A-ORC-17, with 500 seeded
  interleavings each for (c) and (i)) and the stateful fake Slurm `tests/fake_slurm/`.
- **Docs:** `docs/HPC.md` gains the C8(3) sections for these tools; the C7(3) runbook stays below them, labelled as
  inherited.

## 2026-10-01 — archived-value gate follows the reporting rule (C7(3) results review, finding C7-RESULT-02)

- `assemble.gate_checks` now flags the archived C7(3) when the difference exceeds 3 archived SE (`in_archived_se`),
  as the reporting rule states. The combined-uncertainty pull is still reported, as a diagnostic only. Before, the
  combined pull was flagged, which could miss a difference above 3 archived SE when the new SE is not negligible.
- A regression check in `tests/unit_orchestration.py` covers the boundary (±3.1 and 2.9 archived SE with equal SEs).
- Run1's gate values are unchanged (+1.90 archived SE, no flags).

## 2026-10 — symmetry-ready release (fixes of the C7(3) and C7(2) reviews)

Native numerics are unchanged: `src/` is byte-identical. On the same toolchain the default build gives byte-identical
binaries (on symmetry: gmp `635428f9…`, decimal `24b2b941…`). `reference/` and `inputs/` are byte-identical.
Campaigns planned with the delivered tools (`c7-d3-production-1`, e.g. run1) cannot be run or merged by these tools.
They are re-verified and reported with `tools/report.py`.

**Integrity.**
- Every native call runs from a verified job-private copy of the executable, gamma table and Sobol net. Checkpoints
  record the runtime digests and the node and CPU, and merge and restart reject mismatches (L10).
- Assembly inputs are verified against the campaign's inputs manifest, with no import-time load (L15, plan review
  C7P-02).
- Plans verify every input file, packs included, and self-test the executable (L16).
- Only data-determining tools are pinned. `assemble.py` and `report.py` hashes are recorded as provenance (L9).
- URI-safe SQLite paths and `%`-escaped Slurm log paths (L11).

**Throughput.**
- Cost-ordered checkpoint blocks, defaults of 64 threads with 1024-task blocks, and a thread guard and warning (M4).
- Seconds-scaled shards (L4).
- The shipped symmetry cost model gives core-hour, wall-time and suggested `--time` estimates, and a projected SE
  (L2).
- Parallel group merges.

**Operations.**
- Resumable, concurrency-safe merge and idempotent result publication (L1).
- `production.py status|recover|tag|check-sbatch-args`, and one guarded submitter `tools/slurm_submit.py` with
  allowlists, environment filtering and a campaign lock (L2, L3).
- `slurm/merge.sh` no longer aborts on success (the run1 `grep` defect).
- Merges have their own wall time (`C7_MERGE_TIME`, default 1 h; found by the symmetry smoke drill, where the 2 h
  script default exceeded the debug partitions' limit). `--lanes 0` submits a merge for live lane workers.
- `run` refuses a missing index (L3).
- `verified duplicate` logging (L12).

**Lane mode (new).** Whole-node, claim-based workers for exclusive partitions:
- atomic claim files carrying their owner, and requeue reclaim;
- stale-claim release by owner state, a failure limit and a remaining-time guard;
- a merge that waits on every live worker;
- array mode and lane mode are never mixed.

**Statistics.**
- Seven-loop primitives use their frozen Neyman counts, and `--primitive-points` is removed (M3).
- Scored lower-order gates: the C6 reference updated to the 2026-09-29 C6(3) campaign; power differences; a/b;
  bootstrap; the archived C7 (M2, D3-3).
- Test-only results go to `C7_test_result.json` with every physical field under `test_partial` (L19).
- `--max-loop` prefix plans (L20).

**Seeds and nets.**
- Hashed per-group seeds by default. `--seed-scheme legacy` reproduces run1 and refuses used seeds (L8).
- Bounded public-API and GF(2) structure checks of every exported net (L5).

**Report tool (new).** `tools/report.py` gives a read-only re-verification of finished campaigns, the delivered
schema included, by data identity, with all gates.

**Tests and evidence.**
- `make test-replay` replays the archived production streams (D3-2).
- Strict replay gates: gmp bitwise, and decimal exact without MP promotion (L6).
- Every backend gets the thread and split tests (L14).
- Point checks cover the long-double tier (L7).
- Tests write records only with `--output`; records carry host, CPU and executable hashes (L7, L13).
- New tests: orchestration with a fake worker, legacy and archived seeds, assembly equivalence, delivered-tools
  campaigns.

**Build.**
- `OPTFLAGS`/`CPPFLAGS`/`LDFLAGS`/`LDLIBS` with non-droppable strict flags, the Boost ≥ 1.86 refusal and per-binary
  build info (L17, L18).
- Python ≥ 3.10 checks (L21).

**Fixes from the Codex code inspection (round 1).**
- Retained mode never integrates the seven-loop primitives, even with `--points` (they were counted twice), and it
  needs `--max-loop 7`.
- The retained a/b pull excludes the shared primitive SE.
- The cross-CPU result tolerance compares every float (scaled by its vector) and checks that the stored gates are
  consistent with the result's own fields.
- The report handles results with `bootstrap: null`.
- Build info parses flag values robustly, and a failed build-info step deletes the binary (`.DELETE_ON_ERROR`).
- Flags that override STRICT are refused in every user variable.
- The archived replay verifies the gamma table and every graph payload.
- Test and benchmark records carry the compiler and executable identity.
- Resumed lane indices are excluded from the throughput gate.

**Fixes from the Codex code inspection (round 2).**
- A result missing its gates, or with them moved, is refused.
- Lanes never exceed the plan's `checkpoint_tasks`. The default split adds lanes; a too-wide `C7_LANES` refuses
  before any claim.
- A lane stops after 3 consecutive failures.
- Each attempt writes its own log, and the throughput gate requires a single complete attempt.
- Benchmark and profile records carry the host, compiler and executable identity.

**Fixes from the Codex code inspection (round 3).**
- The lane worker's remaining-time query removes inherited `SQUEUE_*` filters.
- Slurm's answer takes precedence; `C7_LANE_SECONDS` is only the fallback.

**Fix from the Codex code inspection (round 4).** The wall-time check for plans without a cost model now reads
option names, never option values: a value such as `--job-name -trial` no longer counts as `-t`.

**Docs.**
- README, HPC, NUMERICS and PERFORMANCE are rewritten: the symmetry recipe, lane mode, CPU dependence (D3-1), Boost
  1.77, and the correct pack size (251 MB).
- `tools/write_delivery.py` regenerates the delivery manifest.
