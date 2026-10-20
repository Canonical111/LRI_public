# Verification and mechanical changes

## Edition of 2026-10-19 (current)

This edition was regenerated from the public tree at commit `235d48fb`, the release export (paper final at `f496d39a`).

**Note pins.**

| Folder | Pin |
|---|---|
| Opening part | `paper/supplement`, unchanged since `809abc03` |
| GFF | `953aa45` |
| SRI | `2573c81` |
| HT_Pert | `1c80acc` |
| HT | `75bf0cd` |
| Resummation | `e4323ea` |
| MC | note file only (no Git history), SHA-256 `c07fed97…` |
| NRG | unchanged |

**What changed in the sources.** It follows the author's rule of 16 October 2026: each direction has one TeX note.
- GFF gains Part V (bulk one-point data) and Appendix B (the derivation of the C6(1) representation).
- SRI gains Appendices A–G, and Sec. 2.7 with Appendix I (the eighth order from the integrable point).
- HT_Pert gains Appendices A–C.
- HT changes in references, following paper commit `827a27bf`, gains three d = 1 reproduction rows (V5–V7) for paper commit `78ff6f6c`, and rewords the treatment of the zero mode in its abstract, summary and Sec. 2.4.
- Resummation changes in references, following paper commit `827a27bf`, and draws the published Monte Carlo values in Figs. 1, 5 and 6 with one color per reference.
- SRI states that the magnetization-scheme calculation of Appendix I ships as the package `integ_d1`, and that the paper quotes its value; the interval for c1 in d = 3 is called an estimated range, as in the paper, also in Resummation.
- HT and HT_Pert cite Elias Miró and Hardy (arXiv:2003.08405) as the precedent for the window correction; HT also states the backtracking of its Newton step (Sec. 2.6).
- SRI and MC name the project's Zenodo data record (DOI 10.5281/zenodo.23466766) for their hosted inputs, which `make fetch-data` downloads and checks; HT_Pert's d = 2 reproduction row for the r2 slope cites its own Sec. 4.4.
- Every note that cites the paper uses its final title, "The long-range Ising CFT: perturbative and nonperturbative approaches".
- New: an opening part, "AI agents and reproducibility", moved out of the paper at the author's request of 19 October 2026 (paper commit `afa897c9`). Its source is `paper/supplement/ai_front.tex` with the figure `paper/supplement/fig_agents.tex`, a self-contained file with the macros, colors and references it uses.

The packaging rules described below are unchanged. Numbers in the sections after this one are those of the first edition where they differ; the current values are given here.

**Size.** The eight sources total 727 pages (3 for the opening part, 724 for the notes), and the combined PDF has 733, of which 9 are front matter: the title, the contents, the preface and the opening part. The part ranges are in the root README.

**Generator counts:**

| Part | Labels | Reference/citation keys | Bibliography keys | Macros scoped | Macros renamed | Explicit paths | Package option families | Inner parts retained |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Opening part | 2 | 10 | 9 | 13 | 0 | 1 | 2 | 0 |
| GFF | 1071 | 4539 | 52 | 26 | 0 | 0 | 2 | 5 |
| SRI | 467 | 1259 | 38 | 19 | 0 | 0 | 4 | 0 |
| HT_Pert | 121 | 257 | 6 | 189 | 0 | 37 | 2 | 0 |
| HT | 60 | 146 | 17 | 101 | 0 | 29 | 2 | 0 |
| NRG | 67 | 236 | 28 | 323 | 0 | 22 | 4 | 0 |
| MC | 48 | 151 | 29 | 8 | 0 | 0 | 4 | 0 |
| Resummation | 65 | 184 | 27 | 14 | 0 | 6 | 4 | 0 |

GFF's five original `part` headings (I–V) are kept as `SourcePart` headings beneath the outer Part I.

**Preservation checks** (`make check`, 2026-10-19). All pass for every part, the opening part included:
- source and asset hashes;
- the inverse source comparison: zero changed physics files, and the `*_source_differences.json` files are empty;
- runtime definitions: all 693 source macro definitions match the standalone builds, with zero leaked definitions;
- figure events: 1 figure in the opening part (one inline TikZ picture), then 0, 0, 2, 3, 7, 2 and 6 figures in the notes; MC has three inline TikZ pictures;
- the normalized PDF character inventories are identical.

**PDF text differences.** The opening part, GFF, SRI and Resummation have zero normalized line or token differences. HT_Pert, HT, NRG and MC have 26, 13, 25 and 21 token edit blocks. All are float, table and page-boundary reading-order changes; each is stored with its explanation in `*_text_differences.json`.

