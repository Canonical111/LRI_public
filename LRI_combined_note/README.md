# The long-range Ising CFT: research notes

This repository combines the seven published research notes into one self-contained document, opened by a short part on how the work was organized and checked. It packages existing text and figures; it does not recompute, update, or adjudicate the physics.

- [Combined PDF](../Supplementary%20Material.pdf), **733 pages**: tracked at the repository root as `Supplementary Material.pdf`; `make` writes the same file here as `lri_combined_notes.pdf`, which Git ignores.
- [Master TeX](lri_combined_notes.tex) and [one-page preface](preface.tex).
- [Detailed verification and mechanical-change inventory](reports/VERIFICATION.md).
- [Machine-readable checks](reports/checks.json) and [privacy audit](reports/privacy_audit.json).

The **seven published folder notes are authoritative**. Read only the copies in `~/Documents/LRI_public/{GFF,SRI,HT_Pert,HT,NRG,MC,Resummation}/note/`. The opening part, "AI agents and reproducibility", was moved out of the paper at the author's request (19 October 2026); its authoritative source is `paper/supplement/ai_front.tex` with its figure `paper/supplement/fig_agents.tex` in the project's working repository. The public release ships no `paper/` folder (the paper is on arXiv), so there the opening part is rebuilt from its verbatim snapshot in `sources/ai/`; `tools/build_combined.py` first checks every file of that snapshot against the SHA-256 recorded in `reports/source_manifest.json`. Never edit `parts/`, `sources/`, or the generated master to correct physics: update the authoritative publication through its own workflow, then regenerate this repository. The generator reads the public tree and writes only to this combined repository. The public repository is https://github.com/Canonical111/LRI_public; its root `README.md` and each folder's `results_map.md` are the code/data/replay entry points. The combined author list is also **TBD**; original part authors and dates are preserved.

## Rebuild

From this repository, with Python 3.9 or newer, GNU Make, `latexmk`, a working pdfLaTeX installation, and Poppler (`pdftotext` and `pdfinfo`) on `PATH`:

```sh
python3 tools/build_combined.py ~/Documents/LRI_public && make
make check
```

The public-root argument is optional and defaults to `~/Documents/LRI_public`. Without a `paper/` folder in that tree, the opening part comes from `sources/ai/` as described above; the seven notes always come from the public tree. Python scripts use only the standard library. No network service, numerical production job, Mathematica installation, or external research checkout is needed to build the combined PDF from this repository.

To build from the tracked snapshot without access to the public tree:

```sh
python3 tools/build_combined.py --from-snapshot && make
make check
```

`make` builds with SyncTeX enabled and checks that `lri_combined_notes.synctex.gz` is readable. `make check` also makes fresh temporary copies of all eight sources (the opening part and the seven notes), builds their standalone PDFs with nonprinting audit hooks, and runs `tools/check_combined.py`. It takes a few minutes, depending on the TeX installation. The temporary copies, complete logs, PDF extraction cache, and rendered review pages are under ignored `build/`. The built PDF, auxiliary build products and SyncTeX are retained locally but ignored by Git; after each rebuild the PDF is copied, byte for byte, to the repository root as `Supplementary Material.pdf`, which is the tracked copy that the paper links to.

When auditing a new public snapshot before merging, use:

```sh
python3 tools/build_combined.py ~/Documents/LRI_public --snapshot-only
python3 tools/build_standalone.py
python3 tools/build_combined.py --from-snapshot
make check
```

The required TeX packages are listed in the generated master and [package-options report](reports/package_options.json). They include the AMS packages, geometry, Latin Modern, microtype, graphicx, fancyhdr, listings, longtable, caption, enumitem, dsfont, rotating, PGFPlots, hyperref, xurl, and etoolbox. No packages are installed by these scripts. This edition was validated with pdfTeX/TeX Live 2021; different TeX/font/Poppler versions may change pagination and extracted-text diffs, so rerun the checks and refresh this report after changing the toolchain.

## Parts and page ranges

“PDF pages” means physical, one-based PDF page indices. Front matter occupies pages 1–9 with roman folios: the title, the contents (pages 2–5), the preface (page 6) and the opening part "AI agents and reproducibility" (pages 7–9, folios vii–ix). The opening part has no part page and no part number, so the seven notes keep Parts I–VII. Body folios restart at 1 and remain continuous through 724. Each note part begins with a title page using its original full title. The eight source PDFs total 727 pages (3 for the opening part, 724 for the notes). Removing their local contents and adding part pages, plus float and table reflow, produces the 733-page combined volume.

This edition follows the author's rule of 16 October 2026: each direction has one TeX note. The separate notes that came with the packages are merged into their folder notes and are no longer cited as notes:
- GFF gains its Part V on bulk one-point data and Appendix B.
- SRI gains Appendices A–G, and Sec. 2.7 with Appendix I (the eighth order from the integrable point).
- HT_Pert gains Appendices A–C.

