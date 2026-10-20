"""Re-evaluate selected disjoint integral blocks without altering proof data."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent

def main():
    pa=argparse.ArgumentParser(description=__doc__)
    pa.add_argument('--batch',action='append',help='For example f3_b0000; may be repeated.')
    pa.add_argument('--all',action='store_true',help='Re-evaluate all 359 blocks.')
    pa.add_argument('--from-stage2',action='store_true',help='Use the saved second-stage expressions; otherwise regenerate stage two when applicable.')
    pa.add_argument('--force',action='store_true',help='Replace only previously generated replay outputs.')
    pa.add_argument('--native',action='store_true',help='Use the bundled/rebuilt optional exact GMP accelerators.')
    a=pa.parse_args()
    if not a.all and not a.batch:pa.error('Select --batch or --all.')
    manifest=json.loads((ROOT/'boundary_batches/manifest.json').read_text())
    requested=set(a.batch or []);selected=[r for r in manifest if a.all or Path(r['path']).stem in requested]
    if not a.all and {Path(r['path']).stem for r in selected}!=requested:pa.error('Unknown batch label.')
    directory=ROOT/'replay_integrals';directory.mkdir(exist_ok=True)
    env={**os.environ,'R6_NATIVE':str(int(a.native)),'R6_LINEAR':str(int(a.native)),'R6_MOD':str(int(a.native)),'R6_ACCEL':'1','R6_SPLIT':'1','R6_SAVE_NEGATIVE':'1','OPENBLAS_NUM_THREADS':'1'}
    results=[]
    for row in selected:
        original=ROOT/'boundary_batches'/Path(row['path']).name
        stage=2 if a.from_stage2 else row['stage']
        source=original.with_suffix('.stage2.jsonl') if a.from_stage2 and row['stage']==1 else original
        copy=directory/original.name;shutil.copy2(source,copy)
        if a.force:
            for suffix in ('.result.json','.negative_moments.json','.stage2.jsonl'):
                p=copy.with_suffix(suffix)
                if p.exists():p.unlink()
        subprocess.run([sys.executable,str(ROOT/'engine/finish_boundaries.py'),'--path',str(copy),'--source-stage',str(stage)],env=env,check=True)
        actual=json.loads(copy.with_suffix('.result.json').read_text())
        expected=json.loads(original.with_suffix('.result.json').read_text())
        negative=json.loads(copy.with_suffix('.negative_moments.json').read_text())
        old_negative=json.loads(original.with_suffix('.negative_moments.json').read_text())
        assert actual['values']==expected['values'],original.name
        assert negative['values']==old_negative['values'],original.name
        results.append({'batch':original.stem,'main':actual['values'],'negative':negative['values'],'exact_equal':True})
        print('EXACT REPLAY MATCH',original.stem,flush=True)
    (directory/'comparison.json').write_text(json.dumps(results,indent=2))
if __name__=='__main__':main()
