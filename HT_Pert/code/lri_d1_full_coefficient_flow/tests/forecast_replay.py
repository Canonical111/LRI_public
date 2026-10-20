"""Regenerate one frozen model from prior input only and check all its forecasts."""
from pathlib import Path
import sys,json,hashlib
import mpmath as mp
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'code'),str(ROOT/'vendor')]
from freeze_forecasts import evaluate
from fit_models import sequential

def main():
    mp.mp.dps=70
    file=ROOT/'results/frozen_forecasts.json'
    expected=(ROOT/'results/forecast_sha256.txt').read_text().split()[0]
    assert hashlib.sha256(file.read_bytes()).hexdigest()==expected
    prior=json.loads((ROOT/'inputs/scheme_data.json').read_text())
    gap=json.loads((ROOT/'inputs/independent_gap_inputs.json').read_text())['extended']
    rows=json.loads(file.read_text())
    chosen=next(r for r in rows if (r['lo'],r['base'],r['mode'])==(8,'A','sources567'))
    fit=sequential(prior,gap,'dconn',8,{3:118,4:118,5:118,6:28,7:28,8:24},8,'A','sources567')
    errors=[]
    for L,values in chosen['predictions'].items():
        calculated=evaluate(fit,int(L),'A','sources567')
        from_record=evaluate(chosen['fit'],int(L),'A','sources567')
        for order in values:
            a=mp.mpf(values[order]);b=mp.mpf(calculated[order]);c=mp.mpf(from_record[order])
            errors.extend([abs(a-b)/max(1,abs(a)),abs(a-c)/max(1,abs(a))])
    maximum=max(errors)
    assert maximum<mp.mpf('1e-25'),maximum
    out=dict(model=dict(lo=8,base='A',mode='sources567'),forecasts_checked=len(chosen['predictions'])*7,
             max_scaled_difference=mp.nstr(maximum,20),unchanged_forecast_sha256=expected,
             scope='Replay uses the original finite input only. It does not validate the physical continuum ansatz.')
    (ROOT/'results/forecast_replay.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
