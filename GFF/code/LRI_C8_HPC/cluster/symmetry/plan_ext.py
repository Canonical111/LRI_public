#!/usr/bin/env python3
"""Plan the extension batches listed in an amendment (extension.json) with the frozen production tools, then check
every planned batch: label and seed exactly as in the amendment (also for batches planned earlier), all labels and
seeds distinct from each other and from the base batches, every campaign seed derived from its batch seed as
production8.py derives it and distinct from the base batches' and the bundle's forbidden campaign seeds (base batches
are looked up next to B1_DIR), and a scientific configuration identical to batch b1's
(the combine8 canonical() fields plus the element list). Exits nonzero on any mismatch, before production.
Usage: plan_ext.py EXTENSION_JSON B1_DIR INPUTS_DIR"""
import hashlib,json,os,subprocess,sys
from pathlib import Path
ext_path,b1,inputs=map(lambda x:Path(x).resolve(),sys.argv[1:4]);ext=json.loads(ext_path.read_text());run=ext_path.parent
root=Path(os.environ['C8_ROOT']);bundle=Path(os.environ['C8_BUNDLE']);exe=os.environ['C8_EXE']
el=ext['extension'];allx=ext['base']+el
labels=[x['label'] for x in allx];seeds=[int(x['seed']) for x in allx]
if len(set(labels))!=len(labels) or len(set(seeds))!=len(seeds):sys.exit('amendment labels or seeds are not distinct')
procs=[]
for x in el:
    d=run/x['path']
    if (d/'production.json').exists():continue
    log=open(run/f"plan_{x['label']}.log",'w')
    procs.append((x,subprocess.Popen([sys.executable,str(root/'tools/production8.py'),'plan',str(d),'--unit',str(bundle/'unit_production.json'),'--design',str(bundle/'design.json'),
        '--design-meta',str(bundle/'design_meta.json'),'--seed',str(x['seed']),'--inputs',str(inputs),'--executable',exe,'--label',x['label']],stdout=log,stderr=subprocess.STDOUT)))
bad=[x['label'] for x,p in procs if p.wait()!=0]
if bad:sys.exit('planning failed for '+', '.join(bad))
sys.path.insert(0,str(root/'tools'))
from campaign import blocks
def sci(b):
    prod=json.loads((b/'production.json').read_text());conf=json.loads((b/'assembly.json').read_text());camps={}
    for c in prod['campaigns']:
        m=json.loads((b/c/'manifest.json').read_text())
        for _ in blocks(b/c,m):pass # every task file exists and matches its manifest digest (raises otherwise)
        camps[c]={k:m[k] for k in ('schema','mode','L','degrees','rate','replicates','counts','selection','inventory_count','input_sha256','executable_sha256','tile','scratch_mib','shards','checkpoint_tasks','chunk_points','total_work_units','samples_per_degree')}
    srcs=[{**{k:s.get(k) for k in ('name','campaign','level','role','L','kind','weight')},'path':s['path'],'subtract':s.get('subtract')} for s in conf['sources']]
    return json.dumps({'campaigns':camps,'sources':srcs,'unit_sha256':prod.get('unit_sha256'),'design_sha256':prod.get('design_sha256'),'design':prod.get('design'),'settings':prod.get('settings'),
                       'executable_sha256':prod['executable_sha256'],'design_meta_sha256':prod['design_meta_sha256'],'jobs':prod['jobs']},sort_keys=True),prod
ref,_=sci(b1)
def derived(batch_seed,name):return int.from_bytes(hashlib.sha256(f'{batch_seed}:{name}'.encode()).digest()[:8],'little') # production8.py plan
meta=json.loads((bundle/'design_meta.json').read_text());forbidden={int(x) for x in meta.get('forbidden_seeds',[])}
campseeds=set()
for x in ext['base']: # base campaign seeds (b1 is given; the others sit next to it)
    bdir=b1.parent/x['label'];bp=json.loads((bdir/'production.json').read_text())
    for c in bp['campaigns']:campseeds.add(json.loads((bdir/c/'manifest.json').read_text())['seed'])
for x in el:
    s,prod=sci(run/x['path'])
    if (prod.get('label'),int(prod['seed']))!=(x['label'],int(x['seed'])):sys.exit(f"{x['path']}: planned label/seed {prod.get('label')}/{prod['seed']} differ from the amendment {x['label']}/{x['seed']}")
    if s!=ref:sys.exit(f"{x['label']}: scientific configuration differs from b1")
    for c in prod['campaigns']:
        cs=json.loads((run/x['path']/c/'manifest.json').read_text())['seed']
        if cs!=derived(int(x['seed']),c):sys.exit(f"{x['label']}/{c}: campaign seed is not derived from the batch seed")
        if cs in campseeds or cs in forbidden:sys.exit(f"{x['label']}/{c}: campaign seed reused or forbidden")
        campseeds.add(cs)
    print(x['label'],'seed',prod['seed'],'elements',len(prod['jobs']),'configuration identical to b1')
print('all',len(el),'extension batches planned and checked')
