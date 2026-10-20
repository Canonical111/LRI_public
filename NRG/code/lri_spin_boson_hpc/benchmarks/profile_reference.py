"""Reproduce the initial profiler without overwriting shipped measurements."""
from pathlib import Path
import argparse,cProfile,pstats,sys
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'reference'))
from nrg import Config,run
from nrg_tangent import run_tangent
p=argparse.ArgumentParser();p.add_argument('--task',choices=['flow','tangent'],default='flow');p.add_argument('--output',required=True);a=p.parse_args()
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from lri_spin.campaign import refuse_campaign_destination
refuse_campaign_destination(a.output)   # never write benchmark output into campaign state
f=run if a.task=='flow' else run_tangent
c=Config(s=.8,Lambda=3,keep=48,nb=10,nsites=30,threads=1)
pr=cProfile.Profile();pr.enable();r=f(.43977045457263714,c);pr.disable()
with open(a.output,'w') as log:pstats.Stats(pr,stream=log).sort_stats('cumtime').print_stats(30)
