"""Per-chain progress of a frozen campaign (read-only).

Usage: python status.py --spec SPEC [--sacct]
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from common import SpecError,chain_dir,check_predecessor,claims_under,load_spec,sacct_state,steps,verify_runtime


def chain_status(spec,chain):
    rows=[];cache={}
    for s in steps(spec,chain):
        out=Path(s['output']);cp=Path(s['output']+'.checkpoint.json')
        if out.exists():
            try:
                _,vsha=check_predecessor(spec,{'chain':chain,'L':s['L'],'nz':s['nz']},cache=cache)
                data=out.read_bytes()
                if hashlib.sha256(data).hexdigest()!=vsha:raise SpecError('record changed after validation')
                r=json.loads(data);st=f"ok D={r['Delta_thermal']:.9f} {r['elapsed_total_seconds']:.0f}s"
            except (SpecError,ValueError,KeyError,TypeError,OSError) as e:st=f'INVALID ({e})'
        elif cp.exists():
            try:
                h=json.loads(cp.read_text()).get('history',[]);st=f"checkpoint it={len(h)} res={h[-1]['residual']:.1e}" if h else 'checkpoint'
            except (ValueError,TypeError,AttributeError,KeyError,IndexError,OSError):st='checkpoint (unreadable/malformed)'
        else:st='-'
        rows.append((s['role'],s['L'],s['nz'],st))
    return rows


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',required=True);ap.add_argument('--sacct',action='store_true')
    a=ap.parse_args(argv);spec=load_spec(a.spec);verify_runtime(spec)
    sub={}
    for fname,key in (('SUBMITTED.jsonl','job'),('CONTINUATIONS.jsonl','continuation')):   # F24
        sf=Path(spec['root'])/fname
        if sf.exists():
            for l in sf.read_text().splitlines():
                if l.strip():r=json.loads(l);sub.setdefault(r['chain'],[]).append(str(r[key]))
    for c in sub:sub[c]=sorted(set(sub[c]),key=int)
    for c in spec['chains']:
        cdir=chain_dir(spec,c);states=sorted((cdir/'state').glob('*.json'),key=lambda q:q.stat().st_mtime) if (cdir/'state').exists() else []
        last={}
        if states:
            import continuation
            last=continuation.read_state(states[-1]) or {'status':f'INVALID ({states[-1].name} malformed)'}
        jobs=sub.get(c,[])
        js=f" jobs {jobs}"+(f" last={sacct_state(jobs[-1],tries=1)}" if a.sacct and jobs else '')
        print(f"== {c} x={spec['chains'][c]['x']} state={last.get('status','-')}{js}")
        for role,L,nz,st in chain_status(spec,c):print(f"   {role:5s} L={L:2d} nz={nz:2d} {st}")
        for cl in claims_under(cdir) if cdir.exists() else []:print(f'   claim {cl}')
    return 0


if __name__=='__main__':raise SystemExit(main())
