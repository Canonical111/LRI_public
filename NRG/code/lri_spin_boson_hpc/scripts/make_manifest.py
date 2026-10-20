"""Freeze a user-supplied item list after a successful compute-node validation."""
from pathlib import Path
import argparse,json,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from lri_spin.io import read_record,source_hash,_atomic
from lri_spin.manifest import validate_items,config_of
from lri_spin.campaign import refuse_campaign_destination,OwnershipError
from lri_spin.workflow import plan
p=argparse.ArgumentParser();p.add_argument('--items',required=True);p.add_argument('--receipt',required=True);p.add_argument('--output',required=True);a=p.parse_args()
try:refuse_campaign_destination(a.output)
except OwnershipError as exc:raise SystemExit(f'Refusing: {exc}')
r=read_record(a.receipt)
if not r.get('passed') or r.get('source_sha256')!=source_hash():raise SystemExit('Receipt is not for this solver')
d=json.loads(Path(a.items).read_text());items=d['items'] if isinstance(d,dict) else d
try:validate_items(items)
except ValueError as exc:raise SystemExit(f'Invalid items: {exc}')
for item in items:
 m=plan(config_of(item),item.get('sector_workers',1))
 print(item['id'],'estimated GiB',round(m['estimated_gib_with_margin'],3))
out={'schema':1,'source_sha256':source_hash(),'items':items}
_atomic(a.output,lambda f:f.write(json.dumps(out,indent=2).encode()+b'\n'))
