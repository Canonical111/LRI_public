# lri_3d_window_hpc: d = 3 Hamiltonian truncation at finite coupling

The production code behind every d = 3 finite-coupling Hamiltonian-truncation (HT) number of the paper and the HT note: the dressed
zero-mode truncation on the sphere S² × ℝ with the vacuum window correction, tuned to Δσ = Ds and Δφ³ = 3 − Ds, solved
at even bath cutoffs N = 8, …, 20 for 15 values 0.518149 ≤ Ds ≤ 0.7499. The cutoff is called L in the code and in
the record names. The method is in the HT note (`HT/note`), Secs. 2–6 and 9.

The package ships **verbatim at git ref `b330ee7`**, the last commit used in production; this folder (`public/`) and
`public.mk` are the only additions. The package's own `README.md`, `EXPANSE.md`, `FIX_L18_L20.md`, `REPORT_L18_L20.md`
and `PERFORMANCE.md` describe its history: the 0.2.0rc1 performance candidate, the 0.2.1rc1 projector repair that made
N = 18 and 20 possible, and the Expanse site layer in `cluster/expanse/`. The numerical source (`code/` and
`inputs/prior_3d_points.json`, hashed by `ht3d.hpc.source_hash()`, d27a3bc2…) is the same in every commit that
produced a record: 33ef4f3 (N ≤ 18), ccd055a (N = 20 at Ds = 0.6) and b330ee7 (the other N = 20 points). Those
commits differ only in `cluster/expanse/` and its tests.

## What is where

| path | content |
|---|---|
| `code/ht3d/` | the solver: bath graph and SO(3) projector (`basis.py`), vertices (`rotational_vertices.py`, `block_vertices.py`), product operator (`operators.py`), zero-mode problem (`local.py`), density basis (`density.py`), window (`window.py`), tuning (`solver.py`), point driver and record format (`hpc.py`), immutable cache (`cache.py`) |
| `cluster/expanse/` | the Expanse layer that ran production: frozen campaigns (`campaign.py`), lanes and recovery (`lanes.py`, `child.py`, `lane.sbatch`), validation receipt (`receipt.py`, `validate.sbatch`), setup and cache probes (`probe.py`, `setup_probe.sbatch`) |
| `tests/` | pytest suite (158 tests at b330ee7) and the five validators the receipt runs |
| `reference/` | earlier code kept as oracles (`baseline/`, `d3original/`, `performance_0_2_0/`) |
| `MANIFEST.sha256` | sha256 of 646 files, checked by `tests/verify_manifest.py` |
| `public/` | `run_tests.py` (test), `replay_ht3d.py` (replay), `bp_x07.py` (Borel–Padé value at Ds = 0.7), `smoke_points.py` (smoke), `slurm/` templates, this README, `REPRODUCE.md`, `PROVENANCE.md`, `REVIEWS.md` |

Records: `../../data/HT_3d/campaigns/` (105 window records and their teachers, with each campaign's frozen
`manifest.json`). Published outputs: `../../results/HT_3d/` (`finite_L_table.csv`).

## Targets

```
make -f public.mk test        # manifest + pytest + validators (~4 min, 4 cores)
make -f public.mk replay      # every quoted number from the records, PASS/FAIL table (~5 s, any OS)
make -f public.mk smoke       # re-solve four N = 8, 10 production points from the shipped inputs (~2 min)
make -f public.mk fetch-data  # nothing is hosted; prints how the N = 20 static cache is rebuilt
```

`public/REPRODUCE.md` gives the production rerun. `../lri_3d_window_indep` is the separately written solver that checks
this one (HT note, d = 3 checks).

## Requirements

`requirements.txt` (package) and `public/requirements.txt` (exact production versions: Python 3.11.9, numpy 2.3.5,
scipy 1.17.0, numba 0.65.1, llvmlite 0.47.0). Replay needs only numpy and scipy.
