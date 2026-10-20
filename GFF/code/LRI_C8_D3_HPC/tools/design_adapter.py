#!/usr/bin/env python3
"""A read-only view of a merged C8(3) pilot campaign in the layout the vendored design tool reads (PLAN E.5, H6).

  design_adapter.py view RUN --out VIEW

C62d's design.py (vendored at the sha256 of HANDOFF_design.json once H6 is delivered) reads another package's campaign
through the campaign interface: manifest.json, the group configs at the manifest's pins, every merged.json and its
tables (graph_replicates.csv, graph_tails.csv, graph_costs.csv), the inputs manifest, inventory and two-loop file, and
the ledger accounting. When tests/check_design_interface.py finds an incompatibility, this adapter fixes it by writing
VIEW: independent byte copies of exactly those files (never hard links: each copy is a new file, made read-only, so the
campaign's own files keep their permissions; S3-011), each copy verified against the campaign's pins (the manifest's,
the configs', merged.json's table digests, the cost model's and the inputs manifest's), and view.json mapping each to its
source and sha256. It changes no number and opens nothing of a scheduling basis (prior_cost_model.json,
synthetic_cost_model.json, tools/bootstrap_proxy.json; D.5: production.verify_base(scheduling_copies=False), S3-013).
A pilot_subset campaign (PA, PC) is refused (65) before any group data is read (R01): the design reads PF only.
"""
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import Refuse,digest,dump
import production as prod

def view(run:Path,out:Path)->dict:
    run=Path(run).resolve();out=Path(out).resolve()
    m,I,mh,_=prod.verify_base(run,check_executable=False,accept_tool_change=True,scheduling_copies=False)
    if m.get('campaign_role')=='pilot_subset':raise Refuse(65,'design_adapter.py: a pilot_subset campaign (PA or PC) has no design input; its merge ends in `pilot_report.py subset-check` (R01)')
    if out.exists():raise FileExistsError(f'{out} exists')
    files={'manifest.json':run/'manifest.json'};pins={'manifest.json':mh}
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name']);d=prod.validate_merged(p,cfg,m,mh);pins[f'groups/{g["name"]}/config.json']=g['sha256']
        for f in ('config.json','merged.json','graph_replicates.csv','graph_tails.csv','graph_costs.csv','graph_promotions.csv'):
            files[f'groups/{g["name"]}/{f}']=p/f
            if f.endswith('.csv'):pins[f'groups/{g["name"]}/{f}']=d[f'{f[:-4]}_sha256']   # merged.json's table digests
        if d.get('graph_prefixes_sha256'):files[f'groups/{g["name"]}/graph_prefixes.csv']=p/'graph_prefixes.csv';pins[f'groups/{g["name"]}/graph_prefixes.csv']=d['graph_prefixes_sha256']
    if m.get('cost_model_sha256'):files['cost_model.json']=run/'cost_model.json';pins['cost_model.json']=m['cost_model_sha256']
    for n in ('manifest.json','inventory.json','two_loop.json'):files[f'inputs/{n}']=I.where(n)
    pins['inputs/manifest.json']=m['inputs_manifest_sha256'];pins.update({f'inputs/{n}':I.sha(n)for n in ('inventory.json','two_loop.json')})
    out.mkdir(parents=True);rec={}
    for rel,src in files.items():
        dst=out/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(src,dst)   # a new file, never a hard link (S3-011): the chmod below must not reach the campaign's inode
        h=digest(dst)
        if rel in pins and h!=pins[rel]:raise ValueError(f'{src} changed while the view was made: its copy differs from the campaign\'s pin')
        rec[rel]={'source':str(src),'sha256':h}
    doc={'schema':'c8-d3-design-view-1','campaign':str(run),'manifest_sha256':mh,'files':rec,'note':'read-only view; no number changed'}
    dump(out/'view.json',doc)
    for p in out.rglob('*'):
        if p.is_file():p.chmod(0o444)
    return doc

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);s=p.add_subparsers(dest='cmd',required=True)
    q=s.add_parser('view');q.add_argument('run',type=Path);q.add_argument('--out',type=Path,required=True);a=p.parse_args(argv)
    try:d=view(a.run,a.out)
    except Refuse as e:print(f'design_adapter: {e}',file=sys.stderr);return e.code
    except (ValueError,OSError)as e:print(f'design_adapter: {e}',file=sys.stderr);return 1
    print(json.dumps({'view':str(a.out),'files':len(d['files'])}));return 0
if __name__=='__main__':sys.exit(main())
