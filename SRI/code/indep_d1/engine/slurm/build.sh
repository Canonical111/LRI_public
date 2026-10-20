#!/bin/bash
# Build the engine on a Linux cluster node (portable x86-64-v3 / AVX2, no AVX-512).
#   bash slurm/build.sh                                   -> bin/lri_engine (v2, src/lri_engine.cpp)
#   SRC=legacy/lri_engine_phase1.cpp OUT=bin/lri_engine_phase1 bash slurm/build.sh   (phase-1 engine, regression)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
CXX=${CXX:-g++}
SRC=${SRC:-src/lri_engine.cpp}
OUT=${OUT:-bin/lri_engine}
mkdir -p "$ROOT/bin"
$CXX -O3 -march=x86-64-v3 -std=c++17 -fopenmp -ffp-contract=off -I"$ROOT/src" "$ROOT/$SRC" -o "$ROOT/$OUT.new.$$"
mv -f "$ROOT/$OUT.new.$$" "$ROOT/$OUT"   # atomic: running jobs keep the old inode
echo "built $ROOT/$OUT from $SRC ($(md5sum "$ROOT/$SRC" | cut -c1-12)) with $($CXX --version | head -1); binary $(md5sum "$ROOT/$OUT" | cut -c1-12)"