| Part | PDF pages | Printed body pages | Standalone pages | Figures |
|---|---:|---:|---:|---:|
| Opening part (AI agents and reproducibility) | 7–9 | vii–ix | 3 | 1 |
| GFF | 10–381 | 1–372 | 373 | 0 |
| SRI | 382–541 | 373–532 | 161 | 0 |
| HT_Pert | 542–603 | 533–594 | 62 | 2 |
| HT | 604–638 | 595–629 | 35 | 3 |
| NRG | 639–672 | 630–663 | 32 | 7 |
| MC | 673–701 | 664–692 | 29 | 2 |
| Resummation | 702–733 | 693–724 | 32 | 6 |

GFF and SRI have no figure environments. The opening part's figure is one inline TikZ picture, and MC has two figures containing three; all these draws match their standalone sources. The other figures use copied PDF assets. Every source figure is drawn exactly once in its corresponding combined part; the selected preface excerpts contain no figures.

## Verification of this edition

Validation date: **2026-10-19**. `make check` completed successfully.

Public tree at commit `235d48fb` (paper final at `f496d39a`), with these folder-note pins:

| Folder | Note pin |
|---|---|
| Opening part | `paper/supplement`, unchanged since `809abc03` |
| GFF | `953aa45` |
| SRI | `2573c81` |
| HT_Pert | `1c80acc` |
| HT | `75bf0cd` |
| Resummation | `e4323ea` |
| MC | note file only (no Git history), SHA-256 `c07fed97…` |
| NRG | unchanged |

Results:
- **0 errors, 0 undefined references, 0 undefined citations, 0 multiply defined labels, and 0 duplicate PDF destinations.**
- **2 overfull-box warnings**, both small table-cell overflows in reproduction tables:
  - HT_Pert, **1.52611 pt**: none in its standalone build;
  - HT, **2.11588 pt**: the same cell overflows by 0.9031 pt in its standalone build.
- All other parts have none in either build. The overflows are reported, not hidden by changing warning tolerances. See [the warning details and the standalone comparison](reports/overfull_comparison.json). No table contents were rewritten to improve layout.

| Part | Differing normalized lines | PDF difference blocks | Source macros checked | Changed physics-source files | Macro mismatches | Leaks | Figure check |
|---|---:|---:|---:|---:|---:|---:|---|
| Opening part | 0 | 0 | 13 | 0 | 0 | 0 | pass |
| GFF | 0 | 0 | 26 | 0 | 0 | 0 | pass |
| SRI | 0 | 0 | 19 | 0 | 0 | 0 | pass |
| HT_Pert | 406 | 26 | 189 | 0 | 0 | 0 | pass |
| HT | 266 | 13 | 101 | 0 | 0 | 0 | pass |
| NRG | 334 | 25 | 323 | 0 | 0 | 0 | pass |
| MC | 530 | 21 | 8 | 0 | 0 | 0 | pass |
| Resummation | 0 | 0 | 14 | 0 | 0 | 0 | pass |

A normalized “line” is a 100-character chunk after whitespace/header normalization, not a physical printed line. The nonzero counts represent PDF reading-order changes associated with float, footnote, and multipage-table placement. They are **not** a claim that the extracted PDF text is identical in sequence. Every remaining edit block and its explanation is saved in `reports/<tag>_text_differences.json`; complete normalized line diffs are in `reports/<tag>_text_diff.txt`. The independent inverse-source audit reports zero changed physics files for every part. All 693 named source/scientific macro definitions match the standalone build at the start and end of their part, and the union of those definitions plus structural state is checked before and after each group. The normalized PDF character inventories also match exactly. See the detailed report for the normalization rules and their limits.

## Repository layout

- `sources/<tag>/`: verbatim source/figure snapshots, SHA-256 recorded in `reports/source_manifest.json`.
- `parts/<tag>/`: generated, mechanically namespaced bodies and scoped preambles, plus copied assets.
- `tools/build_combined.py`: snapshot and regeneration; no Python third-party dependencies.
- `tools/build_standalone.py`: temporary standalone builds and baseline warning/audit records.
- `tools/check_combined.py`: source, macro, figure, PDF text, reference and build checks.
- `reports/`: tracked audit outputs and the human-readable account of all changes.
- `build/`: ignored temporary builds and review material.

There is one master table of contents and one local bibliography per part. Labels, reference keys, and citation/bibliography keys carry the part tags `ai:` (opening part), `gff:`, `sri:`, `htp:`, `ht:`, `nrg:`, `mc:`, and `rs:`. Local section, equation, figure, table, appendix, and bibliography numbering is preserved. Original statements such as “this note,” status qualifiers, caveats, and uncertainties remain unchanged.

## Maintenance limits

The generator supports the opening part and the current seven notes and rejects unresolved figure paths or unsupported dynamic reference keys. Future notes adding new macro-definition forms, theorem environments, package conflicts, or conditional inputs require review of the transformation and audit rather than assuming that the current checks cover new syntax. Macro checks are runtime definition checks and source-preservation checks, not a numerical replay of the research.

NRG and MC currently lack `note/README.md` and `note/MANIFEST.json`; their parent-folder READMEs were used instead. The manifest records those README paths and hashes. All copied public source/asset hashes were rechecked against the read-only public tree. The original notes and all research calculations were left untouched.
