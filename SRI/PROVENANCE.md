# Provenance: SRI

Who wrote what. The author chose the problems, supplied the work of OpenAI GPT-6 astra, approved plans and production
runs, and decided between the options the agents presented. Details, sha256 values and job ids: each package's
`docs/<pkg>/PROVENANCE_<pkg>.md`.

## dual_d1 (C^SR_3..C^SR_8)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| the compendium: code, registry, exact expressions, certificates, records, its note (not shipped; its derivations are the note's Appendices A to C, and the TeX blocks the checks parse are in `code/dual_d1/public/compendium_extract.json`) | OpenAI GPT-6 astra (via ChatGPT), supplied by the author | archive `LRI_1d_full_research_bundle.zip` (408,209,993 bytes), consolidated 2026-10-02 from about 30 earlier packages of the same system | none; the one file the authors' macOS copy lost (case collision) ships restored byte-identical from the archive |
| C^SR_1, C^SR_2 and the dual | Benedetti, Lauria, Mazac, van Vliet (cited) | Benedetti:2024wgx, Benedetti:2025nzp | - |
| `public.mk`, `public/` | Claude Code (Anthropic), SRI session | 2026-10-15 | new |

## indep_d1 (independent re-derivation)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| spec, RG framework, sector engine, direct integration, assembly, results | Claude Code sessions (multi-agent workflows with separate adversarial verifiers), on the author's request; the author set the budgets and approved each phase | project folder (no git), files dated 2026-10-02 to 2026-10-07 | 2026-10-15: 22 files scrubbed of the personal desktop's name and re-pinned (`RE-PINNED.json`; no number changed) |
| its inputs: the compendium's note (definitions, proved closed forms) and the sealed archive values used only for the final comparison | OpenAI GPT-6 astra (as dual_d1) | sealed 2026-10-02/03 | - |
| `public.mk`, `public/` (with the pooled sector record, built from the raw outputs on symmetry) | Claude Code, SRI session | 2026-10-15 | new |

Engine production ran on symmetry (`amdq`); C8 tier A and the cheaper tier-B/C groups (run directories with the
directory suffix `_can`) ran on a personal desktop.

## integ_d1 (C^SR_8 from the integrable point)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| the gauge analysis of the s = 1 flow, the Bethe-ansatz flow, the plan, M1, M2 and the step-0 maps of M3 and M4 | Claude Code, host session of the study, on the author's requests | git repository `LRI_SRI_integrability`, 2026-10-14 | - |
| cluster generator, C++ engine and sector checker, gates, assembly, all engine runs and records from M3 on, fix rounds 1 to 5 | Claude Code, builder subagent of that session | same repository, 2026-10-14 to 2026-10-17 | - |
| plan reviews (three) and code inspections (six) | Codex (OpenAI, gpt-6-astra); no code or record | 2026-10-14 to 2026-10-17 | - |
| the two amendments of check criteria | the author, after their data were seen | 2026-10-17 | disclosed (`docs/integ_d1/REVIEWS.md`) |
| `public.mk`, `public/` (test, replay, git stand-in, the f_202 engine source at b2ab7c6) | Claude Code, the same host session | 2026-10-18 | new |

Engine production ran on symmetry (about 2.7e4 allocated core-hours). Details and commits:
`docs/integ_d1/PROVENANCE_integ_d1.md`.

