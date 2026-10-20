"""Stage C: verify every collected record and reduce it to per-item summaries and plot data.

Reads   data/records/<campaign>/<item id>.json      (gated result records, from collect_records.py)
        inputs/manifests/<campaign>.json            (frozen manifests: item definitions + solver source hash)
        inputs/validation_receipt/receipt.json      (compute-node runtime the records must carry)
        data/lane_logs/<job>/events.jsonl           (per-item wall time, threads, peak RSS)
Writes  data/summaries/<campaign>_summary.json      (one row per item: alpha_c, window audit, diagnostics)
        data/summaries/<campaign>_details.json      (all windows + per-site odd gap / log|d gap/d alpha|)
        data/summaries/resources.json               (core-hours and peak memory per lane job)

Every record is checked against its manifest item: identity (config, kind, bracket, tolerances, solver source,
runtime), checksum and the numerical acceptance gates. A mismatch aborts.
"""
import json,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'code'/'lri_spin_boson_hpc'/'src'))
from lri_spin.io import read_record                       # noqa: E402
from lri_spin.manifest import load_manifest,result_checker   # noqa: E402

CAMPAIGNS=['example_K64_B10','ds13','lambda_pilot','lambda_followup']


def summarize_item(item,r):
    c=item['config'];f=r['critical_flow'];t=f['critical_tuning'];a=r['analysis'];tg=r['tangent']
    passed=[w for w in a['windows'] if w['gap_relative_variation']<.005 and w['log_response_residual']<.003]
    q=a['quality_window_range'];sel=a['selected']
    return {'id':item['id'],'ds':round((1-c['s'])/2,6),'s':c['s'],'Lambda':c['Lambda'],'keep':c['keep'],'nb':c['nb'],
            'nsites':c['nsites'],'threads':c['threads'],'alpha_c':f['alpha'],'bracket_width':t['bracket'][1]-t['bracket'][0],
            'terminal_residual':t['terminal_residual'],'bisect':r['tuning']['iteration'],
            'n_windows':len(a['windows']),'n_quality':a['number_of_quality_windows'],
            'q_lo':q[0] if q else None,'q_hi':q[1] if q else None,'q_mid':(q[0]+q[1])/2 if q else None,
            'q_first_start':min(w['start'] for w in passed) if passed else None,
            'q_last_stop':max(w['stop'] for w in passed) if passed else None,
            'sel':sel['Delta_E'] if sel else None,'sel_start':sel['start'] if sel else None,
            'max_edge':max(x['last_boson_edge'] for x in f['records']),
            'max_occ':max(x['last_boson_occupation'] for x in f['records']),
            'min_gap':tg.get('minimum_kept_discarded_gap'),
            'max_eigen_residual':max(f['validation']['max_checked_eigen_residual'],tg['validation']['max_checked_eigen_residual']),
            'max_orthogonality':max(f['validation']['max_checked_orthogonality'],tg['validation']['max_checked_orthogonality'])}


def details_item(item,r):
    tg=r['tangent']
    return {'id':item['id'],
            'windows':[{k:w[k] for k in ('start','stop','Delta_E','log_response_residual','gap_relative_variation')}
                       for w in r['analysis']['windows']],
            'odd_gap':[x['odd_gap'] for x in tg['records']],
            'log_abs_d_alpha_odd_gap':[x['log_abs_d_alpha_odd_gap'] for x in tg['records']]}


def resources():
    out=[]
    for d in sorted((ROOT/'data'/'lane_logs').iterdir()):
        ev=[json.loads(l) for l in (d/'events.jsonl').read_text().splitlines()]
        start={e['id']:e for e in ev if e['event']=='start'};end=[e for e in ev if e['event']=='end']
        out.append({'job':d.name,'items_started':len(start),'items_ended':len(end),
                    'core_hours':sum(e['seconds']*start[e['id']]['threads'] for e in end)/3600,
                    'longest_item_hours':max((e['seconds'] for e in end),default=0)/3600,
                    'max_peak_rss_mib':max((e['peak_rss_kib'] for e in end),default=0)/1024,
                    'nonzero_rc':[(e['id'],e['rc']) for e in end if e['rc']]})
    return out


def main():
    receipt=read_record(ROOT/'inputs'/'validation_receipt'/'receipt.json')
    if not receipt.get('passed'):raise SystemExit('receipt did not pass')
    outdir=ROOT/'data'/'summaries';outdir.mkdir(parents=True,exist_ok=True)
    for camp in CAMPAIGNS:
        m=load_manifest(ROOT/'inputs'/'manifests'/f'{camp}.json')
        if m['source_sha256']!=receipt['source_sha256']:raise SystemExit(f'{camp}: manifest/receipt source mismatch')
        rows,details=[],[]
        for item in m['items']:
            path=ROOT/'data'/'records'/camp/f'{item["id"]}.json'
            r=result_checker(item,m['source_sha256'],receipt['runtime'])(path)   # identity + checksum + gates
            rows.append(summarize_item(item,r));details.append(details_item(item,r))
        (outdir/f'{camp}_summary.json').write_text(json.dumps(rows,indent=1)+'\n')
        (outdir/f'{camp}_details.json').write_text(json.dumps(details)+'\n')
        print(f'{camp}: {len(rows)} records verified')
    (outdir/'resources.json').write_text(json.dumps(resources(),indent=1)+'\n')
    print('resources.json written')


if __name__=='__main__':
    main()
