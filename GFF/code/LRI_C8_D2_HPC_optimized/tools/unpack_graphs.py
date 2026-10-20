#!/usr/bin/env python3
"""Extract checked graph text from the shipped packs for standalone native runs."""
import argparse
import hashlib
from pathlib import Path
from common import ROOT,load

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('destination',type=Path)
    ap.add_argument('--sector',choices=['free','power'],required=True)
    ap.add_argument('--loop',type=int,choices=range(3,9),required=True)
    ap.add_argument('--ids',help='Comma-separated IDs; omit to extract every active graph at this loop')
    args=ap.parse_args()
    rows=load(ROOT/'inputs/inventory.json')[args.sector][str(args.loop)]
    available={r['id']:r for r in rows}
    ids=sorted(available) if args.ids is None else [int(i)for i in args.ids.split(',')]
    if len(set(ids))!=len(ids) or not set(ids)<=set(available):raise ValueError('Invalid graph IDs')
    out=args.destination/f'L{args.loop}';out.mkdir(parents=True,exist_ok=True)
    with (ROOT/f'inputs/packs/{args.sector}_L{args.loop}.pack').open('rb') as stream:
        for gid in ids:
            row=available[gid];stream.seek(row['offset']);payload=stream.read(row['length'])
            if len(payload)!=row['length'] or hashlib.sha256(payload).hexdigest()!=row['sha256']:
                raise ValueError(f'Graph checksum mismatch: {gid}')
            target=out/f'G{gid}.txt'
            if target.exists():
                if target.read_bytes()!=payload:raise FileExistsError(f'Different existing graph: {target}')
            else:target.write_bytes(payload)
    print(f'Extracted {len(ids)} {args.sector} L{args.loop} graphs to {out.resolve()}')

if __name__=='__main__':main()
