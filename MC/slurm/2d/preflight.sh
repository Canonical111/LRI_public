#!/bin/bash
# Preflight (review item 3): 8 points × L ∈ {512, 1024} × 5 production β × 2 replicas × 5e4 sweeps THROUGH submit.py/array.slurm (first
# use of the array path on the production cluster), then a dependent shared job packs + analyses the 512→1024 crossings (ESS, bracket) and reports ms/sweep.
set -euo pipefail
source /etc/profile.d/modules.sh; <LOAD_MODULES> >/dev/null 2>&1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C2=<SCRATCH>/lri2d; cd <CODE_2D>/code; CAMP=$C2/preflight
[ -e $CAMP ] || python3 prepare.py --out $CAMP --dim 2 --s 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7 --sizes 512 1024 --centers $C2/production_centers.csv --replicas 2 --measurements 50000 --warmup 5000 --beta-points 5 --beta-halfwidth 0.0015 --window-exponent 0.75 --reference-length 64 --seed-base 20260923 --campaign-id preflight2d-20260920 | head -3
echo "chains: $(ls $CAMP/chains | wc -l); compute idle nodes: $(sinfo -p <PARTITION_NODE> -h -t idle -o %D | paste -sd+ | bc); my normal jobs: $(squeue -u $USER -h -q normal | wc -l)"
python3 submit.py $CAMP --workers-per-job 128 --tasks-per-job 160 --concurrency 1 --mem 64G --time 04:00:00 --account <ACCOUNT> --partition <PARTITION_NODE> 2>&1 | tail -3
sleep 5; J=$(squeue -u $USER -h -n lri-precision -o %A | sort -u | tail -1); echo "array job $J"
cat > <CODE_2D>/preflight_analysis.slurm <<EOS
#!/bin/bash
#SBATCH -J lri2d_preflight_an
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=4 --mem=16G
#SBATCH -t 01:00:00
#SBATCH -o $C2/logs/preflight_analysis_%j.out
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
cd <CODE_2D>/code; CAMP=$CAMP
echo "\$(date) preflight analysis; DONE chains \$(ls \$CAMP/chains/*/DONE.json 2>/dev/null | wc -l)/160"
python3 - "\$CAMP" <<'PY'
import json,glob,sys,collections
C=sys.argv[1];sp=collections.defaultdict(list)
for f in glob.glob(C+'/chains/*/DONE.json'):
    d=json.load(open(f));sp[d['L']].append(1e3*d['last_invocation_seconds']/max(1,d['last_invocation_sweeps']))
for L in sorted(sp):
    v=sorted(sp[L]);print(f'L={L}: {len(v)} chains, ms/sweep median {v[len(v)//2]:.2f} min {v[0]:.2f} max {v[-1]:.2f} (whole node, 128 workers, 80 L=1024 chains concurrent at start)')
PY
python3 pack_histograms.py \$CAMP --block 500 > $C2/logs/preflight_pack.log 2>&1; echo "pack exit \$?"
for s in 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7; do python3 precision_analysis.py \$CAMP/hist_b500/index.json --dim 2 --s \$s --bootstrap 100 --out \$CAMP/analysis_s\$s > $C2/logs/preflight_an_s\$s.log 2>&1 || echo "analysis s=\$s exit \$?"; done
python3 - "\$CAMP" <<'PY'
import json,glob,sys
C=sys.argv[1]
for f in sorted(glob.glob(C+'/analysis_s*/results.json')):
    r=json.load(open(f))
    for row in r['rows']:
        v=row['values'];e=row.get('statistical_stderr',[float('nan')]*5);dg=row['diagnostics'];lo,hi=dg['beta_bracket'];pos=(v[0]-lo)/(hi-lo)
        print(f"s={r['s']}: 512->1024 beta_x={v[0]:.6f} at {pos:.2f} of bracket [{lo:.6f},{hi:.6f}] ESS={dg['ESS_fraction'][0]:.2f}/{dg['ESS_fraction'][1]:.2f} D_U4={v[2]:.3f}+-{e[2]:.3f} D_Y={v[1]:.3f} fail={row['bootstrap_failure_fraction']:.2f}")
    for w in r['warnings']:print(f"s={r['s']}: WARNING",w)
    ch=r['chains'];print(f"   chains {len(ch)}: max tau {max(max(c['tau'].values()) for c in ch):.1f}, min block/tau {min(c['block_over_max_tau'] for c in ch):.0f}")
PY
echo "\$(date) PREFLIGHT ANALYSIS DONE"
EOS
J2=$(sbatch --parsable --dependency=afterany:$J <CODE_2D>/preflight_analysis.slurm); echo "analysis job $J2 (afterany:$J)"
squeue -u $USER -h -o "%i %j %T %M %P %r"
