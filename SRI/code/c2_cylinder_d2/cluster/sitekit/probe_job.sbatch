#!/bin/bash
#SBATCH --nodes=1
#SBATCH -J lri_c2_probe
# Node probe: node-local scratch capacity and speed, CPU/NUMA topology (lscpu
# CPU/NODE/SOCKET map), memory cgroup, environment versions; optionally the
# auxiliary-cutoff cost benchmark. Submit through the site wrapper, e.g.
#   $PY cluster/<site>/submit.py --probe --submit          (add --probe-aux for the benchmark)
# Variables: LRI_SITE LRI_PKG_TAR LRI_ROOT LRI_ENV LRI_NODE_SCRATCH_BASE (as for the
#   other jobs); LRI_PROBE_AUX=1 also runs aux_cost_probe.py (LRI_PROBE_LAM,
#   LRI_PROBE_ORDER, LRI_PROBE_MIXED, LRI_PROBE_TAIL override its defaults 0.05,
#   1, "4096 8192 16384", "2048 4096 8192").
# Results: $LRI_ROOT/receipts/<job name>_<job id>/ (node_facts.txt, aux_cost.json, receipt.json).
set -o pipefail
umask 022
LRI_KIND=probe
die() { echo "FATAL($1): $2" >&2; exit "$1"; }
[[ -n "${SLURM_JOB_ID:-}" ]] || die 64 "submit with sbatch"
for v in LRI_PKG_TAR LRI_PKG_SHA256 LRI_ROOT LRI_ENV LRI_NODE_SCRATCH_BASE; do
    [[ -n "${!v:-}" ]] || die 64 "$v is not set"
done

# ---- stage the package: ONE tarball -> node-local scratch, verified twice
T_STAGE=$(date +%s.%N)
STAGE=$LRI_NODE_SCRATCH_BASE/job_$SLURM_JOB_ID
mkdir -p "$STAGE" || die 73 "cannot create $STAGE"
[[ "${LRI_CLEAN_STAGE:-0}" == 1 ]] && trap 'rm -rf "$STAGE"' EXIT
TAR_NAME=$(basename "$LRI_PKG_TAR")
cp "$LRI_PKG_TAR" "$LRI_PKG_TAR.sha256" "$STAGE/" || die 74 "cannot copy $LRI_PKG_TAR(.sha256)"
( cd "$STAGE" && sha256sum -c --quiet "$TAR_NAME.sha256" ) || die 74 "tarball checksum mismatch"
[[ "$(sha256sum "$STAGE/$TAR_NAME" | cut -d' ' -f1)" == "$LRI_PKG_SHA256" ]] \
    || die 65 "staged tarball is not the one submit.py verified (LRI_PKG_SHA256)"
tar -xf "$STAGE/$TAR_NAME" -C "$STAGE" || die 74 "cannot extract $TAR_NAME"
PKG=$STAGE/lri_c2
( cd "$PKG" && sha256sum -c --quiet STAGE_MANIFEST.sha256 ) || die 74 "staged files differ from STAGE_MANIFEST.sha256"
rm -f "$STAGE/$TAR_NAME"
# shellcheck source=lib.sh
source "$PKG/cluster/sitekit/lib.sh" || die 74 "cannot source lib.sh"
trap lri_on_exit EXIT
echo "stage $T_STAGE $(date +%s.%N) 0" >> "$STAGE/phases.txt"
lri_require_shipped_script probe_job.sbatch
lri_env_init
RDIR=$(lri_receipt_dir)
mkdir -p "$RDIR" || lri_die 73 "cannot create $RDIR"