## c2_closed_d2 (closed form and Monte Carlo of c_2)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| the closed-form study (`LRI_C2_final_method`): note, code, inputs, outputs | OpenAI GPT-6 astra (via ChatGPT), supplied by the author (stated by the author 2026-10-14) | note revision 2026-10-07, shipped run 2026-10-08 | 2026-10-14, Claude Code (SRI session): one authorship field and one sentence added to two files, their two `MANIFEST.json` entries updated; nothing else |
| the end-to-end Monte Carlo `mc/` (code, drivers, per-chunk outputs) | Claude Code (the review of 2026-10-08) | runs A and B on symmetry, C on a personal desktop, 2026-10-08 | none (fetched byte-identical 2026-10-15) |
| `public.mk`, `public/` (with the recombination of the Monte Carlo, re-implemented from the review's text) | Claude Code, SRI session | 2026-10-15 | new |

## c2_cylinder_d2 (cylinder Hamiltonian)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| the study (`LRI_C2_complete`): solver, archived N <= 384 records, note (not shipped; its method is the note's Appendix F), first cluster helpers | OpenAI GPT-6 astra (via ChatGPT), supplied by the author (stated 2026-10-14 and 2026-10-15) | imported unchanged as commit 474487c, 2026-10-12 | Claude Code: a configurable leading-tail cutoff (outputs byte-identical with the default), the `continuum` subcommand, documentation; `data/` and the note unchanged |
| launch layer for SDSC Expanse and symmetry | Claude Code sessions | commits 3d1353e..fa3858a (2026-10-12/13) and the extraction-check plans | inspected twice by Codex; fix-round-2 edits uninspected |
| arbitrary-N continuum analysis and its result | Claude Code sessions | commits 86539b6..98e1935 (2026-10-13/14) | plan reviewed by Codex in seven rounds (approved at rev 7), code inspected twice; fix-round-2 edits uninspected |
| plan reviews and code inspections | Codex (OpenAI, gpt-6-astra) | 2026-10-12 to 2026-10-14 | - |
| cluster records `outputs/` | computed by the shipped code on symmetry and SDSC Expanse, submitted by Claude Code sessions | 2026-10-13/14 | none |
| `public.mk`, `public/` | Claude Code, SRI session | 2026-10-15 | new |

## c1_d3 (c_1 in d = 3)

| Part | Author | Source, date | Later changes |
|---|---|---|---|
| the package (pre-review delivery): code, transcribed inputs, note, outputs | OpenAI GPT-6 astra (via ChatGPT), supplied by the author | note dated 2026-10-07 | superseded by the revision (not exported) |
| the review revision (the shipped version) | OpenAI GPT-6 astra (via ChatGPT), after our review, supplied by the author (stated by the author 2026-10-15) | archive file times 2026-10-08 | 11 code files changed, 4 diagnostic scripts added, inputs relabelled (no number changed), note extended; numbers unchanged |
| review and check of the revision | Claude Code | 2026-10-07, 2026-10-08 | - |
| `review_indep/`: the review's two independent re-implementations of a0, b0, c_1 (4 scripts) | Claude Code review agents | 2026-10-07; fetched byte-identical 2026-10-15 from the review's working folder on a personal desktop | none; a README added 2026-10-15 |
| inputs | Simmons-Duffin 2016 (spectrum), Chang et al. 2024 (S, E_SR, couplings), Reehorst 2022 (epsilon-prime window); transcribed by the package | - | - |
| `public.mk`, `public/` | Claude Code, SRI session | 2026-10-15 | new |

## Top level

`results/quoted_numbers.json`, `results/sr_values.json`, `verify/`, `Makefile`, these files and the note (`note/`):
Claude Code (SRI session), 2026-10-15. On 2026-10-16 the derivations of the six separate notes by OpenAI GPT-6 astra
(the compendium's, the c_2 study's, the cylinder base study's, the c_1 package's and the two arguments of `closure_d1`)
were brought into the note as Appendices A to G by Claude Code sessions (one note per direction, at the author's
request); those notes are no longer shipped. On 2026-10-17 the magnetization-scheme calculation of C^SR_8 was added as
Sec. 2.7 and Appendix I, from the working notes of `integ_d1` (not shipped). The note is its own git repository, exported at a pinned commit
(`note/MANIFEST.json`). The reviews (`REVIEWS.md`) were made by Claude Code sessions and, for `c2_cylinder_d2`, by Codex.

## Dated snapshots and git refs

| Package | Exported as | Checksum lists |
|---|---|---|
| `dual_d1` | pruned dated snapshot (705 of 8,560 files) of the archive of 2026-10-02, unchanged since | `public/SNAPSHOT.sha256`; the compendium's `reproduction/MANIFEST.json` (verbatim) |
| `indep_d1` | dated snapshot taken 2026-10-15 (760 files, last changed 2026-10-07) plus the re-pinned overlay | `public/SNAPSHOT.sha256`; `RE-PINNED.json` (original and published sha256 of the 22 files); the project's own sha256 lists |
| `integ_d1` | git repository `LRI_SRI_integrability` at **git_ref 8bd5a22** (2026-10-17; 724 tracked files selected) | `public/SNAPSHOT.sha256`; the record registry `results/frozen_records.json` and the provenance sidecars; `public/git_blobs.json` (blob ids of the files the verbatim tools ask git about) |
| `c2_closed_d2` | dated snapshot, 2026-10-15 (333 files) | `public/SNAPSHOT.sha256`; the study's `MANIFEST.json` |
| `c2_cylinder_d2` | git repository `LRI_C2_expanse` at **git_ref 98e1935** (2026-10-14; tracked subset), and its git-ignored `outputs/` as a dated snapshot of 2026-10-15 (unchanged since 2026-10-14) | `MANIFEST.sha256` (verbatim); `public/SNAPSHOT.sha256` for `outputs/` |
| `c1_d3` | dated snapshot of the revised delivery (file times 2026-10-08), extracted unchanged 2026-10-15 | `public/SNAPSHOT.sha256`; the authors' `SHA256SUMS` (verbatim, checked in subset mode) |
| `note/` | own git repository at a pinned commit | `note/MANIFEST.json` |

## Not recorded

- `dual_d1`: the dates of the about 30 source packages before the 2026-10-02 consolidation; the archive carries no
  licence and no authorship line (its redistribution terms are settled with the repository's licence).
- `indep_d1`: the reports of the adversarial verifiers of phases 2 to 4 were not kept; what is known of them comes from
  the project's own reports.
- `c2_closed_d2`: the review's recombination script (Monte Carlo to c_2) was not kept (the rule is recovered: it
  reproduces every number the review prints); the compiler flags of the desktop binary of run C and the pilot that
  produced the pre-adapted weights of run A are not recorded; the supplied compendium's "independent audit" stage has
  no separate author.
- `c2_cylinder_d2`: the machine, dates and software of GPT-6 astra's runs behind the 17 archived records, and the
  ChatGPT sessions in which it wrote the four archives; the approved analysis plan is identified only by its sha256
  (the plan and review history is not shipped, by author decision).

## closure_d1

| What | Who | Date | Later changes |
|---|---|---|---|
| the two-coupling closure argument (supplied as a TeX note) | OpenAI GPT-6 astra (via ChatGPT), supplied by the author | 2026-10-15 | not shipped since 2026-10-16; its content is the note's Appendix D |
| the prescription argument with its checker, data and manifest (`prescription/`) | OpenAI GPT-6 astra (via ChatGPT), supplied by the author | 2026-10-15 | the supplied archive extracted byte-identical, except its note (not shipped since 2026-10-16; content in Appendix D); its MANIFEST verifies the shipped files |
| public/ tools | Claude Code session | 2026-10-15, 2026-10-16 | - |
