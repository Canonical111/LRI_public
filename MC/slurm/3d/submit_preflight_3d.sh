#!/bin/bash
# 3D preflight (FIT_MODEL_3D §7): prepare + submit. Login node (prepare is light). Refuses duplicates like the 2D production script.
#   SUBMIT=1 to sbatch (default: dry run). Arrays: A = L=128 chains, 32 per node, one per CCX (LRI_CPUMASK=0-127:4); B = L=64 chains, 128 workers.
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C3=<SCRATCH>/lri3d; ROOT=<CODE_2D>/code; cd $ROOT; mkdir -p $C3/logs
CAMP=$C3/preflight; SLOTBIG=${SLOTBIG:-32}; MASK=${MASK:-0-127:4}; TBIG=${TBIG:-06:00:00}; TSMALL=${TSMALL:-02:00:00}
[ -e $CAMP ] || python3 prepare.py --out $CAMP --dim 3 --s 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95 --sizes 64 128 --centers <CODE_3D>/production_centers_3d.csv \
   --replicas 2 --measurements 50000 --warmup 5000 --beta-points 5 --beta-halfwidth 0.001 --window-exponent 1.0 --reference-length 16 \
   --seed-base 2026092150 --campaign-id preflight-3d-20260921 --sampler hybrid --record extended > $C3/logs/preflight_prepare.log 2>&1
echo "manifest sha $(sha256sum $CAMP/manifest.json | cut -c1-16); chains $(ls $CAMP/chains | wc -l)"
Q=$(squeue -u $USER -h -o "%j" 2>&1); QRC=$?; [ $QRC -eq 0 ] || { echo "REFUSED: squeue failed: scheduler state UNKNOWN"; exit 1; }
set +e; QUEUED=$(printf "%s\n" "$Q" | grep -cE "^lri3d_pf(A|B|_an)$"); GRC=$?; set -e; [ $GRC -le 1 ] || { echo "REFUSED: grep failed"; exit 1; }
[ "$QUEUED" = 0 ] || { echo "REFUSED: $QUEUED preflight jobs already queued"; exit 1; }
[ -f $CAMP/logs/submitted.txt ] && { echo "REFUSED: $CAMP/logs/submitted.txt exists:"; cat $CAMP/logs/submitted.txt; exit 1; }
echo "== my normal-QOS jobs: $(squeue -u $USER -h -q normal | wc -l); account: $(squeue -A <ACCOUNT> -h -q normal -o %T | sort | uniq -c | tr '\n' ' '); compute idle: $(sinfo -p <PARTITION_NODE> -h -t idle -o %D | paste -sd+ | bc)"
[ "${SUBMIT:-0}" = 1 ] || { echo "(dry run; SUBMIT=1 to submit: slot-big $SLOTBIG mask $MASK, times $TBIG / $TSMALL)"; exit 0; }
PLANS=$(python3 <CODE_3D>/make_plan.py $CAMP --lbig 128 --slot-big $SLOTBIG --nslot-small 1 | tail -1)
PB=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_big' in p][0])"); PS=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_small' in p][0])")
NB=$(python3 -c "import json;print(len(json.load(open('$PB'))['slots']))"); NS=$(python3 -c "import json;print(len(json.load(open('$PS'))['slots']))")
export LRI_ROOT=$ROOT LRI_CAMPAIGN=$CAMP LRI_AUTOREQUEUE=0 LRI_MEASUREMENTS=
COMMON="--export=ALL --mem=128G --account=<ACCOUNT> --partition=<PARTITION_NODE> --cpus-per-task=128"
echo "$(date) preflight submission: plans=$PB,$PS slotbig=$SLOTBIG mask=$MASK" >> $CAMP/logs/submitted.txt
sub(){ local out; out=$(sbatch "$@" 2>&1) || { echo "sbatch FAILED: $out" | tee -a $CAMP/logs/submitted.txt; exit 1; }; echo "$out" | grep -oE '[0-9]+$'; }
JA=$(LRI_PLAN=$PB LRI_WORKERS=$SLOTBIG LRI_CPUMASK=$MASK sub $COMMON --job-name=lri3d_pfA --array=0-$((NB-1))%$NB --time=$TBIG --output=$CAMP/logs/A_%A_%a.out --error=$CAMP/logs/A_%A_%a.err <CODE_3D>/cluster/array_pinned.slurm); echo "$(date) A=$JA" >> $CAMP/logs/submitted.txt
JB=$(LRI_PLAN=$PS LRI_WORKERS=128 LRI_CPUMASK= sub $COMMON --job-name=lri3d_pfB --array=0-$((NS-1))%$NS --time=$TSMALL --output=$CAMP/logs/B_%A_%a.out --error=$CAMP/logs/B_%A_%a.err <CODE_3D>/cluster/array_pinned.slurm); echo "$(date) B=$JB" >> $CAMP/logs/submitted.txt
JN=$(sbatch --parsable --dependency=afterany:$JA:$JB <CODE_3D>/cluster/preflight_analysis_3d.slurm); echo "$(date) analysis=$JN" >> $CAMP/logs/submitted.txt
echo "submitted: array A $JA (${NB} slots x ${SLOTBIG} L=128 chains, mask $MASK, $TBIG); array B $JB (${NS} slot, 128 workers, $TSMALL); analysis $JN (afterany)"
sleep 10; squeue -u $USER -h -o "%i %j %T %M %P %r" | grep lri3d
