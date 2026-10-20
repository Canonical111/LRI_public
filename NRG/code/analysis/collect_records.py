"""Stage B (run on the cluster): copy the final gated result record of every manifest item out of a campaign root.

For each item the newest generation whose result.json has exactly the item's identity (manifest source hash,
receipt runtime) and passes the numerical gates is copied to <out>/<campaign>/<item id>.json, unchanged.
Checkpoints, trial flows and logs stay behind.

usage: python collect_records.py <solver src dir> <campaign root> <frozen manifest> <receipt> <out dir>
"""
import json,shutil,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from lri_spin.manifest import load_manifest,contained,result_checker
from lri_spin.campaign import classify_results
from lri_spin.io import read_record

src,campaign,manifest,receipt,out=sys.argv[1:6]
m=load_manifest(manifest,campaign);runtime=read_record(receipt)['runtime']
dest=Path(out)/Path(campaign).name;dest.mkdir(parents=True,exist_ok=True)
index=[]
for item in m['items']:
    ok,bad=classify_results(contained(campaign,item['id']),result_checker(item,m['source_sha256'],runtime))
    if not ok:raise SystemExit(f'{item["id"]}: no gated result ({bad})')
    g,path=ok[-1]
    shutil.copyfile(path,dest/f'{item["id"]}.json')
    index.append({'id':item['id'],'generation':g,'conflicting_generations':[x[0] for x in bad]})
(dest/'INDEX.json').write_text(json.dumps(index,indent=1)+'\n')
print(f'{len(index)} records from {campaign} -> {dest}')
