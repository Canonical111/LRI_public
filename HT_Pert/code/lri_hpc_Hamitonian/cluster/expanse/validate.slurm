#!/bin/bash
#SBATCH -A <ACCOUNT> -p shared --nodes=1 --ntasks-per-node=1 --cpus-per-task=64 --mem=128G
#SBATCH -t 01:30:00 -J lriht-validate
#SBATCH -o <SCRATCH>/temp_project/lri_ht/logs/%x_%j.out
# Validation V (PLAN G4). Submit with cluster/expanse/submit_validate.sh, which sets CODE to the frozen checkout.
#   1. tests/run_all.py; 2. regressions against the saved tables (check_regression.py);
#   3. calibration runs (RSS and time per state, thread count recorded).
# Always writes $LRIHT_HOME/validation/<jobid>/summary.json with the code revision; exits nonzero unless every
# stage passed (review LRI-008). Production submission requires a passing summary for the same revision.
[[ -n "${CODE:-}" && -f "$CODE/cluster/expanse/env.sh" && -f "$CODE/GIT_SHA" ]] || { echo "CODE must name a frozen checkout with GIT_SHA (use submit_validate.sh)" >&2; exit 2; }
source "$CODE/cluster/expanse/env.sh"
set -o pipefail
cd "$CODE"
VAL=$LRIHT_HOME/validation/${SLURM_JOB_ID}; mkdir -p "$VAL"
REV=$(cat GIT_SHA)
stage=init
finish(){  # write the summary on every exit path
  local rc=$?
  python - "$VAL" "$REV" "$stage" "$rc" "${rc_tests:-}" "${rc_reg:-}" <<'PY'
import json,sys,glob
from pathlib import Path
V,rev,stage,rc,rt,rr=Path(sys.argv[1]),sys.argv[2],sys.argv[3],int(sys.argv[4]),sys.argv[5],sys.argv[6]
rows=[]
for f in sorted(glob.glob(str(V/'*'/'*_L*.json'))):
    r=json.loads(Path(f).read_text());k=r['ranks'][0]
    rows.append(dict(file=str(Path(f).relative_to(V)),task=r['task'],degree=r['degree'],cutoff=r['cutoff'],dim=r['basis_dimension'],
                     threads=r.get('threads',int(Path(f).parent.name.rsplit('_t',1)[-1]) if '_t' in Path(f).parent.name else None),
                     maxrss_gib=k['maxrss_kib']/2**20,edges_bytes=k['edges_bytes'],seconds=r['seconds'],
                     source_sha256=r['source_sha256'],phase=k['phase_seconds']))
ok = stage=='done' and rc==0 and rt=='0' and rr=='0'
s=dict(revision=rev,job=V.name,stage_reached=stage,exit_code=rc,tests_exit=rt,regression_exit=rr,runs=rows)
s['pass']=ok
(V/'summary.json').write_text(json.dumps(s,indent=1)+'\n')
print('SUMMARY',V/'summary.json',json.dumps({k:v for k,v in s.items() if k!='runs'}))
for r in rows: print(r['file'],r['dim'],r['threads'],round(r['maxrss_gib'],2),round(r['seconds'],1))
sys.exit(0 if ok else 1)
PY
}
trap 'finish; exit $?' EXIT
echo "code $CODE rev $REV node $(hostname) $(lscpu | grep -m1 'Model name')"
python -c "import numpy,numba,scipy,sys;print('python',sys.version.split()[0],'numpy',numpy.__version__,'numba',numba.__version__,'scipy',scipy.__version__)"
stage=tests
NUMBA_NUM_THREADS=4 python tests/run_all.py > "$VAL/tests.log" 2>&1; rc_tests=$?
tail -3 "$VAL/tests.log"; echo "tests exit $rc_tests"
run(){ python -m lri_hpc "$@" --resume; }
stage=regressions
run --task thermal --degree 7 --cutoffs 40 50 --threads 64 --output-dir "$VAL/reg_thermal_t64" || exit 1
run --task phi6 --degree 5 --cutoffs 50 --threads 64 --output-dir "$VAL/reg_phi6_5_t64" || exit 1
run --task phi6 --degree 3 --cutoffs 128 --threads 64 --output-dir "$VAL/reg_phi6_3_t64" || exit 1
mkdir -p "$VAL/reg"; ln -sfn ../reg_thermal_t64 "$VAL/reg/thermal"; ln -sfn ../reg_phi6_5_t64 "$VAL/reg/phi6_5"; ln -sfn ../reg_phi6_3_t64 "$VAL/reg/phi6_3"
python cluster/expanse/check_regression.py "$VAL/reg" "$VAL/regression.json"; rc_reg=$?
stage=calibration
# Allocated cores: 64. Timing at 128 threads is not measured here; production wall limits assume no speedup
# beyond 64 threads (PLAN §3.3, review LRI-010).
for T in 16 32 64; do run --task thermal --degree 7 --cutoffs 60 --threads $T --output-dir "$VAL/cal_thermal_t$T" || exit 1; done
run --task thermal --degree 7 --cutoffs 70 --threads 64 --output-dir "$VAL/cal_thermal70_t64" || exit 1
run --task phi6 --degree 5 --cutoffs 70 --threads 64 --output-dir "$VAL/cal_phi6_5_t64" || exit 1
run --task phi6 --degree 3 --cutoffs 200 --threads 64 --output-dir "$VAL/cal_phi6_3_t64" || exit 1
# Larger anchors for the production memory/time extrapolation (model RSS 44, 21, 28 GiB).
run --task thermal --degree 7 --cutoffs 80 --threads 64 --output-dir "$VAL/cal_thermal80_t64" || exit 1
run --task phi6 --degree 5 --cutoffs 90 --threads 64 --output-dir "$VAL/cal_phi6_5_90_t64" || exit 1
run --task phi6 --degree 3 --cutoffs 320 --threads 64 --output-dir "$VAL/cal_phi6_3_320_t64" || exit 1
stage=done
