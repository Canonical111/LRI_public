# Data of lri_3d_hpc

Everything `make -f public.mk replay` and `make -f public.mk test` read is in git; nothing is hosted.

- Records of the production campaign: `HT_Pert/data/HT_3d/pert3d/` (194 files, 1.5 MB), described in
  `HT_Pert/data/HT_3d/DATA.md` with what is byte-identical and what was scrubbed.
- The table `HT_Pert/results/HT_3d/SUMMARY.md` (C2..C8 at L = 16, 18, 20).
- Inside the package: the original code's reference results `results/reference_coefficients_L14.json` (L = 0..14,
  bound by sha256 in every gate record) and the small vertex store `fixtures/vertices_L4/` (smoke test).

Not hosted: the production vertex stores (L16 2.6 GiB, L18 22 GiB, L20 177 GiB) and the L20 intermediate pipeline
files (363 GiB). A production rerun rebuilds them (`public/REPRODUCE.md`).
