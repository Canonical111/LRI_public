#!/usr/bin/env bash
# Maintainer tool: build the hosted bundles of GFF/data/C8_3_check from the original package working tree (the
# unpacked LRI_C8_D3_HPC_optimized.zip plus the cluster layer, git main) and write public/data_bundles.sha256.
#   usage: make_data_bundles.sh <package working tree> <output directory>
# Needs GNU tar and xz (Linux). Deterministic: sorted names, fixed owner and mtime. About 9 GB are read.
set -euo pipefail
export LC_ALL=C
SRC=$(cd "${1:?package working tree}" && pwd); OUT=$(mkdir -p "${2:?output directory}" && cd "$2" && pwd)
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$SRC"
# Every bundled file must match the package's own checksum list, and the tracked regeneration inputs commit d5deeb9.
grep -E '  (inputs/(free|power)/|results/pilot_20261008/|regeneration/|inputs/complete_inventory_L)' SHA256SUMS \
  | sha256sum -c --quiet -
# In a git work tree the regeneration inputs must also equal commit d5deeb9; a copy without git (the production tree on
# the cluster, used for the published bundles) relies on the SHA256SUMS check above, which lists the same files.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git diff --quiet d5deeb9 -- regeneration inputs/complete_inventory_L3.json inputs/complete_inventory_L4.json \
    inputs/complete_inventory_L5.json inputs/complete_inventory_L6.json inputs/complete_inventory_L7.json \
    inputs/complete_inventory_L8.json
fi
# Every bundled file must be listed in SHA256SUMS (no stray files in the bundled folders).
comm -13 <(grep -oE '  (inputs/(free|power)/|results/pilot_20261008/|regeneration/).*' SHA256SUMS | sed 's/^  //' | sort) \
  <(find inputs/free inputs/power results/pilot_20261008 regeneration -type f ! -name .DS_Store | sort) \
  | { if read -r x; then echo "make_data_bundles: not in SHA256SUMS: $x" >&2; exit 1; fi; }
pack() {   # pack NAME PATH...
  local name=$1; shift
  tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='2026-10-11 00:00:00Z' --exclude=.DS_Store \
      -cf - "$@" | xz -9 -T0 > "$OUT/$name"
}
pack c8opt_inputs_free.tar.xz inputs/free
pack c8opt_inputs_power.tar.xz inputs/power
pack c8opt_pilot_20261008.tar.xz results/pilot_20261008
pack c8opt_regeneration.tar.xz regeneration inputs/complete_inventory_L3.json inputs/complete_inventory_L4.json \
  inputs/complete_inventory_L5.json inputs/complete_inventory_L6.json inputs/complete_inventory_L7.json \
  inputs/complete_inventory_L8.json
cd "$OUT"
sha256sum c8opt_inputs_free.tar.xz c8opt_inputs_power.tar.xz c8opt_pilot_20261008.tar.xz c8opt_regeneration.tar.xz \
  | tee "$HERE/data_bundles.sha256"
ls -l c8opt_*.tar.xz
