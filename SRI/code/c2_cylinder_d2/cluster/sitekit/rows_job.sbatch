#!/bin/bash
#SBATCH --nodes=1
#SBATCH -J lri_c2_rows
# Run one or more plan rows (each: one (N, regulator order) family, all its lambda
# values in sequence) against a published grid, on node-local scratch.
# Site-independent; submit.py adds the scheduler flags and these variables:
#   LRI_SITE LRI_PKG_TAR LRI_ROOT LRI_ENV LRI_NODE_SCRATCH_BASE   as for grid_job.sbatch
#   LRI_PLAN   plan path relative to the package root (cluster/production_plan.json)
#   LRI_ROW_MODE  array: the row is SLURM_ARRAY_TASK_ID (Expanse one-row arrays);
#                 packed: the rows are LRI_ROWS, e.g. "1:2" (symmetry whole nodes)
#   LRI_PKG_SHA256 LRI_PLAN_SHA256 LRI_SOURCES_SHA256   what submit.py verified; re-checked
#   LRI_PIN    none: one row using the allocation's cores (at most one package);
#              package: row k runs on package k under numactl --cpunodebind (plus
#              --membind when several rows share the node), workers = that
#              package's cores. All rows of one job must use the same grid.
#   LRI_WORKERS optional explicit worker count per row (must fit its cores)
# Outputs: $LRI_ROOT/outputs/<plan name>/<task name>/ per row (raw records,
# fixed-lambda sidecars, run/task receipts, job_receipt.json, SHA256SUMS).
# A row whose published output verifies is skipped, so resubmission is safe.
set -o pipefail
umask 022
LRI_KIND=rows
die() { echo "FATAL($1): $2" >&2; exit "$1"; }
[[ -n "${SLURM_JOB_ID:-}" ]] || die 64 "submit with sbatch"
for v in LRI_PKG_TAR LRI_PKG_SHA256 LRI_PLAN_SHA256 LRI_SOURCES_SHA256 LRI_ROOT LRI_ENV LRI_NODE_SCRATCH_BASE \
         LRI_PLAN LRI_ROW_MODE; do
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
lri_log "staged $TAR_NAME into $PKG"
lri_require_shipped_script rows_job.sbatch
lri_env_init

