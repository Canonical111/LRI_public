#!/bin/bash
# Recompute every C8(1)-dependent 1d input of the resummation package for one mode of the C8(1) switch (2026-10-13).
#   LRI_C8_1=final    bash update_2026-10-13/C8_1_ext/run_chain.sh   -> outputs in update_2026-10-13/C8_1_ext/
#   LRI_C8_1=previous bash update_2026-10-13/C8_1_ext/run_chain.sh   -> outputs in update_2026-10-13/C8_1_ext/repro_previous/
# (LRI_C8_1_OUT overrides the output root.) Run from anywhere. Every stage takes seconds (about 1.5 min in total on the
# Mac), so it runs locally; no figure is rendered here (see render_local.sh). Logs: <output root>/logs/chain-<mode>.log.
set -euo pipefail
PKG="$(cd "$(dirname "$0")/../.." && pwd)"
mode="${LRI_C8_1:-final}"; export LRI_C8_1="$mode"
root=$(python3 -B -c "import sys; sys.path.insert(0, '$PKG/update_2026-10-13/C8_1_ext'); import c8_1_switch as S; print(S.out_root())")
mkdir -p "$root/logs"; log="$root/logs/chain-$mode.log"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
{
echo "=== chain mode=$mode root=$root host=$(hostname -s) start $(date '+%Y-%m-%dT%H:%M:%S%z')"
python3 -B -c 'import sys,numpy,scipy,mpmath,matplotlib; print(sys.version.split()[0], "numpy", numpy.__version__, "scipy", scipy.__version__, "mpmath", mpmath.__version__, "matplotlib", matplotlib.__version__)'
run() { echo "--- $1 $(date '+%H:%M:%S')"; (cd "$(dirname "$PKG/$1")" && python3 -B -u "$PKG/$1"); }
run update_2026-10-12/sr_endpoint.py
run update_2026-10-12/prepare_fig05_K8.py
run update_2026-10-12/make_fig.py
run update_2026-10-13/C8_1_ext/instanton_mismatch/analyze.py
run update_2026-10-12/pipeline_K8/run_curve.py
run update_2026-10-12/pipeline_K8/run_ablation.py
run update_2026-10-12/pipeline_K8/run_c9.py
run update_2026-10-12/pipeline_K8/run_precision.py
run update_2026-10-12/pipeline_K8/run_refs.py
run update_2026-10-12/pipeline_K8/run_c9_cbK8ref.py
run update_2026-10-12/pipeline_K8/make_plot_data.py
run update_2026-10-13/make_fig04_c9_inputs.py
run update_2026-10-13/prepare_fig05_gff_only.py
echo "=== chain mode=$mode done $(date '+%Y-%m-%dT%H:%M:%S%z')"
} 2>&1 | tee "$log"
