#!/usr/bin/env python3
"""Regression of the C6/C7 (D4) path after the C8 extension (phase 3): the tooling must reproduce the tier-1
production exactly.  No engine run (the engine source and binary are unchanged; cross-machine identity of the
engine itself: tests/compare_calib.py).
  1. campaign.py plan specs/production_6digit.json (tier 6digit) into a scratch directory: every cfg, the manifest
     (without the later 'refine' entries) and cfglist.txt byte-identical to runs/prod_6digit;
  2. campaign.py collect on a scratch copy of runs/prod_6digit: results.json byte-identical, framework_input.json
     identical except the producer's run path;
  3. outliers.py runs/prod_6digit --T 5e-5: flags identical to the stored runs/prod_6digit/flags.json.
usage: python3 tests/regress_C8.py SCRATCHDIR     (writes results/regress_C8.txt; exit 1 on any difference)
"""
import filecmp, glob, json, os, shutil, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
scr = os.path.abspath(sys.argv[1])
shutil.rmtree(scr, ignore_errors=True)
os.makedirs(scr)
PY = sys.executable
prod = os.path.join(ROOT, 'runs', 'prod_6digit')
out, ok = [], True


def note(s):
    out.append(s)
    print(s)


# 1. re-plan
rp = os.path.join(scr, 'prod_6digit')
subprocess.run([PY, os.path.join(ROOT, 'py', 'campaign.py'), 'plan', os.path.join(ROOT, 'specs', 'production_6digit.json'),
                rp, '--tier', '6digit'], check=True, capture_output=True)
cfgs = sorted(os.path.basename(c) for c in glob.glob(os.path.join(prod, '*.cfg')))
man = json.load(open(os.path.join(prod, 'manifest.json')))
orig = sorted(c for m in man for c in m['cfgs'])
diff = [c for c in orig if not filecmp.cmp(os.path.join(prod, c), os.path.join(rp, c), shallow=False)]
m1 = [{k: v for k, v in m.items() if k != 'refine'} for m in man]
m2 = [{k: v for k, v in m.items() if k != 'refine'} for m in json.load(open(os.path.join(rp, 'manifest.json')))]
same_list = filecmp.cmp(os.path.join(prod, 'cfglist.txt'), os.path.join(rp, 'cfglist.txt'), shallow=False)
note(f'1. re-plan of specs/production_6digit.json: {len(orig)} production cfgs, {len(diff)} differ; manifest '
     f'{"identical" if m1 == m2 else "DIFFERS"}; cfglist.txt {"identical" if same_list else "DIFFERS"}')
ok &= not diff and m1 == m2 and same_list
# 2. re-collect a copy
cp = os.path.join(scr, 'collect', 'prod_6digit')
shutil.copytree(prod, cp)
r = subprocess.run([PY, os.path.join(ROOT, 'py', 'campaign.py'), 'collect', cp], capture_output=True, text=True)
same_res = filecmp.cmp(os.path.join(prod, 'results.json'), os.path.join(cp, 'results.json'), shallow=False)
f1 = json.load(open(os.path.join(prod, 'framework_input.json')))
f2 = json.load(open(os.path.join(cp, 'framework_input.json')))
f1['producer'].pop('run')
f2['producer'].pop('run')
note(f'2. re-collect of a copy of runs/prod_6digit: exit {r.returncode}; results.json '
     f'{"byte-identical" if same_res else "DIFFERS"}; framework_input.json '
     f'{"identical up to the run path" if f1 == f2 else "DIFFERS"}')
ok &= r.returncode == 0 and same_res and f1 == f2
# 3. outliers
fl = os.path.join(scr, 'flags.json')
r = subprocess.run([PY, os.path.join(ROOT, 'py', 'outliers.py'), prod, '--T', '5e-5', '--json', fl], capture_output=True,
                   text=True)
same_fl = json.load(open(fl)) == json.load(open(os.path.join(prod, 'flags.json')))
note(f'3. outliers.py runs/prod_6digit --T 5e-5: exit {r.returncode}; flags {"identical" if same_fl else "DIFFER"} '
     'to the stored flags.json')
ok &= r.returncode == 0 and same_fl
note('REGRESSION ' + ('PASS' if ok else 'FAIL'))
open(os.path.join(ROOT, 'results', 'regress_C8.txt'), 'w').write('\n'.join(out) + '\n')
sys.exit(0 if ok else 1)
