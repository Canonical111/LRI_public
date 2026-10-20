# C7(3): reviews

Summary of every review of the C7(3) code and result. The raw review logs, transcripts and loop folders are not
published; this file replaces them. Reviewers were AI systems: Claude (Anthropic) subagents and OpenAI Codex
(gpt-6-astra, reasoning effort xhigh). There was no human referee. The coordinator in every case was a Claude Code
session (C63d). Dates are 2026, times EDT.

| # | what | reviewer | rounds | verdict | date |
|---|---|---|---|---|---|
| 1 | delivered package before and during production | three read-only Claude subagents | 1 | GO (numerics sound) | 30 Sep |
| 2 | fix-loop plan for a symmetry-ready package | Codex | 3 | APPROVED (round 3) | 1 Oct |
| 3 | fix-loop code (the symmetry-ready package) | Codex, a fresh session each round | 5 | APPROVED (round 5, c71cc56) | 1 Oct |
| 4 | the result C7(3) = -220.35 +- 0.13 | Codex | 2 | APPROVED (round 2) | 1 Oct |

## 1. Code review of the delivered package (GO)

- **Scope.** The package as delivered (`code/LRI_C7_D3_HPC`, local git baseline 4de9412; `verify_delivery --strict`
  passed on 4,909 payload files). The user chose a focused review running alongside production: one reviewer for the d=3
  kernel against the original d=3 code, one for assembly, inputs and sizing, and one mapping the 25 findings of the
  earlier C7(2) review onto the d=3 port.
- **Verdict (30 Sep, 18:05, before the campaign finished).** The d=3 numerics are sound; nothing biases the result;
  GO for the running campaign, to be judged with manual gates.
- **Evidence** (symmetry cluster):
  - build and delivered tests, job 566376: all seven suites pass; thread identity 5,776 rows, 0 mismatches
    (`results/C7_3/evidence/buildtest-566376.out`);
  - AMD vs Intel, job 566410: same rows and promotion counts, values differ by at most 2.0e-11 normalized
    (`evidence/intelcheck-566410.out`; the maximum is recorded in `CAMPAIGN.md`);
  - archived-stream replay, job 566411: all 168,528 archived rows of the previous calculation reproduce, 162,044 bit for
    bit and the rest within 1.0e-11; promotion counts identical in all 20 groups; the previous C7(3) rebuilt as
    -227.61810947469922 against the published -227.61810947469945 (`evidence/replay_report.json`; script
    `code/LRI_C7_D3_HPC/public/replay_archived.py`, rerun with `make -f public.mk archived-replay`);
  - an independent mpmath re-implementation of the sampler and integrand reproduced 13 archived rows across L3-L7 and
    both sectors: free rows to 1e-17-1e-19, power rows to <= 9e-13 (script `public/indep_rows.py`; the row list was
    not archived);
  - line-by-line check of every dimension-dependent expression of `src/kernel.hpp`; `src/` is byte-identical to
    `reference/src/`; `gamma_d3_7.txt` recomputed to 4e-58; rate tables recomputed for 140 graphs; all 3,511 pack
    members byte-identical to `reference/inputs`; reassembly of the archived records reproduces the archive to 4e-13.
- **Findings and what changed.**
  - D3-1 (info): results are not bit-reproducible across CPU types (glibc long-double transcendental functions); about
    1e-7 of the relative statistical error. Recorded per index in the claims; documented in `CAMPAIGN.md`.
  - D3-2 (medium): the package had no independent physics test of the d=3 port. The replay above is that test; it ships
    as `public/replay_archived.py` with its record.
  - D3-3 (medium): the delivered assembly's C6 reference (33.5682) is stale and it emits no pulls. Production was judged
    with manual gates against the new C6(3) = 33.57543 +- 0.00012 (the reporting rule in `CAMPAIGN.md`); the fix loop
    made them the package's scored gates (`reverify_a6ce987`).
  - D3-4 (medium): flat allocation of the 44 seven-loop primitive classes. Production used `--primitive-points 1024` (a
    plan flag; 1.1% of the CPU for 0.4% of the variance) instead of the default 16384. It changes only the variance.
  - Carried over from C7(2): M1 (power sector over-allocated) does not apply in d=3; M4 (idle cores at block barriers)
    applies (about 0.96 utilisation); the 21 low findings (merge not resumable, Slurm templates, seed hygiene, Boost
    >= 1.86 fails, and others) apply and were handled operationally. None biases a correctly run campaign.

