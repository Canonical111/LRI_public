#!/bin/bash
# Build the cluster engine with a build identity = sha256 of the sources and the compile command (fix round 1, MSC-007).
# usage: build_engine.sh OUTPUT_BINARY [extra compiler flags, e.g. -DUSE_DOUBLE]
out=$1; shift
cd "$(dirname "$0")" || exit 1
if command -v sha256sum >/dev/null; then SHA="sha256sum"; else SHA="shasum -a 256"; fi
if [ "$(uname)" = "Darwin" ]; then
  CXX=c++; OMP="-Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib -lomp"; ARCH=""
else
  CXX=g++; OMP="-fopenmp"; ARCH="-march=x86-64-v3"
fi
FLAGS="-O3 $ARCH -ffp-contract=off -std=c++17 -Wall -Wextra $* $OMP"
id=$( (cat cluster_engine.cpp dd.h sha256.h; echo "$CXX $FLAGS") | $SHA | cut -c1-16)
$CXX $FLAGS -DBUILD_ID="\"$id\"" -o "$out" cluster_engine.cpp || { echo "build failed" >&2; exit 1; }
echo "$id"
