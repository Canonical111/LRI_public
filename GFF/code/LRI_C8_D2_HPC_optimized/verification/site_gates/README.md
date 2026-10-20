# Site gates (stage B, 2026-10-09)

`slurm/site_gate.sh` summaries (AC1–AC4 and the package tests) of tag `c8ind-B1` (e744adb) against the delivered
baseline df468f8, one node per site. Both passed: 26 steps, executables identical between base and head, 52-case
frozen replay exact (science digest 366421b2…, equal to the sandbox's), 24-group test plans identical.

| File | Site | Node | gmp executable |
|---|---|---|---|
| `symmetry-20261009-571968.json` | symmetry amddebugq | EPYC 7543, g++ 11.4.0 | 01934e18… |
| `expanse-20261009-54776914.json` | Expanse compute | EPYC 7742, GCC 13.3.0 | e509a2e7… |

`dirty: true` in both records only `chmod +x slurm/site_gate.sh` in the deployed clone (the bug fixed in b1a6c24);
the blob was unchanged. The drill evidence (AC5) is kept outside the repository, in
`LRI_C8_D2_HPC_optimized_loop/stageB/{expanse,symmetry}/`.

## Final head (a791a1f, tag c8ind-B4), 2026-10-09

`expanse-20261009-54781082.json`: the gate on the final head, from a clean clone (`dirty: false`), Expanse debug node
<NODE> (EPYC 7742, the compute nodes' type). It passed all 26 steps with the same executables as stage B (gmp
e509a2e7…) and replay digest 366421b2…. AC4 manifests differ only in `package`. In that job the two Bidirectional
site-layer tests were skipped because the test-repo paths were not exported; debug job 54781158 re-ran
`tests/site_layer.py` on the same head with `C8_TEST_OURS_REPO`/`C8_TEST_C63D_REPO` set: 33 tests OK, none skipped.
