"""Collect accepted campaign records into CSV tables, with branch/convergence flags.

Usage: python collect.py --spec SPEC --out DIR

points.csv     one row per accepted step record
nested.csv     nz-check minus main differences at the same (chain, L)
descendants.csv diagnostics records (W_A = spacing_error), with overlap/ambiguity flags
flags.txt      thermal jumps, Jacobian conditions (max over ALL attempts, incl. archived
               checkpoints), ambiguous primary overlaps. Flags are for a human decision.
"""
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path
from common import SpecError,atomic_json,chain_dir,check_predecessor,digest,load_spec,steps,verify_runtime
import io,os

COND_FLAG=1e8
HEADERS={'points':['chain','x','s','L','nz','role','Delta_thermal','even_gaps','odd_gaps','tuning_residual',
                   'max_eigenvector_residual','window_fixed_point','max_jacobian_condition','seconds','peak_rss_gib',
                   'theta0','theta1','g','r','diagnostics'],
         'descendants':['chain','x','L','nz','family','branch','J','level','rank','primary_gap','descendant_gap',
                        'spacing_error','overlap_probability','ambiguous'],
         'nested':['chain','x','L','nz','dDelta_thermal','max_dgap']}


def ambiguity_flags(chain,L,nz,records):
    return [f"{chain} L={L} nz={nz}: ambiguous {d['family']}/{d['branch']} identification "
            f"(overlap {d['overlap_probability']:.3f} < 0.5); not a verified descendant" for d in records if d.get('ambiguous')]


def publish(path,text):
    tmp=Path(str(path)+f'.{os.getpid()}.tmp');tmp.write_text(text);os.replace(tmp,path)


def history_conditions(history):
    if not isinstance(history,list):return []
    return [h['jacobian_condition'] for h in history if isinstance(h,dict)
            and isinstance(h.get('jacobian_condition'),(int,float)) and not isinstance(h.get('jacobian_condition'),bool)]


def attempt_conditions(cdir,output,row,rejected=None):
    """Max Jacobian condition over the final record and every ARCHIVED attempt of the SAME request.

    Archived checkpoints are merged only if they are checksummed envelopes of this record's request
    (IR-05); anything else is reported in `rejected` and never aborts the collection."""
    vals=history_conditions(row.get('history'))
    stem=Path(output).stem
    for cp in sorted((Path(cdir)/'history').glob(f'{stem}.*.checkpoint.json')):
        try:
            env=json.loads(cp.read_text())
            if not isinstance(env,dict):raise ValueError('not an object')
            body=dict(env);sig=body.pop('checkpoint_sha256',None)
            if sig!=digest(body):raise ValueError('checksum mismatch')
            if env.get('request_digest')!=row.get('request_digest'):raise ValueError('another request')
            vals+=history_conditions(env.get('history'))
        except (OSError,ValueError,TypeError) as exc:
            if rejected is not None:rejected.append(f'{cp.name}: {exc}')
    return max(vals) if vals else None


JUMP_RATIO=3.0
JUMP_FLOOR=1e-10   # documented numerical-noise floor (plan rev 7, IR-08): replays agree to ~1e-12


