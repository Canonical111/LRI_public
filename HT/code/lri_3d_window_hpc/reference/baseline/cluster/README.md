# Target-cluster validation and independent Slurm arrays

This is a locally tested 3D research port, not a symmetry validation receipt or the
reviewed 1D lease infrastructure. Edit partitions/account/memory/time for the actual
site. A single dense/ARPACK eigenproblem stays on one node; different x/L/local-size
checks are independent array items. Use staged arrays for continuation in L.

1. Copy into a new installation, verify its manifest, install dependencies, and run
   all commands in the root README's validation section on a compute node.
2. Train one basis per x with an L6 teacher. Confirm nested sizes and teacher/auxiliary
   resolution at small L. Do not mix 2D basis artifacts with spherical states.
3. Calibrate actual memory and runtime at L8/10/12, first with one thread and then
   four. The supplied resource limits are starting allocations, not predictions.
4. Freeze requests only after all required inputs are complete. An L12 request
   should explicitly name the preceding L10 result as its seed. For example:

```
export HT3D_ROOT="$PWD"
python - <<'PY'
import json
request=[["--L","10","--x",".6","--nz","16","--window","vacuum",
          "--basis","reproduced/teacher_x06.json","--seed","reproduced/window_L8_x06.json",
          "--backend","tensor","--threads","4","--diagnostics","all",
          "--memory-limit-gib","8","--output","runs/window_L10_x06.json","--resume"]]
open('requests.json','w').write(json.dumps(request))
PY
python cluster/make_manifest.py --request-list requests.json --output frozen.json
export HT3D_MANIFEST="$PWD/frozen.json"
mkdir -p logs
sbatch --array=0-0 --export=ALL cluster/array.sbatch
```

`make_manifest.py` binds source hash, input contents and absolute resolved paths.
`run_item.py` verifies them again and the consuming process uses the same bytes.
Each point owns one atomic claim directory. SIGUSR1/TERM/INT request checkpointing
at a Newton or final-publication boundary, not inside ARPACK. Exit75 is a safe
stop; exit73 is an already claimed point. Keep sufficient scheduler warning time.
After a hard failure the claim remains fail-closed. Confirm the remote job and
process are dead before offline removal. Do not automatically clear locks from
age alone. This simple ownership model needs site testing, including simultaneous
writers, forced stop/restart, and hard-crash recovery.

The local basis builder and array driver have exact state-count limits plus a
heuristic total-memory estimate. They cannot bound every transient allocation.
Slurm memory limits, actual high-water RSS and separate numerical convergence are
still required. Raising L does not authorize lowering nz or precision silently.

The three-dimensional Gram backend was slower and larger in the recorded L10/12
benchmark. Tensor is therefore the default; larger-size crossover is unknown.
One-/four-thread measurements do not establish strong scaling to64 or128 cores.
Do not combine these window spectra with a factorizing-mode or tail-solver
prescription under one cutoff sequence or copied production receipt.
