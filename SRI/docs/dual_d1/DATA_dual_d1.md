# Data: dual_d1

The compendium archive holds 8,560 files (2.08 GB). The package ships 705 of them (61 MB, about 8.8 MB packed),
byte-identical, chosen by a dependency trace: every compendium task was run on the full archive with a file-access
tracer (symmetry job 575588), and the package keeps the stored files that `test`, `replay` and `replay-full` read, all
code, and the records they compare with. `public/SNAPSHOT.sha256` lists the shipped files; each one also equals its
entry in the compendium's `reproduction/MANIFEST.json` (checked by `make test`).

| Shipped (code/dual_d1/) | Size | Read by |
|---|---|---|
| `code/` (all programs) | 9.2 MB | every task; `code/archived/C6_closed_form/verify_C6_period_identity.py` (6.9 MB) embeds the C6 certificate |
| `data/archived/C6_closed_form/` | 15.3 MB | C6 input map: the 16 beta inputs, the C6 trace, candidate and difference expressions, the 1,945-word target, the certificate rows of weights 2..5 (`C6_certificate_w5.json`, 14 MB) |
| `data/archived/C8_full_numerical_completion/` (22 of 84 files) | 14.2 MB | run_checks.py, c8-positive-check: the exact expressions P8, Kv, J9, A9_log, Z8_log, EA7_finite, EZ6_finite, J9_lower_shift, F3_known, the P8 divergence expressions, the 70/100-digit input records, the six inherited inputs, U record |
| `data/archived/C8_P6_exact_sources/` (72 of 678 files) | 10.2 MB | c8-saved, c8-numerical: `P6.expr` (66,404 terms), the 64 terminal outputs, `P6_exact_report.json`, the 70/100-digit evaluations and manifests, the divergence controls |
| `data/archived/C7_closed_form_proof/` (5 of 16) | 4.3 MB | C7 input map and certificate: `C7_linear_words.json` (25,212-word target), certificates of weights 2..5 |
| `data/archived/F2_F3_delivery/` (13 of 129) | 1.9 MB | C7 input map: the 9 newer beta inputs (alpha, beta, gamma, Phi, Psi, Omega, K, P, Q) and the D4 and C7 expressions |
| `data/archived/{C8_zeta_candidate, C8_rational_completion/result.json, C8_rational_completion/.../T4_rational_reduction.json, D3_analytic_proof, C8_full_work/full_trace.json}` | 60 kB | the C8 record (`result.json`), the rational C8 = 88 record, the 25 old rational beta inputs, the full trace polynomial |
| `data/coefficients.json`, `data/current_status.json` | 5 kB | the registry |
| `outputs/` (tables, verification, C8 candidate records) | 0.3 MB | comparisons with regenerated reports |
| `reproduction/` | 6.0 MB | `layout.json` and `MANIFEST.json` (read by every task), omissions, source archives, environment |
| `references/`, `documentation/{REPRODUCTION,SCRIPT_OUTPUT_MAP}.md`, `public/compendium_extract.json` (the TeX blocks the checks parse; the compendium's note, TeX and PDF, is not shipped since 16/17 October 2026, `public/NOT_SHIPPED.txt`) | 0.04 MB | reading; the extract is read by the replay and by `indep_d1`'s self-test |

**Work copy.** The compendium's tasks materialize the original executable layouts from `reproduction/layout.json`
(11,124 virtual paths -> stored files). Because the snapshot is pruned, `public/dual_lib.py` runs them on a copy
(`$(WORK)/compendium`) whose `layout.json` keeps only the 1,744 virtual paths whose stored file is shipped and whose
`MANIFEST.json` keeps only the shipped files (minus `layout.json` itself, which the copy rewrites; the shipped original
is checked against the same entry). The scripts are not modified.

**Lost file (case collision).** `data/archived/C6_closed_form/input_expressions/a_check_symbolic.expr` (10 bytes,
`-2*pi**2/3`) and `A_check_symbolic.expr` differ only by case; the authors' macOS copy kept only the upper-case file.
The package ships the lost one, byte-identical from the original archive, as
`public/restored/lowercase_a_check_symbolic.expr.txt`; the work copy writes it under its original name when the work
directory is case-sensitive. It is the beta input `a` (`= -zeta(2)*4`) of the C6 and C7 input maps (both read `a` and
`A`); without it those maps fail, so on a case-insensitive work directory they report SKIP.

**Hosted (make fetch-data).** `data/archived/C7_closed_form_proof/proof/C7.w6.certificate.txt`: 57,283,795 bytes, sha256
`1a310b7fe88ed5b7...` (full value in `public/HOSTED.json`), over the 50 MB file limit; needed only by `replay-full`
(the weight-6 part of the C7 certificate). Hosted in the project's Zenodo data record (https://doi.org/10.5281/zenodo.23466766) as
`SRI__dual_d1__C7.w6.certificate.txt` (the same bytes); `fetch-data` downloads it, or takes it from the original archive
(`ZIP=`) or an unpacked copy (`DIR=`).

**Not shipped** (each folder with its reason in the export fragment `not_exported`; all in the original archive):
the raw integration stages and checkpoints of Task A (R6, 381 MB), Task B (R8, 402 MB), the P8 final run (457 MB), F3
(135 MB) and its P8 checkpoint (112 MB), the rational C8 workspace (167 MB) and the C7 completion (37 MB); the P6 raw
sources (182 MB); the full-C8 period tables (47 MB); the earlier packages (`LRI_1d_complete`, F1b, F1c, F2), the
all-order and Gamma trials; `documentation/archived/` (stage notes) and `outputs/archived/` except the C8 records.
The compendium's README and REPRODUCTION.md describe the full archive: commands that need dropped stages (raw P6/P8
regeneration, `--workflow all`, `--task conjectures`) are not supported by the package (nor, in full, by the archive:
REPRODUCE_dual_d1.md).

**Names and paths.** No shipped file names a personal machine or an author path. The records name the other AI
system's sandbox (`/mnt/data/...`, `/opt/pyvenv`, `/workspace`, `/root`): history, not paths to use. Words that
coincide with names of the authors' machines occur only in their mathematical sense (an adjective meaning "standard
form" in 40 code files and some records; the circle constant). Every shipped
compendium file is hash-bound (MANIFEST.json, SNAPSHOT.sha256) and none needs scrubbing or re-pinning. The verifiers
still honour the repository conventions: a file listed in `public/SCRUBBED.txt` (written by the repository's scrub) is
checked for presence only and left out of the work copy's MANIFEST, and a file listed in `public/RE-PINNED.json` is
checked against its published sha256; neither file exists for this package.
