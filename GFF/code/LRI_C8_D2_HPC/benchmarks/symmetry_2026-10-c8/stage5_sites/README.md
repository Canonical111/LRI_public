# symmetry site preparation, Stage 5 (2026-10-05)

| File | What | sha256 |
|---|---|---|
| `env.sh.bak-20261003` | the previous `~/c8d2/env.sh` (2026-10-03; no `C8_SITE`, no `C8_SEEDS`), kept on symmetry under this name | `0122a133d3ec5bc56fff1c7068e171b8feaf4cab5f0bba6724d85e73a717c30e` |
| `env.sh` | the new `~/c8d2/env.sh`: the symmetry block of `slurm/env.sh.example` (09e8f4a) inside the nounset guard | `e5fdb68c88464071e3f96db10da91dd36fc0d99cff94a831fa84dcd5685e0b65` |
| `forbidden_seeds_symmetry_before.json` | `<SCRATCH>/c8-d2/forbidden_seeds.json` before: an empty `"entries"` list (first layout) | `8598da66e3c8091ef3f0bbae13485239055bcec64925958895b5ded30f17cbdb` |
| `forbidden_seeds_expanse.json` | Expanse's `$C8_DATA/forbidden_seeds.json` after job 54676839 registered the F2 seeds (56 entries) | `73d6c2b903d29696364d461b8e3ca39394ffe7b119610971756c9304969fb0d5` |
| `forbidden_seeds_symmetry_after.json` | the symmetry log after `tools/seeds.py merge forbidden_seeds_expanse.json` (5ddf8ee's tool, under the log's lock): 56 seeds, `c8-d2-seeds-1` layout | `62fd303ffb2d6c5aa77a00a0e5d6dda623ad56921157ad032b65acd45cb8b065` |

Commands (symmetry login node; the tools from `git archive 5ddf8ee tools/seeds.py tools/common.py tools/production.py`
in `<SCRATCH>/c8d2/work/g4cfix-5ddf8eef4c29/`):

```bash
cp -p ~/c8d2/env.sh ~/c8d2/env.sh.bak-20261003     # then env.sh (this folder) copied in and moved over ~/c8d2/env.sh
source ~/c8d2/env.sh
python3 -B tools/seeds.py merge forbidden_seeds_expanse.json --log $C8_SEEDS   # added 56, entries 56
python3 -B tools/seeds.py merge forbidden_seeds_expanse.json --log $C8_SEEDS   # added 0 (idempotent)
python3 -B tools/seeds.py check 820262401                                      # forbidden (exit 1)
```

The package mirror `designs/forbidden_seeds.json` was then merged with both logs on the Mac (`tools/seeds.py merge
<expanse> <symmetry> --log designs/forbidden_seeds.json`): the 7 earlier entries unchanged, 49 appended, 56 seeds,
the same set as each log.
