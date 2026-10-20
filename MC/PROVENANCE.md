# Provenance of the MC folder

The work was directed by the author (Z. Zheng). Three code packages were written by GPT-6 astra (OpenAI, via ChatGPT) and supplied to the
project as separate deliveries:
- the initial 1D package `lri_cluster` (reference engine, campaign tools and analysis core, 2026-09-14);
- the 1D-specialised engine `lri_1d_precision` (2026-09-18);
- the 2D/3D engine `lri_precision_v2` (2026-09).

The fit pipelines, the protocols, the evaluators and the analyses were written by Claude (Anthropic) agent sessions. Protocols and code were reviewed by a second AI system (OpenAI Codex,
model gpt-6-astra); there was no human referee. All simulations ran through Slurm, on a production cluster with 128-core AMD EPYC 7742 nodes
and on project workstations, between 2026-09-14 and 2026-09-23. Later dates are analyses of the stored records only.

## Code

| folder | origin and date | written by | changed afterwards |
|---|---|---|---|
| `code/1d/` | the 1D package `lri_cluster`: delivered 2026-09-14 (reference engine, `prepare.py`, `submit.py`, `analyze.py`, `quotients.py`, `fit_fss.py`), then extended to 2026-09-20 (the v2 and v3 fit pipelines, campaign orchestration, registry and completion checks, tests) | delivery: GPT-6 astra (OpenAI, via ChatGPT); extensions: Claude sessions | Unchanged. Only files needed for tests, replay or a production rerun are released. The orchestration-only drivers of the original campaigns, the superseded v2 report scripts and the planning documents that no code reads are not (`FIT_PLAN.md` is shipped because `select_model.py` hashes it); `SHA256SUMS` was pruned to the shipped files. |
| `code/1d/src/` | reference engine (alias table), from the `lri_cluster` delivery; reviewed 2026-09-14 | GPT-6 astra (OpenAI, via ChatGPT) | unchanged |
| `code/1d/src_1d/` | the 1D-specialised engine, from a separate delivery (`lri_1d_precision`, 2026-09-18); its status record was extended by N, L and the engine name | GPT-6 astra (OpenAI, via ChatGPT); integration: Claude | unchanged since N2 |
| `code/1d_report_tools/` | tables and figures of the 1D report (2026-09-20) | Claude | unchanged |
| `code/2d3d_engine/` | the 2D/3D engine `lri_precision_v2`, from a separate delivery (2026-09); audited 2026-09-20 (exact enumeration, reference cross-check, bitwise restart); MIT licence ("Contributors") | GPT-6 astra (OpenAI, via ChatGPT); working-copy changes: Claude | The production working copy is released. The delivery's audit, results and archive pointers are not. |
| `code/2d/`, `code/3d/` | evaluators: `evaluate_2d.py` (frozen rule, rev 5, 2026-09-20), `evaluate_3d.py` (rev 1, 2026-09-21); P1 revisions rev 6 and rev 2 (2026-09-30); planners | Claude; reviewed by Codex | hash-bound; unchanged since 2026-09-30 |
| `code/reanalysis_p1/` | `calibrate_p1.py`, the 56 P1 tests, and `reanalyse.py` (the reference implementation the tests compare with), 2026-09-24 to 09-30 | Claude; reviewed by Codex | hash-bound; the exploratory prediction scripts are not released |
| `code/oned_xcheck/` | 1D cross-check study (2026-09-30) | Claude | unchanged |
| `code/package_tools/` | packaging tools (2026-10-07) | Claude | **Patched for the public layout (2026-10-13), not hash-bound.** Protocols read from `protocols/`; dropped inputs optional; known platform-sensitive labels and stated tolerances in the comparison; new comparison tables in the note generator; `index_prefix.py` added; the refit script honours `PY=`. |

Slurm templates in `slurm/` are the 2D/3D production job scripts (2026-09-20 to 09-23). Site values are replaced by placeholders, dependency
job ids by `<DEPS>`, and the module-loading lines are kept functional.

## Protocols

`FIT_MODEL_V3` (1D; approved at revision 14 on 2026-09-19), `FIT_MODEL_2D` (revision 5, frozen 2026-09-20; reviewed in four rounds, never
approved), `FIT_MODEL_3D` (revision 5 approved 2026-09-21; production under revision 7, an amendment of one preflight condition made
before any production chain ran), and amendment P1 (approved at revision 4, 2026-09-25; applied 2026-09-30). All were written by Claude
sessions and reviewed by Codex. `PROTOCOL_HISTORY.md` gives every revision, its hash, its review status and what data had been seen.

## Records and results

- `data/`: production records written 2026-09-14 to 09-23, byte-identical to production (they name the cluster paths, user and nodes),
  except the records scrubbed after the results (below).
- `results/`:
  - the P1 evaluations and the calibration (2026-09-30; Python 3.8.8, NumPy 1.20.1);
  - the 1D report tables (2026-09-20);
  - the 1D cross-check study (2026-09-30);
  - the cross-platform 1D refits (2026-10-07);
  - the robust-ladder sensitivity study (2026-10-13). Only summaries are released; logs are not.
- `data/reference/`: theory and literature values compiled 2026-10-12/13 for comparison only.

## Host names and paths

Machines are named only where they are public facilities: the production cluster (Expanse, 128-core AMD EPYC 7742 nodes) and the
symmetry cluster. Personal machines are called "personal desktop" or "workstation". Files written for this release, and records that no
hash binds, have their paths, user names and host names replaced by placeholders (`<HOME>`, `<SCRATCH>`, `<NODE>`, …). Hash-bound
records and results are shipped byte-identical (their hashes are part of the evidence) and keep the cluster paths, user names and node
names of the machines on which they were written. The exception, by the author's decision of 2026-10-13: 25 hash-bound records that named
a personal machine were scrubbed after the results. Only host labels, a home directory and file names changed; no number changed. The
hashes inside the scrubbed set were re-pinned, and `RE-PINNED.json` maps every original SHA-256 to the published one, so the original
hashes quoted in the note and in other records stay traceable. The protocol texts are a disclosed exception to the naming policy (author
decision, 2026-10-13). The frozen evaluators pin `FIT_MODEL_2D.md` and `FIT_MODEL_3D.md` by SHA-256 in their own code, so the protocols
ship unchanged. As a result, one planning sentence in `FIT_MODEL_2D.md` (§5.3) and one in each `FIT_MODEL_3D` revision (§5, data
archiving) still name a personal machine.

## Hash bindings

Each 1D fit run records the SHA-256 of its code, protocol and inputs. Each snapshot manifest hashes every merged summary and block
archive. Each 2D/3D analysis record pins its histogram index and the campaign manifest. The P1 calibration binds the amendment, the
calibration script, both evaluators, both protocols, both production evaluations and the 16 primary analysis records, and the evaluators
refuse to run if any of these changed. The note's appendix "Protocol identities and history" lists the hash prefixes. They can be checked
with `make replay`, which runs the evaluators in a byte-identical copy of the code.
