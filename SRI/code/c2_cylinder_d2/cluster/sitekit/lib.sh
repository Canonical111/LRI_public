# shellcheck shell=bash
# Site-independent helpers for the job scripts in cluster/sitekit/. Sourced from
# the STAGED, checksum-verified package (never from a home or shared-filesystem
# tree), after the job script has set:
#   STAGE  node-local job directory  $LRI_NODE_SCRATCH_BASE/job_$SLURM_JOB_ID
#          (Expanse /scratch/$USER/..., symmetry /local1/$USER/...)
#   PKG    extracted package root inside STAGE
#   LRI_KIND  grid | rows | probe
# Site settings arrive as LRI_* variables from submit.py (site profile):
#   LRI_SITE LRI_ROOT LRI_ENV LRI_MODULES LRI_STRIPE LRI_CLEAN_STAGE LRI_PIN
# submit.py sets every reserved LRI_* variable explicitly (empty when unused), so
# nothing inherited from the submitting shell reaches a job.
# Deliberately no `set -u` (it breaks /etc/bashrc on Expanse) and no `set -e`:
# every step checks its own status and fails closed with a distinct exit code.
#   64 usage   65 staged package/plan/sources differ from what was submitted
#   73 cannot create   74 staging/checksum/publish I/O or a corrupt published
#   directory   75 not enough node-local scratch (resubmit elsewhere)
#   78 environment mismatch

lri_log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }
lri_die() { local code=$1; shift; lri_log "FATAL($code): $*" >&2; exit "$code"; }

# Phase bookkeeping: one "name start end exit" line per phase, epoch seconds.
lri_phase_begin() { LRI_PHASE_NAME=$1; LRI_PHASE_T0=$(date +%s.%N); lri_log "BEGIN $1"; }
lri_phase_end() {
    local code=${1:-0}
    echo "$LRI_PHASE_NAME $LRI_PHASE_T0 $(date +%s.%N) $code" >> "$STAGE/phases.txt"
    lri_log "END $LRI_PHASE_NAME (exit $code)"
}

# The batch script that Slurm runs must be the one shipped in the staged tarball,
# so that every job runs exactly the code that was checksummed.
lri_require_shipped_script() {
    local shipped="$PKG/cluster/sitekit/$1"
    if cmp -s "$0" "$shipped"; then return 0; fi
    if [[ "${LRI_ALLOW_SCRIPT_MISMATCH:-0}" == 1 ]]; then
        lri_log "WARNING: running batch script differs from $shipped (LRI_ALLOW_SCRIPT_MISMATCH=1)"
        return 0
    fi
    lri_die 64 "batch script $0 differs from the staged $shipped; rebuild/upload the tarball or submit the shipped script"
}

