# Stage 4c on Expanse: opt-in numerics profiles (PLAN D1, A-FLAG-1..7; site deviation U1)

The framework (commits 9870a68 and 241baca) lets the profile developers (R3b `dd`, R4b `mp256`, R4c `exp1`) work in
parallel and gives the gate agent its F-gate runs. Design and rules: `docs/NUMERICS.md`, "Opt-in numerics profiles".
Scripts: `scripts/` (Mac driver `submit_s4c.sh`; every sbatch passes the H7E-R admission and the agent's share).
Admission records: `admission/<tag>/`. Framework evidence: `framework/`.

## Commands

Run from the repository root of a checkout, with `ssh -O check expanse` saying "Master running". `C8_S4C_TAG` names
the agent (job names `c8d2-s4c-<tag>-*`); each agent's own live jobs stay within `C8_S4C_MAX_NODES` (default 1)
compute nodes and `C8_S4C_MAX_SHARED` (default 8) shared jobs, on top of H7E-R. Lowercase letters and digits only.

**A profile developer** (`P` = `dd`, `mp256` or `exp1`; own branch or worktree):

```bash
# edit src/numerics/$P.hpp (and NX_FLAGS_$P in the Makefile if the profile needs flags); kernel.hpp and
# numerics.hpp are the shared contract: change them only through the host
C8_ALLOW_NO_L8=1 <HOME>/anaconda3/bin/python3 -B tests/test_numerics_flags.py     # Mac: builds (make -n), hooks, harness
make -n gmp NUMERICS=$P                                                              # the exact profile command
C8_S4C_TAG=$P C8_S4C_PROFILES=$P bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh precheck
#   compile check of the WORKING TREE (no commit): default executables against 99a51c1d/1d2a2181, the profile
#   executable and its F1 tool; record in the printed work directory (precheck.json)
git commit ...                                                                       # then, on the commit:
C8_S4C_TAG=$P C8_S4C_PROFILES=$P bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh build
#   -> "export <PKG> build <JOB>": the export, A-RPL-8 (fails the job if the default executables change),
#      the preprocessed-program identity, --describe and build records
C8_S4C_TAG=$P bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh dev $P <PKG> --after <JOB>
#   development F-gates on 32 shared cores (development scales; never "passed"); custom harness arguments:
#   ... dev $P <PKG> --after <JOB> -- --parts F1,F2 --f1-scale 0.2 --f2-graphs 64
C8_S4C_TAG=$P bash benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh gate $P <PKG> - --after <JOB>
#   a full-scale run on one exclusive node (F1 baseline computed in the run; about 15-25 min, ~30-50 SU)
```

**The gate agent** (on the integrated `c8` head, alone; it may raise `C8_S4C_MAX_NODES` up to H7E-R's 4):

```bash
C8_S4C_TAG=gate bash .../submit_s4c.sh build                                   # -> export <PKG> build <JOB>
C8_S4C_TAG=gate bash .../submit_s4c.sh baseline <PKG> --after <JOB>            # full F1 exact baseline; prints its directory <BASE>
for P in dd mp256 exp1 dd+mp256+exp1; do
  C8_S4C_TAG=gate bash .../submit_s4c.sh gate $P <PKG> <BASE> --after <baseline job>
done
```

Each gate run writes `numerics_flags.json` (verdicts F1, F2, F4 rows, F5; F3 tables; status `passed` only at full
scale) under `$C8_DATA/evidence/<sha12>/s4cgate.<job>.0/jflag_<P>/`. A layout control for F4: the framework's
all-stub `bin/c8d2_gmp_dd` (`e2eb509f…`, export 241baca924d2) computes the exact numbers yet ran 1.2–1.8% faster than
`bin/c8d2_gmp` in the development F4 below (code shape only); a full-scale `gate dd` of that stub export measures the
size of this effect at the gate's scale if a profile's gain is within a few percent.

## Framework evidence (`framework/`)

| Job | What | Result |
|---|---|---|
| 54672436, 54672441 (`shared` 16 CPUs, 0:40 each) | `precheck` of the working tree before the first commit | Default `bin/c8d2_decimal` `99a51c1d…` and `bin/c8d2_gmp` `1d2a2181…` (byte-identical to the final default binary); every profile executable built. The first run's F1 tool failed to compile (an expression template passed to `.str()`), fixed before the commit (`precheck/`) |
| 54672480 (`shared` 16 CPUs, 1:01), export 9870a68535a7 | `build` + `s4c_identity.py` | **A-RPL-8:** both default executables byte-identical to the final default binary. Preprocessed `src/c8d2_integrate.cpp` (each default build's options) token-identical to b47b008's (17 bytes of whitespace from the macro expansions). Stub identity: `dd`, `mp256`, `exp1`, `dd+mp256+exp1` write rows identical to `bin/c8d2_gmp` on L7/L8 blocks of both sectors at rates .8 and .9 (256 rows each, 11,034 binary128 and 1,461 MP points) |
| 54672484 (`shared` 32 CPUs, 2:13), export 9870a68535a7 | `selftest`: `numerics_flags.py --self-test` and `--profile dd` (stub), development scales | Both strict identity and "development run (would pass)" (details below); a Python 3.11 `SyntaxWarning` in the harness, fixed in 241baca |
| 54672538 (`shared` 16 CPUs, 0:44), export 241baca924d2 | `build` + `s4c_identity.py` | As 54672480: A-RPL-8 holds, token-identical preprocessed program, stub identity; every executable byte-identical to 9870a68's build |
| 54672539 (`shared` 32 CPUs, 2:13), export 241baca924d2 | `selftest` | As 54672484, no warning |

**Self-test at development scales** (both exports; `--f1-scale 0.05 --f2-graphs 16 --f4-sample 25 --f4-repeats 2
--f5-threads 1 8 16 --f5-lanes 4 --f5-lane-threads 4`):
- **F1.** The exact baseline holds 7,680 points with 450-digit references (free: 1,591 binary128-accepted and 227 MP;
  power: 2,648 and 696). The exact path itself: 2,518 long-double, 4,239 binary128 and 923 MP points, largest relative
  error 1.3e-10, 3.5e-12 and 1.0e-19 (bound 1e-6). Read back by the exact tool (self-test) and by the dd stub's tool,
  all 7,680 points are identical to the baseline's values, with only diagonal tier transitions.
- **F2.** 5,496 tasks (all L3–L6 graphs, 16 graphs per sector at L7 and L8, both campaigns, 4 × 256 points): every
  per-task difference is 0, dC8 = 0 exactly in total and per (sector, L), the exact-Fraction nonlinear dC8 is 0, and
  the F3 counter changes are 0.
- **F4.** Rows identical within and between the binaries. Self-test speedups 0.999 and 1.002 (noise); the dd stub
  1.018 and 1.013 (code layout; see above).
- **F5.** Thread identity of `bin/c8d2_gmp` and of `bin/c8d2_gmp_dd` at 1, 8 and 16 threads and 4 × 4 lanes.
- **Cost.** 11,472 core-seconds = 3.19 SU for all six jobs (`sacct.txt`). Lustre files of the user 1,331,122 →
  1,351,066 (shared with C63d; this workflow: two exports of about 6,445 files each, the two pre-check trees and the
  evidence).

## Developer branches (`dev_dd/`, `dev_mp256/`, `dev_exp1/`, `dev_r7/`)

Development evidence of R3b, R4b, R4c and R7 (each README lists its jobs, results and SU); merged onto c8 on
2026-10-05. Their records are development runs: the gate records are in `gate/`.

## Integration and J-FLAG gate (`gate/`)

On the integrated head 5569c53 (merges c7aa396, 0d75f19, f4d7609, 5e19ca3 plus the integration commit), with
`C8_S4C_TAG=gate C8_S4C_MAX_NODES=4`:

```bash
S=benchmarks/expanse_2026-10-c8/stage4c/scripts/submit_s4c.sh
X=$C8_DATA/pkg/5569c535dcfd; B=$C8_DATA/evidence/5569c535dcfd/s4cgate.54673899.0/f1_baseline_full/f1_baseline
bash $S precheck                                   # 54673888 (working tree, before the commit)
bash $S build                                      # 54673898: export 5569c535dcfd, A-RPL-8
bash $S baseline $X --after 54673898               # 54673899: the full F1 baseline
for P in dd mp256 dd+mp256+exp1; do bash $S gate $P $X $B --after 54673899; done     # 54673900, 54673901, 54673902
C8_S4C_NAME2=layout_stub_dd C8_S4C_ARGS2="--profile dd --profile-exe $C8_DATA/pkg/241baca924d2/bin/c8d2_gmp_dd --parts F4" \
  bash $S gate exp1 $X $B                          # 54673904: exp1, then the F4 layout control in the same job
bash benchmarks/expanse_2026-10-c8/stage4c/gate/scripts/fetch_gate.sh 5569c535dcfd 54673898 54673899 54673900 54673901 54673902 54673904
python3 benchmarks/expanse_2026-10-c8/stage4c/gate/scripts/aflag7_table.py --gate benchmarks/expanse_2026-10-c8/stage4c/gate \
  --r7 benchmarks/expanse_2026-10-c8/stage4c/dev_r7/expanse/r7refreeze.54673870.0 --out .../gate/aflag7.json --markdown .../gate/aflag7_table.md
```

`gate/` holds `precheck/precheck.json`, `s4cbuild.54673898.0/` (identity.json: A-RPL-8, preprocessed identity,
describe and build records), `s4cgate.54673899.0/` (the baseline record, `baseline.json`, nets, `refs.sha256`),
`s4cgate.<job>.0/jflag_<p>/` (`numerics_flags.json`, `f1/`, `f2/f2.json`, `f4/`, `f5/`; `rows_csv.sha256` pins the
F2 per-row CSV left on Expanse), `s4cgate.54673904.0/layout_stub_dd/`, `logs/`, `sacct.txt`, `aflag7.json` and
`aflag7_table.md`. Every gate record says `"status": "passed"` (no development option). Results:
`docs/NUMERICS.md`, "Stage 4c gate: J-FLAG results (A-FLAG-7)"; jobs and SU: `../README.md`, "Stage 4c integration
and J-FLAG gate" (66.1 SU; Stage 4c in all 205.1 SU).

