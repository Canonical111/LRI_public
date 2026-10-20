#!/bin/bash
# Local render (author's instruction: figures are rendered on the Mac) for the C8(1)-final update (2026-10-13).
#   LRI_C8_1=final    bash update_2026-10-13/C8_1_ext/render_local.sh [comparisons] [dispersion] [2d3d]
#   LRI_C8_1=previous bash update_2026-10-13/C8_1_ext/render_local.sh comparisons dispersion   (regression render into
#                                                                    C8_1_ext/repro_previous/figures/)
# Default plots: comparisons dispersion 2d3d (final) or comparisons dispersion (previous). Uses the package wrapper
# run_plot.wls, which closes its subkernels and exits; each wrapper PID is logged and the wrapper is waited for, so no
# kernel outlives the script (audit afterwards with the wolframscript-no-zombies skill's wolfram_ps.sh).
# plot_lri_2d3d.wl does not depend on C8(1) and has no switch; it always writes figures/06_curves_2d3d*.
set -u
PKG="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$PKG"
mode="${LRI_C8_1:-final}"; export LRI_C8_1="$mode"
logdir=update_2026-10-13/C8_1_ext/logs; [ "$mode" = previous ] && logdir=update_2026-10-13/C8_1_ext/repro_previous/logs
mkdir -p "$logdir"
if [ $# -gt 0 ]; then plots=("$@"); elif [ "$mode" = previous ]; then plots=(comparisons dispersion); else plots=(comparisons dispersion 2d3d); fi
status=0
for name in "${plots[@]}"; do
  case "$name" in
    comparisons) plot=plot_lri_comparisons.wl ;; dispersion) plot=plot_lri_dispersion.wl ;;
    2d3d) [ "$mode" = previous ] && { echo "2d3d has no previous mode" >&2; continue; }; plot=plot_lri_2d3d.wl ;;
    *) echo "unknown plot $name" >&2; exit 64 ;;
  esac
  log=$logdir/render-$mode-${plot%.wl}.out
  echo "=== $plot LRI_C8_1=$mode start $(date '+%Y-%m-%dT%H:%M:%S%z') host $(hostname -s)" >> "$log"
  wolframscript -file "$PKG/run_plot.wls" "$PKG/$plot" >> "$log" 2>&1 &
  pid=$!
  echo "$(date '+%Y-%m-%dT%H:%M:%S%z') wrapper pid $pid for $plot (LRI_C8_1=$mode)" >> "$logdir/render-pids.txt"
  wait "$pid"; rc=$?
  echo "=== $plot exit $rc $(date '+%Y-%m-%dT%H:%M:%S%z')" >> "$log"
  echo "$plot exit $rc (log $log)"
  [ "$rc" -eq 0 ] || status=$rc
done
exit $status
