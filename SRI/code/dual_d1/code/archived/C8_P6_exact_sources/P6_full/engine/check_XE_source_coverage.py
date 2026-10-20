"""Independent exact coverage audit of the complete endpoint finite calculation.
This verifies source ranges and hashes, not a second raw integration.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def relative(p):
 p=Path(p)
 if p.is_absolute():
  try:return ROOT/p.relative_to('/mnt/data/F3_continuation/full_exact')
  except ValueError:return p
 return ROOT/p

def main():
 plan=json.loads((ROOT/'data/XE_final_plan.json').read_text());m=json.loads((ROOT/'XE_terminal/manifest.json').read_text());source=relative(m['whole_source']);assert sha(source)==m['whole_source_sha256'];lines=source.read_bytes().splitlines(keepends=True)
 assert len(lines)==m['source_rows'];off=0;names=[]
 for r in m['blocks']:
  assert r['start']==off and r['end']-r['start']==r['rows'];p=ROOT/'XE_terminal'/r['block']/'stage4.jsonl'
  assert sha(p)==r['source_sha256'] and p.read_bytes()==b''.join(lines[r['start']:r['end']]);off=r['end'];names.append(r['block'])
 assert off==len(lines)
 assert set(plan['retained_chunks']).isdisjoint(plan['combined_chunks']) and sorted(plan['retained_chunks']+plan['combined_chunks'])==sorted(names)
 for n in plan['retained_chunks']:
  folder=ROOT/'XE_terminal'/n;r=json.loads((folder/'growth_stage5_report.json').read_text());assert r['complete'];assert r.get('input_sha256',r.get('source_sha256'))==sha(folder/'stage4.jsonl');assert r['output_sha256']==sha(folder/'growth_stage5.jsonl')
 gr=json.loads((ROOT/'XE_remaining_group/moving_report.json').read_text());actual=[]
 for r in gr['sources']:
  p=relative(r['path']);assert sha(p)==r['sha256'];actual.append(p.parent.name)
 assert sorted(actual)==sorted(plan['combined_chunks'])
 mm=json.loads((ROOT/'XE_moving_chunks/manifest.json').read_text());mp=relative(mm['source']);assert sha(mp)==mm['sha256'];ml=mp.read_bytes().splitlines(keepends=True);off=0
 for r in mm['chunks']:
  assert r['start']==off and r['end']>r['start'];d=relative(r['directory']);p=d/'moving.jsonl';assert sha(p)==r['sha256'] and p.read_bytes()==b''.join(ml[r['start']:r['end']]);off=r['end']
  rr=json.loads((d/'growth_stage5_report.json').read_text());assert rr['complete'] and rr['input_sha256']==sha(p) and rr['output_sha256']==sha(d/'growth_stage5.jsonl')
 assert off==len(ml)==mm['source_rows']
 a=json.loads((ROOT/'XE_growth_total/assembly.json').read_text());assert a['complete'];assert [relative(r['file']).parent for r in a['inputs']]==[ROOT/r for r in plan['evaluation_folders']]
 for r in a['inputs']:assert sha(relative(r['file']))==r['sha256']
 assert sha(ROOT/'XE_growth_total/stage5.jsonl')==a['output_sha256']
 report={'complete_source_coverage':True,'original_stage4_rows':len(lines),'original_source_chunks':len(names),'retained_growth_chunks':len(plan['retained_chunks']),'joint_source_chunks':len(plan['combined_chunks']),'moving_rows':len(ml),'moving_partition_chunks':len(mm['chunks']),'all_ranges_byte_exact':True,'all_current_hashes_exact':True,'final_polynomial_sources':len(a['inputs']),'final_source_rows':a['output_rows'],'not_a_reintegration':True}
 (Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'data/XE_source_coverage.json').write_text(json.dumps(report,indent=2));print('COVERAGE',report,flush=True)
if __name__=='__main__':main()
