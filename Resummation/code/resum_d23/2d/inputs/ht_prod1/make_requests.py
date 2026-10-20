"""Write campaign request JSONs (teach1, drill1, prod1) for cluster/expanse/campaign.py freeze.

Usage (on Expanse login): python make_requests.py RELEASE_TREE CAMPAIGN_ROOT OUTDIR
RELEASE_TREE: an extracted copy of the verified release (source of shipped teachers/seeds).
"""
import json,sys
from pathlib import Path
rel=Path(sys.argv[1]);root=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
LOGS='/home/zzheng8/lri2d_window/logs'
TOL={'eig_tol':1e-12,'residual_tol':1e-8,'tuning_tol':3e-11,'ncv':40,'maxiter':50,'backend':'tensor'}
REF_X=[0.126,0.15,0.2,0.25,0.3,0.35,0.4,0.45,0.475,0.495]
NEW_X=[0.135,0.175]
LADDER=list(range(8,25,2))

teach={'campaign':'teach1','logs':LOGS,
       'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-02:00:00','lead_s':1800,'max_cont':0},
       'common':{**TOL,'threads':8,'memory_limit_gib':12},
       'chains':{f'x{x:.3f}':{'x':x,'ladder':[6],'main':{'nz':24,'osc':192,'diagnostics':'none','train_keep':20},'checks':[]} for x in NEW_X}}

# x = 1/8 crossover benchmark: its teacher starts from the shipped x=0.126 L=6 teacher theta (frozen guess).
g126=json.loads((rel/'reference/results/teacher_L6_x0.126.json').read_text())['theta']
teach2={'campaign':'teach2','logs':LOGS,
        'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-02:00:00','lead_s':1800,'max_cont':0},
        'common':{**TOL,'threads':8,'memory_limit_gib':12},
        'chains':{'x0.125':{'x':0.125,'ladder':[6],'checks':[],
                            'main':{'nz':24,'osc':192,'diagnostics':'none','train_keep':20,'guess':[float(v) for v in g126]}}}}

def drill_chain(x,ladder,diag):
    return {'x':x,'ladder':ladder,'main':{'nz':16,'diagnostics':diag},'checks':[],
            'basis_src':str(rel/f'reference/results/teacher_L6_x{x:.3f}.json'),
            'initial_seed_src':str(rel/f'reference/results/window_L8_z16_x{x:.3f}.json'),
            'initial_seed_origin':'reference_same_L'}
drill3={'campaign':'drill3','logs':LOGS,
       'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-01:00:00','lead_s':1800,'max_cont':1},
       'common':{**TOL,'threads':8,'memory_limit_gib':12},
       'chains':{'g1':drill_chain(0.3,[8,10,12,14,16],'none'),       # D1 graceful USR1 + auto continuation
                 'k2':drill_chain(0.475,[8,10,12,14,16,18],'all'),  # D2 KILL (no USR1) + manual recovery + resubmit
                 'w4':drill_chain(0.45,[8,10,12,14,16,18],'all')}}  # D4 USR1 then immediate KILL (wall) + auto recovery
drill4={'campaign':'drill4','logs':LOGS,
       'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-01:00:00','lead_s':1800,'max_cont':1},
       'common':{**TOL,'threads':8,'memory_limit_gib':12},
       'chains':{'g1':drill_chain(0.3,[8,10,12,14,16],'none'),
                 'k2':drill_chain(0.475,list(range(8,21,2)),'all'),
                 'w4':drill_chain(0.45,list(range(8,21,2)),'all')}}
drill5={'campaign':'drill5','logs':LOGS,
       'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-01:00:00','lead_s':1800,'max_cont':0},
       'common':{**TOL,'threads':8,'memory_limit_gib':12},
       'chains':{'k2':drill_chain(0.475,list(range(8,21,2)),'all')}}
drill={'campaign':'drill2','logs':LOGS,
       'slurm':{'account':'yun124','partition':'shared','cpus':8,'mem_gb':16,'time':'0-01:00:00','lead_s':1800,'max_cont':1},
       'common':{**TOL,'threads':8,'memory_limit_gib':12},
       'chains':{'d1':drill_chain(0.3,[8,10,12,14,16],'none'),      # graceful USR1 + continuation; duplicate refusal
                 'd2':drill_chain(0.35,[8,10,12,14,16],'none'),     # hard kill + manual recovery + resubmit
                 'd4':drill_chain(0.4,[8,10,12,14,16,18],'all')}}   # USR1 in final segment + KILL + auto continuation

chains={}
CHECKS=[{'nz':20,'diagnostics':'all','L':'all'},{'nz':12,'diagnostics':'none','L':'all'}]
for x in REF_X:
    chains[f'x{x:.3f}']={'x':x,'ladder':LADDER,'main':{'nz':16,'diagnostics':'all'},'checks':CHECKS,
        'basis_src':str(rel/f'reference/results/teacher_L6_x{x:.3f}.json'),
        'initial_seed_src':str(rel/f'reference/results/window_L8_z16_x{x:.3f}.json'),'initial_seed_origin':'reference_same_L'}
for x,camp in [(v,'teach1') for v in NEW_X]+[(0.125,'teach2')]:
    t=root/camp/'chains'/f'x{x:.3f}'/'L6_z24.json'
    chains[f'x{x:.3f}']={'x':x,'ladder':LADDER,'main':{'nz':16,'diagnostics':'all'},'checks':CHECKS,
        'basis_src':str(t),'initial_seed_src':str(t),'initial_seed_origin':'teacher_L0m2'}
for x in (0.126,0.25,0.4):
    chains[f'ref{x:.3f}']={'x':x,'ladder':[14],'main':{'nz':32,'osc':256,'diagnostics':'none'},'checks':[],
        'seed_from':{'chain':f'x{x:.3f}','L':14,'nz':16},
        'common':{'threads':32,'memory_limit_gib':28},
        'slurm':{'cpus':32,'mem_gb':32,'time':'0-12:00:00','lead_s':1800,'max_cont':1}}
prod={'campaign':'prod1','logs':LOGS,
      'slurm':{'account':'yun124','partition':'shared','cpus':64,'mem_gb':64,'time':'2-00:00:00','lead_s':7200,'max_cont':2},
      'common':{**TOL,'threads':64,'memory_limit_gib':56},'chains':chains}
for name,req in (('teach1',teach),('teach2',teach2),('drill2',drill),('drill3',drill3),('drill4',drill4),('drill5',drill5),('prod1',prod)):
    (out/f'{name}.request.json').write_text(json.dumps(req,indent=1))
print('wrote',sorted(p.name for p in out.glob('*.request.json')))
