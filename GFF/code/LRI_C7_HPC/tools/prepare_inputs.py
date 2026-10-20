#!/usr/bin/env python3
"""Create byte-offset indices and portable decimal copies of native quadrature weights.
Original files are never changed. Run once, not separately on every cluster worker.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, sys
from pathlib import Path

def atomic_text(path: Path, text: str) -> None:
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(text);tmp.replace(path)

def main() -> None:
    ap=argparse.ArgumentParser();ap.add_argument('inputs',type=Path);ap.add_argument('--portable-weights',action='store_true');a=ap.parse_args()
    records={}
    for file in sorted(a.inputs.glob('L*_coord.txt')):
        offsets=[]
        with file.open('rb') as f:
            L,ng=map(int,f.readline().split())
            for expected in range(ng):
                offsets.append(f.tell());row=f.readline().split()
                if len(row)!=6 or int(row[0])!=expected:raise ValueError(f'Invalid graph header {file}:{expected}')
                for _ in range(int(row[5])):
                    if not f.readline():raise ValueError(f'Truncated {file}')
            if f.read().strip():raise ValueError(f'Extra data in {file}')
        atomic_text(Path(str(file)+'.idx'),f'C7IDX1 {file.stat().st_size} {ng}\n'+'\n'.join(map(str,offsets))+'\n')
        records[file.name]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'graphs':ng,'loops':L}
    if a.portable_weights:
        import numpy as np
        if np.dtype(np.longdouble).itemsize!=16 or np.finfo(np.longdouble).nmant!=63 or sys.byteorder!='little':
            raise RuntimeError('Native files are x86 extended precision; use regenerate_weights.py on this platform.')
        for file in sorted(a.inputs.glob('cw_L*_N*.bin')):
            values=np.fromfile(file,dtype=np.longdouble)
            text='C7WEIGHTS1 '+str(len(values))+'\n'+'\n'.join(np.format_float_scientific(x,unique=True,trim='k') for x in values)+'\n'
            atomic_text(file.with_suffix('.txt'),text)
            records[file.name]={'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'source':'x86 80-bit extended; 16-byte storage','values':len(values)}
    atomic_text(a.inputs/'hpc_input_manifest.json',json.dumps(records,indent=2)+'\n')
    print('Indexed',len([k for k in records if k.endswith('_coord.txt')]),'inventories; original inputs unchanged.')
if __name__=='__main__': main()
