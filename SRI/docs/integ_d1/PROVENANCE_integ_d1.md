# Provenance: integ_d1

**Source.** `code/integ_d1/` is the project repository `LRI_SRI_integrability` (local git) exported at commit 8bd5a22
(2026-10-17), selected files, layout kept (`public/SNAPSHOT.sha256` lists the sha256 of every exported file as stored
at that commit). The working notes of the project (README, DERIVATION, PLAN_C8_MSCHEME, M3_NOTES, M4_NOTES, SUMMARY)
are not exported: by the one-note rule their content is in the SRI note, Sec. 2.7 and Appendix I.

**Authors.** All code and records were written by Claude Code sessions (Anthropic, model Claude Opus) between
2026-10-14 and 2026-10-17, on the author's requests: one host session, which carried out the study, and a builder
subagent it started and resumed for the cluster pipeline. The commits carry the author's git identity and a Claude
co-author line; the author wrote none of the code. The author set the targets and the compute rules (sigma(C8) <= 0.3,
the symmetry cluster only, a 3e4 core-hour cap) and decided the two amendments (REVIEWS.md). OpenAI Codex (GPT-6
astra) reviewed the plan three times and inspected the code six times (REVIEWS.md); it wrote no code or record of the
package, and every fix of its findings was made by the Claude sessions.

| part | dates | written by | commits |
|---|---|---|---|
| gauge analysis of the s = 1 flow (`series_tools.py`, `normal_form.py`, `linear_action.py`, `rank_exact.py`), Bethe-ansatz flow (`ba_numeric.py`), early pole and two-bubble checks (`pole_check_*.py`, `check_*.py`), the derivation of the magnetization formula and the plan (revisions 1-3) | 2026-10-14 | host session | ccaf09e, 7b5ff9a, 9cd36d5, 10b8ce2 |
| M1 (`m1_gate.py`, `mscheme_invariants.py`, `one_bubble.py`) and M2 (`two_bubble.py`, `m2_*.py`, `m2_*.sbatch`, `test_two_bubble.py`, the M2 run and record) | 2026-10-14 | host session | 07cfa17, b8d7eb1, 18f2127 |
| the step-0 maps of M3 and M4 (`m3_step0*.py`, `m4_step0.py`, `c8_dependency.py`) | 2026-10-14 | host session | 6dccb89, 23a4ff7 |
| everything else: cluster generator, C++ engine and sector checker, cluster assembly, `mscheme_numeric.py`, `ba_numeric4.py`, gates, chunking and batch tools, `c8_assemble.py`, provenance and build registry, `test_gates.py`, `test_cluster.py`; all engine runs and records from M3 on; fix rounds 1-5 and the supplemental verification records | 2026-10-14..17 | builder subagent (resumed for each round), coordinated by the host | ad2c8d2..6d94e80, except the host commits listed here |
| test update for the superseded first M4B record, the comparison stage run (`results/C8_comparison.txt`) | 2026-10-17 | host session | a6a627e, 65d920d |

**Inputs from elsewhere.**
- The magnetization formula of the s = 1 chain (the Bethe-ansatz series in the note's App. I.2) was first read in the
  discussion of the research compendium (written by another AI system and supplied by the author; see `dual_d1`) and
  then derived here from the Bethe ansatz of the anisotropic Kondo model (Wiener-Hopf, literature cited in the note);
  its delta = 0 flow agrees with the compendium's s = 1 sector on the one gauge-invariant combination at that order,
  and with the cluster engine at every stage (gates).
- The closed forms of C3..C7 and the compendium's C8 record 247.3812048049935 (paper eq:sr-closed, eq:sr-C8; `dual_d1`)
  and the independent value 242.83 +- 2.37 (`indep_d1`) enter only as checks and in the comparison stage. The record
  of C8 was frozen before any comparison.

**Compute.** Engine production on the symmetry cluster, 2026-10-14..17: about 2.7e4 allocated core-hours (1.85e4 on
Intel `defq`, 0.82e4 on AMD `amdq`), including pilots and failed jobs; no SDSC Expanse time. The early two-bubble checks
(`check_two_bubble.py`) ran on a personal desktop; their batch file is not exported. The gates, the assembly and the
comparison ran on a personal desktop.

**Later changes.** None to the project repository. Added for the public repository by Claude Code (the same host
session, as the integ_d1 builder for the SRI folder), 2026-10-18: `public.mk`, `.gitignore` and `public/`
(`replay_integ.py`, `selftest_integ.py`, `gitstub.py`, `git_blobs.json`, `SNAPSHOT.sha256`, `REPLAY_FULL.md`) and
`public/historic/b2ab7c6/cluster_engine.cpp`, the engine source of the f_202 build exported from commit b2ab7c6
(git blob 2175fb82...; it differs from the pinned engine source, which built the f_301 runs). Not exported:
`code/two_bubble.sbatch` (names a personal desktop path; no target needs it), the pilot runs and cost studies
(`results/m4_runs/p*`, `pilot*`, `b*`; `results/m3_runs/cs`, `ct`, `s1`, `s2`, `g2g3/superseded_*`;
`results/m4_inputs/dd_sectors_t2.json`), the M3 grid-variant records `M3_s1_coarse_*`, `M3_s2_*` (no tool reads them), the partial M2 files
(`m2_runs/*_p0.jsonl`, `*_p1.jsonl`, concatenated in the shipped file), the gate logs except the two cited by the note,
and `results/fix_round1/`, `fix_round2/` (logs of earlier fix rounds).

**Unknowns.** None about authorship. The review transcripts are kept outside the release (REVIEWS.md summarizes them).
