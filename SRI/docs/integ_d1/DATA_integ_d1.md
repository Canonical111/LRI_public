# Data: integ_d1

Everything `test` and `replay` read ships in `code/integ_d1/` (724 files from the project at commit 8bd5a22, 48.6 MB;
about 15 MB packed). Nothing is hosted elsewhere. sha256 of every exported file: `public/SNAPSHOT.sha256`.

## Frozen records (`results/`, registry `results/frozen_records.json`)

Written once, hashed and registered before any comparison; the tools refuse to overwrite them. `make replay` rebuilds
each current one from the shipped engine outputs and requires byte identity.

| record | sha256 | committed | status | role |
|---|---|---|---|---|
| `C8_record_v2.json` | `0d463b29...ec0c` | 74d2f30 | current; App. I.8 | C^SR_8 = 247.381179745789 +- 0.131, the 29 inputs, C3..C7, the uncertainty components, the hashes of its input records and of the confirmatory check, both amendment texts |
| `M2_flow_coefficients.json` | `33cc2e1e...e833` | 18f2127 | current; App. I.8 | two bubbles: f_101, f_111, f_121, f_102, f_112, f_103; Laurent coefficients; gate figures |
| `M3_flow_coefficients.json` | `4328cab9...1bce` | 5fd68cf | current; App. I.8 | three bubbles, one logarithm: f_201, f_211 |
| `M4A_flow_coefficients.json` | `584562ca...1048` | 1a7109f | current; App. I.8 | three bubbles, two logarithms: f_202 = 172415.83018563 +- 1.7e-7 |
| `M4B_flow_coefficients_v2.json` | `90542a62...9899` | f4c50ce | current; App. I.8 | four bubbles, one logarithm: f_301 = -514275.754897833 +- 0.174, the error budget, the double-double validation samples by stratum, amendment B |
| `M4B_cx_check_v2.json` | `66287b2a...f1fb` | 71fa348 | current; App. I.8 | confirmatory check at two complex v under amendment A (PASS) |
| `M3_sector_check_K0.92_L3.json`, `..._K0.92_L4.json`, `..._K1.05_L3.json` | `8097a48a...`, `df1a3528...`, `80b18816...` | afcf28a | current | the independent sector checker against the engine on the 63 simultaneous-contact sectors of three bubbles |
| `fix4_verification.json`, `fix5_verification.json` | `3e20ab3c...`, `8ef88875...` | e84de6f, 6d94e80 | current | every current record rebuilt byte for byte after fix rounds 4 and 5 |
| `C8_record.json` | `d9b3be4e...4f97` | 6735a7f | superseded, cited by App. I.7 | first C8 record, 247.38118 +- 0.077 (same central value; roundoff not validated) |
| `M4B_flow_coefficients.json` | `9a16f1a9...39e2` | 71abb72 | superseded, cited by App. I.7 | first f_301 record, +- 0.102 (same central value) |
| `M4B_cx_check.json` | `ca86bbc1...0666` | 6597988 | superseded, cited by App. I.7 | first confirmatory check, pass = false (K_B 1.62e-12 against 1e-12): the trigger of amendment A |

Not in the registry but hash-bound: the provenance sidecars `*.provenance.json` (each binds its record's sha256, the
sha256 of every engine output, the input manifest, the step-0 maps and the build registry; the M4B v2 sidecar also the
two design files), the step-0 maps `m2/m3/m4_step0_response.json`, `..._F*base.json` (provenance blocks bind their generator
scripts and upstream records), `builds.json` (approved engine builds; ids are sha256 of sources and compile command)
and `legacy_outputs.json` (sha256 of the outputs that predate run fingerprints: the M3 runs).

## Logs cited by the note (`results/`)

| file | sha256 | committed | status |
|---|---|---|---|
| `C8_comparison.txt` | `3416d764...44a1` | 65d920d | the comparison stage, run after the last inspection (uses the rounded 242.83 +- 2.37); `replay` reruns it and requires the same text |
| `M4B_gate_v2_dry.txt` | `633d6cad...7e98` | db2dded | superseded, cited by App. I.7: the dry run of the gate that stopped on the sampled ratio 0.411 and gives the roundoff 21.3 and sigma(C8) about 16 of the original rule (amendment B) |

## Designs fixed before data (`results/m4_inputs/`)

