"""Resume a disjoint row range of the delivered full moving-letter P8 source."""
import sys, json, time, hashlib, argparse
from pathlib import Path
from group_before_fibration import *
from full_boundary import last_stage, full_extract

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',type=int,default=0);p.add_argument('--count',type=int,default=200);p.add_argument('--stop',type=int,default=6);a=p.parse_args()
    source=Path('/mnt/data/F3_P8_checkpoint/B8_moving4_total/moving.jsonl')
    folder=ROOT/'P8_pieces'/f'r{a.start:06d}_{a.count:04d}';folder.mkdir(parents=True,exist_ok=True)
    lines=[]
    with source.open() as f:
        for i,line in enumerate(f):
            if a.start<=i<a.start+a.count:lines.append(line)
            if i>=a.start+a.count:break
    assert len(lines)==a.count
    sh=hashlib.sha256(''.join(lines).encode()).hexdigest()
    mr=folder/'manifest.json'
    if mr.exists():assert json.loads(mr.read_text())['source_sha256']==sh
    else:mr.write_text(json.dumps({'start':a.start,'end':a.start+a.count,'source_sha256':sh,'all_periods':True},indent=2))
    t0=time.time()
    if not (folder/'stage4.jsonl').exists():
        g={}
        for line in lines:
            w,tail,ll,c=json.loads(line)
            g[(tuple(rm.parseK(x) for x in w),tuple(tuple(rm.parseK(x) for x in xw) for xw in tail),tuple(ll))]=rm.parseK(c)
        ans=fibrate_stage(g,4,6);dump(folder/'stage4.jsonl',ans);print('FIBRATED',len(ans),time.time()-t0,flush=True);del ans;clear()
    if a.stop==4:return
    if not (folder/'stage5.jsonl').exists():
        items=load(folder/'stage4.jsonl');ans=one_stage(items,5,6,8);dump(folder/'stage5.jsonl',ans);print('INTEGRATED_5',len(ans),time.time()-t0,flush=True);del items,ans;clear()
    if a.stop==5:return
    if not (folder/'negative.json').exists():
        items=load(folder/'stage5.jsonl');ans=last_stage(items,6,8);rows=[[list(map(int,w)),list(ll),str(c)] for (w,ll),c in ans.items()]
        tmp=folder/'negative.tmp';tmp.write_text(json.dumps(rows));tmp.replace(folder/'negative.json');print('INTEGRATED_6',len(rows),time.time()-t0,flush=True);del rows,ans,items;clear()
    if not (folder/'finite.expr').exists():
        import sympy as s
        ans=full_extract(json.loads((folder/'negative.json').read_text()),7)
        (folder/'finite.expr').write_text(s.sstr(ans,order='none'))
        rat=ans.xreplace({**{f:s.S.Zero for f in ans.atoms(s.Function)},**{f:s.S.Zero for f in ans.free_symbols if str(f).startswith(('R_','Z'))},s.pi:s.S.Zero})
        report={'complete':True,'source_sha256':sh,'terms':len(s.Add.make_args(ans)),'rational':str(rat),'seconds':time.time()-t0}
        (folder/'result.json').write_text(json.dumps(report,indent=2));print('COMPLETE',report,flush=True)
if __name__=='__main__':main()
