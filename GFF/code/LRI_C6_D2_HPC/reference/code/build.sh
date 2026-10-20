#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
CXX=${CXX:-g++}
for d in 2 3; do
 "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d experiment.cpp -lquadmath -o experiment_d$d
 "$CXX" -O3 -std=c++17 -fopenmp -DSPATIAL_D=$d -DREFERENCE_EVAL experiment.cpp -lquadmath -o reference_d$d
 "$CXX" -O3 -std=c++17 -fopenmp -shared -fPIC -DSPATIAL_D=$d bridge.cpp -lquadmath -o bridge_d$d.so
done
