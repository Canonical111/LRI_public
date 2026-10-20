#!/bin/bash
#SBATCH -J lri2d_stage0
#SBATCH -A <ACCOUNT>
#SBATCH -p <PARTITION_SHARED>
#SBATCH --nodes=1 --ntasks=1 --cpus-per-task=64 --mem=48G
#SBATCH -t 04:00:00
#SBATCH -o <SCRATCH>/lri2d/logs/stage0_%j.out
set -uo pipefail
source /etc/profile.d/modules.sh; module purge >/dev/null 2>&1; <LOAD_MODULES> || exit 1  # site modules: gcc >= 10, Python 3 with NumPy/SciPy
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
C2=<SCRATCH>/lri2d; CAMP=$C2/stage0; cd <CODE_2D>/code || exit 1
echo "$(date) $(hostname) stage 0 start; cpus $(python3 -c 'import os;print(len(os.sched_getaffinity(0)))')"
# checkpoint/resume test on Lustre (flock, fsync, truncation): the split run must equal the straight run bitwise
T=$C2/resume_test; rm -rf $T; mkdir -p $T
A="--dim 2 --length 64 --s 1.4 --beta 0.1678 --sampler hybrid --record extended --warmup 2000 --measurements 20000 --seed 777"
./bin/lri_mc $A --out $T/straight > $T/straight.log 2>&1; echo "straight exit $?"
./bin/lri_mc $A --out $T/split --max-seconds 6 > $T/split1.log 2>&1; echo "split first exit $? (75 expected)"
./bin/lri_mc $A --out $T/split > $T/split2.log 2>&1; echo "split resume exit $?"
sha256sum $T/straight/samples.bin $T/split/samples.bin | cut -c1-16,65-
echo "$(date) run_pack 64 workers on $(ls $CAMP/chains | wc -l) chains"
python3 run_pack.py $CAMP --workers 64 > $C2/logs/stage0_runpack_$SLURM_JOB_ID.log 2>&1; echo "$(date) run_pack exit $?"
echo "DONE chains: $(ls $CAMP/chains/*/DONE.json 2>/dev/null | wc -l)"
python3 - "$CAMP" <<'PY'
import json,glob,sys,collections
C=sys.argv[1];sp=collections.defaultdict(list)
for f in glob.glob(C+'/chains/*/DONE.json'):
    d=json.load(open(f));sp[d['L']].append(1e3*d['last_invocation_seconds']/max(1,d['last_invocation_sweeps']))
for L in sorted(sp):
    v=sorted(sp[L]);print(f'L={L}: {len(v)} chains, ms/sweep median {v[len(v)//2]:.3f} min {v[0]:.3f} max {v[-1]:.3f} (64 concurrent chains, shared node)')
PY
python3 pack_histograms.py $CAMP --block 1000 > $C2/logs/stage0_pack_$SLURM_JOB_ID.log 2>&1; echo "pack exit $?"
for s in 1.05 1.1 1.2 1.3 1.4 1.5 1.6 1.7; do python3 precision_analysis.py $CAMP/hist_b1000/index.json --dim 2 --s $s --bootstrap 200 --out $CAMP/analysis_b1000_s$s > $C2/logs/stage0_analysis_s${s}_$SLURM_JOB_ID.log 2>&1; echo "analysis s=$s exit $?"; done
python3 export_centers.py $CAMP/analysis_b1000_s*/results.json --out $CAMP/stage0_centers.csv || echo "export_centers failed (flagged crossings?)"
python3 - "$CAMP" <<'PY'
import json,glob,sys
C=sys.argv[1]
for f in sorted(glob.glob(C+'/analysis_b1000_s*/results.json')):
    r=json.load(open(f));print(f"== s={r['s']} Delta_sigma={r['Delta_sigma']:.3f} warnings={len(r['warnings'])}")
    for row in r['rows']:
        v=row['values'];e=row.get('statistical_stderr',[float('nan')]*5);dg=row['diagnostics'];fs=row.get('finite_size_diagnostics',{});z=fs.get('z')
        print(f"   {row['L']:4d}->{row['L2']:4d}: beta_x={v[0]:.6f} bracket=[{dg['beta_bracket'][0]:.5f},{dg['beta_bracket'][1]:.5f}] ESS={dg['ESS_fraction'][0]:.2f}/{dg['ESS_fraction'][1]:.2f} D_U4={v[2]:.4f}+-{e[2]:.4f} D_Y={v[1]:.4f} (z_Y-U4={z if z is None else round(z,1)}) fail={row['bootstrap_failure_fraction']:.2f} flags={row['precision_flags']}")
    for w in r['warnings'][:4]:print('   warn',w)
    ch=r['chains'];print(f"   chains {len(ch)}: max tau {max(max(c['tau'].values()) for c in ch):.1f}, min block/tau {min(c['block_over_max_tau'] for c in ch):.0f}, max |drift z| {max(abs(c['half_drift_z']) for c in ch):.2f}")
PY
echo "$(date) STAGE0 DONE"
