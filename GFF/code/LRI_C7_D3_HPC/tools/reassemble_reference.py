#!/usr/bin/env python3
"""Non-destructive reassembly of every archived production record, not new integration."""
import importlib.util,json
from pathlib import Path
import numpy as np
from common import ROOT,dump,load,digest
from assemble import calculate
ref=ROOT/'reference'
spec=importlib.util.spec_from_file_location('original_d3_analysis',ref/'code/analyze.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
data={tag:mod.load_campaign(name)[0] for tag,name in [('a','production_a'),('b','production_b')]}
ar={sector:{tag:{L:data[tag][sector][L]for L in range(3,8)}for tag in ('a','b')}for sector in ('free','power')}
r=calculate(ar,None,0);baseline=load(ref/'verification/C7_full_result.json')
keys=('C7_full','sampling_standard_error','power_correction','power_correction_se','power_free_C7','power_free_se')
errors={k:abs(r[k]-baseline[k])for k in keys}
if max(errors.values())>2e-10:raise AssertionError(errors)
if not np.allclose(r['covariance'],baseline['covariance'],rtol=2e-13,atol=1e-12):raise AssertionError('Covariance mismatch')
doc=dict(status='passed',result={k:r[k]for k in keys},absolute_errors=errors,max_absolute_error=max(errors.values()),
 reference_sha256=digest(ref/'verification/C7_full_result.json'),all_raw_record_hashes_verified=True,
 integrations_rerun=False,original_files_modified=False)
p=ROOT/'benchmarks/reassembled.json'
if not p.exists():dump(p,doc)
print(json.dumps(doc,indent=2))
