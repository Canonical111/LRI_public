#!/bin/bash
# quick local per-point cost benchmark: bench_local.sh KIND n N shifts threads [s0] [etarget] [geom] [prec]
ROOT=$(cd "$(dirname "$0")/.." && pwd)
K=$1; n=$2; N=${3:-1009}; SH=${4:-2}; TH=${5:-8}; S0=${6:-0}; ET=${7:-1}; GEOM=${8:-angular}; PREC=${9:-auto}
if [ "$GEOM" = full ]; then d=$n; else d=$((n-2)); fi
A=$(python3 -c "import sys; sys.path.insert(0,'$ROOT/py'); from lri_moments import korobov; print(korobov($N,$d))")
CFG=$(mktemp /tmp/lri_bench_XXXXXX)
cat > $CFG <<EOC
n $n
type $K
geom $GEOM
s0 $S0
etarget $ET
transform 3
prec $PREC
N $N
shifts $SH
threads $TH
korobov $A
channel D0
term 1 0 0 0 0 0 0 0
EOC
$ROOT/bin/lri_engine $CFG > $CFG.json || exit 1
python3 - $CFG.json $N $SH <<'EOP'
import json,sys,statistics as st
r=json.load(open(sys.argv[1])); N=int(sys.argv[2]); SH=int(sys.argv[3]); ch=r['channels']['D0']
cpus=[s['cpu'] for s in ch['per_sector']]
print('n=%d %s wall %.1fs cpu %.1fs sectors %d  us/pt mean %.1f max %.1f'%(r['n'],r['type'],r['wall_seconds'],r['cpu_seconds'],len(cpus),1e6*st.mean(cpus)/(SH*N),1e6*max(cpus)/(SH*N)))
print(ch['orders'], ['%.10g'%v for v in ch['value']], ['%.1e'%e for e in ch['err']])
EOP
