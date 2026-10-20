#!/bin/bash
# A-EXP-1's scratch check (PLAN.md A-EXP-1: "C8_SCRATCH is computed inside the job (a test job shows a login-node value
# is not inherited)"). Submitted from a login shell that exports C8_SCRATCH=<a login-node value> (sbatch's default
# --export=ALL carries it into the job): the job records the value it inherited, sources slurm/common.sh as every C8(3)
# job script does (lane_worker.sh, run_array.sh, merge.sh, plan.sh), and records the value common.sh computed. It passes
# when the inherited value is the submitting shell's (so the test is real) and the computed one is $SLURM_TMPDIR, else
# the site's node-local path (Expanse /scratch/$USER/job_$SLURM_JOB_ID; symmetry, C8_SITE=symmetry,
# /local1/$USER/job_$SLURM_JOB_ID; stated here independently of slurm/site.sh), and differs from the inherited one.
# On symmetry: -p amddebugq --nodes=1 --ntasks=1 --mem=1G -t 00:05:00 (no -A).
#   export C8_SCRATCH=/tmp/login-value C8_PACKAGE=$C8_ROOT/pkg/<sha12> C8_PROBE_OUT=$C8_ROOT/evidence/<sha12>/scratch_probe/result.json
#   python3 -B $C8_PACKAGE/tools/slurm_submit.py raw --role scratchprobe --dir $C8_ROOT/evidence/<sha12>/scratch_probe -- \
#     -A yun124 -p debug --nodes=1 --ntasks=1 -c 1 --mem=1G -t 00:05:00 --no-requeue -o $C8_ROOT/logs/%x_%j.out \
#     $C8_PACKAGE/slurm/scratch_probe.sh
# No #SBATCH lines: the options above are the job's (slurm_submit.py names it and sets the comment, D.11).
set -eo pipefail
INHERITED="${C8_SCRATCH-<unset>}"
EXPECT_INHERITED="${C8_PROBE_EXPECT:-/tmp/login-value}"
: "${C8_PACKAGE:?C8_PACKAGE (the export under test)}" "${C8_PROBE_OUT:?C8_PROBE_OUT (the JSON record)}" "${SLURM_JOB_ID:?runs inside a Slurm job}"
source "$C8_PACKAGE/slurm/common.sh"
if [ -n "${SLURM_TMPDIR:-}" ]; then WANT="$SLURM_TMPDIR"
elif [ "${C8_SITE:-}" = symmetry ]; then WANT="/local1/$USER/job_$SLURM_JOB_ID"
else WANT="/scratch/$USER/job_$SLURM_JOB_ID"; fi
PASS=false
if [ "$INHERITED" = "$EXPECT_INHERITED" ] && [ "$C8_SCRATCH" = "$WANT" ] && [ "$C8_SCRATCH" != "$INHERITED" ] && [ -d "$C8_SCRATCH" ]; then PASS=true; fi
mkdir -p "$(dirname "$C8_PROBE_OUT")"
"$PY" - "$C8_PROBE_OUT" "$INHERITED" "$EXPECT_INHERITED" "$C8_SCRATCH" "$WANT" "${SLURM_TMPDIR-<unset>}" "$PASS" <<'EOF'
import json,os,socket,sys
out,inh,exp,got,want,tmpdir,ok=sys.argv[1:8]
rec={'schema':'c8-d3-gate-1','gate':'A-EXP-1 C8_SCRATCH computed inside the job (slurm/common.sh)','host':socket.gethostname(),
     'slurm_job_id':os.environ.get('SLURM_JOB_ID'),'inherited_C8_SCRATCH':inh,'expected_inherited':exp,'SLURM_TMPDIR':tmpdir,
     'computed_C8_SCRATCH':got,'expected_computed':want,'passed':ok=='true'}
open(out,'w').write(json.dumps(rec,indent=1)+'\n');print(json.dumps(rec))
sys.exit(0 if rec['passed']else 1)
EOF
