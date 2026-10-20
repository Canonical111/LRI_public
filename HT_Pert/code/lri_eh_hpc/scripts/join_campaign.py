#!/usr/bin/env python3
"""Strict, provenance-checked correction join. No fitting or interpolation."""
import argparse,csv,hashlib,io,json,math,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lri_eh.runtime import atomic_json,claim,seal,validate_result
from lri_eh._core.solver import second_order_shell_value


def read_rows(path):
    x=json.loads(Path(path).read_text())
    if isinstance(x,list):return x
    if isinstance(x,dict) and 'cutoff' in x:return [x]
    raise ValueError('Expected one JSON record or list of per-cutoff records: '+str(path))


def join(raw_paths,correction_paths,degree,raw_source,correction_source):
    if len(raw_source)<12 or any(x not in '0123456789abcdef' for x in raw_source):raise ValueError('Expected reviewed raw fingerprint/prefix >=12 hexadecimal characters')
    if len(correction_source)!=64:raise ValueError('Expected full correction source SHA-256')
    delta={}
    for f in correction_paths:
        for d in read_rows(f):
            validate_result(d)
            if d['source_sha256']!=correction_source:raise ValueError('Unexpected correction source')
            if d['degree']<degree:continue
            L=d['cutoff']
            if L in delta:raise ValueError('Duplicate correction cutoff; select one degree explicitly')
            delta[L]=d
    output=[];seen=set()
    for f in raw_paths:
        rawfile=hashlib.sha256(Path(f).read_bytes()).hexdigest()
        for r in read_rows(f):
            L=r.get('cutoff')
            if L in seen:raise ValueError('Duplicate raw cutoff')
            seen.add(L)
            if r.get('task','thermal')!='thermal' or 'raw_C' in r or 'delta_C' in r or r.get('prescription','raw')!='raw':raise ValueError('Input is not raw thermal data; refusing possible double correction')
            if not r.get('source_sha256','').startswith(raw_source):raise ValueError('Unexpected/missing reviewed raw source fingerprint')
            c=r.get('C',[]);d=delta.get(L)
            if d is None:raise ValueError(f'No degree-{degree} correction at L={L}; no interpolation')
            if len(c)<degree+1 or not all(isinstance(x,(int,float)) and math.isfinite(x) for x in c):raise ValueError('Incomplete/nonfinite raw C')
            tuning=r.get('tuning_residual')
            if not isinstance(tuning,(int,float)) or not math.isfinite(tuning) or tuning<0 or tuning>1e-6:raise ValueError('Missing/failed raw tuning gate; use expanded gated JSON exports')
            if abs(c[0]-.5)>1e-10 or abs(c[1]+1/6)>1e-10:raise ValueError('Raw low-order normalization failed')
            if abs(c[2]-second_order_shell_value(L))>1e-10:raise ValueError('Raw shell gate failed')
            rec=dict(cutoff=L,degree=degree,prescription='PARTIAL isolated-vacuum matched',
                     scope='Not complete effective-Hamiltonian matching; isolated delta C4 contains log(L)/17496. No continuum error claim.',
                     raw_source_sha256=r['source_sha256'],correction_source_sha256=d['source_sha256'],
                     raw_file_sha256=rawfile,correction_payload_sha256=d['payload_sha256'],
                     raw_C=c[:degree+1],delta_C=d['delta_C'][:degree+1],
                     C=[c[k]+d['delta_C'][k] for k in range(degree+1)],
                     uncorrected_higher_coefficients_omitted=len(c)>degree+1)
            for k in ('r','g'):
                if k in r:
                    if len(r[k])<degree+1 or not all(math.isfinite(x) for x in r[k]):raise ValueError('Invalid raw '+k)
                    rec[k]=[r[k][j]+d['delta_'+k][j] for j in range(degree+1)]
            output.append(seal(rec))
    return sorted(output,key=lambda x:x['cutoff'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--raw',type=Path,nargs='+',required=True);ap.add_argument('--corrections',type=Path,nargs='+',required=True)
    ap.add_argument('--degree',type=int,choices=[4,5,6,7],default=7)
    ap.add_argument('--expected-raw-source',required=True);ap.add_argument('--expected-correction-source',required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    if a.output.suffix!='.json':raise ValueError('Output must end in .json')
    with claim(a.output.with_suffix('.lock')):
        csvfile=a.output.with_suffix('.csv')
        if a.output.exists() or csvfile.exists():raise FileExistsError('Output exists')
        rows=join(a.raw,a.corrections,a.degree,a.expected_raw_source,a.expected_correction_source)
        # Canonical JSON first; CSV is a derivative and can be reconstructed.
        atomic_json(a.output,rows)
        fd,tmpname=tempfile.mkstemp(prefix=csvfile.name+'.tmp.',dir=csvfile.parent)
        tmp=Path(tmpname)
        with os.fdopen(fd,'w',newline='') as f:
            w=csv.writer(f);w.writerow(['cutoff']+[f'C{k}' for k in range(a.degree+1)])
            for r in rows:w.writerow([r['cutoff']]+r['C'])
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,csvfile)
    print(f'{len(rows)} partially corrected records; no continuum fitting or missing-cutoff interpolation.')
if __name__=='__main__':main()
