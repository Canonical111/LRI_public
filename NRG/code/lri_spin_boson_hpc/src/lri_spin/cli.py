"""Independent trajectories across Slurm tasks; each trajectory is sequential."""
from __future__ import annotations
import argparse,hashlib,json,os,sys
from pathlib import Path
from .config import Config
from .workflow import fixed,critical,plan
from .io import Interrupted,AlreadyRunning,read_record,source_hash,identity
from .validation import validate_result
from .campaign import OwnershipError,ID_RE,GEN_RE,RESERVED,campaign_of,refuse_campaign_destination

def common(p):
    p.add_argument('--s',type=float,default=.8);p.add_argument('--Lambda',type=float,default=3.)
    p.add_argument('--keep',type=int,default=48);p.add_argument('--nb',type=int,default=10)
    p.add_argument('--nsites',type=int,default=65);p.add_argument('--tunneling',type=float,default=.1)
    p.add_argument('--nlevels',type=int,default=8);p.add_argument('--threads',type=int,default=1)
    p.add_argument('--sector-workers',type=int,choices=[1,2],default=1)
    p.add_argument('--backend',choices=['ordered','dense','banded'],default='ordered')

def do_item(item,root,resume):
    if set(item)-{'id','kind','config','alpha','bracket','fraction','atol','maxiter','sector_workers','memory_limit_gib','backend','with_tangent'}:
        raise ValueError('Unrecognized manifest field')
    name=item['id']
    if not isinstance(name,str) or not ID_RE.fullmatch(name) or name in RESERVED or Path(name).name!=name:raise ValueError('Unsafe item ID')
    cfg=Config(**item['config']);folder=Path(root)/name
    opts={'backend':item.get('backend','ordered'),'sector_workers':item.get('sector_workers',1),
          'memory_limit_gib':item.get('memory_limit_gib',4.),'resume':resume}
    if item['kind']=='critical':
        return critical(cfg,folder,bracket=tuple(item.get('bracket',[.01,2.])),fraction=item.get('fraction',.3),
                        atol=item.get('atol',5e-14),maxiter=item.get('maxiter',48),
                        with_tangent=item.get('with_tangent',True),**opts)
    if item['kind'] not in ('flow','tangent'):raise ValueError('Unknown item kind')
    return fixed(item['alpha'],cfg,folder,tangent=item['kind']=='tangent',**opts)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('flow');common(a);a.add_argument('--alpha',type=float,required=True);a.add_argument('--tangent',action='store_true')
    b=sub.add_parser('critical');common(b);b.add_argument('--bracket',type=float,nargs=2,default=[.01,2.]);b.add_argument('--fraction',type=float,default=.3);b.add_argument('--atol',type=float,default=5e-14);b.add_argument('--maxiter',type=int,default=48);b.add_argument('--no-tangent',action='store_true')
    for c in (a,b):
        c.add_argument('--output-dir',required=True);c.add_argument('--resume',action='store_true');c.add_argument('--memory-limit-gib',type=float,default=4.)
        c.add_argument('--checkpoint-every',type=int,default=8)
    c=sub.add_parser('plan');common(c)
    c=sub.add_parser('item');c.add_argument('--manifest',required=True);c.add_argument('--index',type=int,default=None);c.add_argument('--output-dir',required=True);c.add_argument('--resume',action='store_true');c.add_argument('--validation-receipt')
    c=sub.add_parser('export');c.add_argument('inputs',nargs='+');c.add_argument('--output',required=True);c.add_argument('--allow-other-source',action='store_true')
    args=p.parse_args(argv)
    try:
        if args.cmd=='item':
            blob=Path(args.manifest).read_bytes()
            # A lane passes the hash of the snapshot it admitted, so admission and execution see one manifest.
            expect=os.environ.get('LRI_SPIN_MANIFEST_SHA256')
            if expect and hashlib.sha256(blob).hexdigest()!=expect:raise ValueError('Manifest differs from the submitted snapshot')
            expect=os.environ.get('LRI_SPIN_RECEIPT_SHA256')
            if expect and hashlib.sha256(Path(args.validation_receipt or '').read_bytes()).hexdigest()!=expect:raise ValueError('Receipt differs from the submitted snapshot')
            m=json.loads(blob);items=m['items'];ids=[i['id'] for i in items]
            if m.get('source_sha256')!=source_hash():raise ValueError('Manifest not validated for this solver source')
            if not args.validation_receipt:raise ValueError('Array items require a target-cluster validation receipt')
            receipt=read_record(args.validation_receipt)
            if not receipt.get('passed') or receipt.get('source_sha256')!=source_hash():raise ValueError('Invalid/stale validation receipt')
            if receipt.get('runtime')!=identity(Config(),None,'receipt')['runtime']:raise ValueError('Validation runtime differs from task runtime')
            if len(ids)!=len(set(ids)):raise ValueError('Duplicate manifest IDs')
            idx=args.index if args.index is not None else int(os.environ['SLURM_ARRAY_TASK_ID'])
            if not 0<=idx<len(items):raise ValueError('Item index outside manifest')
            out=do_item(items[idx],args.output_dir,args.resume)
        elif args.cmd=='export':
            rows=[]
            for path in args.inputs:
                r=read_record(path)
                lineage=json.loads(Path(path).read_text())['identity']
                if lineage.get('source_sha256')!=source_hash() and not args.allow_other_source:raise ValueError('Export source mismatch; --allow-other-source explicitly permits archived versions')
                found=campaign_of(path)
                if found and len(found[1])==3 and GEN_RE.fullmatch(found[1][1]):
                    lineage={**lineage,'campaign_item':found[1][0],'generation':int(found[1][1][1:])}
                r['_provenance']=lineage
                if 'critical_flow' in r:
                    for key in ('critical_flow','tangent'):
                        if key in r:validate_result(r[key],Config(**r[key]['config']),tangent=key=='tangent')
                else:validate_result(r,Config(**r['config']),tangent='tangent' in r['method'],observers=r['observers'])
                rows.append(r)
            dest=Path(args.output);refuse_campaign_destination(dest);dest.parent.mkdir(parents=True,exist_ok=True)
            from .io import _atomic
            _atomic(dest,lambda f:f.write(json.dumps(rows,indent=2,allow_nan=False).encode()))
            print('Exported',len(rows),'validated records');return 0
        else:
            cfg=Config(**{k:getattr(args,k) for k in Config.__dataclass_fields__})
            if args.cmd=='plan':
                print(json.dumps(plan(cfg,args.sector_workers),indent=2));return 0
            if args.checkpoint_every<1:raise ValueError('Checkpoint interval must be positive')
            kw={'backend':args.backend,'sector_workers':args.sector_workers,'resume':args.resume,
                'memory_limit_gib':args.memory_limit_gib,'checkpoint_every':args.checkpoint_every}
            if args.cmd=='critical':
                out=critical(cfg,args.output_dir,bracket=tuple(args.bracket),fraction=args.fraction,atol=args.atol,maxiter=args.maxiter,with_tangent=not args.no_tangent,**kw)
            else:out=fixed(args.alpha,cfg,args.output_dir,tangent=args.tangent,**kw)
        if 'analysis' in out:print(json.dumps(out['analysis'].get('selected'),indent=2))
        else:print('Completed',len(out.get('records',[])),'iterations')
        return 0
    except Interrupted as e:
        print(str(e),file=sys.stderr);return 75
    except AlreadyRunning as e:
        print('Already claimed:',e,file=sys.stderr);return 73
    except OwnershipError as e:
        print('Not the owner:',e,file=sys.stderr);return 76

if __name__=='__main__':raise SystemExit(main())
