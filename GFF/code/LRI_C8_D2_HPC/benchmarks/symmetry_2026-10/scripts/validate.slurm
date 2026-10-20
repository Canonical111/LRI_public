#!/bin/bash
#SBATCH -p amdq
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -c 64
#SBATCH --exclusive
#SBATCH --mem=240G
#SBATCH -t 10:00:00
#SBATCH -J c7d2-validate
#SBATCH -o <SCRATCH>/c7d2_fix/logs/%x_%j.out
# C7(2) fix loop, symmetry validation of 572a956 against fb64c47: D1 byte identity, A-L18 Boost 1.86, make test, make test-full, --strict.
set -eo pipefail
source $HOME/c7d2_prod/env.sh
set -u
W=<SCRATCH>/c7d2_fix; E=$W/evidence; B186=$W/boost_1_86_0
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
unset CPPFLAGS CXXFLAGS LDFLAGS LDLIBS OPTFLAGS
echo "host $(hostname) job $SLURM_JOB_ID $(date -Is)"; lscpu | grep 'Model name'; g++ --version | head -1; python3 --version
step(){ echo "=== $1 start $(date -Is)"; }
step D1
(cd $W/base  && make -n -B bin/c7d2_decimal bin/c7d2_gmp) > $E/make_n_base.txt 2>&1 || true
(cd $W/final && make -n -B bin/c7d2_decimal bin/c7d2_gmp) > $E/make_n_final.txt 2>&1 || true
(cd $W/base  && make clean >/dev/null && make -j8 && make -j8 gmp && sha256sum bin/c7d2_decimal bin/c7d2_gmp) > $E/d1_base.txt 2>&1
(cd $W/final && make clean >/dev/null && make -j8 && make -j8 gmp && sha256sum bin/c7d2_decimal bin/c7d2_gmp && cat bin/*.build.json) > $E/d1_final.txt 2>&1
tail -2 $E/d1_base.txt; grep -E "c7d2_(decimal|gmp)$" $E/d1_final.txt
if diff <(cd $W/base && sha256sum bin/c7d2_decimal bin/c7d2_gmp) <(cd $W/final && sha256sum bin/c7d2_decimal bin/c7d2_gmp); then echo D1_IDENTICAL; else echo D1_DIFFERENT; fi | tee $E/d1_verdict.txt
echo "2026 production binaries: decimal e696d7f3..., gmp 7e3c8c92..." >> $E/d1_verdict.txt
step A-L18
echo '#include <boost/version.hpp>' | g++ -I$B186 -E -dM -x c++ - | grep BOOST_LIB_VERSION | tee $E/boost186.txt
for t in base final; do for b in decimal gmp; do
  if [ $b = gmp ]; then D=-DC7_USE_GMP; L="-lquadmath -lgmp"; else D=; L=-lquadmath; fi
  if g++ -I$B186 -O3 -std=c++17 -fopenmp -ffp-contract=off -fno-fast-math $D $W/$t/src/c7d2_integrate.cpp $L -o /tmp/b186_${t}_$b >$E/boost186_${t}_$b.log 2>&1
  then echo "$t $b: compiles"; else echo "$t $b: FAILS"; fi; done; done | tee -a $E/boost186.txt
cd $W/final
step make_test;      make test      > $E/make_test.log 2>&1      && echo "make test PASS"      || echo "make test FAIL rc=$?"
step make_test_full; make test-full > $E/make_test_full.log 2>&1 && echo "make test-full PASS" || echo "make test-full FAIL rc=$?"
step strict; python3 -B tools/verify_delivery.py --strict > $E/verify_strict.json 2>&1 && echo "strict PASS" || echo "strict FAIL"
echo "=== done $(date -Is)"
