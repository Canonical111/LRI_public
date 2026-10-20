import sys,json,time,os
import scaled_b as sb
import convert_stages as cv
name=sys.argv[1]
folder=sb.OUT/name
old=sb.ROOT/'blocks'/name
if not (folder/'conversion.json').exists() and any((old/f'stage{k}.jsonl').exists() for k in range(2,5)):
 cv.one(name)
had_result=(folder/'result.json').exists()
had_stage4=(folder/'stage4.jsonl').exists()
grouped=os.environ.get('R8_GROUPED','1')=='1'
if grouped:
 import grouped_stage;grouped_stage.install(from_stage=3)
sb.tb.worker(name)
result=json.loads((folder/'result.json').read_text())
if not had_result:
 result['stage4_assembly']='existing_exact_checkpoint' if had_stage4 else ('denominator_grouped' if grouped else 'original_incremental')
 (folder/'result.json').write_text(json.dumps(result,indent=2))
reference=old/'result.json'
if reference.exists():
 d=json.loads(reference.read_text());assert result['value']==d['value'],(name,result['value'],d['value'])
 if 'dimensionless_negative_inverse_euler' in d:assert result['dimensionless_negative_inverse_euler']==d['dimensionless_negative_inverse_euler']
 result['agrees_with_completed_unscaled_block_exact']=True
 (folder/'result.json').write_text(json.dumps(result,indent=2))
 print('UNSCALED_COMPARISON_PASS',name,flush=True)
