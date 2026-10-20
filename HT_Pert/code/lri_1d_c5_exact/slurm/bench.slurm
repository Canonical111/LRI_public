#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --exclusive
#SBATCH --no-requeue
# Single-task benchmarks for worker sizing (PLAN.md sec. 2, A7a). For each thread count in C5_THREADS and each entry of
# C5_TASKS (default "worst": run5.py's designated worst-case task -- a five-vertex pattern with all four slices occupied
# and a crossing bundle, with the most keys; or task indices of the cost-sorted list) one `run5.py bench --Lmax C5_LMAX
# (--worst | --task k) --block C5_BLOCK` process, bound to socket 0 (numactl --cpunodebind/--membind on its NUMA
# domains). Writes no checkpoints and no results; requires the snapshot's preliminary validation record
# validation/<sha>/PRELIM (A1-A3, A6a-c; written by validate.slurm). Only runs of the designated worst-case task (whose
# spec sha256 must equal `run5.py worstspec`) count for the memory sizing in submit.sh. Peak RSS of a run = max(run5.py's getrusage value,
# /usr/bin/time -v maximum resident set size), in GiB. The JSON record
#   $C5_DATA/validation/<snapshot sha>/bench_L<Lmax>.json
#   {snapshot_sha, Lmax, host, partition (this job), peak_rss_GB (max over runs), updated, jobs: [...],
#    runs: [{job, host, partition, task, threads, block, seconds, peak_rss_GB, run5_peak_rss_GB, time_maxrss_GB,
#            chain, spec, spec_sha, worst_case, keys}]}
# is rewritten atomically (temporary file + rename) with this job's runs appended to those of earlier jobs for the same
# snapshot and Lmax (submit.sh allows one live benchmark job per Lmax). Nothing is recorded unless every run succeeds.
set -euo pipefail
: "${C5_ROOT:?}" "${C5_DATA:?}" "${C5_LMAX:?}" "${C5_THREADS:?}" "${C5_EXPECT_SHA:?}"
export C5_TASKS=${C5_TASKS:-worst} C5_BLOCK=${C5_BLOCK:-8}
source "$C5_ROOT/slurm/env.sh"
[[ $C5_LMAX =~ ^[1-9][0-9]*$ && $C5_BLOCK =~ ^[1-9][0-9]*$ ]] || { echo "bad C5_LMAX/C5_BLOCK" >&2; exit 64; }
for T in $C5_THREADS; do [[ $T =~ ^[1-9][0-9]*$ ]] || { echo "bad thread count '$T'" >&2; exit 64; }; done
for k in $C5_TASKS; do [[ $k =~ ^([0-9]+|worst)$ ]] || { echo "bad task '$k' (index or 'worst')" >&2; exit 64; }; done
cd "$C5_ROOT"
got=$(python run5.py sha --kind snapshot)
[[ $got == "$C5_EXPECT_SHA" ]] || { echo "snapshot sha $got != expected $C5_EXPECT_SHA" >&2; exit 64; }
numa=$(c5_numa 0); cores=$(c5_cores 0)
[[ -n $numa && $cores =~ ^[1-9][0-9]*$ ]] || { echo "cannot determine socket 0 (numa '$numa', cores '$cores')" >&2; exit 64; }
V=$C5_DATA/validation/$C5_EXPECT_SHA; mkdir -p "$V"
grep -q "snapshot_sha $C5_EXPECT_SHA" "$V/PRELIM" 2>/dev/null || { echo "no preliminary validation $V/PRELIM for this snapshot" >&2; exit 64; }
WSPEC=$(python run5.py worstspec --Lmax "$C5_LMAX"); export WSPEC
RUNS=$(mktemp); TF=$(mktemp); trap 'rm -f "$RUNS" "$TF"' EXIT
export C5_CPU_MODEL=$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1) C5_NUMA0=$numa C5_CORES0=$cores
echo "[bench] job ${SLURM_JOB_ID:-} host $(hostname) partition ${SLURM_JOB_PARTITION:-} $(date '+%Y-%m-%dT%H:%M:%S%z')" \
  "socket0 numa=$numa cores=$cores ($C5_CPU_MODEL) Lmax=$C5_LMAX tasks='$C5_TASKS' threads='$C5_THREADS' block=$C5_BLOCK"
