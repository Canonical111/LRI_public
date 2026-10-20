#!/bin/bash
# J-DRL-1 (A-ORC-8a; F7 rerun) cancel step, run from the Mac: record the twin's lane scratch and runtime directories
# (TMPDIR on BeeGFS so that the login node can see them), the claims and the index logs, scancel the lane worker, then
# record the same 30 s and 60 s later. With the F7 fix nothing of the job may be left: no c8d2_lane_<job>_* and no
# c8d2_runtime_* directory, the claims stale (released by the next submit.sh), no failure record.
#   drl1_cancel.sh JOB RUN TMPDIR OUTDIR
set -uo pipefail
job=$1 run=$2 tmp=$3 out=$4; mkdir -p "$out"
snap() {
  ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; date -Is; echo '-- sacct'; sacct -j $job -X -n -o JobID,JobName,State,Start,End,Elapsed; \
    echo '-- claims'; ls $run/lanes/claims 2>/dev/null; echo '-- failure records'; ls $run/lanes/failures 2>/dev/null | head; \
    echo '-- lane scratch and runtime dirs under TMPDIR'; find $tmp -maxdepth 2 -type d 2>/dev/null | sort; \
    echo '-- bytes under TMPDIR'; du -sb $tmp 2>/dev/null; echo '-- checkpoints'; ls $run/groups/*/checkpoints/ 2>/dev/null | grep -c json"
}
snap > "$out/before_cancel.txt" 2>&1
ssh -T symmetry "export PATH=/cm/shared/apps/slurm/current/bin:\$PATH; date -Is; scancel $job; echo scancel $job exit \$?" > "$out/scancel.txt" 2>&1
echo "$(date -u +%Y%m%dT%H%M%SZ) scancel $job (J-DRL-1 drill cancel)" >> "$out/../admission/submitted.txt"
sleep 30; snap > "$out/after_cancel_30s.txt" 2>&1
sleep 30; snap > "$out/after_cancel_60s.txt" 2>&1
ssh -T symmetry "tail -25 $run/slurm_logs/lane-$job.log; echo '-- index logs with a stop line'; grep -l 'stopped by signal\|signal 15' $run/lanes/logs/*.log 2>/dev/null | wc -l; grep -h 'run: \|stopped by signal' $run/lanes/logs/*.log 2>/dev/null | sort | uniq -c | head" > "$out/worker_log_tail.txt" 2>&1
cat "$out/scancel.txt"; grep -A12 'lane scratch' "$out/after_cancel_30s.txt"; tail -8 "$out/worker_log_tail.txt"