## 2-3. Codex fix loop: the symmetry-ready package (APPROVED)

- **Request.** The user asked for a Codex fix loop "for the C7(3) results", with decisions: fix every finding by porting
  the reviewed C6(3) design; native numerics frozen; frozen Neyman counts for the primitives; lane mode for exclusive
  nodes plus a read-only report tool; Boost documented only. Claude planned and built; Codex reviewed and inspected.
- **Plan review.** Round 1 REVISE (5 findings, 2 high: report scope; assembly inputs not bound to the campaign's inputs
  manifest), round 2 REVISE (3 medium), round 3 APPROVED. All findings accepted.
- **Code inspection** (a fresh Codex session each round): round 1 REVISE with 10 findings (2 high: retained primitives
  could be counted twice with `--points`; the rounding tolerance ignored most floats), round 2 REVISE with 4, round 3
  REVISE with 2, round 4 REVISE with 1, round 5 APPROVED with 0 findings at c71cc56 (code bb9d2ca). Every finding was
  accepted and fixed; symmetry validation jobs 567149, 567180, 567184, 567197 passed after each fix round.
- **What ships from it.** Only the read-only re-verifier: `code/LRI_C7_D3_HPC/reverify_a6ce987/` (`tools/report.py`,
  `assemble.py`, `common.py`, the gate references and run1's cost model, at a6ce987). It re-verified run1 bitwise on
  symmetry with the gates of `CAMPAIGN.md` (`results/C7_3/run1_report_bb9d2ca.json`, job 567197).
  `src/`, `inputs/` and `reference/` are byte-identical to the production commit.
- **Not verified by the reviewer.** Static review: live Slurm and BeeGFS behaviour, and Intel lane execution, were not
  exercised; the physics was not re-derived.

## 4. Codex results review of C7(3) = -220.35 +- 0.13 (APPROVED)

- **Round 1: REVISE**, two low findings, neither changing the result.
  - C7-RESULT-01: the dossier said run1's group seeds were hashed; the delivered planner uses arithmetic offsets from one
    base seed. The dossier was corrected (`public/replay_C7_3.py` checks the offsets, row `n.seed`).
  - C7-RESULT-02: the package flagged the archived value by the combined pull instead of the rule's "3 archived SE".
    Fixed in commit a6ce987 with a regression test; run1's gates are unchanged (+1.90 archived SE, no flags). This commit
    had no separate Codex code inspection; the round-2 reviewer inspected its diff.
- **Round 2: APPROVED.** "C7(3) = -220.35 +- 0.13 is supported within its stated empirical sampling-only scope."
- **Reviewer coverage.** All 7,022 allocation entries and the sample total; the identities of the manifest, configs,
  merged files and archive; three production checkpoints; the seed, sampling, promotion, merge, covariance, bootstrap and
  reporting paths. Limitation: static; the reviewer did not recompute the estimator (`make replay` now does).

## Reporting rule

The coordinator wrote the rule (estimator with sampling SE; allowance four SE rounded up to 0.01; gates on the a/b
campaigns, bootstrap, archived value, C3-C6 and the power differences) at launch, before any result, in
`results/C7_3/CAMPAIGN.md`. The user confirmed it unchanged on 1 Oct, after the result was known. The same file carries an
erratum written before the results review: a caveat about a retained analytic power compensation, copied from C6(3), was
wrong (both sectors are integrated explicitly), and the flat seven-loop primitive allocation is clarified.

## Overruled or open recommendations

- None overruled.
- Open: the archived replay ran only on AMD EPYC 7532; an Intel lane run of the symmetry-ready tooling was never
  exercised (not used for the result). As in C7(1), a quadrature-truncation effect, if present in d=3, is outside the
  sampling allowance (`CAMPAIGN.md`, reporting rule item 4).
