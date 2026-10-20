#!/usr/bin/env python3
"""Legacy seed derivation reproduces the archived fresh d=3 campaign-a L6 stream (pure helpers; no plan, no binary).

derive_seeds(882040358,'a',6,'legacy') must give the archived native seed 882048032 and a net seed from which
make_net regenerates reference/inputs/new_a_d3_L6_net.bin byte for byte. The hashed default must differ.
"""
from __future__ import annotations
import filecmp,json,struct,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from production import derive_seeds,make_net

def run():
    archived=ROOT/'reference/inputs/new_a_d3_L6_net.bin';B,dim,bits=struct.unpack('<III',archived.read_bytes()[:12])
    legacy=derive_seeds(882040358,'a',6,'legacy')
    if legacy['native']!=882048032:raise AssertionError(f'legacy native seed {legacy["native"]} != 882048032')
    with tempfile.TemporaryDirectory(prefix='c6_replay_')as td:
        net=Path(td)/'net.bin';info=make_net(net,B,dim,bits,legacy['net'])
        if not filecmp.cmp(net,archived,shallow=False):raise AssertionError('legacy net differs from the archived new_a d3 L6 net')
    hashed=derive_seeds(882040358,'a',6,'hashed')
    if hashed['native']==legacy['native']or hashed['net']==legacy['net']:raise AssertionError('hashed scheme reproduces legacy seeds')
    others=[derive_seeds(882040358,c,L,'hashed')for c in 'ab' for L in range(3,7)]
    if len({s['native']for s in others})!=8 or len({s['net']for s in others})!=8:raise AssertionError('hashed group seeds collide')
    return {'status':'passed','test':'archived_replay','net':{'B':B,'dim':dim,'bits':bits,'sha256':info['sha256']},'legacy_native_seed':legacy['native'],'hashed_native_seed':hashed['native']}
if __name__=='__main__':print(json.dumps(run(),indent=2))
