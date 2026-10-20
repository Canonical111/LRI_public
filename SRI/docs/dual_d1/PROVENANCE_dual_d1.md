# Provenance: dual_d1

## The compendium (everything in code/dual_d1/ except public.mk and public/)

- **Author: OpenAI GPT-6 astra (via ChatGPT), supplied by the author.** The author wrote no part of it. (The paper's
  words: "Another AI system computed C^SR_3 to C^SR_8, and we reviewed the calculation".) It was built in that
  system's sandbox: its records name sandbox paths (`/mnt/data/...`, `/opt/pyvenv/bin/python`, `/workspace`, `/root`)
  and a Linux toolchain (Python 3.13.5, gcc/g++ 14.2.0 Debian, SymPy 1.14.0, mpmath 1.3.0;
  `reproduction/environment.json`). Dates, from the archive: consolidated 2026-10-02 (members dated 19:09 to 19:48
  archive time); the source packages it consolidates carry no dates of their own.
- **Snapshot:** the archive `LRI_1d_full_research_bundle.zip` (408,209,993 bytes, sha256
  `42c09b8cb63e57c029e24a31e1ed1926f997c7b6d8de43052e2facc2408838ed`), whose 8,561 members are dated 2026-10-02
  (19:09 to 19:48 archive time); the author supplied it on 2026-10-02, and it was unpacked into the working folder
  (`<PROJECT>/LRI_SRI_research_compendium`, the archive's top folder `LRI_research_compendium` renamed). Nothing has
  been changed since: every file of the working copy equals the archive's `reproduction/MANIFEST.json`, apart from the
  one file the macOS copy lost (below). The full archive unpacked on Linux matches all 8,560 MANIFEST entries
  (symmetry job 575588, 2026-10-15).
- **Its own history:** the compendium consolidates about 30 earlier packages of the same system
  (`reproduction/source_archives.json`: names, sizes and sha256 of the source zips, from the first thermal closed form
  to the C8 zeta candidate). Their dates are not recorded in the archive beyond the consolidation date.
- **Published inputs:** the dual theory and C^SR_1 = -2, C^SR_2 = 1/2 are from D. Benedetti, E. Lauria, D. Mazac and
  P. van Vliet (Benedetti:2024wgx, Benedetti:2025nzp); the compendium credits them and does not claim them.

## The lost file

`data/archived/C6_closed_form/input_expressions/a_check_symbolic.expr` (10 bytes, `-2*pi**2/3`, sha256
`71471995...`) differs only by case from `A_check_symbolic.expr` in the same folder. Unpacking the archive on the
authors' case-insensitive macOS disk kept only the upper-case file. The package ships the lost file, read from the
original archive with Python's zipfile (never unpacked on macOS), as `public/restored/lowercase_a_check_symbolic.expr.txt`
(byte-identical, checked against the MANIFEST entry by `make test`); `public/dual_lib.py` writes it under its original
name into case-sensitive work copies only. The public tree has no two paths that differ only in case.

## New files (public.mk, public/)

Claude Code (the dual_d1 builder of the SRI session), 2026-10-15: `public.mk`, `public/dual_lib.py`,
`public/replay_dual_d1.py`, `public/fetch_data.py`, `public/HOSTED.json`, `public/SNAPSHOT.sha256`. The restored file
is the archive's own bytes. The pruning (which stored files ship) follows a dependency trace of every compendium task
on the full archive (symmetry job 575588).

## Reviews

The 2026-10-02 review (Claude Code, a multi-agent workflow; REVIEWS.md) and the independent re-derivation of the
inputs of C^SR_5..C^SR_8 (package `indep_d1`).

## Not recorded

- The dates of the about 30 source packages before the 2026-10-02 consolidation are not recorded in the archive.
- Licence: the archive carries no licence and no authorship line (the note's PDF author field reads "Computational research
  compendium"). It was written by OpenAI GPT-6 astra (via ChatGPT) and supplied by the author; its redistribution terms
  are settled together with the repository's licence.
