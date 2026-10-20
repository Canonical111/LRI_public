#!/usr/bin/env python3
"""Write tools/bootstrap_proxy.json (schema c8-d3-bootstrap-proxy-1; PLAN B, D.5, A-ORC-3).

The first-sweep bootstrap basis bounds task lengths of the non-measured plan roles (cost_sweep, a bootstrap
cost_refresh, flag_check, validation) only. Its seconds per point are a WORST-CASE PROXY, never a cost:

  s(A) = 3 (c0 + a_ld A + q0 + a_q A + mp0 + a_mp A)      (q = mp = 1: every point promoted to binary128 and GMP)

with A = products + addends of the graph (inventory inspect fields) and the six coefficients of the RECON's NNLS
tier law, line 6 of reference/c8d3_recon/out/l8cost.log (cd3:l8cost:6; F22: c0 7.35 us, ld 1.131 ns/op, binary128
14.7 us + 25.48 ns/op, GMP 515 us + 63.52 ns/op). The log is read only after its bytes match the sha256 that
reference/SHA256SUMS_c8 records for it, and only those bytes are parsed. Nothing under .git is opened and no git
process is started, so the generator works in a `git archive` export.

  bootstrap_proxy.py [--check] [--output FILE]     (--check: compare with the committed file byte for byte)
"""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCHEMA='c8-d3-bootstrap-proxy-1'
SOURCE='reference/c8d3_recon/out/l8cost.log'
SUMS='reference/SHA256SUMS_c8'
OUT='tools/bootstrap_proxy.json'
LABEL='preliminary_proxy (worst-case NNLS tier law of the RECON at q = mp = 1, x3; not a measurement)'
LAW=re.compile(r'c0 ([0-9.]+) us, ld ([0-9.]+) ns/op, quad ([0-9.]+) us \+ ([0-9.]+) ns/op, GMP ([0-9.]+) us \+ ([0-9.]+) ns/op')

def pinned_sha256(root:Path)->str:
    for line in (root/SUMS).read_text().splitlines():
        f=line.split()
        if len(f)>=2 and f[1]==SOURCE:return f[0]
    raise ValueError(f'{SUMS} has no entry for {SOURCE}')

def build(root:Path=ROOT)->bytes:
    data=(root/SOURCE).read_bytes();want=pinned_sha256(root)
    if hashlib.sha256(data).hexdigest()!=want:raise ValueError(f'Checksum mismatch: {SOURCE} is not the file {SUMS} pins ({want[:12]}...)')
    lines=data.decode().splitlines()
    m=LAW.search(lines[5])if len(lines)>=6 else None
    if not m:raise ValueError(f'{SOURCE} line 6 does not hold the NNLS tier law')
    c0,ld,q0,aq,mp0,amp=(float(x)for x in m.groups())
    doc={'schema':SCHEMA,'label':LABEL,'source':{'path':SOURCE,'sha256':want,'line':6,'text':lines[5].strip()},
         'coefficients_seconds':{'c0':c0*1e-6,'a_ld':ld*1e-9,'q0':q0*1e-6,'a_q':aq*1e-9,'mp0':mp0*1e-6,'a_mp':amp*1e-9},
         'factor':3,'op_count':'A = products + addends (inputs/inventory.json inspect fields)',
         'formula':'s(A) = 3 (c0 + a_ld A + q0 + a_q A + mp0 + a_mp A) seconds per point (q = mp = 1, the worst case)',
         'use':'task-length bound, shard and heaviest-first order of bootstrap-basis plans only (cost_sweep, cost_refresh, flag_check, validation); never a cost'}
    return (json.dumps(doc,indent=1,sort_keys=True)+'\n').encode()

def seconds_per_point(doc:dict,A:int)->float:
    c=doc['coefficients_seconds']
    return doc['factor']*(c['c0']+c['a_ld']*A+c['q0']+c['a_q']*A+c['mp0']+c['a_mp']*A)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--check',action='store_true');p.add_argument('--output',type=Path);a=p.parse_args(argv)
    try:data=build()
    except (ValueError,OSError)as e:print(f'bootstrap_proxy: REFUSED: {e}',file=sys.stderr);return 1
    out=a.output or ROOT/OUT
    if a.check:
        same=out.exists()and out.read_bytes()==data
        print(json.dumps({'file':str(out),'identical':same}));return 0 if same else 1
    out.write_bytes(data);print(json.dumps({'file':str(out),'sha256':hashlib.sha256(data).hexdigest()}));return 0
if __name__=='__main__':sys.exit(main())