**Audit change in this edition.** With the author's approval (18 October 2026), `tools/check_combined.py` also removes the continuation header of HT_Pert's package table (its Sec. 8, a `longtable` whose `\endhead` row is "package (code/), d, role, content, records, cost") before it compares the two texts. It already did this for the reproduction tables of HT_Pert and HT. In this edition the package table breaks across a page in the standalone build, so its header is printed twice there and once in the combined build. Without this rule the extra header unbalances the character inventory and leaves every HT_Pert block unexplained, although no text differs. `checks.json` records the counts removed (standalone 2, combined 1).

**Opening part (generator change, approved by the author on 19 October 2026).** `tools/common.py` lists the opening part first, with tag `ai` and its source folder `paper/supplement`. `tools/build_combined.py` treats it like a note, with the same snapshot, namespacing, macro scoping and audit hooks, except that:
- it gets no part page and no part number, only a contents line repeating its own unnumbered heading;
- it is placed after the contents and the preface (author's order of 19 October 2026), in the roman front matter, followed by `\restoregeometry`;
- it contributes no preface excerpt;
- like HT_Pert and HT, it is set in its source's Computer Modern fonts.

The audit lines now record the numeric page counter, because this part has roman folios. `tools/check_combined.py` compares its text from just after its heading, locates it by physical page and recognizes roman folios. Its standalone build is the source file itself (3 pages). The public release ships no `paper/` folder, so `snapshot()` then keeps the tracked `sources/ai/` and checks each of its files against the SHA-256 recorded in `source_manifest.json`. A rebuild from a `git archive` of the release build without `paper/` (`build_combined.py`, `make`, `make check`) passes for all eight parts. It reproduces the master, the preface, every part and source file and all JSON reports byte for byte, and the PDF text exactly.

**Build.**
- No errors, undefined references or citations, multiply defined labels or duplicate destinations.
- Two overfull warnings, both reproduction-table cells:
  - HT_Pert 1.52611 pt, which does not occur standalone;
  - HT 2.11588 pt; the same cell is 0.9031 pt standalone.
- All standalone notes build with zero overfull boxes, except HT, which has that one cell. See `overfull_comparison.json`.
- SyncTeX is retained for the master and every standalone build.

**Visual inspection.** Rendered review of this edition covered the first contents page, the preface and the opening part (PDF pages 2, 6 and 7–8); the contents pages keep the master's text margins. In earlier builds of 18 October the pages with new material were reviewed: HT_Pert Sec. 2.7, HT Sec. 3, Resummation Fig. 1, the SRI and HT part openings, SRI Sec. 2.7, the input table of Appendix I and HT's summary. These pages now sit three PDF pages later. The preface's title and the other new sentences, including those of the final rebuild (SRI Sec. 4.3 and Table 2, HT Sec. 2.6, Resummation Sec. 5.3), were checked in the extracted text. The figure and text checks above are automated. No full page-by-page review was made.

**Privacy.** `privacy_audit.json` was refreshed for this edition. All 244 tracked and new files, and the tracked root copy `Supplementary Material.pdf`, were scanned, including the PDFs as raw bytes and as extracted text. The scan looked for absolute home paths, the names of the authors' personal machines with their host and user names, and the cluster account name. It found none. The only token matches are graph-theory and JSON terminology and the permitted repository URL.

## First edition (2026-10-15)

This part describes the 2026-10-15 combined edition. It is packaging verification, not an independent verification of the scientific results. Source snapshots, SHA-256 checks, standalone warning baselines, and all machine-readable results are retained beside this report. The seven original notes were compiled before the first merged build; final validation repeated those builds from fresh temporary copies. A second generation from the tracked snapshot reproduced all 103 generated files byte for byte.

## Changes counted by the generator

Counts refer to command/key occurrences or distinct macro names, as specified below; they do not count changed physics statements. Missing count fields in the JSON mean zero.

| Part | Labels | Reference/citation keys | Bibliography keys | Macros scoped | Macros renamed | Explicit paths | Package option families |
|---|---:|---:|---:|---:|---:|---:|---:|
| GFF | 704 | 1400 | 30 | 26 | 0 | 0 | 2 |
| SRI | 39 | 82 | 11 | 17 | 0 | 0 | 4 |
| HT_Pert | 62 | 56 | 2 | 182 | 0 | 34 | 2 |
| HT | 60 | 81 | 5 | 97 | 0 | 29 | 2 |
| NRG | 64 | 201 | 27 | 285 | 0 | 22 | 4 |
| MC | 48 | 130 | 27 | 8 | 0 | 0 | 4 |
| Resummation | 59 | 93 | 19 | 14 | 0 | 6 | 4 |

“Reference/citation keys” includes reference commands and each citation key, including multiline optional citation arguments. Bibliography keys count `bibitem` entries. “Explicit paths” includes inputs, includes, graphics, wrapper graphics commands, and optional-file guards; the search-path changes below are separate. “Package option families” counts source-used packages whose options differ across the seven notes, not distinct error messages.

| Part | Titles moved | Local ToCs removed | Inner parts retained | Input search paths replaced | Graphic search paths rebased | Absent optional paths retained | Source font restoration | Structural fields restored | Checksum metadata removed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GFF | 1 | 1 | 4 | 0 | 0 | 0 | 0 | 3 | 0 |
| SRI | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 1 |
| HT_Pert | 1 | 1 | 0 | 1 | 1 | 4 | 1 | 3 | 0 |
| HT | 1 | 1 | 0 | 1 | 1 | 0 | 1 | 3 | 0 |
| NRG | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| MC | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| Resummation | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 3 | 0 |

Each part additionally has one group wrapper, one independent counter reset, one restored page size/margin/font-size setup, and one retained local bibliography. Three nonlocal structural definitions (`theequation`, `cl@section`, `theHequation`) are explicitly saved and restored per part because `amsmath` makes some numbering assignments globally. All seven source class declarations are replaced by the master report class; the package union is loaded once. No scientific macros or theorem names are renamed. No source-defined theorem environments are present in this snapshot.

GFF's four original article `part` headings become `SourcePart` headings, retain their wording and Roman I–IV numbering, and appear beneath the new outer Part I. The original seven titles become the seven outer part titles; original authors and dates are retained. The master title, one-page excerpt preface, and one master contents are new front matter. Source metadata that describes a standalone PDF is replaced by the combined title/author metadata; SRI's standalone-file checksum metadata is omitted from the merged artifact only.

### Package/layout decisions

- Geometry has four source option strings. Each part restores its source paper size and margins: A4/23 mm for GFF, SRI and Resummation; Letter/2.5 cm for both HT notes; A4/2.2 cm for NRG and MC. Font sizes remain 11 pt or 10 pt as in each original.
- Hyperref options and standalone PDF metadata are consolidated into one hidden-link style and combined metadata. Reference/anchor namespaces avoid collisions, while displayed numbering stays local. The combined author and repository URL remain TBD by request.
- Enumitem is loaded once with `shortlabels`; source-specific list settings stay in their own part.
- Caption is loaded once; the two HT parts restore their original normal caption font. The other source-local caption settings remain scoped.
- The two HT parts restore Computer Modern/OT1 text and a separate original Computer Modern math version; the other parts use their source Latin Modern/T1 setup. A local 3 em emergency paragraph stretch in the HT parts reduces merge-induced line overflow without changing the text or suppressing warnings.
- The master emulates article-style section/appendix/bibliography numbering and includes subsubsection numbering. Source heads, bibliography entries, and status language remain in place. Continuous body folios and part-specific anchors are the intended global numbering changes.

The four affected option families are `geometry`, `hyperref`, `enumitem`, and `caption`. GFF and both HT notes use the first two; SRI, NRG, MC and Resummation use all four. Exact original option strings are in `package_options.json`.

## Preservation checks

1. **Source bytes.** Every snapshot file is checked against its recorded hash. All non-TeX copied assets in `parts/` must have the same hash. On delivery, every recorded file was also rechecked against the public tree; none had changed.
2. **Inverse source comparison.** The checker reverses only the part prefixes, resolved paths, relocated title/contents, and GFF inner-part command. It compares the full active body and every included TeX file with its standalone source, without changing numbers, prose, table rows, or source order. The seven `*_source_differences.json` files are empty. Comments are excluded from this inverse comparison, while original snapshot comments remain covered by the byte hash.
3. **Runtime definitions.** Nonprinting audit hooks compare all 629 source macro definitions at both part boundaries with the corresponding standalone build. They include the generated number macros and explicit `csname` definitions. The union of source macro names, plus three structural definitions, is compared outside every part group. There are zero differing or leaked definitions. This specifically covers the two independent `numbers_d1.tex` inputs.
4. **Figures.** Audit events record figure environments, resolved graphic file draws, and inline TikZ draws. The full event sequence and counts match the standalone sequence in each part, and asset bytes match. Counts are 0, 0, 2, 3, 7, 2 and 6 figures respectively; MC's two figures contain three inline TikZ pictures. Every source figure is drawn once.
5. **PDF text.** `pdftotext -raw -bbox` extracts each part independently using recorded part boundaries, including the original abstracts (HT_Pert starts with its Summary because it has no abstract). Only running heads, actual page-number words, relocated title/front matter, original local contents, documented repeating continuation headers, whitespace, ligatures and alphabetic hyphenation are normalized. Arbitrary scientific numbers are never deleted. Legacy control-code glyphs remain distinguishable using private-use Unicode substitutions. The normalized character inventory is identical for every part.
6. **Build/SyncTeX.** The final log has no errors, undefined references/citations, repeated labels or PDF destinations. SyncTeX is enabled, readable, nonempty and retained for the master and each standalone build. Overfull warnings remain visible and are reported separately.

The extraction normalizes alphabetic compound/discretionary hyphens as well as line breaks; therefore it is not by itself a proof of sign or word-order preservation. The independent verbatim source audit, runtime macro checks, and figure-event checks are required together. No claim is made to have numerically recomputed every formula. The original source numbering already matches, so this snapshot does not need a broad regex that strips equation, citation, or section numbers.

## Remaining PDF text differences

GFF, SRI and Resummation have zero normalized line or token differences. HT_Pert, HT, NRG and MC have 4, 16, 28 and 20 token edit blocks. Every full block is stored with an explanation in its `*_text_differences.json`; the paired 100-character line diff is in `*_text_diff.txt`.

The blocks were reviewed against the unchanged source and correspond to these placement changes:

- **HT_Pert:** section 3.3 versus the preceding floating material, and the first coefficient figure/caption versus surrounding body text.
- **HT:** tables of finite-cutoff results, effective exponents and sector shifts; all three figure/caption blocks; and body paragraphs that move relative to those floats or a page boundary.
- **NRG:** the results table and first comparison figure; validation text versus floats; convergence figures and tables in sections 7–8; a footnote in the method comparison; multipage estimator table headers; and the final table versus the glossary. The source order and all printed numbers remain unchanged.
- **MC:** table-note and footnote positions; the first results figure and results tables; sensitivity-analysis/theory-comparison text around floats; tables and continuation material in the two- and three-dimensional sections; and appendix/glossary text relative to remaining floats.

A PDF edit block can interleave a moved figure with fragments of an otherwise unchanged sentence. This is why some `replace` blocks include short digits or section numbers even though no source value changed. The explanation applies to PDF reading order, not to an authorized source-text reordering. Character-inventory equality alone would not be enough to accept a merge; the independent checks above must also pass.

Continuation-header normalization is explicit and counted in `checks.json`: the two HT reproduction-table headers, the NRG glossary continuation header, and the MC series-continuation headers. Nothing else is dropped as an assumed repeated table row.

## Warnings and visual inspection

The original PDFs total 378 pages. The combined PDF has 388 pages, with six front-matter pages and physical part ranges documented in the root README. Original-size pages are retained, including Letter pages for HT and HT_Pert.

There are 69 overfull warnings (HT_Pert 36; HT 33), versus 70 in the standalone baselines (35 each). Two newly appearing warning locations are 1.12584 pt and 0.91765 pt in reproduction-table cells. The other warning locations also occur in their standalone note, though magnitudes and counts can change with pagination. `overfull_comparison.json` records every warning and identifies new locations by warning type and source line range. This is a location comparison, not a claim of identical layout. The largest inherited overflow is 170.95035 pt; the source table formatting has been retained, so some reproduction tables remain crowded.

Rendered review covered 44 selected physical pages: 1, 2, 3, 6, 7, 8, 208, 209, 210, 232, 233, 234, 243, 247, 267, 268, 269, 278, 284, 287, 298, 299, 300, 303, 309, 311, 313, 315, 316, 330, 331, 332, 340, 348, 358, 359, 360, 372, 373, 376, 379, 381, 382, 388. This includes all figure pages, each part opening and ending, and representative contents/front matter. Contact sheets were inspected; the final one-page preface was additionally inspected at full size after setting the repository URL to TBD. The review confirms visible part structure and intact figure placement; it does not assert that all 388 pages were manually read or that inherited source layout problems have been repaired. Local renders are retained under ignored `build/qa/`.

## Privacy, provenance and limitations

The delivery privacy audit scans all intended tracked files, raw PDF bytes, extracted PDF text and metadata for forbidden absolute home-directory paths and the specified personal-host tokens. Mathematical constants, state-label extraction artifacts, graph/JSON terminology, and comments identifying the authoritative source version are reviewed as non-host usages, not silently erased. Results are in `privacy_audit.json`.

The public tree is read-only throughout this task. No older private research-note copies are used. NRG and MC have no note-level README/manifest in this snapshot, so parent READMEs are used and recorded. The missing public URL stays TBD with the author's approval. Two small newly appearing overflow warnings and the inherited larger table warnings are the remaining layout limitations. No system-wide software was installed and no scientific production calculations were run.