for T in $C5_THREADS; do
  (( T <= cores )) || { echo "threads $T > $cores physical cores of socket 0" >&2; exit 64; }
  for task in $C5_TASKS; do
    out=$(numactl --cpunodebind="$numa" --membind="$numa" env OMP_NUM_THREADS=$T MKL_NUM_THREADS=$T NUMBA_NUM_THREADS=$T \
      NUMBA_CACHE_DIR="$C5_DATA/numba_cache/$(hostname)_bench" \
      /usr/bin/time -v -o "$TF" python run5.py bench --Lmax "$C5_LMAX" $([[ $task == worst ]] && echo --worst || echo --task "$task") --block "$C5_BLOCK")
    printf '%s\n' "$out"
    grep -E 'Maximum resident|Elapsed' "$TF" || true
    line=$(grep '^{' <<<"$out" | tail -n 1) || true
    kb=$(sed -n 's/^[[:space:]]*Maximum resident set size (kbytes): \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$TF")
    [[ -n $line && -n $kb ]] || { echo "bench threads=$T task=$task: no JSON line or no time -v RSS" >&2; exit 65; }
    printf '%s\t%s\t%s\t%s\n' "$T" "$task" "$kb" "$line" >> "$RUNS"
  done
done
python - "$RUNS" "$V/bench_L$C5_LMAX.json" <<'PY'
import json, os, platform, sys, time
runs_f, rec_f = sys.argv[1], sys.argv[2]
sha, L, block = os.environ["C5_EXPECT_SHA"], int(os.environ["C5_LMAX"]), int(os.environ["C5_BLOCK"])
job = dict(job=os.environ.get("SLURM_JOB_ID"), host=platform.node(), partition=os.environ.get("SLURM_JOB_PARTITION"),
           cpu_model=os.environ.get("C5_CPU_MODEL"), socket0_numa=os.environ.get("C5_NUMA0"),
           socket0_cores=int(os.environ["C5_CORES0"]), date=time.strftime("%Y-%m-%dT%H:%M:%S%z"))
new = []
with open(runs_f) as fh:
    for ln in fh:
        T, task, kb, js = ln.rstrip("\n").split("\t", 3)
        d = json.loads(js)
        if d.get("snapshot_sha") != sha:
            sys.exit(f"bench output names snapshot {d.get('snapshot_sha')!r}, expected {sha}")
        if int(d.get("Lmax", -1)) != L or str(d.get("task")) != task or int(d.get("block", -1)) != block:
            sys.exit(f"bench output Lmax/task/block {d.get('Lmax')}/{d.get('task')}/{d.get('block')} != {L}/{task}/{block}")
        if task == "worst" and not (d.get("worst_case") is True and d.get("spec_sha") == os.environ["WSPEC"]):
            sys.exit(f"bench 'worst' run is not the designated worst-case task (spec_sha {d.get('spec_sha')})")
        rss_run5, rss_time = float(d["peak_rss_GB"]), int(kb) / 2 ** 20          # GNU time: KiB -> GiB
        if not (rss_run5 > 0 and float(d["seconds"]) >= 0):
            sys.exit(f"implausible bench output {js}")
        new.append(dict(job=job["job"], host=job["host"], partition=job["partition"], task=task, threads=int(T),
                        block=block, seconds=float(d["seconds"]), peak_rss_GB=round(max(rss_run5, rss_time), 3),
                        run5_peak_rss_GB=rss_run5, time_maxrss_GB=round(rss_time, 3), chain=d.get("chain"),
                        spec=d.get("spec"), spec_sha=d.get("spec_sha"), worst_case=bool(d.get("worst_case")),
                        keys=d.get("keys")))
if not new:
    sys.exit("no benchmark runs")
old = dict(jobs=[], runs=[])
if os.path.exists(rec_f):
    with open(rec_f) as fh:
        old = json.load(fh)
    if old.get("snapshot_sha") != sha or int(old.get("Lmax", -1)) != L:
        sys.exit(f"{rec_f} names snapshot {old.get('snapshot_sha')!r} / Lmax {old.get('Lmax')!r}")
runs = old["runs"] + new
rec = dict(snapshot_sha=sha, Lmax=L, host=job["host"], partition=job["partition"],
           peak_rss_GB=max(r["peak_rss_GB"] for r in runs), updated=job["date"], jobs=old["jobs"] + [job], runs=runs)
tmp = f"{rec_f}.tmp{os.getpid()}"
with open(tmp, "w") as fh:
    json.dump(rec, fh, indent=1, sort_keys=True)
    fh.write("\n")
    fh.flush()
    os.fsync(fh.fileno())
os.replace(tmp, rec_f)
for r in new:
    print(f"[bench] task {r['task']} threads {r['threads']} block {r['block']}: {r['seconds']:.1f} s, peak RSS "
          f"{r['peak_rss_GB']:.3f} GiB (run5 {r['run5_peak_rss_GB']:.3f}, time -v {r['time_maxrss_GB']:.3f})")
print(f"[bench] record {rec_f}: {len(runs)} runs, peak_rss_GB {rec['peak_rss_GB']:.3f}")
PY
