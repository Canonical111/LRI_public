#!/usr/bin/env python3
"""Non-destructive reassembly of accepted data via original and new assembly."""
from pathlib import Path
import importlib.util,json,subprocess,sys
import numpy as np
from common import ROOT,dump,load,digest
from assemble import calculate
ref=ROOT/'reference';old=ref/'LRI_C7_d2_progress'
# Import original readers with their original, immutable path conventions.
sys.path.insert(0,str(old/'code'));from analyze import read
from finalize import primitive,checked
frees=[read(t)[0]for t in ('productionA','productionB')]
prs=[primitive(t)for t in ('primitiveA','primitiveB')]
manifest=load(ref/'power_mass/verification/production_manifest.json');plan=load(ref/'power_mass/inputs/production_plan.json')
spec=importlib.util.spec_from_file_location('ref_full_assembly',ref/'power_mass/code/assemble_full.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
powers=[mod.read_power(s,plan)[0]for s in manifest['campaigns']]
primitive_input={'mean':sum(p['mean']for p in prs)/2,'sampling_se':(sum(p['sampling_se']**2 for p in prs)/4)**.5}
a={s:{tag:{L:x[L]for L in range(3,8)}for tag,x in zip(('a','b'),rows)}for s,rows in [('free',frees),('power',powers)]}
r=calculate(a,primitive_input,0);baseline=load(ref/'verification/C7_full_result.json')
fields={'C7_full':'C7_full','sampling_standard_error':'sampling_se','power_correction':'power_correction','power_correction_se':'power_correction_se','power_free_C7':'power_free_C7','power_free_se':'power_free_se'}
errors={k:abs(r[k]-baseline[v])for k,v in fields.items()}
if max(errors.values())>2e-8:raise AssertionError(errors)
if not np.allclose(np.array(r['covariance']),baseline['covariance'],rtol=2e-13,atol=1e-9):raise AssertionError('Covariance mismatch')
result={'status':'passed','result':{k:r[k]for k in fields},'absolute_errors':errors,'max_absolute_error':max(errors.values()),'reference_source_sha256':digest(ref/'verification/C7_full_result.json'),'integrations_rerun':False,'original_files_modified':False}
p=ROOT/'benchmarks/reassembled.json'
if not p.exists():dump(p,result)
print(json.dumps(result,indent=2))
