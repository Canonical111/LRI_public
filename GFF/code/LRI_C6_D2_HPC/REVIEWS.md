# Reviews of LRI_C6_D2_HPC (C6(2), note Sections 24.6 and 33)

The numerical code (kernel, sampler, fixed-point assembly, inputs) and `reference/` (the earlier method-refinement
calculation) were written by OpenAI GPT-6 astra (model stated by the author, 2026-10-13), in a ChatGPT session and delivered on 28 September 2026
as `LRI_C6_D2_HPC_optimized.zip` (git baseline 3e643c8). The same day a Claude Code session reviewed it, made it ready
for SDSC Expanse under OpenAI Codex review (commits 7293480..6aaf656), ran the production on 28 September and wrote the
note text on 1 October; Codex then reviewed the result. Raw review logs and transcripts are not part of the release.

| Stage | Reviewer | Rounds | Verdict | What changed |
|---|---|---|---|---|
| Code review of the delivery (2026-09-28) | Claude Code, multi-agent (six review dimensions, each finding checked by a refutation and an impact verifier, plus a completeness critic; 50 agents) with native runs on Expanse | 1 | numerics sound, nothing critical or high | 3 medium findings (M1 the executable and inputs hashed once per job but used for every block; M2 assembly did not hash-check the two-loop input B2 and the primitive reference P10; M3 checkpoint-block overheads cap parallel efficiency) and 19 low (Expanse templates, resumable merge, status and recovery, array offsets, seeds, primitive allocation, test gaps, file modes). Verified on Expanse: new and original code agree on all 492 kernels to 8.7e-20 (normalized) with equal fallback counts, end to end to 1.1e-16. Four claims were rejected after verification. |
| Fix plan | OpenAI Codex (gpt-6-astra, effort xhigh) | 5 | APPROVED in round 2; amendment rounds 3–5 REVISE | Round 1: 7 findings (idempotent assembly in merge.sh, archived replay vs the seed guard, self-test net size, --points precedence, Neyman feasibility, reference thresholds, Python >= 3.10), all accepted. Rounds 3–5 reviewed amendments to the recovery tooling (AM1–AM4), all accepted. |
| Code inspections | OpenAI Codex (gpt-6-astra, xhigh), a fresh session each time | 7 | 1–6 REVISE, 7 BLOCKED | 7, 3, 3, 2, 2 and 4 findings, all accepted and fixed (job-private executable, inputs and Sobol nets with recorded digests; submission guards and an sbatch-option allowlist; environment handling of the scripts; one guarded submission path, tools/slurm_submit.py). None concerned the numerics: the production binary stayed byte-identical to the build of the delivered sources (sha256 5818340b...). Inspection 7: R1 (low) status lines did not carry an explicit array size; R2 (medium) no Expanse drill of the final submission layer. |
| After the loop | none | – | – | R1 fixed in 6aaf656 with a regression test; R2 closed by real-Slurm recovery and status-line drills on a personal workstation and then on Expanse (validation records not shipped). |
| Results (2026-10-01) | OpenAI Codex (gpt-6-astra, xhigh) | 2 | APPROVED in round 2 | Round 1 REVISE: C62-001 the 0.0015 projection was described with the wrong scaling (variance 1/n vs SE 1/√n); C62-002 archived Lagrange and delete-one checks of the previous estimator were presented as checks of the new production. Both fixed in the note and the campaign record. Round 2: no findings. The reviewer re-verified the 996 checkpoints and 865,664 task identities, all record, tool and input hashes, the zero C6 projection of the 28 floor-sampled kernels, and the pulls (a/b 0.31, bootstrap ratio 1.002, previous estimator 0.12, C7(2) by-product 0.73). |

Recommendations overruled or decided by the author:
- The plan's acceptance criterion for the independent Kirchhoff point checks (every check relative 1e-9) was amended by
  the author ("amend the criterion and re-review", rather than "report as not met" or "change the numerics"): one point
  of 516, graph L6G160 at scale 1e-130, needs about 395 digits and lies beyond the 300-digit tier; it is required instead
  to equal the original code's value, which it does.
- The plan-review budget (5 rounds) ran out with amendment AM4 reviewed only as code: the author chose to go on to the
  code inspection. The author extended the inspection budget twice (inspections 6 and 7); the fix rounds exceeded their
  budget by two.
- The author chose the variance-based (Neyman) split of the primitive budget, hashed per-group seeds, and the
  validation scope (tests, smoke run, throughput pilot).
- The quoted allowance: the four-SE rule was written before the result; after it, the author changed the rounding step
  from 0.01 to 0.001 (disclosed in note Section 24.6).

What was never reviewed:
- the two last code changes (6aaf656, the status-line fix of R1, and the drill evidence) by any Codex inspection;
- the inherited physics: the graph and renormalization framework and the analytic power-sector compensation (the note
  says so; the seventh-order calculation, which integrates the power sector explicitly, checks the latter at sixth order);
- the four defects of the submission and merge layer found on 29 September by the review of the three-dimensional sibling
  package (no submission lock, a concurrent-merge crash, an unescaped SQLite URI, `%` in Slurm log paths). They are fixed
  there, not here; the production was not affected (see `GFF/results/C6_2/CAMPAIGN.md`). The release ships the code as it
  ran and only warns.
