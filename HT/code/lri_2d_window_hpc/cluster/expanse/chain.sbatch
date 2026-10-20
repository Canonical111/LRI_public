#!/bin/bash
# Body of one Expanse chain job. submit.py prepends the #SBATCH header (account, shared
# partition, cores, memory, wall, --signal=B:USR1@LEAD, name, log) and passes
# HT2D_SPEC, HT2D_SPEC_SHA256, HT2D_CHAIN, HT2D_CONT, HT2D_MAX_CONT via --export.
# Nothing is read from or written to Lustre: release tarball and outputs are in $HOME,
# code and the Numba cache are staged on node-local /scratch.
# Do NOT use `set -u` on Expanse (it breaks /etc/bashrc).
set -o pipefail
module purge >/dev/null 2>&1; module load cpu/0.15.4 slurm/expanse/23.02.7 >/dev/null 2>&1
say(){ echo "[$(date '+%F %T')] ht2d-chain ${HT2D_CHAIN:-?} job ${SLURM_JOB_ID:-?}: $*"; }
for v in HT2D_SPEC HT2D_SPEC_SHA256 HT2D_CHAIN HT2D_CONT HT2D_MAX_CONT; do
  [[ -n "${!v:-}" ]] || { say "missing $v"; exit 74; }
done
say "host $(hostname); continuation ${HT2D_CONT}/${HT2D_MAX_CONT}; prev ${HT2D_PREV:-none}"

# 1. Verify the frozen spec and the release BEFORE executing any release script (F5).
#    Every input is copied ONCE into node-local scratch; only those snapshots are hashed,
#    parsed, extracted and used afterwards (IR2-01: no re-read of a replaceable file).
STAGE=${HT2D_STAGE_ROOT:-/scratch/${USER}}/job_${SLURM_JOB_ID}
mkdir -p "${STAGE}" || { say "cannot create ${STAGE}"; exit 74; }
SPEC=${STAGE}/spec.json
cp -- "${HT2D_SPEC}" "${SPEC}" || { say "cannot snapshot spec"; exit 74; }
echo "${HT2D_SPEC_SHA256}  ${SPEC}" | sha256sum -c --quiet - || { say "spec sha256 mismatch"; exit 74; }
read -r TAR TARSHA MAN MANSHA ENVPY ENVID ROOT ACCT PART CPUS MEMG WALL LEAD LOGS CAMP < <(/usr/bin/python3 -I -c '
import json,sys
s=json.load(open(sys.argv[1]));r=s["release"];e=s["env"];c=s["chains"][sys.argv[2]]["slurm"]
print(r["tar"],r["tar_sha256"],r["manifest"],r["manifest_sha256"],e["python"],e["env_id"],s["root"],
      c["account"],c["partition"],int(c["cpus"]),int(c["mem_gb"]),c["time"],int(c["lead_s"]),s["logs"],s["campaign"])' \
  "${SPEC}" "${HT2D_CHAIN}") || { say "cannot parse spec"; exit 74; }
cp -- "${TAR}" "${STAGE}/release.tar" && cp -- "${MAN}" "${STAGE}/release.sha256" || { say "cannot snapshot release"; exit 74; }
echo "${TARSHA}  ${STAGE}/release.tar" | sha256sum -c --quiet - || { say "release tar sha256 mismatch"; exit 74; }
echo "${MANSHA}  ${STAGE}/release.sha256" | sha256sum -c --quiet - || { say "release manifest sha256 mismatch"; exit 74; }
tar -xf "${STAGE}/release.tar" -C "${STAGE}" || { say "extraction failed"; exit 74; }
( cd "${STAGE}" && sha256sum -c --quiet release.sha256 ) || { say "staged files corrupted"; exit 74; }
REL=${STAGE}/ht2d
"${ENVPY}" -E -s "${REL}/cluster/expanse/envcheck.py" --expect "${ENVID}" || { say "environment mismatch"; exit 74; }

export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 BLIS_NUM_THREADS=1
export NUMBA_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1} NUMBA_CACHE_DIR=${STAGE}/numba
mkdir -p "${NUMBA_CACHE_DIR}"

# 2. Continuation guard (only when this job continues a predecessor).
if [[ -n "${HT2D_PREV:-}" ]]; then
  "${ENVPY}" -E -s "${REL}/cluster/expanse/continuation.py" --spec "${SPEC}" --chain "${HT2D_CHAIN}" --prev "${HT2D_PREV}"
  g=$?
  case $g in
    0) say "guard passed; resuming";;
    10|11|12) say "guard: nothing to resume (code $g)"; exit 0;;
    *) say "guard refused (code $g); manual check needed"; exit 75;;
  esac
fi

# 3. Run the chain in the background so the USR1 trap can run while we wait.
child=''
continued=0
on_usr1() {
  trap - USR1
  [[ -n "$child" ]] && kill -USR1 "$child" 2>/dev/null
  if (( continued == 0 && HT2D_CONT < HT2D_MAX_CONT )); then
    continued=1
    # Frozen resources passed EXPLICITLY; SBATCH_* input variables removed so nothing overrides them (IR-02).
    if nid=$(env $(compgen -e | grep '^SBATCH_' | sed 's/^/-u /') sbatch --parsable \
             -A "${ACCT}" -p "${PART}" --nodes=1 --ntasks-per-node=1 --cpus-per-task="${CPUS}" --mem="${MEMG}G" \
             -t "${WALL}" --signal=B:USR1@"${LEAD}" -J "ht2d-${CAMP}-${HT2D_CHAIN}" -o "${LOGS}/%x_%j.out" \
             --dependency=afterany:${SLURM_JOB_ID} \
             --export=ALL,HT2D_PREV=${SLURM_JOB_ID},HT2D_CONT=$((HT2D_CONT+1)) "$0"); then
      say "continuation ${nid} queued"
      echo "{\"campaign_job\": \"${SLURM_JOB_ID}\", \"continuation\": \"${nid}\", \"chain\": \"${HT2D_CHAIN}\", \"cont\": $((HT2D_CONT+1))}" \
        >> "${ROOT}/CONTINUATIONS.jsonl"
    else
      say "continuation submission FAILED"
    fi
  else
    say "no continuation (count ${HT2D_CONT} of ${HT2D_MAX_CONT})"
  fi
}
trap on_usr1 USR1
trap '[[ -n "$child" ]] && kill -USR1 "$child" 2>/dev/null' TERM INT
"${ENVPY}" -E -s "${REL}/cluster/expanse/chain.py" --spec "${SPEC}" --chain "${HT2D_CHAIN}" &
child=$!
rc=0
while kill -0 "$child" 2>/dev/null; do wait "$child"; rc=$?; done
wait "$child" 2>/dev/null; last=$?
[[ $last -ne 127 ]] && rc=$last
say "chain exited ${rc}"
exit "${rc}"
