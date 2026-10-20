#!/usr/bin/env python3
"""Public replay of C8(1): rerun the production combination from the shipped merged records.

Runs the package's own tools/combine8.py and tools/assemble8.py (verbatim, the code that produced the published
results) on the merged per-campaign records in data/C8_1, for the three quoted combinations:

  K=4   b1-b4                                   -> results/C8_final/C8_final.json          (published 2026-10_expanse)
  A1    b1-b9, interim, A1-close inclusion set  -> results/C8_A1_close/combination/C8_interim.json
  K=14  b1-b14, closed extension                -> results/C8_final_A3/C8_final.json       (the final result)

Two substitutions, both made here and nowhere in the shipped code:
1. campaign.verify_campaign is replaced by light_verify(): the same checks of the manifest, the merge audit, the merged
   outputs (SHA-256 against the audit) and the merged headers, but WITHOUT re-validating the ~93,000 checkpoint files,
   which are not shipped (their SHA-256 values are listed in every merged/audit.json). The published C8_final.json
   records the SHA-256 of every merged stream it used, so verify8.py checks the chain end to end.
2. campaign_inputs() maps a batch's missing ../inputs directory to one shared copy of the numerical inputs (inputs8 of
   this package plus data/C8_1/inputs8/L8_coord.txt.xz, decompressed); every file is checked against the SHA-256 that
   all 420 campaign manifests record, before use and again by the coverage guard.
The work tree is a copy (not links) of data/C8_1/c8_hpc, so that combine8.py writes the same relative paths as in
production. Nothing outside --work is written.
"""
from __future__ import annotations
import argparse, hashlib, json, lzma, os, shutil, sys, time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / 'tools'))
import campaign, assemble8, combine8  # noqa: E402  (the production modules)

AFF = 'analysis/v1/full_affine8.json'
EX5 = ['runs/exact8_L5/exact_L5/merged/N14.json', 'runs/exact8_L5/exact_L5/merged/N12.json']
META = 'designs_frozen/prod4_34000/design_meta.json'
BASE = ['runs/prod4/b1', 'runs/prod4/b2', 'runs/prod4/b3', 'runs/prod4/b4']
EXT = [f'runs/ext1/b{i}' for i in range(5, 15)]
RUNS = {  # name: (combine8 arguments, output file relative to the work tree)
    'K4': (BASE + ['--output', 'results/C8_final'], 'results/C8_final/C8_final.json'),
    'A1': (BASE + EXT[:5] + ['--extension', 'runs/ext1/extension_A1close.json', '--output', 'results/C8_A1_close/combination'],
           'results/C8_A1_close/combination/C8_interim.json'),
    'K14': (BASE + EXT + ['--extension', 'runs/ext1/extension.json', '--closed', '--output', 'results/C8_final_A3'],
            'results/C8_final_A3/C8_final.json'),
}
SHARED = ['L6_coord.txt', 'L6_coord.txt.idx', 'exact_zero_L6.txt', 'L7_coord.txt', 'L7_coord.txt.idx', 'exact_zero_L7.txt',
          'L8_coord.txt', 'L8_coord.txt.idx', 'exact_zero_L8.txt']


def sha(p: Path) -> str:
    return campaign.digest(Path(p))


def light_verify(directory: Path) -> dict:
    """campaign.verify_campaign without re-validating the checkpoints (not shipped); every other check is kept."""
    directory = Path(directory).resolve(); mp = directory / 'manifest.json'; m = json.loads(mp.read_text()); mh = sha(mp)
    ap = directory / 'merged' / 'audit.json'
    if not ap.is_file(): raise FileNotFoundError('campaign not merged: ' + str(directory))
    audit = json.loads(ap.read_text())
    if audit.get('manifest_sha256') != mh or audit.get('complete') is not True:
        raise ValueError('audit does not match the manifest or is incomplete: ' + str(directory))
    if audit.get('work_units_per_degree') != m['total_work_units']: raise ValueError('audit work-unit count mismatch: ' + str(directory))
    if not audit.get('sources'): raise ValueError('audit lists no checkpoints: ' + str(directory))
    outs = [{'file': f'merged/N{N}.json', 'sha256': sha(directory / 'merged' / f'N{N}.json')} for N in m['degrees']]
    if outs != audit.get('outputs'): raise ValueError('merged outputs differ from the audit: ' + str(directory))
    for N in m['degrees']:
        o = json.loads((directory / 'merged' / f'N{N}.json').read_text())
        if (o.get('L'), o.get('N'), o.get('replicates'), o.get('seed'), o.get('counts'), o.get('manifest_sha256'), o.get('complete'),
                len(o.get('batches', []))) != (m['L'], N, m['replicates'], m['seed'], m['counts'], mh, True, m['replicates']):
            raise ValueError(f'merged output N{N} does not match its manifest: ' + str(directory))
    LIGHT['campaigns'] += 1; LIGHT['checkpoints_listed'] += len(audit['sources'])
    return {'manifest': m, 'manifest_sha256': mh, 'audit': audit}