# Facts: each essential measurement records its own status; a failure is kept in
# node_facts.txt (partial diagnostics) and makes the phase and the job fail (R010).
DD_BYTES=$((256 * 16 * 1024 * 1024))
FACTS_FAILED=()
fact() {   # fact NAME CMD...: run, keep its output, remember a failure
    local name=$1; shift
    "$@" || FACTS_FAILED+=("$name")
}
lri_phase_begin facts
{
    echo "## site ${LRI_SITE:-?}  host $(hostname)  job $SLURM_JOB_ID  partition ${SLURM_JOB_PARTITION:-?}  $(date -u +%FT%TZ)"
    echo "## node-local job directory"
    fact df df -B1 "$STAGE"; df -h "$STAGE"; findmnt -T "$STAGE" 2>/dev/null
    echo "## block devices"; lsblk -d -o NAME,SIZE,ROTA,TYPE,MODEL 2>/dev/null
    echo "## other users' usage of the node-local filesystem (top level)"; du -sh "$(dirname "$LRI_NODE_SCRATCH_BASE")"/* 2>/dev/null | sort -h | tail -5
    echo "## cpu"; fact lscpu lscpu
    echo "## CPU -> NUMA node -> socket (lscpu -p=CPU,NODE,SOCKET, compressed to ranges per node)"
    lscpu -p=CPU,NODE,SOCKET | grep -v '^#' | awk -F, '{k=$2" "$3; if(!(k in first)){first[k]=$1; order[++n]=k} last[k]=$1; cnt[k]++}
        END{for(i=1;i<=n;i++){split(order[i],a," "); printf "node %s socket %s: %d cpus (first %s, last %s)\n", a[1], a[2], cnt[order[i]], first[order[i]], last[order[i]]}}'
    echo "## package topology seen by the job (jobtools topology)"
    fact topology "$PY" "$PKG/cluster/sitekit/jobtools.py" topology --json
    echo "## allowed cpus"; grep -E 'Cpus_allowed_list|Mems_allowed_list' /proc/self/status
    echo "## numa"; numactl -H 2>/dev/null | head -12
    echo "## memory"; free -g
    echo "## cgroup"; cat /proc/self/cgroup
    fact cgroup "$PY" -c 'import sys; sys.path.insert(0, sys.argv[1]); import jobtools, json; c = jobtools.job_cgroup(); print(json.dumps({"cgroup": c, "sample": jobtools.cgroup_sample(c)}))' "$PKG/cluster/sitekit"
    echo "## tools"; command -v lfs numactl sha256sum /usr/bin/time
    echo "## node-local write/read speed (4 GiB, direct I/O)"
    avail=$(df -B1 --output=avail "$STAGE" | tail -1 | tr -d ' ')
    if [[ "$avail" =~ ^[0-9]+$ ]] && (( avail >= DD_BYTES + 2000000000 )); then
        fact dd_write dd if=/dev/zero of="$STAGE/ddtest" bs=16M count=256 oflag=direct
        fact dd_read dd if="$STAGE/ddtest" of=/dev/null bs=16M iflag=direct
        echo "## sha256sum speed on that file"
        fact sha256sum /usr/bin/time -f '%e s' sha256sum "$STAGE/ddtest"
        fact hashlib "$PY" - "$STAGE/ddtest" <<'EOF'
import hashlib, sys, time
t = time.time(); h = hashlib.sha256()
with open(sys.argv[1], 'rb') as f:
    for b in iter(lambda: f.read(1 << 24), b''):
        h.update(b)
print(f'python hashlib sha256: {time.time() - t:.2f} s')
EOF
        rm -f "$STAGE/ddtest"
    else
        echo "SKIPPED: only $avail bytes free for the $DD_BYTES-byte speed test"
        FACTS_FAILED+=(scratch_capacity)
    fi
    echo "## failed measurements: ${FACTS_FAILED[*]:-none}"
} > "$RDIR/node_facts.txt" 2>&1
FACTS_RC=0
(( ${#FACTS_FAILED[@]} == 0 )) || FACTS_RC=70
lri_phase_end $FACTS_RC
cat "$RDIR/node_facts.txt"

AUX_RC=0
if [[ "${LRI_PROBE_AUX:-0}" == 1 ]]; then
    lri_phase_begin aux_cost
    # shellcheck disable=SC2086
    "$PY" "$PKG/cluster/sitekit/jobtools.py" monitor --label aux --interval 10 \
        --summary "$STAGE/monitor_aux.json" --samples "$STAGE/samples_aux.jsonl" -- \
        "$PY" "$PKG/cluster/sitekit/aux_cost_probe.py" --lam "${LRI_PROBE_LAM:-0.05}" --order "${LRI_PROBE_ORDER:-1}" \
            --mixed ${LRI_PROBE_MIXED:-4096 8192 16384} --tail ${LRI_PROBE_TAIL:-2048 4096 8192} \
            --out "$RDIR/aux_cost.json"
    AUX_RC=$?
    lri_phase_end $AUX_RC
fi
(( FACTS_RC == 0 )) || lri_die 70 "some node measurements failed (see node_facts.txt; partial results kept)"
(( AUX_RC == 0 )) || lri_die "$AUX_RC" "aux_cost_probe.py failed (partial results kept in aux_cost.json)"
lri_log "probe complete: $RDIR"
