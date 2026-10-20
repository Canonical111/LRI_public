#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CXX=${CXX:-g++}
case ${1:-} in ""|--with-fast) ;; *) echo "Usage: build.sh [--with-fast]" >&2; exit 2;; esac
for d in 2 3; do
  "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d "$HERE/stratified.cpp" -lquadmath -o "$HERE/stratified_d$d"
  "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d -DSINGLE_ORDER=1 "$HERE/stratified.cpp" -lquadmath -o "$HERE/stratified_d${d}_single"
  "$CXX" -O3 -std=c++17 -fopenmp -fPIC -shared -DSPATIAL_D=$d "$HERE/bridge.cpp" -lquadmath -o "$HERE/bridge_d$d.so"
  if [ "${1:-}" = --with-fast ]; then
    "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d -DFAST_INITIAL "$HERE/stratified.cpp" -lquadmath -o "$HERE/stratified_d${d}_fast"
    "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d -DFAST_INITIAL -DSINGLE_ORDER=1 "$HERE/stratified.cpp" -lquadmath -o "$HERE/stratified_d${d}_single_fast"
    "$CXX" -O3 -std=c++17 -fopenmp -fPIC -shared -DSPATIAL_D=$d -DFAST_INITIAL "$HERE/bridge.cpp" -lquadmath -o "$HERE/bridge_d${d}_fast.so"
  fi
done
