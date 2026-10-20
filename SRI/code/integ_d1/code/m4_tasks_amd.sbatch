#!/bin/bash
#SBATCH --job-name=integ-m4amd
#SBATCH --partition=amdq
#SBATCH --nodes=1
#SBATCH --exclusive
#SBATCH --exclude=cn112
#SBATCH --mem=200G
#SBATCH --time=12:00:00
#SBATCH --output=<SCRATCH>/lri_integ/logs/%x_%j.out
# usage: sbatch m4_tasks_amd.sbatch CE1 TASKFILE1 [CE2 TASKFILE2]
# amdq node (2 x EPYC 7532, 64 cores): one task stream per physical socket, 32 OpenMP threads each, pinned to that
# socket's cores; each stream runs m4_tasks.sbatch (same fingerprint/reuse/validation logic) with OMP_THREADS=32.
# The engine binaries are the same x86-64-v3 builds as on defq (same build id), so AMD and Intel outputs of one build
# merge under the single-build rule.
cd <SCRATCH>/lri_integ/code/m4 || { echo "FAIL: cannot cd"; exit 1; }
echo "node $(hostname) start $(date)"; lscpu | grep -E 'Model name|^CPU\(s\)|Socket'
pids=()
for sock in 0 1; do
  ce=$1; tf=$2
  [ -z "$tf" ] && break
  shift 2
  cpus=$(lscpu -p=CPU,CORE,SOCKET | grep -v '^#' | awk -F, -v s=$sock '$3==s && !seen[$2]++ {print $1}' | paste -sd,)
  echo "socket $sock: CE=$ce tasks=$tf cpus=$cpus"
  CE=$ce OMP_THREADS=32 taskset -c "$cpus" bash m4_tasks.sbatch "$tf" > ../../logs/m4amd_${SLURM_JOB_ID}_s$sock.out 2>&1 &
  pids+=($!)
done
rc=0
for p in "${pids[@]}"; do wait $p || rc=1; done
for sock in 0 1; do [ -f ../../logs/m4amd_${SLURM_JOB_ID}_s$sock.out ] && { echo "== socket $sock"; tail -3 ../../logs/m4amd_${SLURM_JOB_ID}_s$sock.out; }; done
echo "end $(date) rc $rc"
exit $rc