| file | git blob (commit) | role |
|---|---|---|
| `fix3_design.json` | `8f353c3c...` (6295185) | the radius run (taurat 0.3, grid (10,14,12), 14 double-double sectors) and the first validation sample (16 + 24 sectors), with the original stopping rule |
| `fix3b_design.json` | `67ce9a56...` (e49157f) | amendment B: per-decile rule, strata, and the held-out sample of 16 sectors (seed 20261017) |
| `cx_v2_design.json` | (d4d5967) | the double-double rerun at K_B that the original rule of the confirmatory check required (1337 sectors, about 1.7e4 core-hours): withdrawn, not run; cited by App. I.7 |
| `dd_sectors_prod.json` | | the 8 production double-double overrides, selected by their first-order roundoff bound in a coarse survey (no reference values) |
| `n4.manifest.json`, `n4.mirror.json` | | the n = 4 engine input (regenerate with `code/cluster_gen.py 4 n4.txt --no-radii`) and its mirror weights |

## Engine outputs (raw; every record is rebuilt from them)

| directory | content | build |
|---|---|---|
| `m2_runs/m2_laurent_L4_d40_r0.1_n96.jsonl` | J2^(0..3) on 96 contour points (pure mpmath, `two_bubble.py`) | - |
| `m3_runs/s3/` | three bubbles, delta^1, grid (24,32,30): 6 chunks, the M3 record | legacy (binary from the working tree of a01ccc3) |
| `m3_runs/g2g3/` | J3^(0) at real and complex v against the exact cluster (12 outputs) | legacy |
| `m3_runs/sector_check/` | the independent checker's outputs for the three sector-check records | checker builds |
| `m4_runs/n3d2_A/`, `n3d2_B/` | three bubbles, delta^2, grids (12,16,16) and (20,28,24): f_202 | 5345fdf1bcec7a5a (source `public/historic/b2ab7c6/`) |
| `m4_runs/prod/F/`, `C/`, `R/` | four bubbles, delta^1: fine (12,14,14) and coarse (10,12,12) at taurat 0.2, radius (10,14,12) at taurat 0.3; 3445 sectors each | b0da6f7bc003c829 (double, double-double accumulators) |
| `m4_runs/prod/Fdd/`, `Cdd/`, `Rdd/` | double-double overrides (8, 8, 14 sectors) | 06c88f4c378ed21d (double-double) |
| `m4_runs/prod/Vdd/`, `Vdd2/` | double-double validation samples at the fine grid (40 and 16 sectors) | 06c88f4c378ed21d |
| `m4_runs/prod/cxA/`, `cxB/` | J4^(0) at K = 0.92 + 0.05i and 1.05 + 0.06i (complex mode) | b0da6f7bc003c829 |

Each M4 output carries a runner fingerprint `<out>.fp` (engine sha256, build id, input sha256, arguments, output
sha256), checked by the gates.

## Added for the release (`public/`)

| file | role |
|---|---|
| `historic/b2ab7c6/cluster_engine.cpp` | the engine source of the f_202 build, exported from commit b2ab7c6 (git blob `2175fb828ab6e3af2c19dcc5369756adf2f57e43`); with `code/dd.h`, `code/sha256.h` and `-DLS=13 -DVMIN=-8` it gives build id 5345fdf1bcec7a5a (checked by `test`); the pinned `code/cluster_engine.cpp` (blob `fc5d358a...`, commit 3bf22f0) built the f_301 runs |
| `git_blobs.json` | the git facts the verbatim tools query (9 blob ids, 1 first-add commit, 1 historic file) |
| `SNAPSHOT.sha256` | sha256 of every exported project file |

## Not exported

Pilot runs and cost studies (`results/m4_runs/p5`..`p12`, `pilot*`, `b0`, `b2`, `b3` and their archives;
`results/m3_runs/cs`, `ct`, `s1`, `s2`; `g2g3/superseded_job574465`; `m4_inputs/dd_sectors_t2.json`) and the M3 grid-variant
records `M3_s1_coarse_flow_coefficients.json`, `M3_s2_flow_coefficients.json` (with sidecars): they enter no current record. The partial M2 files
`*_p0.jsonl`, `*_p1.jsonl` (concatenated in the shipped file). Gate logs other than the two above, `fix_round1/`,
`fix_round2/`. The project's working notes (their content is in the note's Appendix I). `code/two_bubble.sbatch`
(early two-bubble checks on a personal desktop; no target needs it). The review log.
