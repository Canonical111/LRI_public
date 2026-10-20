# Provenance: Resummation

| Package | Source | Author | Dates |
|---|---|---|---|
| `code/resum_d1` | `resummation/` (dated snapshot, layout kept) | 2026-10-07 tables and first figure scripts: OpenAI GPT-6 astra (via ChatGPT), supplied by the author; K-pipeline, C8(1) switch, NRG rev 2 table, K = 4/K = 8 table, figure scripts as shipped: Claude Code (resum session and its parent Draft session) | 2026-10-07; 2026-10-12 to 2026-10-14 |
| `code/resum_d23` | `resummation/{2d,3d,combined}` | 2d and 3d packages and the first version of the literature-table script: OpenAI GPT-6 astra (via ChatGPT), supplied by the author; CB3 script, literature-table edits and figure script as shipped: Claude Code (resum session) | 2026-10-07 to 2026-10-13 |
| `code/instanton` | `resummation/instanton_amplitude/` | Claude Code session C71d; independent re-derivation by a Claude Code subagent | 2026-10-07 |
| `code/comparison`, `verify/`, `public/` tools | new | Claude Code (resum session) | 2026-10-14 |
| `note/` | public edition of the resum session's combined note | Claude Code (resum session) | 2026-10-13/14 |
| `vendor/MaTeX/` (in resum_d1, resum_d23) | MaTeX 1.7.10 | Szabolcs Horvat, MIT licence | third party |

Inputs: see `data/inputs/INPUTS.json` (sources, sha256, citations) and each package's PROVENANCE file. The full-text
extraction of the published 2d/3d MC values (`data/inputs/literature/lit_{2d,3d}.csv`, 2026-10-12) was made by OpenAI GPT-6 astra (via ChatGPT), supplied by the author.
