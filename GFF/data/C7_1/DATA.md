# GFF/data/C7_1: data of the C7(1) result

Nothing needed by `make test` or the Tier 1 `make replay` is hosted: those run from git (`GFF/code/LRI_C7_HPC`,
113.3 MB, of which `reference/` 111.7 MB; `GFF/results/C7_1`, 28.1 MB including `v1_46batches/` 2.8 MB).

## (a) Hosted in the project's Zenodo data record ([doi:10.5281/zenodo.23466766](https://doi.org/10.5281/zenodo.23466766)), needed by `make -f public.mk replay-full` (Tier 2)

| Archive | Content | Size | sha256 |
|---|---|---|---|
| `C7_1_merged_records.tar.gz` (unpacks to `GFF/data/C7_1/c7_hpc/`) | for each of the 399 batches (b001–b400 except b215): `production.json`, `assembly.json`, `full_affine_assembly.json`, `C7_result.json`, and for each of its 24 campaigns `manifest.json`, `merged/audit.json`, `merged/N*.json`; for the direct primitive campaign `primitive/P1/`: `manifest.json`, `merged/audit.json`, `merged/N0.json`; `c7_hpc/MANIFEST.sha256` listing every file | 338,360,779 bytes compressed; 968,740,277 bytes (0.97 GB) uncompressed, 35,116 files (88 per batch, 3 for P1, the manifest) | `ed57516b93d650d83c25a7db3175c0409a1e7f9f03a5cc7d84b0543d56f4e678` (manifest `81d264b6668780b9c556e0f1bb6c4c6c9dd6d8f41558cb391ac6be563bf5898b`) |

- Record file name: `GFF__data__C7_1__C7_1_merged_records.tar.gz` (its repository path with `/` replaced by `__`);
  `fetch-data` saves it under the name above.
- Source: the production tree on SDSC Expanse (Lustre scratch, `.../temp_project/c7_hpc/`), built by
  `public/make_data_archive.py` (read-only selection; it checks every merged stream against the SHA-256 recorded in
  `GFF/results/C7_1/C7_final.json` before writing the tarball). The tree itself was moved to the author's Drive
  archive on 2026-10-15 and is no longer on Expanse; see (b).
- Bound: the merged files embed their manifest's SHA-256, each audit lists the manifest's and the merged files'
  SHA-256, and `C7_final.json` (in git) names every merged stream by path and SHA-256. The manifests and
  `production.json` record the absolute path of the production executable on Expanse (with the cluster user name);
  they are hash-bound and must ship byte-identical.
- Not included (used by no target): the worker checkpoints and task files (their SHA-256 values remain listed in every
  `merged/audit.json`), the Sobol nets (SHA-256 in the manifests), the per-batch input snapshots `inputs/` (copies of
  `reference/inputs` and `inputs_extra`, SHA-256 in the manifests; Tier 2 rebuilds the one file it reads), logs and
  Slurm ledgers.
- Built 2026-10-13 on Expanse (Slurm job 54901438, 68 min); `make -f public.mk replay-full` run in the same job from the
  unpacked tarball: 14 checks PASS.
- `fetch-data` downloads it from `https://zenodo.org/records/23466766/files/GFF__data__C7_1__C7_1_merged_records.tar.gz` (url in
  `public/data_C7_1.json`), checks its sha256 and unpacks it. A copy placed at
  `GFF/data/C7_1/C7_1_merged_records.tar.gz` is unpacked if its sha256 matches.
- Privacy scan (2026-10-18, all 35,116 members, names and contents): none of the personal-desktop names occurs. The
  Expanse scratch path with the cluster user name occurs in 9,976 files, the 399 `production.json`, the 9,576 batch
  campaign manifests and the P1 manifest (field `executable`); all are hash-bound and ship unchanged.

## (b) Archive only, not hosted, used by no target

These are not in the Zenodo record, which holds only what a `fetch-data` target reads. They are in the author's Drive
archive of the complete production tree (255.7 GB in 622,824 files; 67.2 GB as 18 gzip tar parts, each with a
per-file sha256 manifest) and are available on request.

| Item | Content | Size | Use |
|---|---|---|---|
| pilot production `batches/pilot` (complete, with checkpoints) | the multiplier-1 pilot (seed 2026092501) from which `tools/design.py` froze `design_v1.json` | 151,131,373 bytes in 653 files | `tools/design.py --pilot <pilot> --archive v1_46batches/archive_original.json` reproduces `design_v1.json` byte-identical (done three times on Expanse during the review); it needs the checkpoints for the CPU-second costs |
| checkpoints of the 399 batches and of P1 | raw worker outputs | 222,342,579,760 bytes in 520,695 files (batches), 76,243,979 bytes in 192 files (P1) | full `campaign.py verify` of every campaign, as in the production combination |

Without (b), the design reproduction and the full re-verification remain documented in `REVIEWS.md` and
`REPRODUCE.md` but cannot be rerun from public data.
