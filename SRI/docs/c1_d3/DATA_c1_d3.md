# Data: c1_d3

Everything ships in the package (286 files with the public tools, 6.5 MB, 3.7 MB packed); nothing is hosted, so there
is no `fetch-data`.

| Path | Size | What |
|---|---|---|
| `data/inputs/` | 60 kB | inputs (see PROVENANCE_c1_d3.md): the transcribed spectrum, the low inputs, the retained snapshot, the original selection, the assumptions (metadata), the literature transcription |
| `data/provenance/` | 16 kB | bibliography registry, source archives with sha256, the revision records |
| `outputs/reference/` | 1.5 MB | regression baseline read by `verify.py results` (5 `.npz` arrays: crossing bases at levels 32/40/48, two final LP arrays) |
| `outputs/reproduced/` | 2.0 MB | the shipped full from-scratch run (20 steps; 6 `.npz` arrays) and `run_receipt.json` |
| `outputs/review_validation/` | 0.6 MB | fixed-LP audit and the 19 sensitivity scenarios: JSON summaries, receipts, final envelopes |
| `outputs/tables/`, `figures/`, `verification/` | 0.5 MB | `current_summary.json` and CSV/TeX tables, four figures (PDF, PNG), run/PDF/release records |
| `review_indep/` | 21 kB | the review's two independent re-implementations (4 scripts, verbatim, and a README) |

Left out of the export (`public/NOT_SHIPPED.txt`, 33 files of the authors' `SHA256SUMS`): the 25 `.npz` arrays of
`outputs/review_validation/` (6.6 MB; `make replay-full` regenerates them and compares the scenario summaries), the
review report `review/ising3d_C1_review.md` (summarised in REVIEWS.md), the previous-delivery records and the revision
diff `review/source_changes.diff` (history), and, since 16 October 2026, the package's TeX note and its PDF (0.5 MB,
31 pages; one note per direction: the content is in the SRI note, Appendix G). The complete delivery is kept in the authors' archive.

Machine-readable values for other folders (`SRI/results/sr_values.json`):
`code/c1_d3/outputs/tables/current_summary.json` at `/retained/C1` (0.27315242382601645), `/retained/a`, `/retained/b`,
`/nominal_conditional_interval`, `/doubled_nonlinear_padding_interval`, `/recommended_working_summary/interval`
([0.269, 0.276]); the inputs S and E_SR at `/values/S/value` and `/values/E/value` of
`code/c1_d3/data/inputs/low_inputs.json`.
