#!/usr/bin/env python3
"""Preview assembly of ONE batch (normally the pilot) with assemble8 in preview mode: an end-to-end check of the chain
(verified streams, affine map, controls, coverage guard, telescoping, checks) and a provisional C8. A preview is never a
result: the pilot trained the controls and the allocation it is assembled with, and campaigns planned before the
exact-zero hashing are accepted without that hash.
Usage: preview8.py BATCH --affine FULL_AFFINE --exact5 CHOSEN PREVIOUS --output DIR
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from assemble8 import assemble,result_text
from campaign import publish_or_verify

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('batch',type=Path);p.add_argument('--affine',type=Path,required=True)
    p.add_argument('--exact5',type=Path,nargs=2,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    b=a.batch.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    rp=lambda x:os.path.relpath(Path(x).resolve(),out)
    conf=json.loads((b/'assembly.json').read_text())
    srcs=[{**s,'path':rp(b/s['path']),**({'subtract':rp(b/s['subtract'])} if 'subtract' in s else {})} for s in conf['sources']]
    config={'preview':True,'affine_map':rp(a.affine),'exact_loop5':{'path':rp(a.exact5[0]),'previous':rp(a.exact5[1])},'sources':srcs}
    publish_or_verify(out/'preview_config.json',json.dumps(config,indent=2)+'\n')
    r=assemble(config,out)
    publish_or_verify(out/'C8_preview.json',result_text(r))
    show={'C8_preview':r['C8_full'],'sampling_se':r['sampling_se'],'allowance':r['allowance'],'resolution':[(x['degree'],x['mean'][8],x['sampling_se'][8]) for x in r['resolution_sequence']],
          'check_refine9':{k:(v['mean'][8],v['sampling_se'][8]) for k,v in r['check_levels'].items()},'lower_order_checks':r['lower_order_checks'],'truncation':r['truncation_assessment'],
          'campaigns':{k:(round(v['mean_C8'],3),round(v['sampling_se_C8'],3)) for k,v in r['campaign_aggregates'].items()},'flags':r['flags'],'coverage':r['coverage']}
    print(json.dumps(show,indent=1))
if __name__=='__main__':main()
