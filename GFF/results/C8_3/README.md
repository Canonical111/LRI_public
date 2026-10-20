# C8(3) production records (campaign prod1-20261008)

Byte-identical copy of the top-level files and the per-group merged records of the C8(3) production campaign, run on the
symmetry cluster from 2026-10-09 to 2026-10-12 by `code/LRI_C8_D3_HPC` at git commit 4fbd1bae. Do not edit: the files
are bound to each other by sha256, and `make -C ../../code/LRI_C8_D3_HPC -f public.mk replay` checks every binding.

| file | sha256 (prefix) | what | bound by |
|---|---|---|---|
| `C8_result.json` | b0776258 | the result: C8(3) = 1602.6052229663408, sampling SE 0.9516489064069612, the coefficients C0..C8 and their covariance, the power-free part and the power correction, campaigns, half streams, bootstrap (4,096), lower-order checks, power null rows, the b_3^p(0) control, the hard gates, error by loop, the tail monitor, and the provenance (tools, vendored assembly, inputs, references, every group's merged.json and scientific identity) | `SHA256SUMS.symmetry` |
| `manifest.json` | ac2ec093 | the frozen plan: 1,941 work indices, 25,714 checkpoint blocks, seed, executable, build, inputs manifest, the design bundle (meta 60a87d5a), the group configs' sha256 | `C8_result.json` source_manifest_sha256 |
| `cost_model.json` | 01b67d0a | the measured cost model of the production binary on AMD EPYC 7543 (= `code/LRI_C8_D3_HPC/cost_models/gmp_symmetry_epyc7543_c8.json`) | `manifest.json` |
| `cpu_vendor.json` | c26f4970 | the campaign's CPU-vendor lock (AMD) | – |
| `groups/<group>/config.json` | | the group plan: graphs and their per-replicate sample counts, replicates (128), seed, rate, digital net | `manifest.json` groups[].sha256 |
| `groups/<group>/merged.json` | | the merged replicate batches (replicates × the 2(9−L) jet entries) from which the estimator is assembled, with the sha256 of the group's per-graph tables | `C8_result.json` merged_sha256, science_sha256 |
| `SHA256SUMS.symmetry` | | written on symmetry after the run: the result, the manifest, the 24 merged.json and the 24 graph_replicates.csv | – |

Groups are `<campaign>_<sector>_L<loops>`: campaigns a (rates ×0.8, 52-bit nets) and b (×0.7, 60-bit nets), sectors
`free` (power-free) and `power` (power-containing), L = 3..8.

Not here: the 24 `graph_replicates.csv` (per-graph replicate jets, 332 MB) are hosted in `../../data/C8_3/results/`
(`make -f public.mk fetch-data TIER=replay`). The rest of the run tree (checkpoints, task databases, per-graph tail,
promotion and cost tables, lane logs; 13 GB) is not published (authors' archive, catalog id c8d3). The production report,
the campaign split and the tail analyses are in
`../../code/LRI_C8_D3_HPC/benchmarks/symmetry_2026-10-c8/production/prod1/`.

The records name the cluster paths, user, nodes and submission host on which they were written; they are hash-bound and
released unchanged. No code resolves those paths.
