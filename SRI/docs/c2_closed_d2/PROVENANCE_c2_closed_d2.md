# Provenance: c2_closed_d2

Dated snapshot of 2026-10-15 (sha256 list `public/SNAPSHOT.sha256`, 333 files, checked by `make -f public.mk test` and
`replay`). Neither part is a git repository.

| Part | Author | Dates |
|---|---|---|
| Closed-form study (`README.md`, `note/` (not shipped since 16 October 2026; its derivation is the SRI note, Appendix E), `code/`, `inputs/`, `outputs/`, `provenance/`, `MANIFEST.json`, `DEPENDENCIES.json`, `requirements.txt`) | OpenAI GPT-6 astra (via ChatGPT), supplied by the author; stated by the author on 2026-10-14. The note's `\author{}` is empty (PDF metadata "C2 research project"). | note presentation revision 2026-10-07; shipped run 2026-10-08 (`outputs/run_manifest.json`, 01:36 UTC, Python 3.12.14 on Linux); note build and document validation 2026-10-08 |
| Coordinator edit of three study files | Claude Code (SRI session), 2026-10-14: added the field `authorship` to `provenance/source_map.json` and one authorship sentence to `README.md` ("Provenance and exclusions"), and updated the two entries of `MANIFEST.json` for these files (bytes and sha256). No other change. | 2026-10-14 |
| `mc/` (`c2mc3.c`, `integrand2.h`, `summ.py`, `prod.sbatch`, `prodC.sbatch`, `alpha_*.txt`, `run_{A,B,C}/`) | Claude Code (review session of 2026-10-08): code, drivers and runs | 2026-10-08 |
| `public.mk`, `public/` | Claude Code (SRI package builder for c2_closed_d2), new | 2026-10-15 |

The 2026-10-14 edit, as sha256 before -> after (the originals are kept by the SRI session and are also inside the
unchanged archive `SRI/LRI_C2_final_method.zip` of 2026-10-12, not exported):

- `README.md`: 8554e710485f2030... (12 791 bytes) -> 911f622c14da3b26... (12 951 bytes);
- `provenance/source_map.json`: 6274266b694eb8bf... (9 326 bytes) -> 35f16b1d5212579f... (9 637 bytes);
- `MANIFEST.json`: d284752f3ecbc63f... -> a9d556fe3b299002... (only the two entries above changed).

The study's own provenance (`provenance/source_map.json`) names its source: a supplied research compendium
(`01-LRI_2D_research_compendium-1-.zip`, 185 560 943 bytes, sha256 6da49f9f...; not shipped, not needed to run), from
which `code/lri_C2_three_4F3.py`, `code/lri_C2_renormalization_checks.py`, `inputs/ising2d_exact_data.json` and the two
`inputs/reference/` files were copied unchanged, `code/source_contact_checks.py` and `code/independent_c2_checks.py` were
trimmed (removals listed there), and the remaining files were newly written for the package.

The Monte Carlo was fetched read-only on 2026-10-15 and checked byte-identical (sha256) against the remote files:
`c2mc3.c`, `integrand2.h`, `summ.py`, `prod.sbatch`, `alpha_e0.05_L16_k35.txt`, `run_A/`, `run_B/` from symmetry
scratch (`<SCRATCH>/c2rev_e2e/`); `run_C/` and `prodC.sbatch` from the personal desktop (`<DATA>/<USER>/c2rev_e2e/`),
whose copies of the four shared files are byte-identical to symmetry's. The review session's local working copy is
lost. Runs: A, Slurm job 571407 and B, job 571408 (symmetry amdq, one 64-core AMD EPYC node each, binaries built by
`prod.sbatch` with gcc 11.2.0, `-O2 -march=x86-64-v3 -DUSE_QUAD`); C, Slurm job 461 on the personal desktop (14 workers).
`public/mc_production_logs.json` transcribes what `summ.py` printed in the three job logs (not shipped: they name the
compute nodes and the desktop). The personal desktop's chunks were found on that machine and ship as `run_C/` (file
names carry no machine name; the chunk headers name none).

No shipped file was changed by this package (no re-pinned records). Files with private paths, for the publication scrub
(listed then in `public/SCRUBBED.txt`): `outputs/run_manifest.json` (the authoring sandbox's absolute paths; bound only
by the study's `MANIFEST.json`), `mc/prod.sbatch` and `mc/prodC.sbatch` (cluster and desktop paths). No shipped file
names a personal machine.

## Not recorded

- The "independent audit" stage inside the supplied compendium (`reproduction/stages/01_independent_audit/`, source of
  `code/independent_c2_checks.py` and of the audit scope quoted in the note) is part of the supplied study, so it is
  OpenAI GPT-6 astra's work (via ChatGPT, supplied by the author); the archive records no separate author for it.
- Run C: the compiler flags of the desktop binary are not recorded (it links libquadmath, so it was built with
  `-DUSE_QUAD`, 1 s after `c2mc3.c` was written, from the same source).
- The review's recombination script (Monte Carlo -> c_2) was not kept. `public/c2lib.py` re-implements the rule from the
  review's text and the note's formulas; it reproduces every number the review prints (Omega_4 66.34 +- 0.24, chi^2
  1.29, J 10.559 +- 0.039, z_41 1.6391 +- 0.0076, c_2 -4.075 +- 0.019, 16.185 +- 0.053 and the predicted 16.150), so the
  rule is recovered, not the script.
- The pilot adaptation that produced the pre-adapted weights `alpha_e0.05_L16_k35.txt` of run A (same review session, on
  the personal desktop) is not recorded beyond these weights; the pilot run itself is not shipped.
