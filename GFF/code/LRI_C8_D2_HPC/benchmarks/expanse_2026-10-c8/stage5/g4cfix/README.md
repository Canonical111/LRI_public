# Stage 5: the G4c verifier's fixes on Expanse (D1, D2, D3, D6), 2026-10-05

Fix commit 5ddf8ee (code, tests, docs; Mac suites in `mac/`). Site deviation U1 (Expanse) for the build check; the
symmetry side (environment, seed log) is in `../../../symmetry_2026-10-c8/stage5_sites/`.

## The check job

`scripts/submit_g4cfix.sh` (Mac): `git archive 5ddf8ee` into `$C8_DATA/work/g4cfix-5ddf8eef4c29` (7,144 files, equal
to the archive: `setup_export_check_5ddf8eef4c29.json`), the H7E-R admission (`admission/`), one sbatch of
`scripts/g4cfix_check.slurm`.

| Job | Where | Wall | Result |
|---|---|---|---|
| 54676839 `c8d2-s5-g4cfix` | `shared` 16 CPUs, 32 GB, <NODE> | 10:57 | every check passed (status 0); 10,512 core-s = **2.92 SU** (`sacct.txt`) |

Log `logs/c8d2-s5-g4cfix_54676839.out`; evidence `g4cfix.54676839.0/` (`d2.json`, `d1.json`, `d3_register.json`,
`d6_*.txt`, build records, `binaries.sha256`).

**D2 (A-FLAG-1): profile-parameter overrides are development builds; the default binaries are unchanged.**
- Default builds in the archive: `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…`, **the final default
  binary byte for byte** (A-RPL-8).
- Profile builds without an override are byte-identical to the gate export's (5569c535dcfd): dd `51614820…`, mp256
  `9e884b1b…`, exp1 `0bf3f1a8…`, dd+mp256+exp1 `6bc26966…`. Their `--describe` has no `development` field, the build
  records list no override, and plan's executable checks (`production.describe`, `read_build_record`) accept them.
- Override builds (each in its own copy of the tree, `CPPFLAGS=...`):

  | Build | `numerics_params` | Build record `parameter_overrides` | plan's checks |
  |---|---|---|---|
  | mp256, `-DC8_MP256_RATIO=1e-60` (`43e7bf59…`) | `"development":true`, `"overrides":["C8_MP256_RATIO"]` | `-DC8_MP256_RATIO=1e-60`, `development: true` | both refuse |
  | exp1, `-DC8_EXP1_RANGE=4000` (`5463fb83…`) | `"development":true`, `"overrides":["C8_EXP1_RANGE"]` | `-DC8_EXP1_RANGE=4000`, `development: true` | both refuse |
  | dd, `-DC8_DD_DEVELOPMENT -DC8_DD_RATIO=1e-21` (`87042984…`) | `"development":true` | both macros, `development: true` | both refuse |

**D1 (A-FLAG-6): `design.py rates --rule one-step` on real data.** On J-SWEEP-1 (`sweep1-81aa9770e6fe`) with the
Stage-4c source bundle, the rule reproduces the Stage-4c map: the rate tables equal those of `r7-ebf01f62e833/prov`
(derived by `dev_r7/scripts/r7_spec.py`) for every graph, the spec is equal, and every stratum's graphs, W, V, C,
ratio and bootstrap quantiles equal r7_spec.py's record (`dev_r7/expanse/r7prep.54673789.0/spec_derivation.json`) to
1e-12 relative (the same random stream). Ratios W_b²/W_a²: free L8 0.763 (.9/1), power L6 0.469, L7 0.783, L8 0.783
(.9/1); every other stratum keeps .8/.9 (fewer than 100 graphs, or within the band). The new provisional bundle
(`d1_rule_prov_design_meta.json`, rates identity `b0760c8f…`, which differs from `98a215a8…` only through
`provenance`) records `rate_rule`; it lived in the work directory and is not a design input.

