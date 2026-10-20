#!/bin/bash
#SBATCH --nodes=1
#SBATCH -J lri_c2_grid
# Prepare ONE Ising coefficient grid on node-local scratch and publish it to the
# site's shared filesystem. Site-independent: submit.py (cluster/<site>/submit.py)
# adds account, partition, CPUs, memory, wall time, log path and these variables
# from the site profile cluster/<site>/profile.json:
#   LRI_SITE               expanse | symmetry (recorded in every receipt)
#   LRI_PKG_TAR            package tarball (its .sha256 must sit next to it)
#   LRI_PKG_SHA256 LRI_SOURCES_SHA256   what submit.py verified; re-checked after staging
#   LRI_ROOT               campaign root on the shared filesystem (grids/, receipts/, logs/)
#   LRI_ENV                Python environment made by cluster/<site>/setup_env.sh
#   LRI_NODE_SCRATCH_BASE  node-local scratch base; the job works in <base>/job_<id>
#   LRI_N LRI_OVERSAMPLE LRI_RADIUS_COST   grid parameters
#   LRI_GRID_WORKERS       worker count, or "auto" (default): min(cores of one
#                          package, memory cap of the request)
#   LRI_PIN                none | package: bind the generator to one package's NUMA nodes
#   LRI_MODULES LRI_STRIPE LRI_CLEAN_STAGE  site details (see lib.sh)
# The temporary (6, M/2+1, K, K) complex array and the stored grid stay on node-
# local scratch. The published directory $LRI_ROOT/grids/<key>_src<tag>/ holds the
# .npy, its .json metadata, grid_receipt.json and SHA256SUMS; it appears
# atomically after verification.
set -o pipefail
umask 022
LRI_KIND=grid
die() { echo "FATAL($1): $2" >&2; exit "$1"; }
[[ -n "${SLURM_JOB_ID:-}" ]] || die 64 "submit with sbatch"
for v in LRI_PKG_TAR LRI_PKG_SHA256 LRI_SOURCES_SHA256 LRI_ROOT LRI_ENV LRI_NODE_SCRATCH_BASE LRI_N \
         LRI_OVERSAMPLE LRI_RADIUS_COST; do
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
lri_require_shipped_script grid_job.sbatch
lri_env_init
lri_check_binding

eval "$("$PY" "$PKG/cluster/sitekit/jobtools.py" grid-info --cutoff "$LRI_N" \
        --oversample "$LRI_OVERSAMPLE" --radius-cost "$LRI_RADIUS_COST")" || lri_die 64 "bad grid parameters"
DEST="$LRI_ROOT/grids/$GRID_DIR"
LRI_RECEIPT_EXTRA=("grid_key=$GRID_KEY" "grid_dir=$DEST")
# Published means complete and verified, array included (R003); corruption stops the job.
"$PY" "$PKG/cluster/sitekit/jobtools.py" published-check --kind grid --dir "$DEST" > /dev/null; rc=$?
case $rc in
    0) lri_log "grid already published and verified: $DEST (nothing to do)"; exit 0 ;;
    3) ;;
    *) lri_die 74 "published grid $DEST is incomplete or corrupt (see above); inspect it, do not overwrite" ;;
esac

WORKERS=${LRI_GRID_WORKERS:-auto}
if [[ "$WORKERS" == auto ]]; then
    WORKERS=$("$PY" "$PKG/cluster/sitekit/jobtools.py" grid-workers --cutoff "$LRI_N" --oversample "$LRI_OVERSAMPLE" \
              --mem-mb "${SLURM_MEM_PER_NODE:?}" --cores "$CORES") || lri_die 64 "cannot size grid workers"
fi
[[ "$WORKERS" =~ ^[0-9]+$ ]] && (( WORKERS >= 1 )) || lri_die 64 "bad grid worker count '$WORKERS' (memory request too small?)"
(( WORKERS <= CORES )) || lri_die 64 "LRI_GRID_WORKERS=$WORKERS exceeds the $CORES cores one process may use here"
PIN_CMD=()
if [[ "${LRI_PIN:-none}" == package ]]; then
    # The pool and the final FFT threads stay on package 0; memory is local-first
    # but may spill (the N=1024 generator needs more than one package's memory).
    PIN_CMD=(numactl --cpunodebind="$TOPO_PKG0_NODES")
fi
LRI_RECEIPT_EXTRA+=("workers=$WORKERS" "pin=${LRI_PIN:-none}" "numactl=${PIN_CMD[*]}")
NEED=$("$PY" "$PKG/cluster/sitekit/jobtools.py" scratch-need --kind grid --cutoff "$LRI_N" --oversample "$LRI_OVERSAMPLE") \
    || lri_die 64 "cannot estimate scratch need"
lri_require_scratch "$NEED"

lri_phase_begin compute
"${PIN_CMD[@]}" "$PY" "$PKG/cluster/sitekit/jobtools.py" monitor --label grid --watch "$STAGE" --interval 20 \
    --summary "$STAGE/monitor_grid.json" --samples "$STAGE/samples_grid.jsonl" -- \
    "$PY" "$PKG/cluster/run_task.py" prepare-grid --cutoff "$LRI_N" --oversample "$LRI_OVERSAMPLE" \
        --radius-cost "$LRI_RADIUS_COST" --cache-root "$STAGE/grid_cache" --workers "$WORKERS"
rc=$?
lri_phase_end $rc
(( rc == 0 )) || lri_die "$rc" "prepare-grid failed"

SRC="$STAGE/grid_cache/$GRID_KEY"
ARRAY=$("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["array"])' "$SRC/grid_receipt.json") \
    || lri_die 74 "no grid receipt"
lri_phase_begin hash
mkdir -p "$STAGE/publish" || lri_die 73 "cannot create publish dir"
for f in "$ARRAY" "${ARRAY%.npy}.json" grid_receipt.json; do
    mv "$SRC/$f" "$STAGE/publish/$f" || lri_die 74 "missing $SRC/$f"
done
lri_write_sums "$STAGE/publish"; rc=$?
lri_phase_end $rc
(( rc == 0 )) || lri_die 74 "cannot checksum the grid"

lri_phase_begin publish
lri_publish_dir "$STAGE/publish" "$DEST" "${LRI_STRIPE:-0}"; rc=$?
lri_phase_end $rc
(( rc == 0 )) || lri_die 74 "publishing to $DEST failed"
du -sh "$DEST"
lri_log "grid ready: $DEST"
