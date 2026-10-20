#!/bin/bash
#SBATCH -p debugq -N 1 -n 1 --exclusive --mem=180G -t 01:00:00 --no-requeue
#SBATCH -o <SCRATCH>/c8d2/logs/%x_%j.out
# J-SWEEP-3 on symmetry (PLAN job table; A-PERF-4): the CPU-class factors of the Intel Xeon Gold 6148 (debugq, 2 x 20
# cores) relative to symmetry AMD, per (campaign, sector, L >= 6), from the SAME points as J-SWEEP-2: J-SWEEP-2's plan
# arguments and seed (--pilot --points 512 --replicates 2 --backend gmp --threads 8 --cost-model <J-SWEEP-1's model>
# --seed <J-SWEEP-2's seed>; identical chunking, hence identical tasks) restricted to a stratified subset
# (--test-graphs 168 --test-selection stratified: 168 graphs per (sector, L), half cheapest and half heaviest by
# J-SWEEP-1's measured cost, every L7 primitive and 16 L8 primitives; 1,008 graphs at L >= 6 per campaign), registered
# in its own ledger (role sweep) before any index, run as 2 x 20 socket-pinned processes (s5sweep3_driver.py, the
# package's sweep runner), merged; then tools/make_cost_model.py on it (the Intel subset model) and
# `make_cost_model.py class-factors <J-SWEEP-2 model> <this run>` = the J-SWEEP-2 model plus
# cpu_class_factors["Intel(R) Xeon(R) Gold 6148 CPU @ 2.40GHz"][c][s][L]. Finally every graph row of this campaign is
# compared with J-SWEEP-2's (graph_replicates.csv: identical points on another CPU must give identical values).
# Usage: C8_PACKAGE=... SWEEP_SEED=<J-SWEEP-2 seed> M2=<J-SWEEP-2 cost model> W2=<J-SWEEP-2 campaign> DRIVER=<s5sweep3_driver.py>
#        sbatch --export=ALL --dependency=afterok:<J-SWEEP-2> -J c8d2-s5sweep3 s5sweep3.slurm
set -uo pipefail
source "$HOME/c8d2/env.sh"
: "${C8_PACKAGE:?}" "${SWEEP_SEED:?}" "${M2:?}" "${W2:?}" "${DRIVER:?}"
D=<SCRATCH>/c8d2; TAG=$(basename "$C8_PACKAGE"); RUN=s5sweep3.${SLURM_JOB_ID}.${SLURM_RESTART_COUNT:-0}
E=$D/evidence/$TAG/$RUN; mkdir -p "$(dirname "$E")"; mkdir "$E" || exit 64
W=<SCRATCH>/c8-d2/sweep3-$TAG; CM1=$C8_PACKAGE/benchmarks/expanse_2026-10-c8/stage3b/sweep1.54641706.0/cost_model.json
echo "job $SLURM_JOB_ID on $(hostname) at $(date -Is); package $C8_PACKAGE; campaign $W; evidence $E"
{ hostname; lscpu; numactl --hardware 2>&1; df -h /tmp; } > "$E/node.txt" 2>&1; grep -E 'Model name|NUMA node\(s\)|Socket' "$E/node.txt"
sha256sum "$HOME/c8d2/env.sh" "$DRIVER" "$M2" "$CM1" | tee "$E/inputs.sha256"
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 C8_LANES=socket
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS GMP_PREFIX NUMERICS C8_INPUTS
cd "$C8_PACKAGE" || exit 64
sha256sum bin/c8d2_gmp | tee "$E/binaries.sha256"
S=/tmp/c8d2_$SLURM_JOB_ID; mkdir -p "$S"
status=0; t0=$(date +%s)
if [ ! -e "$W/manifest.json" ]; then
  python3 -B tools/production.py plan "$W" --pilot --points 512 --replicates 2 --test-graphs 168 --test-selection stratified --backend gmp \
    --threads 8 --seed "$SWEEP_SEED" --cost-model "$CM1" > "$E/plan.stdout" 2>&1 || { echo "plan failed"; tail -20 "$E/plan.stdout"; exit 3; }
fi
tail -5 "$E/plan.stdout" | cut -c1-300
python3 -B tools/ledger.py register "$W" --role sweep | tee "$E/ledger_register.txt" || { echo "ledger registration failed" >&2; exit 3; }
python3 -B "$DRIVER" "$C8_PACKAGE" "$W" --threads 20 --scratch "$S" --merge-jobs 20 > "$E/driver.stdout" 2>&1 || status=$?
echo "runner + merge exit $status after $(( $(date +%s) - t0 )) s"; tail -6 "$E/driver.stdout" | cut -c1-300
if [ $status -eq 0 ]; then
  python3 -B tools/make_cost_model.py "$W" "$E/cost_model_intel6148_subset.json" --note "J-SWEEP-3 symmetry debugq $SLURM_JOB_ID" || status=3
  python3 -B tools/make_cost_model.py class-factors "$M2" "$W" "$E/cost_model_with_class_factors.json" || status=3
  python3 - "$W" "$W2" "$E/rows_vs_sweep2.json" <<'PY' || status=3
import csv,json,sys
from pathlib import Path
w3,w2,out=map(Path,sys.argv[1:4]);m=json.loads((w3/'manifest.json').read_text());res={};bad=0;n=0
for g in m['groups']:
    name=g['name']
    def rows(w):
        with open(w/'groups'/name/'graph_replicates.csv')as f:return {(r['rep'],r['graph']):r for r in csv.DictReader(f)}
    a=rows(w3);b=rows(w2);miss=[k for k in a if k not in b];diff=[k for k in a if k in b and a[k]!=b[k]]
    res[name]={'rows':len(a),'missing_in_sweep2':len(miss),'different':len(diff),'examples':[list(k)for k in diff[:3]]};n+=len(a);bad+=len(miss)+len(diff)
doc={'rule':'every (rep, graph) row of graph_replicates.csv of this J-SWEEP-3 campaign equals J-SWEEP-2\'s row (same seed, same chunking, same points; Intel 6148 vs AMD)',
     'rows':n,'mismatches':bad,'identical':bad==0,'groups':res}
out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps({k:doc[k]for k in('rows','mismatches','identical')}));sys.exit(0 if bad==0 else 3)
PY
fi
cp "$W/manifest.json" "$E/manifest.json"; cp "$W/submissions.jsonl" "$E/submissions.jsonl" 2>/dev/null
rm -rf "$S"
echo "finished $(date -Is), status $status"
exit $status
