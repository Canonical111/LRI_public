#!/bin/sh
# args: d tau r dps Lmax K b Wref ; prints JSON with W_r(d;b) from the lattice-mode route vs reference
d=$1; tau=$2; r=$3; dps=$4; L=$5; K=$6; b=$7; W=$8
python3 rmode_check.py $d $tau $r $dps $L $K | python3 -c "
import json, sys, mpmath as mp
mp.mp.dps = 30
o = json.loads(sys.stdin.read())
d, tau, r = mp.mpf('$d'), mp.mpf('$tau'), $r; q = d/4
pref = (mp.gamma(2*q)*mp.gamma(q+tau/2)/mp.gamma(q-tau/2))**r
Wm = pref*mp.mpmathify(o['W_from_modes'].replace(' ','')).real
Wr = mp.mpf('$W')
print(json.dumps(dict(d='$d', b='$b', r=r, W_modes=mp.nstr(Wm, 22), W_ref=mp.nstr(Wr, 22), rel=mp.nstr(abs(Wm-Wr)/Wr, 3), top_over_max=o['rel_top_mode'])))
"
