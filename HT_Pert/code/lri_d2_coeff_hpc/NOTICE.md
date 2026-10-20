# Source attribution

The unchanged reference numerical package is the conversation attachment
`lri_2d_C8_perturbative_check.zip`, including its supplied upstream code and
independent exact oracle. Its original files and attribution are retained in
`reference/lri_d2_perturbative_C8/`. The ZIP checksum is recorded in
`docs/PROVENANCE.json`. No new redistribution license is asserted for inherited
source files.

New numerical implementations are in `src/lri_coeff/`; local validation,
benchmark and job-array helpers are in `tests/`, `scripts/` and `cluster/`.
The source's angular-envelope theorem, perturbative particle support,
stationary-quotient method, and physical window prescription are attributed
inputs, not claimed as new discoveries. The optimized ranked envelope
construction, shared graph and fused kernels, annihilation-only moment
implementation, persistence wrapper, and fresh benchmark/pilot results are this
release's changes.

This archive contains no font files, compiled libraries, graph caches, private
credentials, automatically submitted cluster jobs, or modified production
receipts. Reference reports describe historical work; only explicitly identified
root results are fresh computations.
