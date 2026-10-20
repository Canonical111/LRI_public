from full_runner import *
import sympy as s
out=[]
for i in range(6):
 orig=ROOT/f'EQ6_v/b{i:02}/stage1.jsonl';ref=ROOT/f'rational_sources/b{i:02}/stage1.jsonl'
 aa={}
 for (ww,ll),c in load(orig):
  if ll:continue
  # Formal weight zero only for this source consistency check, not production.
  for ix in range(8,K.ngens):c=sub(c,ix,K.zero)
  c=sub(c,0,K.one)
  words=tuple(tuple(sub(a,0,K.one) for a in w) for w in ww)
  addto(aa,(words,()),c)
 bb={}
 for line in ref.open():
  ww,ll,c=json.loads(line);assert ll==0
  words=tuple(tuple(rm.parseK(x) for x in w) for w in ww)
  addto(bb,(words,()),rm.parseK(c))
 assert set(clean(aa))==set(clean(bb)),(i,len(aa),len(bb))
 for k in aa:assert aa[k]==bb[k],(i,k)
 out.append({'block':f'b{i:02}','source_rows_full':sum(1 for _ in orig.open()),'projected_rows':len(clean(aa)),'reference_rows':len(clean(bb)),'all_coefficients_equal':True})
 print(out[-1],flush=True);clear()
(ROOT/'data/source_projection_check.json').write_text(json.dumps(out,indent=2))
