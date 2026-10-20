# The long-range Ising CFT from five descriptions: code, data and notes

**Status: in preparation. Nothing here is final yet.**

This repository accompanies the Article *The long-range Ising CFT: perturbative and nonperturbative approaches* (arXiv: TBD). It contains the code, the data and the notes needed to reproduce every numerical result of the Article and of its Supplemental Material.

The long-range Ising (LRI) fixed point is studied with five descriptions whose errors are unrelated. Each has its own folder, with a self-contained note, the code, the merged data, and a verifier:

| Folder | Description |
|---|---|
| [`GFF/`](GFF/) | epsilon expansion of the perturbed generalized free field: C_0..C_8 in d = 1, 2, 3, closed forms through fifth order, independent eight-loop codes |
| [`SRI/`](SRI/) | expansions about the short-range end: the strong-weak dual of the chain (d = 1) and the short-range Ising crossover (d = 2, 3) |
| [`HT_Pert/`](HT_Pert/) | perturbative Hamiltonian truncation: the epsilon-expansion coefficients from the truncated Hamiltonian, without Feynman graphs |
| [`HT/`](HT/) | Hamiltonian truncation at finite coupling: the thermal dimension from the dressed zero-mode truncation (d = 1) and window truncations (d = 2, 3) |
| [`NRG/`](NRG/) | numerical renormalization group of the sub-ohmic spin-boson model (d = 1 only) |
| [`MC/`](MC/) | cluster Monte Carlo of the lattice model in d = 1, 2, 3, with the pre-registered fitting protocols |
| [`Resummation/`](Resummation/) | resummation and comparison: Borel resummation of the two expansions, and the comparison of all descriptions with each other and with the published literature values |

Also:
- The Article is on arXiv (arXiv: TBD) and is not part of this repository. Its Supplemental Material is the combined research notes, [`Supplementary Material.pdf`](Supplementary%20Material.pdf), built from [`LRI_combined_note/`](LRI_combined_note/). arXiv v1 contains one additional sentence in Sec. 3.5 (on Hamiltonian truncation lying above NRG), removed in v2.
- [`RESULTS_INDEX.md`](RESULTS_INDEX.md) and [`results.json`](results.json): the index of every number in the Article with the folder, command and tolerance that reproduce it (in preparation; until it is filled, each folder's `results_map.md` and `REPRODUCE.md` give the same information).
- [`AGENTS.md`](AGENTS.md): instructions for AI agents that reproduce the results.
- [`tools/`](tools/): the repository's privacy check (`check_public.py`). The statistics of the AI collaboration and the compute accounting are not part of this release.

## The notes

Each folder has exactly one self-contained note (TeX source and PDF in `<folder>/note/`); its reproduction section maps
every quoted number to a package, record, replay command and tolerance.

| Note | Pages | Contents |
|---|---|---|
| [`GFF/note/long_range_ising_condensed.pdf`](GFF/note/long_range_ising_condensed.pdf) | 373 | epsilon expansion of the perturbed GFF: C_0..C_8 in d = 1, 2, 3, closed forms, the eight-loop computations and their independent checks, and the bulk one-point coefficient a_phi2 through eps^6 (Part V) |
| [`SRI/note/sri_short_range.pdf`](SRI/note/sri_short_range.pdf) | 161 | expansions about the short-range end: the dual series C_1..C_8 of the chain, C_8 from the integrable point s = 1, the two-coupling closure and the prescription, c_2 in d = 2, c_1 in d = 3 |
| [`HT_Pert/note/lri_ht_perturbative.pdf`](HT_Pert/note/lri_ht_perturbative.pdf) | 62 | perturbative Hamiltonian truncation: C_2..C_8 at finite cutoff, window corrections, exact sums, extrapolations; the d = 2 derivations in Apps. A to C |
| [`HT/note/lri_ht_finite_coupling.pdf`](HT/note/lri_ht_finite_coupling.pdf) | 35 | Hamiltonian truncation at finite coupling in d = 1, 2, 3 |
| [`NRG/note/lri_nrg_1d_note.pdf`](NRG/note/lri_nrg_1d_note.pdf) | 32 | numerical renormalization group of the sub-ohmic spin-boson model (d = 1) |
| [`MC/note/lri_mc_note.pdf`](MC/note/lri_mc_note.pdf) | 29 | cluster Monte Carlo in d = 1, 2, 3 and the pre-registered fit protocols |
| [`Resummation/note/lri_resummation.pdf`](Resummation/note/lri_resummation.pdf) | 32 | Borel resummation with the short-range end imposed, large orders, and the comparison of all descriptions |

All seven notes are also combined in one document, [`Supplementary Material.pdf`](Supplementary%20Material.pdf) (built from [`LRI_combined_note/`](LRI_combined_note/); see its `README.md`), which is the Supplemental Material of the Article. The seven folder notes remain the authoritative sources.

The separate notes that came with some packages (the SRI compendium, closure, prescription, C2 and C1 notes, the d = 2
method write-up of HT_Pert, and the GFF proofs, chapters and earlier note versions) are merged into these seven notes and
are not shipped, nor are the scripts that only built them; each package's `NOT_SHIPPED.txt` or `dropped_paths.txt` lists
what is left out. Checks that read a merged note read a small verbatim extract instead
(`SRI/code/dual_d1/public/compendium_extract.json`). The Markdown derivation records that the stage scripts of
`GFF/code/C6_research_note` read or write remain, as records, not as notes.

## Reproducing a result

Each folder has a `REPRODUCE.md` with the same steps: environment, fast tests, **replay** (recompute the published values from the shipped data, minutes on a laptop), a small validation run, and the production runs with their measured cost. Start with `make test` and `make replay` in the folder of interest.

The data files that are too large for git (about 25 GB) are archived at Zenodo, [doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766). The replays do not need them; the `fetch-data` target of each package that uses them downloads and checks them (`make -f public.mk fetch-data` in the package folder, or `make fetch-data` in `SRI/` and `MC/`). Each folder's data documentation lists what is hosted and what is not shipped.

## Licence and citation

Copyright (c) 2026 Zechuan Zheng. Two licences apply:

- **Code: MIT** ([`LICENSE`](LICENSE)). Source code and build or run scripts: `*.py`, `*.cpp`, `*.h`, `*.wl`, `*.wls`,
  `*.m`, `*.sh`, `*.sbatch`, `*.slurm`, `Makefile` and `*.mk` files.
- **Everything else: CC BY 4.0** ([`LICENSE-CC-BY-4.0.txt`](LICENSE-CC-BY-4.0.txt)). The notes (TeX and PDF), figures,
  data, records, tables and documentation. Attribution means citing the Article.

Both licences cover every file in the repository, including the code and notes drafted by AI systems (OpenAI GPT-6
astra, Claude Code; see each folder's `PROVENANCE.md`), except the third-party components below, which keep their own
licences:

- MaTeX (Copyright (c) 2019 Szabolcs Horvat, MIT), in `Resummation/code/resum_d1/vendor/MaTeX/` and
  `Resummation/code/resum_d23/vendor/MaTeX/`, each with its `LICENSE.txt`;
- the 2D/3D Monte Carlo engine in `MC/code/2d3d_engine/`, delivered under the MIT licence (`delivery_LICENSE`,
  "Copyright (c) 2026 Contributors").

Citation: see `CITATION.cff` (the Article's reference will be added on publication).