# Python environment, thread caps, core count. CORES = physical cores of this
# allocation, capped at one physical package (and 64) for a single process.
lri_env_init() {
    if [[ -n "${LRI_MODULES:-}" ]]; then        # e.g. the module python a venv was built from
        source /etc/profile.d/modules.sh 2>/dev/null || lri_die 78 "cannot initialise environment modules"
        # shellcheck disable=SC2086
        module load ${LRI_MODULES//:/ } || lri_die 78 "module load ${LRI_MODULES//:/ } failed"
    fi
    PY="$LRI_ENV/bin/python"
    [[ -x "$PY" ]] || lri_die 78 "python environment missing: $LRI_ENV (run cluster/$LRI_SITE/setup_env.sh)"
    unset PYTHONPATH PYTHONHOME VIRTUAL_ENV
    export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg MPLCONFIGDIR="$STAGE/.mpl"
    # Hidden BLAS/OpenMP pools stay at one thread (run_task.py enforces the same for
    # its children); the solver's parallelism is LRI_FFT_WORKERS / grid workers.
    export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
    "$PY" "$PKG/cluster/sitekit/jobtools.py" check-env --requirements "$PKG/requirements-tested.txt" \
        --out "$STAGE/env_check.json" > /dev/null \
        || lri_die 78 "installed versions differ from requirements-tested.txt (see $STAGE/env_check.json)"
    CORES=$("$PY" "$PKG/cluster/sitekit/jobtools.py" cores --per-process) || lri_die 64 "cannot count cores"
    [[ "$CORES" =~ ^[0-9]+$ ]] && (( CORES >= 1 )) || lri_die 64 "bad core count '$CORES'"
    eval "$("$PY" "$PKG/cluster/sitekit/jobtools.py" topology)" || lri_die 64 "cannot read the CPU topology"
    lri_log "site=${LRI_SITE:-?} host=$(hostname) cpu=$TOPO_VENDOR/$TOPO_MODEL packages=$TOPO_PACKAGES physical_cores=$TOPO_PHYSICAL_CORES cpus_on_node=${SLURM_CPUS_ON_NODE:-?} mem_per_node_MB=${SLURM_MEM_PER_NODE:-?} cores_per_process=$CORES python=$("$PY" -c 'import platform;print(platform.python_version())')"
}

# The staged package must be the one submit.py checked (R001): the tarball sha256
# is compared during staging; here the scientific sources and, for row jobs, the
# plan file are compared with the values exported at submission.
lri_check_binding() {
    local plan=${1:-} sources plan_sha
    [[ -n "${LRI_SOURCES_SHA256:-}" ]] || lri_die 65 "LRI_SOURCES_SHA256 not set; submit with submit.py"
    sources=$("$PY" "$PKG/cluster/sitekit/jobtools.py" sources-hash) || lri_die 65 "cannot hash the staged sources"
    [[ "$sources" == "$LRI_SOURCES_SHA256" ]] \
        || lri_die 65 "staged scientific sources ($sources) differ from the submitted ones ($LRI_SOURCES_SHA256)"
    if [[ -n "$plan" ]]; then
        [[ -n "${LRI_PLAN_SHA256:-}" ]] || lri_die 65 "LRI_PLAN_SHA256 not set; submit with submit.py"
        plan_sha=$(sha256sum "$plan" | cut -d' ' -f1) || lri_die 65 "cannot hash $plan"
        [[ "$plan_sha" == "$LRI_PLAN_SHA256" ]] \
            || lri_die 65 "staged plan $plan ($plan_sha) differs from the submitted one ($LRI_PLAN_SHA256)"
    fi
    lri_log "binding verified: package ${LRI_PKG_SHA256:0:12}, sources ${sources:0:12}${plan:+, plan ${plan_sha:0:12}}"
}

# Rows of a row job (R002), explicit by mode:
#   array   one row = SLURM_ARRAY_TASK_ID (required; LRI_ROWS must be empty)
#   packed  LRI_ROWS ("1:2" or "1 2"); not allowed inside an array job
# Sets the array ROWS.
lri_select_rows() {
    ROWS=()
    case "${LRI_ROW_MODE:-}" in
        array)
            [[ "${SLURM_ARRAY_TASK_ID:-}" =~ ^[0-9]+$ ]] || lri_die 64 "LRI_ROW_MODE=array outside a job array"
            [[ -z "${LRI_ROWS:-}" ]] || lri_die 64 "LRI_ROWS is set in array mode; the row comes from SLURM_ARRAY_TASK_ID only"
            ROWS=("$SLURM_ARRAY_TASK_ID") ;;
        packed)
            [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]] || lri_die 64 "LRI_ROW_MODE=packed inside a job array"
            read -r -a ROWS <<< "${LRI_ROWS//[,:]/ }"
            (( ${#ROWS[@]} >= 1 )) || lri_die 64 "LRI_ROW_MODE=packed needs LRI_ROWS" ;;
        *) lri_die 64 "LRI_ROW_MODE must be array or packed (got '${LRI_ROW_MODE:-}')" ;;
    esac
    local r
    for r in "${ROWS[@]}"; do
        [[ "$r" =~ ^[0-9]+$ ]] || lri_die 64 "bad plan row '$r'"
    done
}

# Fail early (exit 75) if node-local scratch cannot hold NEED bytes.
lri_require_scratch() {
    local need=$1 avail
    avail=$(df -B1 --output=avail "$STAGE" | tail -1 | tr -d ' ')
    lri_log "node-local scratch: need $((need / 1000000000)) GB, available $((avail / 1000000000)) GB ($(df -h "$STAGE" | tail -1))"
    (( avail >= need )) || lri_die 75 "not enough node-local scratch on $(hostname): need $need bytes, have $avail"
}

# Write SHA256SUMS for the regular files directly inside a directory.
lri_write_sums() {
    local dir=$1
    ( cd "$dir" && find . -maxdepth 1 -type f ! -name SHA256SUMS ! -name '.*' -printf '%P\0' \
        | LC_ALL=C sort -z | xargs -0 -r sha256sum > SHA256SUMS ) || return 74
    [[ -s "$dir/SHA256SUMS" ]] || return 74
}

# Validated file names of DIR/SHA256SUMS, one per line (manifests.py: no
# traversal, absolute, subdirectory or hidden names, no duplicates, non-empty).
# Every loop over a manifest uses this list, never the raw manifest lines.
lri_manifest_names() {
    "$PY" "$PKG/cluster/sitekit/manifests.py" names "$1"
}

# Copy the files named in SRC/SHA256SUMS (plus SHA256SUMS) to DEST on the shared
# filesystem: snapshot the manifest into a hidden partial directory, validate the
# snapshot's names, copy exactly those files, verify the copies by re-reading
# them, then rename the directory into place (atomic; no lock needed, which
# matters on BeeGFS where flock is node-local). An existing DEST is never
# overwritten (published results are immutable). STRIPE > 1 sets the Lustre
# stripe count of the new directory (ignored where lfs is absent).
lri_publish_dir() {
    local src=$1 dest=$2 stripe=${3:-0} parent name tmp f names
    parent=$(dirname "$dest"); name=$(basename "$dest")
    tmp="$parent/.${name}.partial.${SLURM_JOB_ID}"
    [[ -s "$src/SHA256SUMS" ]] || { lri_log "no SHA256SUMS in $src"; return 74; }
    [[ -e "$dest" ]] && { lri_log "refusing to overwrite existing $dest"; return 74; }
    mkdir -p "$parent" && rm -rf "$tmp" && mkdir "$tmp" || return 74
    if (( stripe > 1 )) && command -v lfs > /dev/null; then
        lfs setstripe -c "$stripe" -S 4M "$tmp" 2>/dev/null || lri_log "note: lfs setstripe failed; default striping"
    fi
    cp -- "$src/SHA256SUMS" "$tmp/SHA256SUMS" || return 74
    names=$(lri_manifest_names "$tmp") || { lri_log "invalid manifest in $src"; return 74; }
    while IFS= read -r f; do
        cp -P -- "$src/$f" "$tmp/$f" || return 74
    done <<< "$names"
    if [[ "${LRI_VERIFY_PUBLISH:-1}" == 1 ]]; then
        ( cd "$tmp" && sha256sum -c --quiet SHA256SUMS ) || { lri_log "verification of $tmp FAILED"; return 74; }
    fi
    mv -T "$tmp" "$dest" || return 74
    lri_log "published $dest"
}

# Copy a published grid from the shared filesystem to node-local scratch (R2-001):
# snapshot its SHA256SUMS first, validate the snapshot's names before anything
# else is copied, copy exactly those files (symlinks are not followed), and
# require a complete grid (manifests.py grid-status: receipt, array, metadata,
# no unlisted entries, every hash). A crafted manifest therefore cannot write
# outside DEST or overwrite the staged package.
lri_fetch_grid() {
    local src=$1 dest=$2 f names
    mkdir -p "$dest" || return 73
    [[ -z "$(ls -A "$dest")" ]] || { lri_log "fetch target $dest is not empty"; return 74; }
    cp -- "$src/SHA256SUMS" "$dest/SHA256SUMS" || { lri_log "not published (no SHA256SUMS): $src"; return 74; }
    names=$(lri_manifest_names "$dest") || { lri_log "invalid manifest of $src; nothing copied"; return 74; }
    while IFS= read -r f; do
        cp -P -- "$src/$f" "$dest/$f" || return 74
    done <<< "$names"
    "$PY" "$PKG/cluster/sitekit/manifests.py" grid-status "$dest" > /dev/null \
        || { lri_log "grid copied from $src is incomplete or corrupt"; return 74; }
}

# Receipt directory on the shared filesystem for this job, filled by the EXIT trap.
lri_receipt_dir() { echo "$LRI_ROOT/receipts/${SLURM_JOB_NAME:-job}_${SLURM_JOB_ID}"; }

lri_on_exit() {
    local code=$? rdir status
    trap - EXIT
    rdir=$(lri_receipt_dir)
    mkdir -p "$rdir" 2>/dev/null
    status=ok; (( code == 0 )) || status="failed:$code"
    if [[ -n "${PY:-}" && -x "${PY:-}" && -n "${PKG:-}" ]]; then
        "$PY" "$PKG/cluster/sitekit/jobtools.py" receipt --kind "$LRI_KIND" --status "$status" \
            --out "$rdir/receipt.json" --phases "$STAGE/phases.txt" --package "$PKG" \
            --monitor "$STAGE"/monitor_*.json --extra "${LRI_RECEIPT_EXTRA[@]}" > /dev/null 2>&1
        cp "$STAGE"/monitor_*.json "$STAGE"/samples_*.jsonl "$STAGE"/env_check.json "$STAGE"/phases.txt \
            "$rdir/" 2>/dev/null
    else
        printf '{"kind": "%s", "status": "%s", "site": "%s", "job": "%s", "host": "%s", "note": "failed before the package environment was available"}\n' \
            "${LRI_KIND:-unknown}" "$status" "${LRI_SITE:-unknown}" "${SLURM_JOB_ID:-}" "$(hostname)" > "$rdir/receipt.json"
    fi
    lri_log "exit $code; receipt in $rdir"
    if [[ "${LRI_CLEAN_STAGE:-0}" == 1 && -n "${STAGE:-}" && "$STAGE" == */job_"${SLURM_JOB_ID}" ]]; then
        rm -rf "$STAGE"                       # node-local scratch that Slurm does not remove itself
    fi
    exit "$code"
}
