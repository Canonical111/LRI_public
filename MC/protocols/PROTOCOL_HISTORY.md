# Protocol history: which text was approved, which text governed the production

The aim was to write each analysis protocol, and have it reviewed, before the production data it governs were analysed. That held for
d = 2 and d = 3 (with the preflight amendment of the 3D protocol described below). It did not hold for d = 1, where the protocol was
rewritten after most of the data had been analysed under its predecessor, nor for amendment P1, which was written after the 2D/3D
evaluations. The table gives, for each protocol, the reviewed and approved revisions, their SHA-256 hashes and the data seen when the
rules were fixed. Reviews were done by an independent AI model (OpenAI Codex, gpt-6-astra), and one round by a fresh Claude session;
`REVIEWS.md` summarizes every round. A `.sha256` file next to a protocol records the hash **at approval**, and the evaluators pin the
hash of the text that governed the production. Where the two differ, the difference is documented here.

| protocol | governs | production text (SHA-256) | review status | data seen when the rules were fixed |
|---|---|---|---|---|
| `FIT_MODEL_V3_rev14.md` | d = 1 fits, cross-check, decision table | rev. 14, `f05b835b…` = `FIT_MODEL_V3.sha256` | APPROVED at rev. 14 (2026-09-19). The first evaluation of all 20 couplings (N1, 2026-09-18) ran under rev. 8, which was unreviewed (the review of rev. 7 had returned REVISE); approval came after the N1 results and the N0 data had been seen. | The predecessor v2 (approved 2026-09-16) had been applied to stages A and B, 8 000 of the 10 240 chains of the final fits. v3 was written after those results, and its frozen window parameters come from v2 fits of those data. Two v2 gates were replaced after couplings had failed them: the absolute σ_sys cap (failed at all four couplings Δσ ≤ 0.05) and the per-group equilibration rule (failed at 0.0875 and 0.125, one group of 50 each, \|z\| = 3.04 and 3.05). The ACCEPTED labels at 0.025, 0.05, 0.0875 and 0.125 depend on these changes. The N0 rule was amended twice after the N0 data had been seen: the pre-registered rule gave INCONCLUSIVE (its δ/2 retest was not run), the rev. 11 rule FAIL, the rev. 12–14 joint test PASS, which released N2 with x_max = 0.35. Only the N2 data (2 240 chains) were taken after approval. |
| `FIT_MODEL_2D.md` | d = 2 design, extrapolation, decisions | rev. 5, `4d2efc63…` (pinned by the evaluators) | reviewed, **never APPROVED**: one fresh-Claude round (rev. 1) and three Codex rounds (revs 2–4), all REVISE. The author closed the review at three Codex rounds, and rev. 5 carries the round-3 fixes without a further pass. | Frozen 2026-09-20, before the production was submitted (≈21:35 EDT). Stage-0 and preflight data had been seen. |
| `FIT_MODEL_3D.md` | d = 3 design, extrapolation, decisions | rev. 7, `682858f0…` (pinned by the evaluators) | rev. 5 APPROVED (`b4ccf436…` = `FIT_MODEL_3D.md.sha256`); revs 6–7 are a disclosed, reviewed post-approval amendment of one preflight-gate condition. The last round (rev. 7) returned REVISE with one finding, which was fixed without a further round (below). | Rev. 5: stage-0 data. Revs 6–7: also the first preflight gate record, which contains preliminary effective dimensions (below). No production chain had run. |
| `AMENDMENT_PROFILED_SIGMA.md` | d = 2, 3 uncertainty rule (P1) | rev. 4, `2a18c0ae…` = `AMENDMENT_PROFILED_SIGMA.md.sha256` | APPROVED at rev. 4 (four rounds); the code passed two inspection rounds, and **the round-2 fixes are not inspected** | Drafted, reviewed and approved after both production evaluations (2026-09-22/23) were known, with its effect on every label already computed by an exploratory reanalysis (only 3D s = 1.6 changes). |

## FIT_MODEL_3D: revision 5 → revision 7

Files: `FIT_MODEL_3D_rev5_approved.md` (the approved text, SHA-256 `b4ccf436fce3c907de9b5b0b26f245e8c3cdce9047aef039c17435185871e357`),
`FIT_MODEL_3D_rev6.md` (`71a832e52920fb60…`), `FIT_MODEL_3D.md` (rev. 7, `682858f0327f7dbd0513…`), and
`FIT_MODEL_3D_rev5_to_rev7.diff`. The rev-5 and rev-6 texts were recovered byte-exactly from the inputs of review rounds 5 and 6, which
embed the reviewed plan together with its hash.

