"""Independent exact coverage and coefficient assembly; standard library only.

This checks the complete regulated boundary sum, not a fitted R6 value. It
uses ordinary Fractions and compares every disjoint shard with its original
source-line range. No integration-module implementation is imported.
"""
from pathlib import Path
from fractions import Fraction as Q
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parent.parent

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def verify(allow_incomplete=False):
    folder=ROOT/'boundary_batches'
    manifest=json.loads((folder/'manifest.json').read_text())
    assert len({Path(x['path']).name for x in manifest})==len(manifest)
    faces=[];missing=[];all_results=[]
    for face,stage in [(1,2),(2,1),(3,1)]:
        src=ROOT/'boundary'/f'B6_vd_f{face}_stage{stage}.jsonl'
        digest=sha(src);entries=sorted((x for x in manifest if x['face']==face),key=lambda x:x['start'])
        value=[Q(0)]*3;cursor=0;complete=0;checkpoints=[]
        with src.open('rb') as stream:
            for row in entries:
                assert row['source_sha256']==digest and row['stage']==stage
                assert row['start']==cursor and row['stop']>cursor
                lines=[stream.readline() for _ in range(row['stop']-cursor)]
                assert all(lines),'Source ends before declared range'
                p=folder/Path(row['path']).name
                data=b''.join(lines)
                assert p.read_bytes()==data,('Shard differs from source',p.name)
                cursor=row['stop'];result=p.with_suffix('.result.json')
                if not result.exists():missing.append(result.name);continue
                d=json.loads(result.read_text())
                assert d['status']=='complete disjoint batch'
                assert d['input_sha256']==hashlib.sha256(data).hexdigest()
                assert d['source_rows']==len(lines) and d['source_stage']==stage
                assert d['demands']==[[0,0],[-2,0],[-1,0]]
                assert len(d['values'])==3
                value=[x+Q(y) for x,y in zip(value,d['values'])];complete+=1
                all_results.append({'file':result.name,'sha256':sha(result)})
                mid=p.with_suffix('.stage2.jsonl') if stage==1 else p
                if stage==1:assert mid.exists()
                checkpoints.append({'file':mid.name,'sha256':sha(mid)})
            assert not stream.read(1),'Source lines omitted from partition'
        faces.append({'face':face,'multiplicity':2 if face<3 else 1,'source_rows':cursor,'source_sha256':digest,
            'batches':len(entries),'completed_batches':complete,'values':list(map(str,value)),
            'complete':complete==len(entries),'intermediate_checkpoints':checkpoints})
    report={'status':'incomplete' if missing else 'complete boundary sum','definition':'pi_0 [epsilon^0 log(epsilon)] partial_v partial_delta Q6 at v=1,delta=0',
       'method':'minus the constant part of -epsilon d/d epsilon of the regulated moment',
       'demands_for_each_face':[[0,0],[-2,0],[-1,0]],'faces':faces,'missing':missing,
       'total_batches':len(manifest),'complete_batches':len(all_results),'result_hashes':all_results,
       'coverage':'Each disjoint shard compared byte-for-byte with its consecutive original source range',
       'C8_conjecture_used':False,'old_epoch_subtotals_used':False}
    if missing:
        if not allow_incomplete:raise RuntimeError(f'{len(missing)} incomplete batches')
        return report
    total=[sum(Q(f['values'][i])*f['multiplicity'] for f in faces) for i in range(3)]
    checks=[{'power':p,'actual':str(v),'expected_from_lower_divergences':str(expected),'exact_equal':v==expected}
        for p,v,expected in [(-2,total[1],Q(18)),(-1,total[2],Q(1638))]]
    r=-total[0]
    report.update({'boundary_total':list(map(str,total)),'power_checks':checks,'R6':str(r),
        'C8_contribution':str(-r/2),'updated_C8_constant':str(Q(5345,12)-r/2),
        'remaining_C8_groups':['R8','R_tail','R9']})
    assert all(x['exact_equal'] for x in checks),('Independent divergence check failed',checks)
    report['status']='exact_Task_A_complete_with_boundary_controls'
    return report

if __name__=='__main__':
    pa=argparse.ArgumentParser();pa.add_argument('--allow-incomplete',action='store_true');pa.add_argument('--output')
    a=pa.parse_args();r=verify(a.allow_incomplete)
    dest=Path(a.output) if a.output else ROOT/('partial_coverage_report.json' if a.allow_incomplete else 'Task_A_result.json')
    dest.write_text(json.dumps(r,indent=2))
    print(json.dumps({k:v for k,v in r.items() if k not in ['faces','result_hashes','missing']},indent=2))
    print('Face totals:',[(f['face'],f['completed_batches'],f['batches'],f['values']) for f in r['faces']])
