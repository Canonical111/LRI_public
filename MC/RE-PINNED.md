# Records scrubbed after the results and re-pinned

By the author's decision of 2026-10-13, hash-bound records that named a personal machine were scrubbed before publication. Only host
labels, a home directory and the host part of file names were replaced. Inside the scrubbed set, every SHA-256 of another scrubbed file
(and the portable-view hash of every scrubbed registry, which `scan_v3_report.py` checks) was replaced by its new value, so the lineage,
coverage and union checks of the 1D code pass on the published bytes. No number changed: every JSON file was compared field by field, and
only string fields differ. Records outside this list keep their original pins (for example the P1 evaluations, which pin the original
`CALIBRATION.json`); `RE-PINNED.json` maps each original SHA-256 to the published one, and `code/package_tools/compare_outputs.py` applies
the map before every comparison. The note and `protocols/PROTOCOL_HISTORY.md` quote the original hashes.

Substitution classes (published form):
- home directory of the personal desktop in paths: `<HOME>/`
- host value: `"host": "personal desktop"`
- declared host value: `"host_declared": "personal desktop"`
- host token in a manifest header: ` host personal-desktop `
- host part of a file name: `_personal-desktop.`

| published file | renamed | original SHA-256 | published SHA-256 | substitutions | re-pinned hashes | changed |
|---|---|---|---|---|---|---|
| `data/1d/scan_data/ds0.225/analysis_v3_20260920_133256.manifest` |  | `f3daba63c90455d6…` | `219af8901816c3ca…` | 162 | 7 | 157 of 332 lines |
| `data/1d/scan_data/ds0.225/analysis_v3_20260920_133256_personal-desktop.manifest` | yes | `6f656f5f78b9a4a8…` | `61367fa0525770b2…` | 161 | 2 | 151 of 171 lines |
| `data/1d/scan_data/ds0.225/campaigns.json` |  | `f9561d9e46f391f3…` | `b3d2856c331dd47f…` | 2 | 4 | 6 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/completion_20260920_133256_personal-desktop.json` | yes | `57a738e0ce45d8f2…` | `5961da01919f6a4d…` | 6 | 1 | 7 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/registry_20260920_133256_exp-6-24.json` |  | `f9561d9e46f391f3…` | `b3d2856c331dd47f…` | 2 | 4 | 6 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/registry_20260920_133256_personal-desktop.json` | yes | `687bfe7ca7216e9a…` | `802ce2283dc4622f…` | 3 | 4 | 7 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/union_check_20260920_133256.json` |  | `f0ebc0bf23f53b16…` | `72012c0c95eb0a40…` | 1 | 1 | 2 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/fits_v3_20260920_103900/MANIFEST.txt` |  | `c3712aad29c80989…` | `b4af1e4c6f268862…` | 2 | 2 | 4 of 42 lines |
| `data/1d/scan_data/ds0.225/fits_v3_20260920_103900/fit_v3.json` |  | `4933f22b79302cf1…` | `e7c1551dc8e0825e…` | 6 | 9 | 15 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/fits_v3_20260920_103900/pre.json` |  | `7c3bb5079e632f38…` | `131421dfdd7d990d…` | 1 | 0 | 1 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/analysis_v3_20260920_133256.manifest` |  | `a0771f6a06b21a6c…` | `6288e844da9c1ca6…` | 5 | 6 | 9 of 332 lines |
| `data/1d/scan_data/ds0.2375/analysis_v3_20260920_133256_personal-desktop.manifest` | yes | `49fb33aa49ad0d30…` | `c8b67022c6060b86…` | 4 | 2 | 4 of 171 lines |
| `data/1d/scan_data/ds0.2375/campaigns.json` |  | `3663ae85c6667332…` | `d9a14b35fa0125c9…` | 2 | 0 | 2 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/completion_20260920_133256_personal-desktop.json` | yes | `8873bd84510ae45a…` | `9b5b344f393b87bb…` | 3 | 1 | 4 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/registry_20260920_133256_personal-desktop.json` | yes | `4b742af92c5699ba…` | `177117c6c25f5ca1…` | 2 | 0 | 2 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/registry_20260920_133256_exp-2-26.json` |  | `3663ae85c6667332…` | `d9a14b35fa0125c9…` | 2 | 0 | 2 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/union_check_20260920_133256.json` |  | `8e31d06d1fe83f42…` | `6338000ff75b3572…` | 1 | 1 | 2 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/fits_v3_20260920_104501/MANIFEST.txt` |  | `3c3c989fc6d1b11b…` | `6a52f27c2870c5f2…` | 2 | 1 | 3 of 42 lines |
| `data/1d/scan_data/ds0.2375/fits_v3_20260920_104501/fit_v3.json` |  | `115f46df5f08e425…` | `bfb907161393bb59…` | 4 | 7 | 11 string fields, 0 numbers |
| `results/1d/records/points/pre_ds0.225.json` |  | `7c3bb5079e632f38…` | `131421dfdd7d990d…` | 1 | 0 | 1 string fields, 0 numbers |
| `results/2d3d_reanalysis/calibration/run_20260930_213748/CALIBRATION.json` |  | `897142c1685bcc8a…` | `1afae79a22ef790d…` | 1 | 0 | 1 string fields, 0 numbers |
| `data/1d/scan_data/ds0.225/analysis_v3_20260920_133256_exp-6-24.manifest` |  | `c2f839b0f3270ce1…` | `2b1c26a591211a78…` | 0 | 2 | 2 of 129 lines |
| `data/1d/scan_data/ds0.225/completion_20260920_133256_exp-6-24.json` |  | `0b7588ff77bce7e1…` | `8fac835ff5c999b6…` | 0 | 1 | 1 string fields, 0 numbers |
| `data/1d/scan_data/ds0.2375/analysis_v3_20260920_133256_exp-2-26.manifest` |  | `4b79225a44dc39bb…` | `b9402609bd19b255…` | 0 | 2 | 2 of 129 lines |
| `data/1d/scan_data/ds0.2375/completion_20260920_133256_exp-2-26.json` |  | `a6681512f032476f…` | `c78c40c6092bfd9a…` | 0 | 1 | 1 string fields, 0 numbers |

Full hashes, per-file substitution counts and the registries' portable-view hashes are in `RE-PINNED.json`.
