"""Independent Fraction check of the four mixed-volume divergence coefficients.
The complete new dimensionless mixed boundary is integrated independently.
Explicit scale terms use the measured base/v/d boundary jets and the
squared-charge singular jet fixed by the lower-moment normalization.
Neither the new finite residue nor the C8 conjecture is an input.
"""
from pathlib import Path
from fractions import Fraction as Q
import json,hashlib,argparse
ROOT=Path(__file__).resolve().parent.parent
DEMANDS=[[-2,0],[-2,1],[-1,0],[-1,1]]
def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def main(allow_incomplete=False):
    folder=ROOT/'boundary_batches';manifest=json.loads((folder/'manifest.json').read_text())
    faces={f:[Q(0)]*4 for f in (1,2,3)};missing=[];files=[]
    for row in manifest:
        p=folder/Path(row['path']).name;d=p.with_suffix('.negative_moments.json')
        if not d.exists():missing.append(d.name);continue
        data=json.loads(d.read_text());source=p.with_suffix('.stage2.jsonl') if row['stage']==1 else p
        assert data['source_sha256']==digest(source)
        assert data['demands']==DEMANDS
        main_result=json.loads(p.with_suffix('.result.json').read_text())
        iv=list(map(Q,data['values']));bv=list(map(Q,main_result['values']))
        assert 2*iv[0]-iv[1]==bv[1],('Inverse-Euler batch identity',p.name,-2)
        assert iv[2]-iv[3]==bv[2],('Inverse-Euler batch identity',p.name,-1)
        faces[row['face']]=[a+Q(b) for a,b in zip(faces[row['face']],data['values'])]
        files.append({'file':d.name,'sha256':digest(d)})
    if missing:
        if not allow_incomplete:raise RuntimeError(f'{len(missing)} divergence moment blocks missing')
        report={'status':'incomplete','completed':len(files),'missing':len(missing),'face_subtotals':{str(k):list(map(str,v)) for k,v in faces.items()}}
        (ROOT/'negative_partial_report.json').write_text(json.dumps(report,indent=2));print(report);return
    total=[sum(faces[f][j]*(2 if f<3 else 1) for f in (1,2,3)) for j in range(4)]
    controls=json.loads((ROOT/'vv_singular_control.json').read_text());lower=json.loads((ROOT/'lower_divergence_prediction.json').read_text());checks=[]
    for idx,(power,degree) in enumerate(DEMANDS):
        entry=next(e for e in controls['entries'] if e['power']==power)
        target=next(e for e in lower['prediction'] if e['power']==power)
        correction=Q(entry['scale_correction_to_mixed_volume'][degree])
        expected=Q(target['constant' if degree==0 else 'single_log'])
        predicted_dimensionless=Q(entry['expected_dimensionless_mixed_moments'][degree])
        actual=total[idx]+correction
        checks.append({'power':power,'log_degree':degree,'measured_dimensionless_moment':str(total[idx]),'independent_dimensionless_prediction':str(predicted_dimensionless),'known_scale_correction':str(correction),'physical_volume_coefficient':str(actual),'lower_moment_prediction':str(expected),'exact_equal':actual==expected and total[idx]==predicted_dimensionless})
    result={'status':'exact_divergence_checks_passed' if all(c['exact_equal'] for c in checks) else 'divergence_checks_failed',
        'checks':checks,'face_values':{str(k):list(map(str,v)) for k,v in faces.items()},'complete_batches':len(files),'per_batch_inverse_Euler_identity_checks':2*len(files),'no_new_finite_coefficient_used':True,'C8_conjecture_used':False,'squared_charge_control_source':'exact lower-moment singular factorization; not a full new finite Bvv integration','input_hashes':files,'lower_prediction_sha256':digest(ROOT/'lower_divergence_prediction.json'),'scale_control_sha256':digest(ROOT/'vv_singular_control.json')}
    (ROOT/'mixed_divergence_checks.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='input_hashes'},indent=2))
    assert all(c['exact_equal'] for c in checks),'Mixed scale/divergence check mismatch'
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--allow-incomplete',action='store_true');a=p.parse_args();main(a.allow_incomplete)