**D3 (D9): the J-FLAG F2 seeds.** `numerics_flags.register_f2_seeds` added the F2 base seed 820262401 and its 48
derived native and net seeds (every group of loops 3..8) to `$C8_DATA/forbidden_seeds.json`: 7 → 56 entries
(`seeds_before.json`, `seeds_after.json`, sha256 `73d6c2b9…`). The same entries are now in the symmetry log and in
`designs/forbidden_seeds.json` (two-log rule, `docs/HPC.md`).

## D6: the export survey and the pruning that was not done

`$C8_DATA/pkg` holds 39 exports, 242,594 entries (`find | wc -l` per export), on 2026-10-05 before any deletion; the
user's Lustre count was 1,524,608 of 2,000,000 after the check job (C63d included).

**Survey** (`g4cfix.54676839.0/d6_pkg_refs.txt`: 795 file:path references to `pkg/<sha12>` in `$C8_DATA/evidence`
and `$C8_DATA/logs`; `d6_c8d3_refs.txt`: none in C63d's c8d3 tree; `d6_export_content.txt`: baseline directories
and L8 packs per export). Every export's L8 packs are hard links of two inodes (35 links each), so deleting an export
frees no pack bytes. An input of a later job from ANOTHER export's evidence:

| Export | Referenced by | What |
|---|---|---|
| c17688158e2b | 18 later build and bench jobs | `inputs/packs` (C8_L8_PACKS) and `bin/` (the Stage-3 baseline `3dbd51bb…`/`5c5328af…`, C8_BASELINE_BIN) |
| 138d4866c7e4 | int-gate 54669707, int-speed 54669709 | `bin/baseline` (copies of the Stage-3 baseline) and its executables |
| bc0bedc3d72b | int-gate 54669708, int-speed 54669709 | `bin/baseline` and its executables |
| 6bdc081cc8bd | r4a-trace 54666315 | `bin/baseline` and its executables |
| 241baca924d2 | gate 54673904 | `bin/c8d2_gmp_dd`, the all-stub F4 layout control (`--profile-exe`) |
| d46e7360fe88 | int-speed 54669709 | `bin/c8d2_gmp` as a speed candidate only (byte-identical to `1d2a2181…` in b47b0082c0f7); its `bin/baseline` only by its own jobs |

The repository's evidence adds 7aac898add43 (`inputs/packs`, C8_L8_PACKS) and b47b0082c0f7 (C8_REF_PACKAGE).

**Keep (9 exports, 55,317 entries):** b4273c59e911, c17688158e2b, 7aac898add43, b47b0082c0f7 and 5569c535dcfd (the
host's list), plus 138d4866c7e4, bc0bedc3d72b and 6bdc081cc8bd (baseline directories that later jobs read) and
241baca924d2 (the layout-control executable a later job read).

**Delete (30 exports, 187,277 entries): NOT DONE.** The deletion was refused by the session's permission classifier
(irreversible deletion); it is left to the user. Every one is `git archive` of a recorded commit plus its builds, and
no live job uses one (the only live jobs are C63d's, from `c8d3/pkg`):

```
00c675d3cfe9 10b19d9a0ae3 18c216e27e4c 1d25d9e1deec 2c8b28f46538 36043bbc2117 3e9d66490893 4eb79cde99e6 6eedd3f55b65
7607a9fc2777 81aa9770e6fe 8e4ad72661ac 908bd9de0265 913e56a97a6b 964f39d13aec 9870a68535a7 ab2a822a10e5 add273b9ecc7
b4ad81beea16 bb1a3c945482 cb401889a37f d0f0e05a4c21 d46e7360fe88 d98e3a10c6e9 dd171982f690 e7ef98d90487 ebf01f62e833
ec2b0583b6da ef705e395924 f327bb910151
```

Also left for the user: this check's work directory `$C8_DATA/work/g4cfix-5ddf8eef4c29` (7,907 entries; its jobs are
done and its evidence is copied here). After both, `pkg/` would hold 55,317 entries and the user's count would fall
by about 195,000.
