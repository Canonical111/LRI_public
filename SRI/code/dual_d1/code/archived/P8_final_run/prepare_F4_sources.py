"""Restore complete unprojected base-integral stages after exact zero-defect audit.
Variable renaming identifies the last two coordinates with q,r in the replay
engine. Reflection weights are applied explicitly; no target scalar is an input.
"""
from pathlib import Path
import json,re,hashlib
base=Path('/mnt/data/P8_final_run/rational_stages/C8_rational_completion/workspace/R8_work')
root=Path('/mnt/data/P8_final_run/F3_six_kink_completion')
for kind,n,N,stage,nb,kap,interval in [('Z',8,6,4,16,-1,True),('A',9,7,5,64,0,True),('EA',7,7,5,32,1,False)]:
 name=f'F4_{kind}{n}';folder=root/name;folder.mkdir(exist_ok=True)
 sourcepath=base/'endpoint_odd' if kind=='EA' else base/'tail_blocks'/f'{kind}_base'
 pattern=(f'EA{n}_b*' if kind=='EA' else f'n{n}_f*_b*')+f'/stage{stage}.jsonl'
 inputs=sorted(sourcepath.glob(pattern));assert inputs
 if (folder/'source_manifest.json').exists():continue
 files=[(folder/f'source_b{i:03d}.tsv.tmp').open('w') for i in range(nb)]
 records=[];nr=0
 rename={'r':'q','h':'r'} if N==7 else {}
 def ren(s):return re.sub(r'\b(r|h)\b',lambda m:rename.get(m[0],m[0]),s) if rename else s
 for source in inputs:
  data=source.read_bytes();records.append({'file':str(source),'sha256':hashlib.sha256(data).hexdigest()})
  if kind=='EA':mu=1
  else:
   face=int(source.parent.name.split('_')[1][1:]);mu=1 if (n-1)%2 and face==n//2 else 2
  for line in data.decode().splitlines():
   ww,ll,c=json.loads(line);assert not ll and not any(ww[:-2]);wq=list(map(ren,ww[-2]));wr=list(map(ren,ww[-1]));c=ren(c)
   key=json.dumps([wq,wr,[]],separators=(',',':'));i=int.from_bytes(hashlib.blake2b(key.encode(),digest_size=8).digest(),'little')%nb
   files[i].write(f'{key}\t{c}\t{mu}\n');nr+=1
 for f in files:f.close()
 for i in range(nb):(folder/f'source_b{i:03d}.tsv.tmp').rename(folder/f'source_b{i:03d}.tsv')
 (folder/'source_manifest.json').write_text(json.dumps({'target':name,'n':n,'dimensionless_endpoint_offset':n-1,'kappa':kap,'interval_factor':interval,'source_blocks':len(inputs),'rows':nr,'buckets':nb,'sources':records,'full_constant_status':'Upstream fibration defects are checked separately; EA7 additionally requires 2 log(16/5) A7 finite.'},indent=2));print('PREPARED',name,nr,flush=True)
