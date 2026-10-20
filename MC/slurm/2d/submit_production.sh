#!/bin/bash
# Prepare and submit the 2D production campaign (FIT_MODEL_2D.md §5.2, size-class packing). Login node (light). Refuses if the campaign exists.
#   DRY=1        prepare dry-run only          SUBMIT=1  actually sbatch (default: print the sbatch commands)
#   TBIG=36:00:00  wall limit of array A (L=1024 slots; set to 1.5 x the preflight-measured chain time)
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C2=<SCRATCH>/lri2d; ROOT=<CODE_2D>/code; cd $ROOT
CAMP=$C2/prod2d; ID=prod2d-20260921
REPLICAS=${REPLICAS:-12}; MEAS=${MEAS:-1000000}; WARM=${WARM:-50000}; HW=${HW:-0.0015}; WEXP=${WEXP:-0.75}; SIZES=${SIZES:-"64 128 256 512 1024"}
TBIG=${TBIG:-42:00:00}; TSMALL=${TSMALL:-12:00:00}; SLOTBIG=${SLOTBIG:-96}; NSMALL=${NSMALL:-4}
if [ "${DRY:-0}" = 1 ]; then python3 prepare.py --out $CAMP/dry --dim 2 --s 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7 --sizes $SIZES --centers $C2/production_centers.csv --replicas $REPLICAS --measurements $MEAS --warmup $WARM --beta-points 5 --beta-halfwidth $HW --window-exponent $WEXP --reference-length 64 --seed-base 20260921 --campaign-id $ID --dry-run | head -8; exit 0; fi
[ -e $CAMP ] || python3 prepare.py --out $CAMP --dim 2 --s 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7 --sizes $SIZES --centers $C2/production_centers.csv --replicas $REPLICAS --measurements $MEAS --warmup $WARM --beta-points 5 --beta-halfwidth $HW --window-exponent $WEXP --reference-length 64 --seed-base 20260921 --campaign-id $ID | head -4
echo "manifest sha $(sha256sum $CAMP/manifest.json | cut -c1-16); chains $(ls $CAMP/chains | wc -l)"
# FIT2D-009: no duplicate submission — refuse when any job of this campaign is queued or running; plans are immutable, written only when submitting
Q=$(squeue -u $USER -h -o "%j" 2>&1); QRC=$?   # FIT2D-009: a failed scheduler query is UNKNOWN, never "no jobs"
[ $QRC -eq 0 ] || { echo "REFUSED: squeue failed ($Q): scheduler state UNKNOWN"; exit 1; }
set +e; QUEUED=$(printf "%s\n" "$Q" | grep -cE "^lri2d_(A|B|A2|B2)$"); GRC=$?; set -e   # FIT2D-014: grep -c exits 1 on zero matches, 2 on error
[ $GRC -le 1 ] || { echo "REFUSED: grep failed ($GRC) while checking the queue"; exit 1; }
[ "$QUEUED" = 0 ] || { echo "REFUSED: $QUEUED lri2d_A/B jobs already queued or running for this campaign"; squeue -u $USER -h -o "%i %j %T %M"; exit 1; }
[ -f $CAMP/logs/submitted.txt ] && { echo "REFUSED: $CAMP/logs/submitted.txt exists (a submission was started):"; cat $CAMP/logs/submitted.txt; exit 1; }
echo "== account normal-QOS before: $(squeue -A <ACCOUNT> -h -q normal -o %T | sort | uniq -c | tr '\n' ' '); compute idle nodes: $(sinfo -p <PARTITION_NODE> -h -t idle -o %D | paste -sd+ | bc); my normal jobs: $(squeue -u $USER -h -q normal | wc -l)"
[ "${SUBMIT:-0}" = 1 ] || { echo "(dry run: plans are written and jobs submitted only with SUBMIT=1; would use slot-big $SLOTBIG, nslot-small $NSMALL, times $TBIG / $TSMALL)"; exit 0; }
PLANS=$(python3 <CODE_2D>/make_plan.py $CAMP --lbig 1024 --slot-big $SLOTBIG --nslot-small $NSMALL | tail -1); PB=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_big' in p][0])"); PS=$(echo "$PLANS" | python3 -c "import json,sys;print([p for p in json.load(sys.stdin) if 'plan_small' in p][0])")
NB=$(python3 -c "import json;print(len(json.load(open('$PB'))['slots']))"); NS=$(python3 -c "import json;print(len(json.load(open('$PS'))['slots']))")
export LRI_ROOT=$ROOT LRI_CAMPAIGN=$CAMP LRI_AUTOREQUEUE=0 LRI_MEASUREMENTS=
COMMON="--export=ALL --mem=64G --account=<ACCOUNT> --partition=<PARTITION_NODE>"
echo "$(date) submission started: plans=$PB,$PS slotbig=$SLOTBIG tbig=$TBIG tsmall=$TSMALL" >> $CAMP/logs/submitted.txt   # FIT2D-009: written BEFORE the first sbatch
sub(){ local out; out=$(sbatch "$@" 2>&1) || { echo "sbatch FAILED: $out" | tee -a $CAMP/logs/submitted.txt; exit 1; }; echo "$out" | grep -oE '[0-9]+$'; }
JA=$(LRI_PLAN=$PB LRI_WORKERS=$SLOTBIG sub $COMMON --job-name=lri2d_A --array=0-$((NB-1))%$NB --cpus-per-task=$SLOTBIG --time=$TBIG --output=$CAMP/logs/A_%A_%a.out --error=$CAMP/logs/A_%A_%a.err $ROOT/array.slurm); echo "$(date) A=$JA" >> $CAMP/logs/submitted.txt
JB=$(LRI_PLAN=$PS LRI_WORKERS=128 sub $COMMON --job-name=lri2d_B --array=0-$((NS-1))%$NS --cpus-per-task=128 --time=$TSMALL --output=$CAMP/logs/B_%A_%a.out --error=$CAMP/logs/B_%A_%a.err $ROOT/array.slurm); echo "$(date) B=$JB" >> $CAMP/logs/submitted.txt
# FIT2D-010/013: checked wall-time continuations through continue.slurm, released after the whole predecessor array has ended (afterany; aftercorr
# would release only after a SUCCESSFUL predecessor slot); each continuation slot inspects its own predecessor slot with sacct and runs only after
# TIMEOUT or a checkpointed stop (exit 75)
JA2=$(LRI_PRED=$JA LRI_PLAN=$PB LRI_WORKERS=$SLOTBIG sub $COMMON --job-name=lri2d_A2 --dependency=afterany:$JA --array=0-$((NB-1))%$NB --cpus-per-task=$SLOTBIG --time=$TBIG --output=$CAMP/logs/A2_%A_%a.out --error=$CAMP/logs/A2_%A_%a.err <CODE_2D>/continue.slurm); echo "$(date) A2=$JA2" >> $CAMP/logs/submitted.txt
JB2=$(LRI_PRED=$JB LRI_PLAN=$PS LRI_WORKERS=128 sub $COMMON --job-name=lri2d_B2 --dependency=afterany:$JB --array=0-$((NS-1))%$NS --cpus-per-task=128 --time=$TSMALL --output=$CAMP/logs/B2_%A_%a.out --error=$CAMP/logs/B2_%A_%a.err <CODE_2D>/continue.slurm); echo "$(date) B2=$JB2" >> $CAMP/logs/submitted.txt
echo "submitted: array A $JA (+checked continuation $JA2): ${NB} x ${SLOTBIG} L=1024 chains, $TBIG; array B $JB (+continuation $JB2): ${NS} slots, $TSMALL"
sleep 15; squeue -u $USER -h -o "%i %j %T %M %P %r" | head -14
