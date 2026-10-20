#!/usr/bin/env python3
"""Reassemble the archived final d=3 estimate with the ARCHIVED analysis code (reference/code/analyze.py).

This checks the archived evidence, not tools/assemble.py (tests/archived_assembly.py covers the new assembly).
The comparison is to relative 1e-12: the last bits depend on the NumPy/BLAS build (FMA use in convolve/dot).
Never runs integrations or edits evidence.
"""
from __future__ import annotations
import importlib.util,math,os,sys
from pathlib import Path
from common import ROOT,dump,load
REL_TOL=1e-12
R=ROOT/'reference'
os.environ['LRI_BASELINE']=str(R/'baseline_previous')
sys.path.insert(0,str(R/'code'))
spec=importlib.util.spec_from_file_location('archived_method_analysis',R/'code/analyze.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
x=mod.evaluate(3,write=False);expected=load(R/'verification/method_precision_results.json')['3']
checks={k:{'reassembled':x[k],'archived':expected[k],'difference':x[k]-expected[k],'bitwise_identical':x[k]==expected[k]}for k in ('C6','sampling_standard_error')}
ok=all(math.isclose(c['reassembled'],c['archived'],rel_tol=REL_TOL,abs_tol=0)for c in checks.values())
record={'C6':x['C6'],'sampling_standard_error':x['sampling_standard_error'],'checks':checks,'relative_tolerance':REL_TOL,'agrees_with_archived_result':ok,'bitwise_identical':all(c['bitwise_identical']for c in checks.values()),
        'scope':'Saved-data reassembly with the archived analysis code only; no fresh integrations, no overwrites of reference files, and not a test of tools/assemble.py.'}
if len(sys.argv)>1:dump(Path(sys.argv[1]),record)  # optional record; never written into the package by default
print(record)
if not ok:sys.exit('archived reassembly differs from the archived result beyond relative tolerance %g'%REL_TOL)
