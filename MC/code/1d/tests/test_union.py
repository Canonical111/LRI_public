#!/usr/bin/env python3
"""§4.7 union-data schema, end to end on a tiny point: two campaigns per (s, N) (engine v1 'stageA' and engine 1d 'stageBx'), registry active
lists (legacy string values read as lists; activation appends, never replaces), completion evidence per campaign, analysis at three block
sizes, union merge (5 x 2 entries per pair, coincident temperature kept, campaign/task stamps), union_check (PASS; a duplicated chain archive or a
shared seed -> FAIL), window_filter list-aware, select_model_v3.validate_inputs and verify_lineage on the union, and the reuse of registry
consumers by run_point_v3.sh (snapshot + finalize up to the merge)."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import registry, run_task
sys.argv=['x']; import select_model_v3 as v3

def sh(*cmd,check=True,**kw):
    r=subprocess.run([str(c) for c in cmd],capture_output=True,text=True,**kw)
    if check and r.returncode: raise AssertionError(f'{cmd[0]} failed: {r.stderr[-600:]}\n{r.stdout[-400:]}')
    return r

def prepare(D,name,engine,N,beta,ns):
    c=D/f'centres_{name}.csv'; c.write_text(f's,N,beta\n0.65,,{beta}\n')
    sh(sys.executable,ROOT/'prepare.py','--out',D/name,'--s','0.65','--sizes',str(N),'--replicas','2','--measurements','90000','--warmup','100','--beta-points','5',
       '--beta-halfwidth','0.002','--window-exponent','0','--centers',c,'--seed-base','31','--seed-namespace',ns,'--engine',engine)
    man=json.loads((D/name/'manifest.json').read_text())
    for t in man['tasks']: sh(*run_task.command(D/name,t['id']))
    return man

def main():
    report={}
    with tempfile.TemporaryDirectory(prefix='lri-union-') as tmp:
        D=Path(tmp)/'ds0.175'; D.mkdir(); N=64
        mA=prepare(D,'stageA','v1',N,0.31,'A'); mB=prepare(D,'stageBx_64','1d',N,0.31,'Bx')    # coincident central temperature by construction
        reg=dict(root=str(D),measurements=90000,replicas=2,beta_points=5,expected_pairs=[f'0.65:{N}'],stageA_max_N=N,
                 campaigns=[dict(name='stageA',dir='stageA',stage='A',seed_base=31,s=[0.65],sizes=[N],status='complete',job_ids=[1]),
                            dict(name='stageBx_64',dir='stageBx_64',stage='Bx',engine='1d',seed_base=31,s=[0.65],sizes=[N],status='complete',job_ids=[2])],
                 active={f'0.65:{N}':'stageA'})                                  # legacy string value
        (D/'campaigns.json').write_text(json.dumps(reg,indent=1))
        r=registry.load(D/'campaigns.json'); assert r['active'][f'0.65:{N}']==['stageA']       # legacy string -> list
        pairs=registry.validate(r,D,'all'); assert [c['name'] for c,_ in pairs[f'0.65:{N}']]==['stageA']
        sh(sys.executable,ROOT/'registry.py',D/'campaigns.json','--activate','stageBx_64')      # appends, never replaces
        r=registry.load(D/'campaigns.json'); assert r['active'][f'0.65:{N}']==['stageA','stageBx_64'] and registry.active_names(r)==['stageA','stageBx_64']
        report['active_lists']=True
        # snapshot on this host: completion evidence + analyses
        T='T1'; sh('bash',ROOT/'run_point_v3.sh','snapshot',D,T,cwd=ROOT)
        host=os.uname().nodename.split('.')[0]
        ev=json.loads((D/f'completion_{T}_{host}.json').read_text()); assert ev['result']=='PASS' and len(ev['tasks'])==20 and set(ev['campaigns'])=={'stageA','stageBx_64'} and all('s' in t and 'samples_sha256' in t for t in ev['tasks'])
        for b in (2048,4096,8192):
            for n in ('stageA','stageBx_64'): assert (D/f'{n}_an_b{b}_{T}/summary.json').exists()
        assert (D/f'registry_{T}_{host}.json').exists() and (D/f'analysis_v3_{T}_{host}.manifest').exists()
        report['snapshot']=True
        # finalize through the merge (RUN_POINT_V3_STOP_AFTER_MERGE=1): per-host manifest verified and assembled, registry snapshot compared
        # in its portable view (a different root must not matter), union_check PASS, three merged summaries
        rs=json.loads((D/f'registry_{T}_{host}.json').read_text()); rs['root']='/some/other/host/root/ds0.175'; (D/f'registry_{T}_{host}.json').write_text(json.dumps(rs))   # hash changes -> re-list it
        man=D/f'analysis_v3_{T}_{host}.manifest'; import hashlib; lines=man.read_text().splitlines()
        lines=[l if not l.endswith(f'registry_{T}_{host}.json') else f"{hashlib.sha256((D/f'registry_{T}_{host}.json').read_bytes()).hexdigest()}  {D/f'registry_{T}_{host}.json'}" for l in lines]; man.write_text('\n'.join(lines)+'\n')
        (D/'pre.json').write_text(json.dumps({'0.65':dict(beta_c=.31,Delta_epsilon=.5)}))
        r=sh('bash',ROOT/'run_point_v3.sh','finalize',D,T,D/'pre.json',cwd=ROOT,env={**os.environ,'RUN_POINT_V3_STOP_AFTER_MERGE':'1'})
        assert 'portable view identical' in r.stdout and (D/f'analysis_v3_{T}.manifest').exists() and (D/f'union_check_{T}.json').exists(),r.stdout[-600:]
        for b in (2048,4096,8192): assert (D/f'merged_b{b}_{T}/summary.json').exists()
        # a registry snapshot with a different campaign list is refused
        rs['campaigns'][0]['seed_base']=99; (D/f'registry_{T}_{host}.json').write_text(json.dumps(rs)); lines=[l if not l.endswith(f'registry_{T}_{host}.json') else f"{hashlib.sha256((D/f'registry_{T}_{host}.json').read_bytes()).hexdigest()}  {D/f'registry_{T}_{host}.json'}" for l in lines]; man.write_text('\n'.join(lines)+'\n')
        for b in (2048,4096,8192): shutil.rmtree(D/f'merged_b{b}_{T}')
        # RV3-003: a finalize attempt is immutable while its published manifest exists
        r=sh('bash',ROOT/'run_point_v3.sh','finalize',D,T,D/'pre.json',cwd=ROOT,check=False,env={**os.environ,'RUN_POINT_V3_STOP_AFTER_MERGE':'1'}); assert r.returncode!=0 and 'immutable' in r.stdout+r.stderr
        (D/f'analysis_v3_{T}.manifest').unlink()   # explicit removal of the previous attempt, then the divergent registry snapshot is refused
        r=sh('bash',ROOT/'run_point_v3.sh','finalize',D,T,D/'pre.json',cwd=ROOT,check=False,env={**os.environ,'RUN_POINT_V3_STOP_AFTER_MERGE':'1'}); assert r.returncode!=0 and 'differs from the gathering registry' in r.stdout+r.stderr and not (D/f'analysis_v3_{T}.manifest').exists()
        rs['campaigns'][0]['seed_base']=31; (D/f'registry_{T}_{host}.json').write_text(json.dumps(rs)); lines=[l if not l.endswith(f'registry_{T}_{host}.json') else f"{hashlib.sha256((D/f'registry_{T}_{host}.json').read_bytes()).hexdigest()}  {D/f'registry_{T}_{host}.json'}" for l in lines]; man.write_text('\n'.join(lines)+'\n')
        report['finalize_through_merge']=True
        for b in (2048,4096,8192): shutil.rmtree(D/f'merged_b{b}_{T}',ignore_errors=True)
        sh(sys.executable,ROOT/'merge_summaries.py',D/'campaigns.json','--coverage','all','--suffix',f'_an_b4096_{T}','--out',D/f'merged_b4096_{T}')
        S=json.loads((D/f'merged_b4096_{T}/summary.json').read_text())
        assert S['union'] and len(S['entries'])==10 and all(e['campaign'] in ('stageA','stageBx_64') and len(e['task_ids'])==2 for e in S['entries'])
        cen=[e for e in S['entries'] if abs(e['beta']-0.31)<1e-12]; assert len(cen)==2 and {e['campaign'] for e in cen}=={'stageA','stageBx_64'}   # coincident temperature kept twice
        assert [e['campaign_index'] for e in S['entries'] if e['campaign']=='stageBx_64']==[1]*5
        report['union_merge']=True
        # RV3-001: exact registry coverage — the union summary covers the active union; a summary lacking one campaign's chains does not
        evf=D/f'completion_{T}_{host}.json'
        ok,notes,rec=v3.verify_coverage(D/f'merged_b4096_{T}',D/'campaigns.json',[evf]); assert ok and rec['campaign_pairs_checked']==2 and rec['registry_authenticated_by'].endswith('campaigns.json'),notes
        Sm=json.loads((D/f'merged_b4096_{T}/summary.json').read_text()); part=D/'merged_partial'; part.mkdir()
        (part/'summary.json').write_text(json.dumps(dict(Sm,entries=[e for e in Sm['entries'] if e['campaign']=='stageA'])))
        ok,notes,_=v3.verify_coverage(part,D/'campaigns.json',[evf]); assert not ok and 'incomplete' in ' '.join(notes),notes
        Sa=dict(Sm,coverage='stageA'); (part/'summary.json').write_text(json.dumps(Sa)); ok,notes,_=v3.verify_coverage(part,D/'campaigns.json',[evf]); assert not ok and "!= 'all'" in ' '.join(notes)
        assert not v3.verify_coverage(D/f'merged_b4096_{T}',None,[evf])[0]
        # R11-001: without evidence the definitions cannot be authenticated; a manifest changed after the snapshot is refused; an unauthenticated
        # registry (changed portable content, no matching snapshot) is refused, while a re-rooted registry snapshot with identical content passes
        ok,notes,_=v3.verify_coverage(D/f'merged_b4096_{T}',D/'campaigns.json',[]); assert not ok and 'cannot be authenticated' in ' '.join(notes)
        mpath=D/'stageBx_64'/'manifest.json'; orig=mpath.read_text(); mj=json.loads(orig); mj['tasks'][0]['seed']+=1; mpath.write_text(json.dumps(mj))
        ok,notes,_=v3.verify_coverage(D/f'merged_b4096_{T}',D/'campaigns.json',[evf]); assert not ok and 'manifest hash' in ' '.join(notes),notes
        mpath.write_text(orig)
        reg2=json.loads((D/'campaigns.json').read_text()); reg2['expected_pairs']=reg2['expected_pairs']+['0.65:128']; (D/'campaigns_changed.json').write_text(json.dumps(reg2))
        ok,notes,_=v3.verify_coverage(D/f'merged_b4096_{T}',D/'campaigns_changed.json',[evf]); assert not ok and ('not authenticated' in ' '.join(notes) or 'differs from the authenticated' in ' '.join(notes) or 'registry validation failed' in ' '.join(notes)),notes
        reg3=json.loads((D/'campaigns.json').read_text()); reg3['root']='/elsewhere/ds0.175'; (D/'campaigns_rerooted.json').write_text(json.dumps(reg3))
        shutil.copy(D/'campaigns.json',D/f'registry_{T}_hostB.json')   # an authentic snapshot copy (hash = the evidence's registry_sha256) next to the point
        ok,notes,rec=v3.verify_coverage(D/f'merged_b4096_{T}',D/'campaigns_rerooted.json',[evf]); assert ok and rec.get('registry_root_used') and rec['registry_authenticated_by'].endswith(f'registry_{T}_hostB.json'),notes
        (D/f'registry_{T}_hostB.json').unlink()
        # RV3-003: a snapshot attempt is immutable — repeating the same tag on the same host is refused before any write
        r=sh('bash',ROOT/'run_point_v3.sh','snapshot',D,T,cwd=ROOT,check=False); assert r.returncode!=0 and 'immutable' in r.stderr+r.stdout
        report['coverage_and_immutability']=True
        # union_check: PASS; then a copied archive (shared samples hash) and a shared seed -> FAIL
        sh(sys.executable,ROOT/'union_check.py',D/'campaigns.json','--tag',T,'--point-dir',D,'--out',D/f'union_check_{T}.json')
        assert json.loads((D/f'union_check_{T}.json').read_text())['result']=='PASS'
        bad=json.loads((D/f'completion_{T}_{os.uname().nodename.split(".")[0]}.json').read_text()); bad['tasks'][10]['samples_sha256']=bad['tasks'][0]['samples_sha256']
        evb=D/f'completion_{T}_hostB.json'; evb.write_text(json.dumps(bad)); os.rename(D/f'completion_{T}_{os.uname().nodename.split(".")[0]}.json',D/'hidden.json')
        r1=sh(sys.executable,ROOT/'union_check.py',D/'campaigns.json','--tag',T,'--point-dir',D,check=False); assert r1.returncode==1 and 'samples.bin archives shared' in r1.stdout
        bad=json.loads((D/'hidden.json').read_text()); bad['tasks'][10]['seed']=bad['tasks'][0]['seed']; bad['tasks'][10]['beta']=bad['tasks'][0]['beta']; evb.write_text(json.dumps(bad))
        r2=sh(sys.executable,ROOT/'union_check.py',D/'campaigns.json','--tag',T,'--point-dir',D,check=False); assert r2.returncode==1 and ('shared by several chains' in r2.stdout or 'differ from the manifest' in r2.stdout)
        evb.unlink(); os.rename(D/'hidden.json',D/f'completion_{T}_{os.uname().nodename.split(".")[0]}.json')
        report['union_check']=True
        # window_filter is list-aware (stamped entries keep their own campaign's grid metadata)
        sh(sys.executable,ROOT/'window_filter.py',D/f'merged_b4096_{T}/summary.json',D/'campaigns.json','--keep','1','2','3','--out',D/f'merged_b4096_{T}/summary_c3.json')
        assert len(json.loads((D/f'merged_b4096_{T}/summary_c3.json').read_text())['entries'])==6
        # v3 input validation on the union (block sizes 2048/8192 merged too) and lineage against a manifest that lists everything
        for b in (2048,8192): sh(sys.executable,ROOT/'merge_summaries.py',D/'campaigns.json','--coverage','all','--suffix',f'_an_b{b}_{T}','--out',D/f'merged_b{b}_{T}')
        ok,notes,by=v3.validate_inputs(D/f'merged_b4096_{T}',[D/f'merged_b2048_{T}',D/f'merged_b8192_{T}']); assert ok and sorted(by)==[2048,8192],notes
        import hashlib
        sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest(); lines=[f"{sha(D/'campaigns.json')}  campaigns.json"]
        evf=D/f'completion_{T}_{os.uname().nodename.split(".")[0]}.json'; lines.append(f'{sha(evf)}  {evf}')
        for b in (2048,4096,8192):
            f=D/f'merged_b{b}_{T}/summary.json'; lines.append(f'{sha(f)}  {f}')
            for e in json.loads(f.read_text())['entries']: q=(f.parent/e['blocks_file']).resolve(); lines.append(f'{sha(q)}  {q}')
        man=D/f'analysis_v3_{T}.manifest'; man.write_text('\n'.join(lines)+'\n')
        ev=json.loads(evf.read_text()); ev['registry_sha256']=sha(D/'campaigns.json'); evf.write_text(json.dumps(ev)); man.write_text('\n'.join(l for l in lines if 'completion_' not in l)+f'\n{sha(evf)}  {evf}\n')
        ok,notes,rec=v3.verify_lineage(D/f'merged_b4096_{T}',[D/f'merged_b2048_{T}',D/f'merged_b8192_{T}'],man,[evf],False); assert ok and rec['entries_matched']==10 and rec['evidence_tasks']==20,notes
        assert v3.multi_campaign_pairs(D/f'merged_b4096_{T}')==[(0.65,N)]
        report['union_validation_and_lineage']=True
        # REV-003: a complete 3-temperature supplemental campaign coexists with the 5-temperature ones (each validated against its own grid)
        c=D/'centres_sup.csv'; c.write_text('s,N,beta\n0.65,,0.31\n')
        sh(sys.executable,ROOT/'prepare.py','--out',D/'stageBx_64sup','--s','0.65','--sizes',str(N),'--replicas','2','--measurements','90000','--warmup','100','--beta-points','3',
           '--beta-halfwidth','0.001','--window-exponent','0','--centers',c,'--seed-base','77','--seed-namespace','sup','--engine','1d')
        msup=json.loads((D/'stageBx_64sup'/'manifest.json').read_text())
        for t in msup['tasks']: sh(*run_task.command(D/'stageBx_64sup',t['id']))
        reg=json.loads((D/'campaigns.json').read_text()); reg['campaigns'].append(dict(name='stageBx_64sup',dir='stageBx_64sup',stage='Bx',engine='1d',seed_base=77,s=[0.65],sizes=[N],status='complete',job_ids=[3])); (D/'campaigns.json').write_text(json.dumps(reg,indent=1))
        r0=sh(sys.executable,ROOT/'registry.py',D/'campaigns.json','--activate','stageBx_64sup',check=False); assert r0.returncode!=0 and 'not a 5-point grid' in r0.stderr   # IR9-001: without a registered override the registry budget rules
        reg['campaigns'][-1]['grid']=dict(beta_points=3); (D/'campaigns.json').write_text(json.dumps(reg,indent=1))   # independently registered supplemental grid
        sh(sys.executable,ROOT/'registry.py',D/'campaigns.json','--activate','stageBx_64sup')
        r=registry.load(D/'campaigns.json'); pairs=registry.validate(r,D,'all'); assert [c['name'] for c,_ in pairs[f'0.65:{N}']]==['stageA','stageBx_64','stageBx_64sup']
        T2='T2'; sh('bash',ROOT/'run_point_v3.sh','snapshot',D,T2,cwd=ROOT)
        ev2=json.loads((D/f'completion_{T2}_{host}.json').read_text()); assert ev2['result']=='PASS' and len(ev2['tasks'])==26
        sh(sys.executable,ROOT/'merge_summaries.py',D/'campaigns.json','--coverage','all','--suffix',f'_an_b4096_{T2}','--out',D/f'merged_b4096_{T2}')
        S2=json.loads((D/f'merged_b4096_{T2}/summary.json').read_text()); assert len(S2['entries'])==13 and sum(1 for e in S2['entries'] if e['campaign']=='stageBx_64sup')==3
        report['supplemental_grid']=True
        # R12-003: the scan report marks a selected result HISTORICAL when its authenticated coverage does not match the current registry
        import hashlib,importlib.util
        spec=importlib.util.spec_from_file_location('scanrep',ROOT/'scan_v3_report.py');scanrep=importlib.util.module_from_spec(spec);spec.loader.exec_module(scanrep)
        cur=hashlib.sha256(json.dumps(registry.portable_view(registry.load(D/'campaigns.json')),sort_keys=True).encode()).hexdigest()
        def fake_run(name,cov_sha,production=True):
            d=D/name;d.mkdir(exist_ok=True)
            (d/'fit_v3.json').write_text(json.dumps(dict(production=production,points={'0.175':dict(Delta_sigma=0.175,s=0.65,decision='ACCEPTED',quoted=dict(Delta_epsilon=.5,sigma_stat=1e-3,config='x',degree=4),sigma_sys=dict(value=1e-3,ratio=1.,n_quotable=5),crossing_value=None,fallback_pairs=None,equilibration=dict(passed=True),crosscheck=dict(status='pass'))},provenance=dict(coverage=dict(verified=True,registry_portable_sha256=cov_sha)))))
        fake_run('fits_v3_20260101_000000',cur);(D/'fits_v3_SELECTED.json').write_text(json.dumps(dict(selected_run='fits_v3_20260101_000000',snapshot='X')))
        row=scanrep.load_point(D,0.175);assert row['status'].startswith('ACCEPTED') and 'HISTORICAL' not in row['status'] and row['production'],row['status']
        fake_run('fits_v3_20260101_000000','0'*64);row=scanrep.load_point(D,0.175);assert row['status'].startswith('AWAITING ANALYSIS; historical') and not row['production'],row['status']
        # R12-001: node scripts draw singleton names from the shared pool and carry the packing label as a comment (generation path, no submission)
        c=D/'centres_pack.csv'; c.write_text('s,N,beta\n0.65,,0.31\n')   # an unexecuted campaign (packing skips chains with DONE.json)
        sh(sys.executable,ROOT/'prepare.py','--out',D/'stageBx_64pack','--s','0.65','--sizes',str(N),'--replicas','2','--measurements','90000','--warmup','100','--beta-points','3',
           '--beta-halfwidth','0.001','--window-exponent','0','--centers',c,'--seed-base','78','--seed-namespace','pack','--engine','1d')
        r=sh(sys.executable,ROOT/'pack_nodes.py',D/'stageBx_64pack','--nodes','1','--slots','4','--out',D/'packtest','--name','ptest')
        sc=(D/'packtest'/'ptest0.sbatch').read_text();assert '#SBATCH -J lriN0' in sc and '#SBATCH --comment=pack:ptest' in sc and 'ptest0_ds0.175_stageBx_64pack_t' in sc and '_$SLURM_JOB_ID.out' in sc,sc[:600]
        pk=json.loads((D/'packtest'/'packing.json').read_text());assert pk['chains']==6 and all('log' in ch for q in pk['queues'] for ch in q)
        report['report_history_and_name_pool']=True
    (ROOT/'tests/union_test_results.json').write_text(json.dumps(report,indent=1)+'\n'); print('union schema checks passed',report)
if __name__=='__main__':main()
