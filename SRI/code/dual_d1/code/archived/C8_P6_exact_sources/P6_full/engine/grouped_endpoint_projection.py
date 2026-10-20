"""Group exact polynomial endpoint contributions before fibration.
All full constant periods retained. Intended for the e-times-integral finite
part only, using the polynomial-growth lemma, not the weight-zero projection.
"""
from endpoint_projected_stage import *

def projected_moving(paths):
 group={};st=time.time();n=0
 for fp in paths:
  for line in Path(fp).open():
   ww,ll,txt=json.loads(line);words=tuple(tuple(rm.parseK(a) for a in w) for w in ww);logs=tuple(sorted(ll));R=rm.parseK(txt);idx=5;N=6
   assert all(not w for w in words[:4]);pol,po=apart(R,idx)
   for kin,a,p,pref in [('poly',K.zero,p,c) for p,c in pol.items()]+[('pole',a,p,c) for (a,p),c in po.items()]:
    audit_basis(kin,a,p,words[4],5)
    for wa,c in integrate_basis(kin,a,p,words[4],5).items():
     for wb,cb in endpoint_value(c,wa,5,GEN[6]).items():
      cf=pp_as_fraction(pref*cb,6)
      if cf:addto(group,(wb,words[5],logs),cf)
     for wb,cb in endpoint_value(c,wa,5,K.zero,lower=True).items():
      assert not wb;cf=pp_as_fraction(pref*cb,6)
      if cf:addto(group,((),words[5],logs),-cf)
   n+=1
   if n%500==0:print('GROUP_MOVING',n,len(group),time.time()-st,flush=True)
 return clean(group),n

def fibrate_group(group):
 out={};st=time.time();n=len(group);j=0
 while group:
  (a,b,ll),cf=group.popitem();j+=1
  for wf,mu in endpoint_fibrate(a,6).items():
   assert not mu.diff(GEN[6])
   for w,c in shuffle(wf,b).items():addto(out,(((),(),(),(),(),w),ll),cf*mu*c)
  if j%1000==0:
   out=clean(out)
   if j%2000==0:clear()
   print('GROUP_FIBRATE',j,n,len(out),time.time()-st,flush=True)
 return clean(out)
if __name__=='__main__':
 if sys.argv[1]=='check':
  folder=Path(sys.argv[2]);g,n=projected_moving([folder/'stage4.jsonl']);gn=len(g);res=fibrate_group(g)
  ref=dict(load(folder/'growth_stage5.jsonl'));dif=res.copy()
  for k,v in ref.items():addto(dif,k,-v)
  assert not clean(dif),len(clean(dif))
  r={'rows':n,'grouped_endpoint_terms':gn,'full_output_rows':len(res),'exact_equal':True}
  (ROOT/'data/grouped_endpoint_projection_check.json').write_text(json.dumps(r,indent=2));print('EXACT_GROUP_CHECK',r,flush=True)
 else:
  spec=json.loads(Path(sys.argv[1]).read_text());paths=[ROOT/r['path'] for r in spec['inputs']];folder=ROOT/spec['output'];folder.mkdir(exist_ok=True)
  if not (folder/'moving.jsonl').exists():
   g,n=projected_moving(paths);p=folder/'moving.jsonl';tmp=p.with_suffix('.tmp')
   with tmp.open('w') as f:
    for (a,b,ll),c in g.items():f.write(json.dumps([list(map(str,a)),list(map(str,b)),list(ll),str(c)],separators=(',',':'))+'\n')
   tmp.replace(p)
   (folder/'moving_report.json').write_text(json.dumps({'input_rows':n,'moving_terms':len(g),'sources':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]},indent=2))
  else:
   g={}
   for line in (folder/'moving.jsonl').open():
    a,b,ll,c=json.loads(line);g[(tuple(rm.parseK(x) for x in a),tuple(rm.parseK(x) for x in b),tuple(ll))]=rm.parseK(c)
  out=fibrate_group(g);dest=folder/'growth_stage5.jsonl';dump(dest,out)
  (folder/'growth_stage5_report.json').write_text(json.dumps({'complete':True,'output_rows':len(out),'output_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'grouped_before_fibration':True},indent=2))
