#!/usr/bin/env python3
"""Verify delivered SHA-256 hashes or just byte-exact historical archives.

Use --archives-only after running checks that update derived files and logs.
The full manifest describes the delivered snapshot, not a modified work tree.
"""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--archives-only',action='store_true');p.add_argument('--report',type=Path)
    args=p.parse_args();root=args.root.resolve()
    if args.archives_only:
        entries=json.loads((root/'provenance/original_archive_hashes.json').read_text())
    else:
        m=root/'MANIFEST.sha256'
        if not m.exists():p.error('MANIFEST.sha256 not found; use --archives-only for a development tree.')
        entries=[]
        for line in m.read_text().splitlines():
            digest,name=line.split('  ',1);entries.append({'sha256':digest,'path':name})
    failed=[]
    for item in entries:
        q=(root/item['path']).resolve()
        if not q.is_relative_to(root):raise ValueError('Unsafe path '+item['path'])
        if not q.is_file():failed.append({'path':item['path'],'reason':'missing'});continue
        digest=hashlib.sha256(q.read_bytes()).hexdigest()
        if digest!=item['sha256']:failed.append({'path':item['path'],'reason':'hash mismatch'})
    out={'status':'PASS' if not failed else 'FAIL','checked_files':len(entries),'scope':'original archives' if args.archives_only else 'delivered file snapshot','failures':failed}
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
    if failed:sys.exit(1)
if __name__=='__main__':main()