**What changed.** Only §5 (numerics plan) and §7 (verification), plus the status line. §1–§4 are byte-identical, including the analysis
protocol, the extrapolation, the eligibility gates, the cross-check and the decision table. The single substantive change is one
condition of the preflight gate, the go/no-go check before production:
- rev. 5: "τ ≤ 30 sweeps";
- rev. 7: "τ_int ≤ 50 sweeps", i.e. block/τ ≥ 20 at the smallest production block b = 1000. This is the equilibration rule that §4.1 of
  the same protocol already applies to every production record.

Rev. 7 also:
- names the gate records per attempt (`GATE_<jobid>.json`);
- records the measured pinned rate (103.3 ms per sweep at L = 128, giving a 43 h wall limit).

The matching evaluator change (FIT3D-021) applies the §4.1 equilibration rule to the reblocking records as well. It can only make a label
stricter.

**Why.** The first gate attempt (job 54385730, record `data/3d/preflight/GATE_attempt1.json`) met every condition at all eight points
except the τ cap: τ_max = 34.3 at s = 1.6 and 32.6 at s = 1.85. The cap of 30 had no basis in the analysis protocol. The amendment is
disclosed in §5.1 of rev. 7 as post hoc. The second gate attempt, on the same preflight data, passed (`GATE_54386940.json`).

**When.** All on 2026-09-21 (EDT), before any production chain ran:
- ≈17:55: rev. 5 APPROVED (round 5);
- next: first gate attempt FAILED;
- ≈18:45: rev. 6 written;
- ≈18:55: round 6, REVISE, 2 findings, both applied (FIT3D-021, 022);
- ≈19:08: round 7 on rev. 7, REVISE, 1 finding: FIT3D-023, a one-line evaluator fix already applied two minutes after the round
  started;
- ≈19:25: the author accepted that fix without an eighth round and submitted the production under rev. 7.

The production ran 2026-09-21 to 23. The production analysis (snapshot 54387089) and its evaluation are dated 2026-09-23, and the
s = 1.6 value comes from that evaluation and from the amendment-P1 evaluation of 2026-09-30.

**What was visible when the rule was amended.** The failed gate record contains, besides the τ values, preflight effective dimensions of
the 64→128 pair from 5 × 10⁴ sweeps per chain (for example D_U4 = 1.479 and D_Y = 1.444 at s = 1.6). The amendment concerns an
equilibration threshold, not an estimator or an acceptance rule, and it adopts the criterion the production analysis applies anyway. It
was nevertheless made after data had been seen, and it is recorded as such.

**Review coverage.**
- Rev. 5: approved.
- Revs 6–7: reviewed in rounds 6 and 7. Every finding was applied, and the reviewer confirmed that the amendment is disclosed.
- The final state (rev. 7 plus the FIT3D-023 one-line fix) is formally unreviewed for that fix, by the author's decision at the round cap.
- The full record is the review log of the 3D protocol (summarized in `REVIEWS.md`).

## Checksum files

`FIT_MODEL_V3.sha256` originally named the protocol's path in the project tree. For this release it names the shipped copy,
`FIT_MODEL_V3_rev14.md`, so `cd protocols && shasum -a 256 -c FIT_MODEL_V3.sha256` passes; the hash is unchanged.
`AMENDMENT_PROFILED_SIGMA.md.sha256` passes as shipped. `FIT_MODEL_3D.md.sha256` records the approved rev. 5 and therefore fails against
`FIT_MODEL_3D.md` (rev. 7) and passes against `FIT_MODEL_3D_rev5_approved.md`, as explained above. `FIT_MODEL_2D.md` was never approved
and has no `.sha256`.

The protocol texts were not changed for the release, because the evaluators pin them by SHA-256 in their code. Two planning sentences
in them therefore still name a personal machine: §5.3 of `FIT_MODEL_2D.md` and the data-archiving sentence of §5 in each `FIT_MODEL_3D`
revision. The author decided on 2026-10-13 to keep them as a disclosed exception. The records that were scrubbed after the results (host labels naming a
personal machine) are listed with their original and published SHA-256 in `RE-PINNED.json`; the hashes quoted in this file are
unaffected.