def jump_flags(chain,seq):
    """Flag |D(L3)-D(L2)| > 3 |D(L2)-D(L1)| (plan section 4.3) above the documented noise floor."""
    out=[]
    for (L1,d1),(L2,d2),(L3,d3) in zip(seq,seq[1:],seq[2:]):
        if abs(d3-d2)>JUMP_RATIO*abs(d2-d1) and abs(d3-d2)>JUMP_FLOOR:
            out.append(f'{chain}: thermal jump L={L2}->{L3} {d3-d2:+.3e} > 3x previous {d2-d1:+.3e}')
    return out


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--spec',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args(argv);spec=load_spec(a.spec);verify_runtime(spec);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    points=[];desc=[];flags=[];rec={};cache={}
    for c in spec['chains']:
        cdir=chain_dir(spec,c)
        for s in steps(spec,c):
            p=Path(s['output'])
            if not p.exists():continue
            try:_,vsha=check_predecessor(spec,{'chain':c,'L':s['L'],'nz':s['nz']},cache=cache)
            except (SpecError,ValueError,KeyError) as e:flags.append(f'{c} L={s["L"]} nz={s["nz"]}: INVALID record ({e})');continue
            data=p.read_bytes()
            if hashlib.sha256(data).hexdigest()!=vsha:flags.append(f'{c} L={s["L"]} nz={s["nz"]}: record changed during collection');continue
            r=json.loads(data);rec[(c,s['L'],s['nz'])]=r
            W=r.get('window_correction',{})
            rej=[];cond=attempt_conditions(cdir,s['output'],r,rej)
            flags+=[f'{c} L={s["L"]} nz={s["nz"]}: archived checkpoint ignored ({m})' for m in rej]
            points.append({'chain':c,'x':r['delta'],'s':r['s'],'L':s['L'],'nz':s['nz'],'role':s['role'],
                'Delta_thermal':r['Delta_thermal'],'even_gaps':json.dumps(r['even_gaps']),'odd_gaps':json.dumps(r['odd_gaps']),
                'tuning_residual':r['tuning_residual'],'max_eigenvector_residual':r['max_eigenvector_residual'],
                'window_fixed_point':max([W.get('top_fixed_point_residual',0),*W.get('sublevel_fixed_point_residuals',{}).values()]),
                'max_jacobian_condition':cond,'seconds':r['elapsed_total_seconds'],'peak_rss_gib':r['peak_rss_kib']/2**20,
                'theta0':r['theta'][0],'theta1':r['theta'][1],'g':r.get('g'),'r':r.get('r'),'diagnostics':r['configuration']['diagnostics']})
            if cond is not None and cond>COND_FLAG:flags.append(f'{c} L={s["L"]} nz={s["nz"]}: Jacobian condition {cond:.2e} > {COND_FLAG:g}')
            for d in (r.get('diagnostics') or {}).get('records',[]):
                desc.append({'chain':c,'x':r['delta'],'L':s['L'],'nz':s['nz'],**{k:d[k] for k in
                    ('family','branch','J','level','rank','primary_gap','descendant_gap','spacing_error','overlap_probability','ambiguous')}})
            flags+=ambiguity_flags(c,s['L'],s['nz'],(r.get('diagnostics') or {}).get('records',[]))   # F22
    nested=[]
    for (c,L,nz),r in rec.items():
        main=spec['chains'][c]['main']['nz']
        if nz!=main and (c,L,main) in rec:
            m=rec[(c,L,main)]
            nested.append({'chain':c,'x':r['delta'],'L':L,'nz':nz,'dDelta_thermal':r['Delta_thermal']-m['Delta_thermal'],
                'max_dgap':max(abs(u-v) for u,v in zip(r['even_gaps'][:5]+r['odd_gaps'][:5],m['even_gaps'][:5]+m['odd_gaps'][:5]))})
    for c in spec['chains']:
        nzm=spec['chains'][c]['main']['nz'];seq=sorted((L,r['Delta_thermal']) for (cc,L,nz),r in rec.items() if cc==c and nz==nzm)
        flags+=jump_flags(c,seq)
    # F23: every report is regenerated on every collection (empty tables keep their header) and
    # replaced atomically, so results of an earlier collection cannot survive.
    for name,rows in (('points',points),('descendants',desc),('nested',nested)):
        buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=HEADERS[name]);w.writeheader();w.writerows(rows)
        publish(out/f'{name}.csv',buf.getvalue())
    publish(out/'flags.txt','\n'.join(flags)+'\n')
    print(f'{len(points)} records, {len(nested)} nested, {len(desc)} descendant rows, {len(flags)} flags -> {out}')
    return 0


if __name__=='__main__':raise SystemExit(main())
