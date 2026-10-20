#!/usr/bin/env python3
"""Collect the v3 results of every scan point into one table (FIT_MODEL_V3.md §4.6 labels).

Usage: scan_v2_report.py SCAN_ROOT [--out SCAN_ROOT/FIT_V2_SCAN.md] [--published reference/dimension_comparison.csv]
For each SCAN_ROOT/ds*/fits_v3_*/fit_v3.json (the newest per point) the decision, quoted value, sigma_stat, sigma_sys, quotable
count, cross-check status and the published Monte Carlo value (if any) are listed. Points without a v2 result are listed
as PENDING; nothing is dropped. No comparison with the epsilon expansion is made here.
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path

def published(path):
    pub={}
    if path and Path(path).exists():
        for r in csv.DictReader(open(path)):
            if r.get('published_MC_Delta_epsilon'):pub[round(float(r['Delta_sigma']),6)]=(float(r['published_MC_Delta_epsilon']),float(r['published_MC_quoted_error']),r['published_MC_source'])
    return pub

SCAN_GRID=[round(k/80,7) for k in range(1,20)]+[0.1727335]   # SCAN_PLAN.md: the twenty declared points
def label(ds):return ('%.7f'%ds).rstrip('0').rstrip('.')

def load_point(pt,ds,tol=5e-8):
    """Newest fits_v2 result of one point directory, matched to the declared coordinate (FIT-013: no fallback)."""
    runs=sorted(pt.glob('fits_v3_*/fit_v3.json'))
    def is_legacy(f):   # V3-STATIC-004: a legacy-window run is anchor reproduction (§4.1), never a scan determination
        try:return bool(json.load(open(f)).get('legacy_windows'))
        except (json.JSONDecodeError,OSError):return False
    legacy=[r.parent.name for r in runs if is_legacy(r)];runs=[r for r in runs if r.parent.name not in legacy]
    if not runs:return dict(ds=ds,status='PENDING (no fits_v3 result yet)'+(f' [legacy-window runs ignored: {legacy}]' if legacy else ''))
    # AUDIT-005: one selection policy — the driver's fits_v3_SELECTED.json names the validated run; newer unselected attempts are listed apart
    sel=pt/'fits_v3_SELECTED.json';chosen=runs[-1];note='';S=None
    if sel.exists():
        try:S=json.load(open(sel))
        except (json.JSONDecodeError,OSError) as ex:note=f' [selection file unreadable ({type(ex).__name__}); newest run used]'   # IR9-002
    if S is not None and (S.get('legacy_windows') or S.get('selected_run') in legacy):   # V3-STATIC-004: such a selection is invalid
        note=f" [selection {S.get('selected_run')} is a legacy-window run: ignored; newest x-window run used]";S=None
    if S is not None:
        cand=pt/S['selected_run']/'fit_v3.json'
        if cand.exists():chosen=cand
        else:note=f" [selection {S['selected_run']} missing; newest used]"
        newer=[r.parent.name for r in runs if r.parent.name>S['selected_run']]
        if newer:   # REV-007: an unreadable newer attempt is annotated, never fatal
            prod=[];broken=[]
            for n in newer:
                try:
                    if json.load(open(pt/n/'fit_v3.json')).get('production'):prod.append(n)
                except (json.JSONDecodeError,OSError):broken.append(n)
            note+=f" [newer unselected attempts: {newer}"+(f"; PRODUCTION runs not selected: {prod}" if prod else '')+(f"; unreadable: {broken}" if broken else '')+"]"
    elif not sel.exists():note=' [no selection file; newest run used]'
    try:rep=json.load(open(chosen))
    except (json.JSONDecodeError,OSError) as ex:return dict(ds=ds,status=f'UNREADABLE RESULT ({chosen.parent.name}: {type(ex).__name__})'+note)
    # R12-003: a result is CURRENT only if its authenticated coverage matches the point's current registry (portable view); otherwise it is
    # historical and the point is awaiting analysis on the changed active union
    hist=''
    reg=pt/'campaigns.json'
    if reg.exists():
        try:
            import hashlib,sys as _s;_s.path.insert(0,str(Path(__file__).resolve().parent));import registry as regmod
            cur=hashlib.sha256(json.dumps(regmod.portable_view(regmod.load(reg)),sort_keys=True).encode()).hexdigest()
            rec_cov=(rep.get('provenance',{}).get('coverage') or {})
            if not rec_cov.get('verified') or rec_cov.get('registry_portable_sha256')!=cur:hist=' [HISTORICAL: coverage of this result does not match the current registry — awaiting analysis on the active union]'
        except SystemExit as ex:hist=f' [current registry invalid: {ex}]'
        except (json.JSONDecodeError,OSError,ValueError,KeyError,TypeError) as ex:hist=f' [current registry unreadable ({type(ex).__name__}): coverage unverifiable at this moment]'   # R17-003
    else:hist=' [no registry: coverage unverifiable]'
    hits=[(k,P) for k,P in rep['points'].items() if abs(P.get('Delta_sigma',-1)-ds)<=tol and abs((1-P.get('s',-9))/2-ds)<=tol]
    if len(hits)!=1:return dict(ds=ds,status=f'INPUT MISMATCH ({chosen.parent.name} holds points {sorted(rep["points"])}, expected {label(ds)})'+note)
    P=hits[0][1];q=P.get('quoted') or {};ss=P.get('sigma_sys') or {};cv=P.get('crossing_value') or {};fb=P.get('fallback_pairs') or {}
    return dict(ds=ds,status=(('AWAITING ANALYSIS; historical: ' if hist.startswith(' [HISTORICAL') else '')+P['decision']+note+hist),run=chosen.parent.name,production=rep['production'] and not hist,Delta_epsilon=q.get('Delta_epsilon'),
        sigma_stat=q.get('sigma_stat'),sigma_sys=ss.get('value'),cap=ss.get('ratio'),n_quotable=ss.get('n_quotable'),range=ss.get('range'),
        config=q.get('config'),degree=q.get('degree'),xcheck=P.get('crosscheck',{}).get('status') or P.get('crosscheck',{}).get('standalone',{}).get('status'),
        Delta_inf=cv.get('Delta_inf'),sigma_inf=cv.get('sigma_inf'),Delta_omega=cv.get('Delta_omega_prime'),
        pairs=fb.get('pairs',[]),equilibration=P.get('equilibration',{}).get('passed'))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scan',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--grid',type=Path,help='CSV with a Delta_sigma column overriding the built-in 20-point grid')
    p.add_argument('--published',type=Path,default=Path(__file__).resolve().parent/'reference/dimension_comparison.csv')
    a=p.parse_args();pub=published(a.published);rows=[]
    grid=SCAN_GRID
    if a.grid:grid=sorted({round(float(r['Delta_sigma']),7) for r in csv.DictReader(open(a.grid))})
    for ds in sorted(grid):                                   # FIT-012: enumerate the declared grid, never the directories
        cands=[d for d in a.scan.glob('ds*') if d.is_dir() and abs(float(d.name[2:])-ds)<=5e-8]
        if not cands:rows.append(dict(ds=ds,status='MISSING INPUT (no point directory)'));continue
        if len(cands)>1:rows.append(dict(ds=ds,status=f'INPUT MISMATCH (several directories: {[d.name for d in cands]})'));continue
        rows.append(load_point(cands[0],ds))
    extra=[d.name for d in a.scan.glob('ds*') if d.is_dir() and not any(abs(float(d.name[2:])-ds)<=5e-8 for ds in grid)]
    f=lambda x,fmt='%.5f':'—' if x is None else fmt%x
    L=['# v3 protocol on the Δ_σ scan','',f'Declared grid: {len(grid)} points; newest fits_v2 snapshot per point; decisions per FIT_MODEL_V3.md §4.6. Published MC values from reference/dimension_comparison.csv.',
       ('Directories outside the declared grid (ignored): '+', '.join(extra)) if extra else '','',
       '| Δσ | decision | Δε | σ_stat | σ_sys (ratio to med σ_stat) | quotable | range | quoted configuration | cross-check | crossing value Δε∞ ± σ∞ ± Δω′ | largest pairs Δ_eff(U) / Δ_eff(Y) | equilibration | published MC |','|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    def esc(x):return str(x).replace('|','\\|')   # a '|' inside a cell (e.g. "|difference| > 2 sigma_D") must not split the markdown row
    for r in rows:
        r={k:(esc(v) if isinstance(v,str) else v) for k,v in r.items()}
        pb=pub.get(round(r['ds'],6));pbs=f"{pb[0]}({pb[1]}) {pb[2].split()[0]}" if pb else '—'
        if 'Delta_epsilon' not in r:L.append(f"| {label(r['ds'])} | {r['status']} | | | | | | | | | | | {pbs} |");continue
        rg=f"[{r['range'][0]:.5f}, {r['range'][1]:.5f}]" if r.get('range') else '—'
        cv=f"{f(r['Delta_inf'])} ± {f(r['sigma_inf'])} ± {f(r['Delta_omega'])}" if r.get('Delta_inf') is not None else '—'
        pr='; '.join(f"{q['N']}–{q['N2']}: {f(q['Delta_eff_U'])}({f(q['sigma_U'])}) / {f(q['Delta_eff_Y'])}({f(q['sigma_Y'])})" for q in r.get('pairs',[])) or '—'
        L.append(f"| {label(r['ds'])} | {r['status']}{'' if r['production'] else ' (NON-PRODUCTION)'} | {f(r['Delta_epsilon'])} | {f(r['sigma_stat'])} | {f(r['sigma_sys'])} ({f(r['cap'],'%.1f')}) | {r['n_quotable']} | {rg} | {r['config']} deg{r['degree']} | {r['xcheck']} | {cv} | {pr} | {r['equilibration']} | {pbs} |")
    out=a.out or a.scan/'FIT_V3_SCAN.md';out.write_text('\n'.join(L)+'\n');(out.with_suffix('.json')).write_text(json.dumps(rows,indent=1,default=float)+'\n');print(out)
if __name__=='__main__':main()