PLAN="$PKG/$LRI_PLAN"
[[ -f "$PLAN" ]] || lri_die 64 "plan $LRI_PLAN is not in the package"
lri_check_binding "$PLAN"
PLAN_NAME=$(basename "$LRI_PLAN" .json)
lri_select_rows
PIN=${LRI_PIN:-none}
case "$PIN" in none|package) ;; *) lri_die 64 "LRI_PIN must be none or package" ;; esac
if [[ "$PIN" == none ]]; then
    (( ${#ROWS[@]} == 1 )) || lri_die 64 "several rows in one job need LRI_PIN=package"
else
    (( ${#ROWS[@]} <= TOPO_PACKAGES )) || lri_die 64 "${#ROWS[@]} rows but only $TOPO_PACKAGES packages on this node"
fi
LRI_RECEIPT_EXTRA=("plan=$LRI_PLAN" "rows=${ROWS[*]}" "pin=$PIN")

# ---- describe the rows; skip the ones already published
TODO=()
GRID_SET=""
for row in "${ROWS[@]}"; do
    eval "$("$PY" "$PKG/cluster/sitekit/jobtools.py" task-info --plan "$PLAN" --index "$row")" \
        || lri_die 64 "invalid plan row $row of $LRI_PLAN"
    dest="$LRI_ROOT/outputs/$PLAN_NAME/$TASK_NAME"
    lri_log "row $row: $TASK_ID N=$TASK_N order=$TASK_ORDER lambda=[$TASK_LAMBDAS] stage=$TASK_STAGE -> $dest"
    "$PY" "$PKG/cluster/sitekit/jobtools.py" published-check --kind row --dir "$dest" --plan "$PLAN" --index "$row" \
        > /dev/null; rc=$?
    case $rc in
        0) lri_log "row $row already published and verified (skipped)"; continue ;;
        3) ;;
        *) lri_die 74 "published output $dest is incomplete or corrupt (see above); inspect it, do not overwrite" ;;
    esac
    if [[ -n "$GRID_SET" && "$GRID_SET" != "$GRID_DIR" ]]; then
        lri_die 64 "rows of one job must share a grid ($GRID_SET vs $GRID_DIR)"
    fi
    GRID_SET=$GRID_DIR; GRID_KEY_SET=$GRID_KEY; GRID_N=$TASK_N; GRID_O=$GRID_OVERSAMPLE
    TODO+=("$row")
    eval "TASK_NAME_$row=\$TASK_NAME"
done
if (( ${#TODO[@]} == 0 )); then
    lri_log "nothing to do"
    exit 0
fi

NEED=$("$PY" "$PKG/cluster/sitekit/jobtools.py" scratch-need --kind task --cutoff "$GRID_N" --oversample "$GRID_O") \
    || lri_die 64 "cannot estimate scratch need"
lri_require_scratch "$NEED"
lri_phase_begin fetch_grid
lri_fetch_grid "$LRI_ROOT/grids/$GRID_SET" "$STAGE/grid_cache/$GRID_KEY_SET"; rc=$?
lri_phase_end $rc
(( rc == 0 )) || lri_die 74 "cannot stage the grid from $LRI_ROOT/grids/$GRID_SET"

# ---- run the rows concurrently, one per package when pinned
PIDS=(); T0S=(); ROWLOG=()
for k in "${!TODO[@]}"; do
    row=${TODO[$k]}
    PIN_CMD=()
    if [[ "$PIN" == package ]]; then
        nodes_var="TOPO_PKG${k}_NODES"; cores_var="TOPO_PKG${k}_CORES"
        nodes=${!nodes_var}; workers=${!cores_var}
        [[ -n "$nodes" ]] || lri_die 64 "no NUMA nodes found for package $k"
        PIN_CMD=(numactl --cpunodebind="$nodes")
        (( ${#TODO[@]} > 1 )) && PIN_CMD+=(--membind="$nodes")
        (( workers <= CORES )) || workers=$CORES
    else
        workers=$CORES
    fi
    if [[ -n "${LRI_WORKERS:-}" ]]; then
        (( LRI_WORKERS <= workers )) || lri_die 64 "LRI_WORKERS=$LRI_WORKERS exceeds the $workers cores available to row $row"
        workers=$LRI_WORKERS
    fi
    LRI_RECEIPT_EXTRA+=("row${row}_workers=$workers" "row${row}_numactl=${PIN_CMD[*]}")
    ROWLOG[$k]="$LRI_ROOT/logs/${SLURM_JOB_NAME:-rows}_${SLURM_JOB_ID}_row$row.log"
    lri_log "row $row: $workers workers ${PIN_CMD[*]:+(${PIN_CMD[*]}) }-> live log ${ROWLOG[$k]}"
    T0S[$k]=$(date +%s.%N)
    "${PIN_CMD[@]}" "$PY" "$PKG/cluster/sitekit/jobtools.py" monitor --label "row$row" --watch "$STAGE" --interval 20 \
        --summary "$STAGE/monitor_row$row.json" --samples "$STAGE/samples_row$row.jsonl" -- \
        "$PY" "$PKG/cluster/run_task.py" run --plan "$PLAN" --task-index "$row" \
            --work-root "$STAGE/work" --output-root "$STAGE/out" --coefficient-cache "$STAGE/grid_cache" \
            --workers "$workers" --fft-workers "$workers" > "${ROWLOG[$k]}" 2>&1 &
    PIDS[$k]=$!
done
FAILED=0
for k in "${!TODO[@]}"; do
    row=${TODO[$k]}
    wait "${PIDS[$k]}"; rc=$?
    echo "run_row$row ${T0S[$k]} $(date +%s.%N) $rc" >> "$STAGE/phases.txt"
    lri_log "row $row finished (exit $rc); its log:"
    sed "s/^/  [row $row] /" "${ROWLOG[$k]}"
    eval "name=\$TASK_NAME_$row"
    out="$STAGE/out/$name"
    if (( rc != 0 )) || [[ ! -s "$out/task_receipt.json" ]]; then
        FAILED=1
        continue
    fi
    cp "${ROWLOG[$k]}" "$out/run_log.txt" || lri_die 74 "cannot copy the log of row $row"
    "$PY" "$PKG/cluster/sitekit/jobtools.py" receipt --kind rows --status "row $row completed-before-publish" \
        --out "$out/job_receipt.json" --phases "$STAGE/phases.txt" --package "$PKG" \
        --monitor "$STAGE/monitor_row$row.json" --extra "${LRI_RECEIPT_EXTRA[@]}" "row=$row" > /dev/null \
        || lri_die 74 "cannot write the job receipt of row $row"
    lri_write_sums "$out" || lri_die 74 "cannot checksum outputs of row $row"
    lri_phase_begin "publish_row$row"
    lri_publish_dir "$out" "$LRI_ROOT/outputs/$PLAN_NAME/$name"; rc=$?
    lri_phase_end $rc
    (( rc == 0 )) || FAILED=1
    ls -l "$LRI_ROOT/outputs/$PLAN_NAME/$name" 2>/dev/null
done
(( FAILED == 0 )) || lri_die 70 "at least one row failed (see the row logs above); successful rows were published"
lri_log "rows complete: ${TODO[*]}"