LIGHT = {'campaigns': 0, 'checkpoints_listed': 0}
_orig_inputs = campaign.campaign_inputs


def make_inputs_mapper(shared: Path):
    def campaign_inputs(directory: Path, m: dict) -> Path:
        p = _orig_inputs(directory, m)
        return p if p.is_dir() else shared
    return campaign_inputs


def build_inputs(dst: Path, data: Path, ref_manifest: Path) -> None:
    """Shared numerical inputs of loops 6-8, each checked against the hashes recorded by the campaign manifests."""
    rec = {}
    for g in sorted(ref_manifest.parent.parent.glob('*/manifest.json')):  # every campaign of batch b1
        rec.update(json.loads(g.read_text())['input_sha256'])
    dst.mkdir(parents=True)
    for name in SHARED:
        out = dst / name
        if name == 'L8_coord.txt':
            with lzma.open(data / 'inputs8' / 'L8_coord.txt.xz') as f, out.open('wb') as g: shutil.copyfileobj(f, g, 1 << 22)
        else:
            shutil.copyfile(PKG / 'inputs8' / name, out)
        h = sha(out)
        if rec.get(name) != h: raise ValueError(f'input {name}: sha256 {h} differs from the campaign manifests ({rec.get(name)})')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data', type=Path, default=Path('../../data/C8_1'))
    ap.add_argument('--work', type=Path, default=Path('.work'))
    ap.add_argument('--only', choices=sorted(RUNS), nargs='*', help='subset of the combinations (default: all three)')
    a = ap.parse_args()
    data = a.data.resolve(); work = a.work.resolve(); tree = work / 'c8_hpc'
    if tree.exists(): shutil.rmtree(tree)
    if (work / 'inputs_shared').exists(): shutil.rmtree(work / 'inputs_shared')
    t0 = time.time()
    shutil.copytree(data / 'c8_hpc', tree, ignore=shutil.ignore_patterns('results'))
    build_inputs(work / 'inputs_shared', data, tree / 'runs/prod4/b1/tprodA_L8/manifest.json')
    mapper = make_inputs_mapper(work / 'inputs_shared')
    for mod in (campaign, assemble8, combine8):
        if hasattr(mod, 'verify_campaign'): mod.verify_campaign = light_verify
        if hasattr(mod, 'campaign_inputs'): mod.campaign_inputs = mapper
    print(f'work tree ready in {time.time() - t0:.1f} s: {tree}', flush=True)
    os.chdir(tree); status = {}
    for name in (a.only or ['K4', 'A1', 'K14']):
        args, out = RUNS[name]; t1 = time.time(); LIGHT.update(campaigns=0, checkpoints_listed=0)
        sys.argv = ['combine8.py'] + args + ['--affine', AFF, '--exact5', *EX5, '--design-meta', META]
        try:
            combine8.main(); ok = (tree / out).is_file()
        except (OSError, ValueError, ArithmeticError) as e:
            print(f'{name}: combine failed: {e}', file=sys.stderr); ok = False
        status[name] = {'ok': ok, 'output': out, 'seconds': round(time.time() - t1, 1), **LIGHT}
        print(f'{name}: {"done" if ok else "FAILED"} in {status[name]["seconds"]} s ({LIGHT["campaigns"]} campaign verifications, '
              f'{LIGHT["checkpoints_listed"]} checkpoints listed in their audits, not re-validated)', flush=True)
    (work / 'replay_status.json').write_text(json.dumps(status, indent=2) + '\n')
    return 0 if all(v['ok'] for v in status.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
