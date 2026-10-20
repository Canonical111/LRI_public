#!/bin/bash
#SBATCH -J lri3d_stage0
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=64 --mem=64G
#SBATCH -t 06:00:00
#SBATCH -o <SCRATCH>/lri3d/logs/stage0_%j.out
# 3D stage 0: crossing centres, ESS, tau and rates for the 8 reference points at L = 8, 16, 32, 64 (analogue of the 2D stage 0).
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C3=<SCRATCH>/lri3d; CAMP=$C3/stage0; cd <CODE_2D>/code || exit 1; mkdir -p $C3/logs
echo "$(date) $(hostname) 3D stage 0; cpus $(python3 -c 'import os;print(len(os.sched_getaffinity(0)))')"
if [ ! -e $CAMP ]; then
  python3 prepare.py --out $CAMP --dim 3 --s 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95 --sizes 8 16 32 64 \
    --centers <CODE_3D>/reference_centers_3d.csv --replicas 2 --measurements 100000 --warmup 10000 \
    --beta-points 5 --beta-halfwidth 0.0008 --window-exponent 0.75 --reference-length 16 \
    --seed-base 20260921 --campaign-id stage0-3d-20260921 --sampler hybrid --record extended > $C3/logs/stage0_prepare.log 2>&1 || { echo "prepare failed"; tail -5 $C3/logs/stage0_prepare.log; exit 1; }
fi
echo "$(date) prepared $(ls $CAMP/chains | wc -l) chains; run_pack 64 workers"
python3 run_pack.py $CAMP --workers 64 > $C3/logs/stage0_runpack_$SLURM_JOB_ID.log 2>&1; echo "$(date) run_pack exit $?"
echo "DONE chains: $(ls $CAMP/chains/*/DONE.json 2>/dev/null | wc -l)/$(ls $CAMP/chains | wc -l)"
python3 - "$CAMP" <<'PY'
import json,glob,sys,collections
C=sys.argv[1];sp=collections.defaultdict(list)
for f in glob.glob(C+'/chains/*/DONE.json'):
    d=json.load(open(f));sp[d['L']].append(1e3*d['last_invocation_seconds']/max(1,d['last_invocation_sweeps']))
for L in sorted(sp):
    v=sorted(sp[L]);print(f'L={L}: {len(v)} chains, ms/sweep median {v[len(v)//2]:.3f} min {v[0]:.3f} max {v[-1]:.3f} (64 concurrent chains, shared node)')
PY
python3 pack_histograms.py $CAMP --block 1000 > $C3/logs/stage0_pack_$SLURM_JOB_ID.log 2>&1; echo "pack exit $?"
for s in 1.55 1.6 1.7 1.75 1.8 1.85 1.9 1.95; do python3 precision_analysis.py $CAMP/hist_b1000/index.json --dim 3 --s $s --bootstrap 200 --out $CAMP/analysis_b1000_s$s > $C3/logs/stage0_analysis_s${s}_$SLURM_JOB_ID.log 2>&1 || echo "analysis s=$s failed"; done
python3 export_centers.py $CAMP/analysis_b1000_s*/results.json --out $CAMP/stage0_centers.csv || echo "export_centers failed (flagged crossings?)"
python3 - "$CAMP" <<'PY'
import json,glob,sys
C=sys.argv[1]
for f in sorted(glob.glob(C+'/analysis_b1000_s*/results.json')):
    r=json.load(open(f));print(f"== s={r['s']} Delta_sigma={r['Delta_sigma']:.3f} warnings={len(r['warnings'])}")
    for row in r['rows']:
        v=row['values'];e=row.get('statistical_stderr',[float('nan')]*5);dg=row['diagnostics'];lo,hi=dg['beta_bracket'];pos=(v[0]-lo)/(hi-lo)
        print(f"   pair L={row.get('L')}: beta_x={v[0]:.6f} at {pos:.2f} of bracket [{lo:.6f},{hi:.6f}] ESS={dg['ESS_fraction'][0]:.2f}/{dg['ESS_fraction'][1]:.2f} D_U4={v[2]:.4f}+-{e[2]:.4f} D_Y={v[1]:.4f}+-{e[1]:.4f} fail={row['bootstrap_failed']}")
    for w in r['warnings']:print("   WARNING",w)
    ch=r['chains'];print(f"   chains {len(ch)}: max tau {max(max(c['tau'].values()) for c in ch):.1f}, min block/tau {min(c['block_over_max_tau'] for c in ch):.0f}")
PY
echo "$(date) STAGE 0 DONE"
