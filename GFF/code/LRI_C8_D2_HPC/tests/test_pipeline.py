#!/usr/bin/env python3
"""C8(2) pipeline tests with the fake integrator (PLAN component F; A-DES-1/2/6, A-ASM-6/7 on campaign directories,
A-ORC-9 sweep -> ledger -> accounting -> design, A-FLAG-6 / R14 / R19 rates flows). Pure Python (numpy, scipy), no
native build; runs in a scratch copy of the package (tests/pkgcopy.py: fake bin/c8d2_gmp, inputs_mini) with fake
sacct, scontrol and squeue. Records go only to --output.

Part 1, synthetic pilots in-process (tools/design.py):
  A-DES-1  full size (all 24,173 graphs of inputs/inventory.json, 16 replicates, campaign b 1.5x as costly as a):
           power-of-two counts >= 4096, replicates in [32, 128], the target met with the margin, an integer budget
           respected with --spent-core-hours and --total-cap, an infeasible budget refused with its minimum (= the hand
           value), the minimum batch count K and a smaller --batches refused with K, an atomic never-overwritten bundle,
           forbidden seeds = pilot seed + $C8_SEEDS, every cap enforced (a too-long shortest task refused by graph).
  A-DES-2  report prints the target table; the bundle's predicted SE equals an independent recomputation.
  F11/F13  (with A-DES-1/2/6) every target bundle (A-DES-1, d = 3, the imputed subsample, route (b)) passes
           check_optimizer, written independently: the target met, never costlier than either old rule's greedy design
           (r from the group's SMALLEST multiplier, F11, or its LARGEST, Stage 5; greedy_hand), r and s powers of two,
           and no cheaper feasible lattice neighbour (one allocation halved, or one halved and another doubled). A
           synthetic full-size pilot reproduces F11 (cheap free L8 primitives with 2x the sigma: multiplier 7.8x the
           other free L8 graphs' 35.1): the frozen design has r = 32 at free L8, the primitives at s > 1, the target met
           at 1.07x the continuous Neyman optimum (the F11 greedy design 1.09x), while the old rule (r from the LARGEST
           multiplier, by hand) gives r = 128 and 2.85x; the SE recomputed from the bundle's counts.
  F13      optimizer_property: on 2,000 seeded random stratum sets at a target, design.optimize is feasible and never
           costlier than either old rule's final design (old_rule_hand), while the old F11 rule alone is costlier than
           the Stage-5 rule in some sets; on 600 sets at a budget it is within the budget, never less precise, and
           refuses exactly when the old rules do. jdes5_records: J-DES-5's strata from the committed records of job
           570241 reproduce the frozen numbers, and the optimizer and route (b)'s keep-cheaper give at most them (the
           table in docs/DESIGN.md, "Route (b)").
  route b  (design.py freeze --numerics, in-process) an approved profile for a bundle frozen from an EXACT pilot,
           re-costed with a profile cost model (non-uniform per stratum and graph), sigma kept; F13's keep-cheaper
           recomputed independently (check_route_b_choice) with both branches exercised (a second profile keeps the
           exact allocation at one target and re-optimizes at a tighter one); the re-optimized bundle's counts, r, s,
           SE and cost equal the independent recomputation with the profile's costs, the SE from the counts is the
           frozen one, the record is complete, report re-costs the table and names the branch; 28 refusals (a profile
           outside {dd+mp256}, no
           approval, a cost model of another numerics or rates identity or missing a graph or measured with a build no
           gate passed, no cost model or gate, a gate failed, of another profile, development, not full scale, twice,
           without the Stage-6 fix round 1 evidence (no F1 coverage, one sector, an unmet quota, unbound, an executable
           not reproduced, unverified F5 teams), a
           pilot under a profile, a rate map, a c8-d3 pilot, route-(b) options on the exact path), each creating
           nothing.
  A-DES-6  a d = 3 freeze with the vendored inputs_d3/two_loop.json at the HANDOFF sha256 (--dimension 3
           --half-d 1.5); a 1/8 L8 subsample imputed exactly (the imputed variance share = the hand value); nested
           point counts give alpha within 0.02 of the built-in 0.7.
  tails    C63d's heavy-tail rule: screen and confirmation on L8 graphs only, L <= 7 diagnostics without labels,
           undefined replicates make the graph undefined (never thresholded, never averaged over the others), the
           sector P8 pooled over L8 graph-campaigns at 4,096 points only, the stratum P8 flag on L8 strata only.
Part 2, fake campaigns on inputs_mini (all test-only):
  the bootstrap sweep (R13) under a fake Slurm job registers itself (ledger), runs, merges and writes the cost model;
  design.py freeze on it takes eta_node from accounting.py (= the hand value), refuses an unregistered sweep
  ("allocation unknown"), and accepts checkpoints without a Slurm id only in a --test-only freeze (A-ORC-9);
  plan --pilot with the measured cost model -> lanes (fake Slurm env) -> merge --jobs -> freeze (A-DES-2 on it) ->
  two batches plan --design -> run -> merge -> assemble -> combine.py --test-only partial and final (the chi-square
  = the hand value) and verify_result; rejected combinations: one batch without --partial, a different bundle, a
  repeated seed, a missing group, a missing graph, a different rates identity (A-ASM-6/7).
  R14/R19: design.py rates -> a provisional bundle (rates.json + design_meta.json only; report "unavailable
  (provisional)"; plan --design refused, test-only and non-test) -> sweep.py --rates and plan --pilot --rates under
  the map (cost model identity = the map's sha256; D15) -> freeze --rates-bundle (refused for the source pilot and
  for a pilot under another identity) -> a fresh bundle whose counts x s, r, predicted SE, cost, efficiencies,
  batches and budget verdict equal an independent recomputation, which differs from the source bundle (its
  allocation under the map misses the target and under-predicts the cost by the injected 1.5x), and which a plan
  under the map accepts.
  route b  (test-only, command line) sweep.py --numerics dd+mp256 (refused without the approval and with the package
           calibration) measures the profile cost model; freeze --numerics re-costs the exact pilot's bundle (the
           keep-cheaper choice and the chosen design recomputed independently); plan --design under the profile runs,
           merges and assembles; combine refuses that batch with an exact batch (different bundles; with equal bundle
           identities, different numerics).
  A-FLAG-6 additions (Stage 4c R7): the source bundle byte-unchanged by design.py rates; per-graph spec entries; a
  spec with equal a and b rates for one graph refused before anything is created; a pilot whose pinned tools changed
  after planning accepted with the change recorded (the J-SWEEP-1 case); the sweep under the map (its labelled
  allocation) -> a fresh freeze equal to the independent recomputation from the sweep, not the default sweep's
  allocation; freeze --rates-bundle of another map refused for the pilot and the sweep measured under the first.
Stage-6 fix round 1 (G3), in part 2:
  X15      accounting on live allocations: a RUNNING, PENDING, COMPLETING, SUSPENDED or unknown current attempt, a
           requeue as the current attempt, an earlier RUNNING attempt and a PENDING array range are incomplete (eta_node
           unavailable, design.py refuses, exit 4); a requeue followed by COMPLETED (both attempts in the sum),
           'CANCELLED by <uid>' and a range cancelled before it started are complete.
  X10      make_cost_model.py class-factors only between the same numerics (exact against exact: factors 1; a model
           labelled dd+mp256 or without numerics refused, exit 3).
  X14      a c8-d2 pilot's --two-loop / --inventory / --selection must be the files its inputs manifest pins (the
           pinned files accepted with the same J8; the d = 3 two-loop file, a changed B2 entry, an inventory without a
           graph and a selection refused, also by report and freeze).
Stage-6 fix round 2 (G3):
  Y10      (part 1, in-process, and parts 2 and 3 on the command line) the allocation options are validated before
           anything is designed: a production freeze refuses --min-replicates 1 --max-replicates 1 (the finding's case,
           also on the non-test pilot of part 3, by freeze and report), replicates below 32 or above 128 or not powers of
           two, max < min, --min-points below 4096 or not a power of two, a variance margin below 1 or not finite, a
           non-finite target, negative spent hours, a --min-chunk that is not a power of two, --checkpoint-tasks below
           --threads and --batches 0; a test-only bundle may reduce the bounds (r in [8, 16] accepted) but never below
           two replicates (refused in-process and on the command line); a designed allocation outside its bounds (r = 1
           injected) is refused before publication. Each refusal creates nothing.
  Y9       (part 3, the non-test pilot) a copy with every checkpoint removed: design.py freeze and report refuse it
           (no assumed efficiency for a production design; before the fix: eta_node 1.0 "assumed"), eta_node refuses it
           in-process, and a --test-only freeze accepts it with the assumed 1.0; a copy with one checkpoint removed is
           refused by a production and by a test-only freeze (incomplete accounting) and accounting.py exits 4 naming
           the missing checkpoint; the intact pilot's accounting is complete.
Stage-6 fix round 3 (G3):
  Z10      (part 1, in-process; z_bundle_setup, z10_synthetic) a bundle frozen with --variance-margin 2 and --impute
           median from a synthetic pilot (a third of its graphs unpiloted, exact power laws) is reported by report()
           with the command's defaults (1.5, addends) at its FROZEN settings (the SE = the frozen prediction = the
           independent recomputation at 2 and the median; before: 27% below), explicitly requested other settings only
           as the labelled projection (= the independent recomputation at 1.5 and addends), another pilot's report
           labelled a projection; (part 2, z10_cli) report on the command line without --variance-margin, with 2 and with
           1.5 (projection 0.75 x).
  Z9       (part 1, z9_synthetic) report refuses damaged copies of the bundle: a count doubled, design.json changed, a
           counts file unpinned (digests unchanged), a repeated graph line, a count 0, a count "+n" and another schema
           (digests re-pinned); a byte-identical copy is accepted; (part 2, z9_cli) report --bundle exits 2 on a doubled
           count and a changed design.json; (z9_class_cli) freeze --rates-bundle refuses a provisional bundle whose
           rates.json changed and rates --source-bundle a source bundle with a changed count, creating nothing.
  Z12      (part 1, z12_nested) nested_alpha keeps every graph's own point ratio: the finding's case (alpha 1/2, before
           0.28) in both graph orders and with one graph's counts reversed, mixed ratios at alpha 0.7, a common ratio in
           closed form with equal counts left out, alpha per ratio; a nested pilot of another numerics, rates identity,
           inputs manifest, backend or two-loop jet is refused by nested_alpha and by report.
Stage-6 fix round 4 (G3):
  W12      (part 1, w12_batches) a synthetic pilot needing K_min = 92 batches: without --batches the search stops at 64 and
           says it is the search limit, not infeasibility; --batches 128 searches past 64 and freezes 128 batches (K_min
           recorded, every cap held, the target met); --batches 91, 70 and 32 are below the minimum; a cap the minimum
           design of one batch breaks is infeasible; an optimizer allocation for the requested K that breaks the caps is
           refused (before the fix it was frozen unchecked).
  W18      (part 1, route_b_synthetic; part 2, route_b_cli_test_only; part 3) every synthetic gate record carries the
           authenticated input set it ran on; freeze refuses a gate without it, of another inputs manifest (the
           package's inputs for a fixture pilot), changed during the run or incomplete; a non-test plan refuses a gate
           of other inputs (production.gated_route through check_gate); the bundle's gate entries carry the identity.
  W10      (part 2, w10_calibration_checkpoints) calibrate.py validates every checkpoint before reading timings: a
           timing changed without its checksum, a campaign-b checkpoint over campaign a's, one from another run, a NaN,
           negative or string timing are refused; the intact campaign calibrates to the hand value.
  W11      (part 2, w11_rates_calibration) one measurement identity per calibration file: sweep.py --rates into the
           package calibration or an exact file refused before planning; calibrate.py --update of map rows into
           tools/calibration.json or an exact file, of exact rows into the map's file, into a mixed file refused.
  W20      (part 2, w20_sweep_seed) the sweep's seed registration is one locked check-and-append: a seed another
           campaign registered after the plan is refused before any index runs; a new sweep on a logged seed refused
           before planning; a resumed sweep is present.
G4c fixes (Stage 5, D1):
  rule     design.py rates --rule one-step CHOOSES the rates from the pilot (A-FLAG-6): on a synthetic pilot whose
           W_b^2/W_a^2 is known per stratum (part 1) every branch of the rule (step up, step down, keep in the band,
           keep with fewer than min_graphs graphs), W, r and the bootstrap equal the hand values, a and b differ
           everywhere, a pilot under a map and a step leaving (0, 1] are refused; on the fake pilot (part 2) the command
           line writes the map the rule chose for every graph, records the rule and its inputs (rate_rule in
           design_meta.json, its W equal to an independent recomputation from the merged tables), and refuses --rule
           with --spec, neither, rule options with --spec, a pilot under a map and a bad step, creating nothing.
  part3    a NON-test plan accepts the fresh R7 bundle given --approved-numerics-change, the cost model under the map
           and the map in production.APPROVED_RATES (monkeypatched by a wrapper: the set is empty, R7 stays off), and
           refuses it without either (and without any cost model); unpatched, the non-test pilot and batch under the
           map are refused, and the non-test pilot under the map also needs its key in production.APPROVED_PROFILE_PILOTS
           (refused with APPROVED_RATES patched alone; Stage 6): a scratch package whose inputs/ is a
           minimal non-test inputs folder (the fixture's two cheapest graphs per (sector, L) and its L8 packs, a manifest
           without test_fixture), a non-test pilot at 4,096 points under fake Slurm, a non-test source bundle, the map
           by the one-step rule, the sweep and a non-test pilot under the map, and the fresh non-test bundle.
  route b  NON-test: a non-test route-(b) bundle of the exact non-test pilot (a uniform 0.4x profile: the same counts,
           0.4x the cost); plan --design accepts it with every piece (--numerics dd+mp256, the approval, the profile
           cost model, a gated production build) and records numerics_route; it refuses no approval, a cost model of
           another numerics identity, an exact plan, a development build, an ungated build, a profile outside the set
           (a tampered bundle) and a bundle without the route record; freeze refuses no approval, an exact cost model,
           a profile outside the set and no gate. A refusal creates nothing.
  allow    the allow-list scope: NON-test plan --pilot --numerics dd | mp256 | exp1 | dd+exp1 | dd+mp256+exp1 and plan
           --design of a route-(a) bundle under dd and dd+mp256+exp1 are refused with the approval, creating nothing;
           a test-only dd plan is accepted.
  pilot    Stage 6 (the pilot stays exact; a gated build for every non-test plan under a profile): a NON-test plan
           --pilot --numerics dd+mp256 is refused (production.APPROVED_PROFILE_PILOTS is empty), with the set
           monkeypatched it still needs a passed gate of this build (--numerics-gate; refused without, with another
           build's gate and a failed one); a non-test route-(a) dd+mp256 bundle is planned only with a gate of this build
           (numerics_route route 'a'); --numerics-gate is refused on an exact plan and on a route-(b) bundle; a test-only
           dd+mp256 pilot needs no gate (and a gate given must cover the build).
--only refuses an unknown part or an empty list before any setup (exit 2); the record lists the requested and the
executed parts (checkpoint review T-03).
Usage: python3 -B tests/test_pipeline.py [--output FILE] [--only part1,part2,part3]"""
from __future__ import annotations
import argparse,hashlib,json,math,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PY=sys.executable
sys.path.insert(0,str(ROOT/'tests'))
from pkgcopy import link_or_copy,make_package  # noqa: E402
for k in list(os.environ):
    if k.startswith(('C7_','C8_','SBATCH_','SQUEUE_','SLURM_')):os.environ.pop(k)
RESULTS=[]
def ok(name,**info):RESULTS.append({'test':name,**info});print('PASS',name,flush=True)
def digest(p)->str:return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_bytes())
def close(a,b,rel=1e-9):return math.isclose(float(a),float(b),rel_tol=rel,abs_tol=0.)

# ---------------------------------------------------------------- fake Slurm accounting commands
FAKE_SACCT=r'''import os,sys
args=sys.argv[1:];ids=set(args[args.index('-j')+1].split(','))if '-j'in args else set()
for line in open(os.environ['FAKE_SACCT']):
    f=line.strip().split('|')
    if len(f)>=7 and f[0].split('_')[0].split('.')[0]in ids:print(line.strip())
'''
FAKE_SCONTROL=r'''import os,sys
if sys.argv[1:3]==['show','node']:print(f'NodeName={sys.argv[3]} Arch=x86_64 CoresPerSocket=64 ThreadsPerCore={os.environ.get("FAKE_TPC","1")}');sys.exit(0)
sys.exit(1)
'''
def fake_bin(td:Path)->Path:
    fb=td/'fakebin';fb.mkdir()
    for name,src in (('sacct',FAKE_SACCT),('scontrol',FAKE_SCONTROL),('squeue','import sys;sys.exit(1)\n')):
        (fb/name).write_text(f'#!{PY}\n'+src);(fb/name).chmod(0o755)
    return fb

def fake_build_record(exe:Path,backend:str='gmp',numerics:str='exact')->dict:
    """Z3 (Stage-6 fix round 3): the build record make writes beside a build, for a fake worker (a non-test plan needs one)."""
    rec={'schema':'c8-d2-build-record-1','executable':exe.name,'backend':backend,'executable_sha256':digest(exe),'NUMERICS':numerics,
         'compiler_options':['g++','-O3','-std=c++17','-fopenmp','-ffp-contract=off','-fno-fast-math'],'compiler':'fake (tests/test_pipeline.py)',
         'parameter_overrides':[],'macro_overrides':[],'development':False,'diagnostic':None,'required_flags_present':True,'optimized':True}
    exe.with_name(exe.name+'.build.json').write_text(json.dumps(rec,indent=2)+'\n');return rec

class Pkg:
    def __init__(self,td:Path):
        self.td=td;self.pkg=make_package(td);self.fixture=self.pkg/'tests/fixtures/inputs_mini';self.fb=fake_bin(td)
        for b,be in (('c8d2_gmp','gmp'),('c8d2_decimal','decimal')):fake_build_record(self.pkg/'bin'/b,be)
        self.sacct=td/'sacct.txt';self.sacct.write_text('');self.seeds=td/'seeds.json'
        self.env={'C8_INPUTS':str(self.fixture),'PATH':f'{self.fb}:{os.environ["PATH"]}','FAKE_SACCT':str(self.sacct),'PYTHONDONTWRITEBYTECODE':'1',
                  'OPENBLAS_NUM_THREADS':'1','C8_SEEDS':str(self.seeds)}
        sys.path[:0]=[str(self.pkg/'tools')]
        for n in ('common','production','design','assemble','accounting','ledger','seeds','combine','verify_result','prepare_inputs'):sys.modules.pop(n,None)
        import design,production,accounting,combine,verify_result,seeds
        self.D=design;self.prod=production;self.acc=accounting;self.comb=combine;self.vr=verify_result;self.seedmod=seeds
    def T(self,script,*args,env=None,expect=0):
        e={**os.environ,**self.env,**(env or{})}
        cp=subprocess.run([PY,'-B',str(self.pkg/'tools'/script),*map(str,args)],capture_output=True,text=True,env=e)
        if (cp.returncode==0)!=(expect==0):raise AssertionError(f'{script} {args}: exit {cp.returncode}, expected {expect}\n{cp.stderr[-2500:]}\n{cp.stdout[-800:]}')
        return cp
    def sacct_add(self,job,elapsed,cpus,node='exp-1-01'):
        with self.sacct.open('a')as f:f.write(f'{job}|{job}|{elapsed}|{cpus}|{node}|COMPLETED|shared\n')

# ---------------------------------------------------------------- design argument namespaces and synthetic pilots
def fargs(D,out,**kw):
    p=argparse.ArgumentParser();D.common_args(p)
    for k in ('--target-rel','--target-se','--budget-core-hours','--total-cap','--eta-node'):p.add_argument(k,type=float)
    p.add_argument('--batches',type=int);p.add_argument('--spent-core-hours',type=float,default=0.);p.add_argument('--seeds-log',type=Path)
    p.add_argument('--rates-bundle',type=Path);p.add_argument('--test-only',action='store_true')
    a=p.parse_args([]);a.out=Path(out)
    for k,v in kw.items():setattr(a,k,v)
    return a

def synth_pilot(D,inv,meta,reps=16,points=4096,sigma=None,cost=None,piloted=None,exact=False,seed=1,eta_omp=0.9,eta_node=0.95,J8=None,full_jets=False):
    """GroupData per (campaign, sector, L) from closed forms: per-graph sigma (so that n Var_rep = sigma^2) and cost per
    point; exact=True makes every sample variance exact (+-d pattern), else Gaussian replicate noise."""
    rng=np.random.default_rng(seed);groups={}
    for c in ('a','b'):
        for s in ('free','power'):
            for L in range(3,9):
                rows=sorted((r for r in inv[s][str(L)]if piloted is None or piloted(c,s,L,r)),key=lambda r:r['id']);gids=[r['id']for r in rows];dim=2*(9-L)
                Y=np.zeros((reps,len(gids),dim));secs={}
                for i,r in enumerate(rows):
                    sd=sigma(c,s,L,r)/math.sqrt(points)
                    dev=(np.array([1.,-1.]*(reps//2))*sd*math.sqrt((reps-1)/reps))if exact else rng.normal(0.,sd,reps)
                    if full_jets:Y[:,i,:]=1e-3*(1+np.arange(dim))[None,:]+dev[:,None]
                    else:Y[:,i,0]=1.+dev
                    secs[r['id']]=cost(c,s,L,r)*reps*points
                groups[(c,s,L)]=D.GroupData(c,s,L,reps,gids,{g:points for g in gids},Y,secs,eta_omp,None)
    P=D.Pilot(groups,inv,dict(meta));P.eta_node=eta_node;P.eta_source='synthetic'
    P.J8=J8 if J8 is not None else{L:np.eye(2*(9-L))[0]for L in range(3,9)}
    return P

def counts_of(bundle:Path)->dict:
    out={}
    for f in sorted((bundle/'counts').glob('*.txt')):
        c,s,L=f.stem.split('_');out[(c,s,int(L[1:]))]={int(a):int(b)for a,b in (x.split()for x in f.read_text().splitlines()if x)}
    return out

# ---------------------------------------------------------------- the independent recomputation (A-DES-2, R14)
def graph_stats(P,impute_fit:bool=False,costs=None)->dict:
    """sigma and cost per (c, s, L, g) for every inventory graph, written independently of tools/design.py: piloted
    graphs from Y . J8 and the row seconds; the others the stratum median (fewer than 3 piloted graphs) or the exact
    log-linear fit on the addends; the 3% sigma floor. costs (route (b)): {(c, s, L, g): seconds per point} of a
    profile cost model replaces every graph's cost; sigma stays the pilot's."""
    out={}
    for (c,s,L),G in P.groups.items():
        rows=P.inventory[s][str(L)];strat=lambda r:'free_L8_primitive'if (s=='free'and L==8 and r.get('primitive'))else f'{s}_L{L}'
        y=G.Y@P.J8[L] if len(G.graphs)else np.zeros((G.reps,0));T={}
        for i,g in enumerate(G.graphs):
            T[g]=dict(sigma=math.sqrt(G.points[g]*float(np.var(y[:,i],ddof=1))),cost=max(1e-12,G.seconds[g]/(G.reps*G.points[g])),piloted=True)
        add={r['id']:max(1,int(r.get('addends')or r.get('cost')or 1))for r in rows}
        for st in sorted({strat(r)for r in rows}):
            mem=[r['id']for r in rows if strat(r)==st];pil=[g for g in mem if g in T and T[g]['sigma']>0]
            miss=[g for g in mem if g not in T]
            if miss:
                if not pil:pil=[g for g in T if T[g]['piloted']and T[g]['sigma']>0]
                xs=np.log([add[g]for g in pil])
                for key in ('sigma','cost'):
                    ys=np.log([T[g][key]for g in pil])
                    if impute_fit and len(pil)>=3 and np.ptp(xs)>0:
                        b,a=np.polyfit(xs,ys,1);val={g:math.exp(a+b*math.log(add[g]))for g in miss}
                    else:med=float(np.exp(np.median(ys)));val={g:med for g in miss}
                    for g in miss:T.setdefault(g,dict(piloted=False))[key]=val[g]
            sig=[T[g]['sigma']for g in mem if T[g]['piloted']and T[g]['sigma']>0]
            fl=0.03*(float(np.median(sig))if sig else max(T[g]['sigma']for g in mem))
            for g in mem:out[(c,s,L,g)]=dict(T[g],sigma=max(T[g]['sigma'],fl),stratum=st)
    if costs is not None:
        for k,x in out.items():x['cost']=max(1e-12,float(costs[k]))
    return out

def predict(stats,counts,r,s_map,K,margin,eta)->dict:
    """Predicted SE and allocated cost of an allocation (counts x s, replicates r, K batches); eta(c, s, L) the
    efficiency product eta_omp x eta_node."""
    var=0.;var_imp=0.;cost=0.
    for (c,s,L,g),x in stats.items():
        n=counts[(c,s,L)][g]*s_map[x['stratum']];rr=r[f'{s}_L{L}'];v=.25*x['sigma']**2/(n*rr);var+=v
        if not x['piloted']:var_imp+=v
        cost+=x['cost']*n*rr/eta(c,s,L)
    return dict(se_total=margin*math.sqrt(var/K),se_raw_total=math.sqrt(var/K),cost_total_core_hours=K*cost/3600,imputed_variance_share=var_imp/var)

def base_counts_hand(stats,pp:int,min_points:int)->dict:
    """n_g ~ sigma_g/sqrt(c_g), normalized per (campaign, stratum) to the pilot cost per replicate, powers of two."""
    p2=lambda x:1<<max(0,int(round(math.log2(x))))if x>1 else 1;out={};by={}
    for (c,s,L,g),x in stats.items():by.setdefault((c,s,L,x['stratum']),[]).append(g)
    for (c,s,L,st),gs in by.items():
        unit=pp*sum(stats[(c,s,L,g)]['cost']for g in gs);den=sum(stats[(c,s,L,g)]['sigma']*math.sqrt(stats[(c,s,L,g)]['cost'])for g in gs);k=unit/den
        for g in gs:x=stats[(c,s,L,g)];out.setdefault((c,s,L),{})[g]=max(min_points,p2(max(1.,k*x['sigma']/math.sqrt(x['cost']))))
    return out

def strata_hand(stats,counts,eta)->tuple[dict,dict]:
    """V1 (C8 variance per replicate at s = 1, campaigns at weight 1/2) and C1 (allocated core-seconds per replicate at
    s = 1) per stratum, from the independent per-graph statistics and base counts."""
    V={};C={}
    for (c,s,L,g),x in stats.items():
        k=x['stratum'];n=counts[(c,s,L)][g];V[k]=V.get(k,0.)+.25*x['sigma']**2/n;C[k]=C.get(k,0.)+x['cost']*n/eta(c,s,L)
    return V,C

def r_rule_hand(V,C,target_se,K,margin=1.5,min_reps=32,max_reps=128,rule='F11')->tuple[dict,dict,float]:
    """The Neyman multipliers m_k = lambda sqrt(V1/C1) at the target, the replicates r of each (sector, L) = the largest
    power of two in [min_reps, max_reps] not above the group's SMALLEST positive multiplier (F11; rule 'Stage5': its
    LARGEST), and the continuous Neyman optimum's cost (core-hours) margin^2 (sum_k sqrt(V1 C1))^2 / (K target^2), all
    written independently of tools/design.py."""
    act=[k for k in V if V[k]>0];W=sum(math.sqrt(V[k]*C[k])for k in act);lam=margin**2*W/(K*target_se**2)
    m={k:lam*math.sqrt(V[k]/C[k])for k in act};r={};pick=min if rule=='F11'else max
    for k in m:
        grp=k.replace('_primitive','');r[grp]=pick(r.get(grp,m[k]),m[k])
    rr={g:min(max_reps,max(min_reps,2**math.floor(math.log2(v))))if v>=1 else min_reps for g,v in r.items()}
    return m,rr,K*lam*W/3600

P2=lambda x:1<<max(0,int(round(math.log2(x))))if x>1 else 1
def alloc_eval(V,C,a,K,margin=1.5)->tuple[float,float]:
    """(cost core-hours, SE with the margin) of per-stratum allocations a (= r x s), by hand."""
    return K*sum(C[k]*a[k]for k in a)/3600,margin*math.sqrt(sum(V[k]/a[k]for k in a)/K)

def greedy_hand(V,C,target_se,K,rule,margin=1.5,min_reps=32,max_reps=128)->tuple[dict,float,float]:
    """The Stage-3 integer allocation (Stage 5 and F11), written independently of tools/design.py: r of each (sector,
    L) by the rule, s = pow2_round(m/r) when m > r, else 1; then double the s of the stratum with the largest variance
    removed per cost added until the SE meets the target. Returns the allocation r x s per stratum, its cost and SE."""
    m,rr,_=r_rule_hand(V,C,target_se,K,margin,min_reps,max_reps,rule);g=lambda k:k.replace('_primitive','')
    a={k:rr[g(k)]*(P2(m[k]/rr[g(k)])if m[k]>rr[g(k)]else 1)for k in m}
    while alloc_eval(V,C,a,K,margin)[1]>target_se*(1+1e-12):
        k=max(a,key=lambda k:(V[k]/(2*a[k]))/(C[k]*a[k]));a[k]*=2
    return (a,)+alloc_eval(V,C,a,K,margin)

def check_optimizer(P,bundle,eta,costs=None,impute_fit=False):
    """F13 / F11 follow-up, from the pilot P and the bundle's own counts, written independently of tools/design.py: the
    design meets its target; it is never costlier than either old rule's greedy design (greedy_hand, F11 and Stage 5);
    r and s are powers of two (r in [32, 128], s >= 1); and it is a local optimum of the lattice: no single halving of
    one stratum's allocation and no move halving one and doubling another (allocations >= the minimum replicates)
    meets the target at a lower cost (a margin of 1e-9 on both sides). Returns the cost, SE and the two greedy costs."""
    meta=load(bundle/'design_meta.json');d=load(bundle/'design.json');tgt=meta['target']['se'];K=int(d['batches'])
    lo,hi=meta['parameters']['min_replicates'],meta['parameters']['max_replicates'];mg=meta['parameters']['variance_margin']
    V,C=strata_hand(graph_stats(P,impute_fit,costs),counts_of(bundle),eta)
    r={k:int(v)for k,v in d['replicates'].items()};s={k:int(v['s'])for k,v in d['strata'].items()}
    assert all(lo<=v<=hi and v&(v-1)==0 for v in r.values())and all(x>=1 and x&(x-1)==0 for x in s.values()),(r,s)
    a={k:r[k.replace('_primitive','')]*s[k]for k in V};cost,se=alloc_eval(V,C,a,K,mg)
    assert se<=tgt*(1+1e-12)and close(se,meta['predictions']['se_total'])and close(cost,meta['predictions']['cost_total_core_hours']),(se,cost,meta['predictions'])
    greedy={rule:greedy_hand(V,C,tgt,K,rule,mg,lo,hi)for rule in ('F11','Stage5')}
    assert all(cost<=g[1]*(1+1e-12)for g in greedy.values()),(cost,{k:g[1:]for k,g in greedy.items()})
    keys=sorted(a);moves=[{k:a[k]//2}for k in keys if a[k]//2>=lo]+[{k:a[k]//2,j:a[j]*2}for k in keys for j in keys if j!=k and a[k]//2>=lo]
    for mv in moves:
        c2,se2=alloc_eval(V,C,{**a,**mv},K,mg)
        assert not (se2<=tgt*(1-1e-9)and c2<cost*(1-1e-9)),('a cheaper feasible lattice neighbour',mv,c2,cost,se2,tgt)
    return dict(cost=cost,se=se,greedy_F11=greedy['F11'][1],greedy_Stage5=greedy['Stage5'][1],kept=meta['optimizer']['kept'],neighbours=len(moves))

def check_bundle_against(P,bundle,eta,impute_fit=False,margin=1.5,costs=None):
    """design.json, counts and design_meta predictions of a frozen bundle against the independent recomputation from
    the pilot P (exact counts; predictions to 1e-9); costs: route (b), the profile cost model's seconds per point."""
    d=load(bundle/'design.json');meta=load(bundle/'design_meta.json');stats=graph_stats(P,impute_fit,costs);counts=counts_of(bundle)
    pp=max([G.points[g]for G in P.groups.values()for g in G.graphs]+[meta['parameters']['min_points']])
    hand=base_counts_hand(stats,pp,meta['parameters']['min_points'])
    assert hand==counts,'the counts differ from the independent recomputation'
    s_map={k:int(v['s'])for k,v in d['strata'].items()};r={k:int(v)for k,v in d['replicates'].items()};K=int(d['batches'])
    pr=predict(stats,counts,r,s_map,K,margin,eta)
    for k in ('se_total','se_raw_total','cost_total_core_hours','imputed_variance_share'):
        assert close(pr[k],meta['predictions'][k]),(k,pr[k],meta['predictions'][k])
    return pr,stats,counts,r,s_map,K

def check_route_b_choice(P,rb:Path,ex:Path,eta,costs,impute_fit=False,margin=1.5):
    """F13 keep-cheaper of a route-(b) bundle rb, written independently of tools/design.py: the kept candidate is the
    exact bundle ex (frozen from the same pilot with the same arguments: the exact path's design) re-costed with the
    profile's costs (its counts x s, r and K; its SE the exact one's); the re-optimized candidate is the recorded r, s
    and K on the base counts recomputed with the profile's costs (n_g ~ sigma_g / sqrt(c_g)). Both recomputed costs and
    SEs equal route_b_choice's; the bundle is the kept candidate iff that one is feasible (the target met, the recorded
    cap verdict) and strictly cheaper (1e-12); the bundle's counts, r, s and predictions are the chosen candidate's.
    Returns (chosen, kept, re-optimized)."""
    m=load(rb/'design_meta.json');ch=m['route_b_choice'];tgt=m['target']['se'];d=load(rb/'design.json');dx=load(ex/'design.json')
    stats=graph_stats(P,impute_fit,costs);pp=max([G.points[g]for G in P.groups.values()for g in G.graphs]+[m['parameters']['min_points']])
    cx=counts_of(ex);rx={k:int(v)for k,v in dx['replicates'].items()};sx={k:int(v['s'])for k,v in dx['strata'].items()};Kx=int(dx['batches'])
    kept=predict(stats,cx,rx,sx,Kx,margin,eta);kc=ch['kept_exact_allocation']
    assert close(kept['cost_total_core_hours'],kc['cost_total_core_hours'])and close(kept['se_total'],kc['se_total'])and close(kept['se_total'],load(ex/'design_meta.json')['predictions']['se_total'])
    assert kc['replicates']==rx and kc['s']==sx and kc['batches']==Kx and close(kc['exact_cost_total_core_hours'],load(ex/'design_meta.json')['predictions']['cost_total_core_hours'])
    cp=base_counts_hand(stats,pp,m['parameters']['min_points']);ro=ch['reoptimized']
    reo=predict(stats,cp,ro['replicates'],ro['s'],ro['batches'],margin,eta)
    assert close(reo['cost_total_core_hours'],ro['cost_total_core_hours'])and close(reo['se_total'],ro['se_total'])and reo['se_total']<=tgt*(1+1e-12)
    feas=bool(kc['feasible'])and kept['se_total']<=tgt*(1+1e-12)and kc['caps_ok']
    want='kept_exact_allocation'if feas and kept['cost_total_core_hours']<reo['cost_total_core_hours']*(1-1e-12)else'reoptimized'
    assert ch['chosen']==want and kc['feasible']==(kc['caps_ok']and kept['se_total']<=tgt*(1+1e-12)),(ch['chosen'],want,kept,reo)
    win,cnt,rr,ss=(kept,cx,rx,sx)if want=='kept_exact_allocation'else(reo,cp,ro['replicates'],ro['s'])
    assert counts_of(rb)==cnt and {k:int(v)for k,v in d['replicates'].items()}==rr and {k:int(v['s'])for k,v in d['strata'].items()}==ss
    assert close(m['predictions']['cost_total_core_hours'],win['cost_total_core_hours'])and close(m['predictions']['se_total'],win['se_total'])
    return want,kept,reo

# ---------------------------------------------------------------- route (b) fixtures
APPR_B='user check-in 2026-10-05: dd+mp256 approved for production after the pilot (test_pipeline.py route (b))'

GATE_SNAPSHOT='5'*64
def gate_coverage()->dict:
    """The full F1 coverage record (tests/numerics_flags.py f1_coverage) of job 570210's numbers (X1)."""
    L={'7':{'graphs':200,'points_per_graph':256,'points_baseline':51200,'points_profile':51200},'8':{'graphs':400,'points_per_graph':64,'points_baseline':25600,'points_profile':25600}}
    return {'complete':True,'why':[],'scale':1.0,'profile_checked':True,
            'sectors':{s:{'doublings':0,'binary128_accepted':q,'mp_promoted':m,'need_met':True,'by_L':json.loads(json.dumps(L))}for s,q,m in (('free',29284,3541),('power',50625,12568))}}

def gate_record(path:Path,profile:str,profile_sha:str,exact_sha:str,inv:dict,mutate=None,*,inputs:str)->Path:
    """A synthetic passed full-scale J-FLAG gate record (schema c8-d2-numerics-flags-1, the fields design.py freeze
    checks) of the profile build profile_sha, with the evidence check_gate requires since Stage-6 fix round 1 (F1
    coverage X1, the build binding X2, the F5 team sizes X3), since fix round 3 the libgmp provenance of both F1
    tools (gate_libraries, Z19) and since fix round 4 the authenticated input set (W18): inputs is the sha256 of the
    inputs manifest the gate ran on (the pilot's for a freeze, the plan's for production); mutate(rec) edits it for a
    refusal case."""
    graphs={f'{c}_{s}_L{L}':len(inv[s][str(L)])for c in 'ab'for s in ('free','power')for L in range(3,9)}
    bound=lambda sha:{'sha256':sha,'reproduced_sha256':sha,'reproduced':True,'snapshot_sha256':GATE_SNAPSHOT}
    rec={'schema':'c8-d2-numerics-flags-1','mode':'profile','profile_name':profile,'status':'passed','development':[],'parts':['F1','F2','F4','F5'],
         'verdicts':{'F1':True,'F2':True,'F4_rows':True,'F5':True},'utc_start':'2026-10-05T16:53:33Z','exact':{'sha256':exact_sha},
         'profile':{'sha256':profile_sha,'describe':{'numerics':profile,'compiler':'fake'},'build_record':{'development':False,'parameter_overrides':[]}},
         'build_binding':{'schema':'c8-d2-build-binding-1','snapshot':{'sha256':GATE_SNAPSHOT,'files':{}},'executables':{'exact':bound(exact_sha),'profile':bound(profile_sha)}},
         'F1':{'verdict':{'passed':True,'violations':0},'coverage':gate_coverage(),'tool_snapshot_sha256':GATE_SNAPSHOT,'baseline_binding':bound(exact_sha)},
         'F2':{'graphs':graphs,'total':{'dC8':1.3e-16,'se':9.8e-17,'bound':4.25e-16,'passed':True,'resolved':True}},
         'F5':{'passed':True,'team_sizes_verified':True},'environment':{'host':'fake-node','cpu_model':'fake CPU'}}
    gate_libraries(rec)
    rec['inputs']={'schema':'c8-d2-gate-inputs-1','folder':'inputs','manifest_sha256':inputs,'verified':True,'verified_at_end':True,'skipped':[],'complete':True}
    rec['f1_baseline']['inputs_manifest_sha256']=inputs
    if mutate:mutate(rec)
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(rec,indent=1)+'\n');return path

def gate_libraries(rec:dict,exact_lib:str='1'*64,profile_lib:str='1'*64)->dict:
    """Z19 downstream (fix round 3): the libgmp provenance design.check_gate requires of a gate record: each build
    record's gmp_library, the profile's F1 tool and a fresh baseline's exact tool matched to it."""
    lib=lambda w:{'tool':{'sha256':w},'worker_now':{'sha256':w},'want_sha256':w,'match':True}
    rec['exact'].setdefault('build_record',{})['gmp_library']={'sha256':exact_lib};rec['profile']['build_record']['gmp_library']={'sha256':profile_lib}
    rec['F1']['tool_gmp_library']=lib(profile_lib);rec['f1_baseline']={'path':'f1_baseline','sha256':'2'*64,'reused':False,'reused_gmp_library':None,'tool_gmp_library':lib(exact_lib)}
    return rec

def cost_model_doc(numerics:str,spp:dict,rates:str='default')->dict:
    return {'schema':'c8-d2-cost-model-1','dimension':2,'order':8,'backend':'gmp','numerics':numerics,'rates_identity':rates,'executable_sha256':'e'*64,
            'cpu_models':['fake CPU'],'keys':len(spp),'seconds_per_point':spp}

def fake_profile_exe(pkg:Path,profile:str='dd+mp256')->Path:
    """bin/c8d2_gmp_<profile>: a copy of the fake worker, which reports numerics <profile> by its name (no delta: the
    values equal the exact path's, as dd+mp256's F2 shows to 1e-16)."""
    exe=pkg/'bin'/f'c8d2_gmp_{profile}';shutil.copy2(pkg/'bin/c8d2_gmp',exe);exe.chmod(0o755);fake_build_record(exe,'gmp',profile);return exe

def costs_of(model:Path)->dict:
    return {(c,s,int(L),int(g)):float(v)for k,v in load(model)['seconds_per_point'].items()for c,s,L,g in [k.split(':')]}

# ================================================================ part 1: synthetic pilots
def part1(X:Pkg):
    D=X.D;inv=load(X.pkg/'inputs/inventory.json');n_graphs=sum(len(v)for s in inv for v in inv[s].values());assert n_graphs==24173,n_graphs
    meta=dict(campaign='synthetic',manifest_sha256='0'*64,seed=424242,executable_sha256='0'*64,numerics='exact',rates_identity='default',
              inputs_manifest_sha256=digest(X.pkg/'inputs/manifest.json'),test_only=False,backend='gmp',threads=8,allocation={'source':'pilot','points':4096,'replicates':16})
    sig=lambda c,s,L,r:1e-2*(1+(r['id']%7))*(1.+.2*(L-3))
    cst=lambda c,s,L,r:(1.5 if c=='b'else 1.)*2e-7*math.sqrt(max(1,r['addends']))
    P=synth_pilot(D,inv,meta,sigma=sig,cost=cst)
    eta=lambda c,s,L:0.9*0.95
    td=X.td/'des1';td.mkdir()
    # the minimum design (a target no design misses) and its SE
    b0=D.freeze_core(P,fargs(D,td/'b0',target_se=1e30));se0=b0['predicted_se_total']
    d0=load(td/'b0/design.json');assert all(v==32 for v in d0['replicates'].values())and all(x['s']==1 for x in d0['strata'].values())
    # a target 1/3 of it: powers of two >= 4096, r in [32, 128], target met with the margin, caps
    seeds_log=X.td/'seeds_des1.json'
    for sd in (111,222):X.seedmod.add(seeds_log,sd,f'test seed {sd}')
    target=se0/3;b1=D.freeze_core(P,fargs(D,td/'b1',target_se=target,seeds_log=seeds_log))
    d1=load(td/'b1/design.json');m1=load(td/'b1/design_meta.json');c1=counts_of(td/'b1')
    allc=[n for g in c1.values()for n in g.values()];pow2=lambda n:n>0 and n&(n-1)==0
    assert len(allc)==2*n_graphs and all(pow2(n)and n>=4096 for n in allc)
    assert all(pow2(v)and 32<=v<=128 for v in d1['replicates'].values())and all(pow2(x['s'])for x in d1['strata'].values())
    assert b1['predicted_se_total']<=target*(1+1e-12)and m1['predictions']['se_total']==b1['predicted_se_total']
    cp=d1['caps'];o=D.Opts()
    assert all(v<=o.max_tasks for v in cp['tasks_per_campaign'].values())and cp['checkpoints']<=o.max_checkpoints and cp['max_replicates']<=128 and cp['predicted_max_task_seconds']<=o.max_task_seconds
    assert set(m1['forbidden_seeds'])>={424242,111,222},m1['forbidden_seeds']
    # A-DES-2 on the synthetic pilot: the report table, and the bundle's SE recomputed independently from the counts
    pr,stats,counts,r,s_map,K=check_bundle_against(P,td/'b1',eta)
    opt1=check_optimizer(P,td/'b1',eta)  # F13: the target met, never costlier than either old rule, a lattice local optimum
    import contextlib,io
    rep=D.report(P,D.Opts(),D.C8_MAGNITUDE,bundle=td/'b1');buf=io.StringIO()
    with contextlib.redirect_stdout(buf):D.print_report({k:v for k,v in rep.items()if k!='_tail_rows'})
    txt=buf.getvalue();assert 'target rel'in txt and all(f'{t:>10}'in txt for t in D.TARGETS_REL),txt[:400]
    assert close(rep['bundle']['se_total'],pr['se_total'])and close(rep['bundle']['se_total'],b1['predicted_se_total'])
    # an integer budget, spent core-hours and the total cap
    budget=math.floor(b1['allocated_core_hours_total']*0.8);bb=D.freeze_core(P,fargs(D,td/'bb',budget_core_hours=float(budget),spent_core_hours=3.,total_cap=float(budget+3)))
    assert bb['allocated_core_hours_total']<=budget
    for kw,needle in ((dict(budget_core_hours=float(budget),spent_core_hours=4.,total_cap=float(budget+3)),'exceeds the total cap'),):
        try:D.freeze_core(P,fargs(D,td/'bad_cap',**kw));raise AssertionError('accepted')
        except ValueError as e:assert needle in str(e)and not (td/'bad_cap').exists()
    # an infeasible budget, refused with its minimum = the hand value (the minimum design r = 32, s = 1)
    minimum=predict(stats,counts,{k:32 for k in r},{k:1 for k in s_map},1,1.5,eta)['cost_total_core_hours']
    try:D.freeze_core(P,fargs(D,td/'infeasible',budget_core_hours=math.floor(minimum*0.5)));raise AssertionError('accepted')
    except ValueError as e:assert f'minimum budget {math.ceil(minimum)} core-hours'in str(e)and not (td/'infeasible').exists(),str(e)
    # the minimum batch count: a per-campaign task cap that one batch of this target cannot meet
    t1=max(cp['tasks_per_campaign'].values());tmin=32*n_graphs  # r = 32, s = 1, one task per graph and replicate
    assert t1>tmin,(t1,tmin)
    capped=(t1+tmin)//2;bk=D.freeze_core(P,fargs(D,td/'bk',target_se=target,max_tasks=capped));kmin=bk['batches_minimum']
    assert kmin>=2 and bk['batches']==kmin and load(td/'bk/design.json')['batches']==kmin
    try:D.freeze_core(P,fargs(D,td/'bk_low',target_se=target,max_tasks=capped,batches=kmin-1));raise AssertionError('accepted')
    except ValueError as e:assert f'K = {kmin}'in str(e)and not (td/'bk_low').exists()
    bk2=D.freeze_core(P,fargs(D,td/'bk_more',target_se=target,max_tasks=capped,batches=kmin+1));assert bk2['batches']==kmin+1
    # every cap: a shortest task above --max-task-seconds is refused naming the graph
    try:D.freeze_core(P,fargs(D,td/'bad_task',target_se=target,max_task_seconds=1e-4));raise AssertionError('accepted')
    except ValueError as e:assert 'the shortest allowed task'in str(e)and 'graph ('in str(e),str(e)
    # atomic, never overwritten: an existing bundle is refused; a failure mid-publication leaves no bundle and no staging
    try:D.freeze_core(P,fargs(D,td/'b1',target_se=target));raise AssertionError('overwrote')
    except FileExistsError:pass
    real=Path.write_bytes;calls=[0]
    def boom(self,data):
        calls[0]+=1
        if calls[0]==3:raise OSError('injected failure')
        return real(self,data)
    with mock.patch.object(Path,'write_bytes',boom):
        try:D.freeze_core(P,fargs(D,td/'torn',target_se=target));raise AssertionError('accepted')
        except OSError:pass
    assert not (td/'torn').exists()and not list(td.glob('torn.staging.*'))
    ok('A-DES-1_full_size_freeze_counts_replicates_budget_infeasible_K_atomic_seeds_caps',graphs=n_graphs,K_min=kmin,se_min=se0,target=target,
       allocated_core_hours=b1['allocated_core_hours_total'],infeasible_minimum=math.ceil(minimum),optimizer=opt1)
    ok('A-DES-2_report_table_and_independent_bundle_SE',se_total=pr['se_total'])
    y10_options(X,P,td)  # Stage-6 fix round 2
    f11_case(X,inv,meta,td,eta)
    optimizer_property(X)
    jdes5_records(X)
    # ---- A-DES-6 (a): d = 3 with the vendored inputs_d3/two_loop.json at the HANDOFF sha256
    h=load(X.pkg/'vendor/c8_assembly/HANDOFF_assembly.json');pin=next(f['sha256']for f in h['files']if f['path']=='inputs_d3/two_loop.json')
    tl3=X.pkg/'vendor/c8_assembly/inputs_d3/two_loop.json';assert digest(tl3)==pin
    small={s:{str(L):inv[s][str(L)][:3]for L in range(3,9)}for s in ('free','power')}
    P3=synth_pilot(D,small,dict(meta,seed=5151),reps=16,sigma=sig,cost=cst,full_jets=True,J8={})
    P3.J8=D.jacobian_rows(P3,D.read_two_loop(tl3),1.5)
    b3=D.freeze_core(P3,fargs(D,td/'d3',target_rel=1e-3,dimension=3,half_d=1.5,schema_prefix='c8-d3',two_loop=tl3,test_only=True))
    m3=load(td/'d3/design_meta.json');assert m3['parameters']['dimension']==3 and m3['parameters']['half_d']==1.5 and len(m3['counts_sha256'])==24
    assert m3['schema']==load(td/'d3/design.json')['schema']=='c8-d3-design-1',m3['schema']  # O11: the bundle schema follows --schema-prefix
    for kw,needle in ((dict(dimension=3,half_d=1.,schema_prefix='c8-d3'),'--half-d'),(dict(dimension=3,half_d=1.5,schema_prefix='c8-d2'),'--schema-prefix'),
                      (dict(dimension=2,half_d=1.,schema_prefix='c8-d3'),'--schema-prefix')):
        try:D.freeze_core(P3,fargs(D,td/'d3_bad',target_rel=1e-3,two_loop=tl3,test_only=True,**kw));raise AssertionError(f'accepted {kw}')
        except ValueError as e:assert needle in str(e)and not (td/'d3_bad').exists(),(kw,str(e))
    assert all(digest(td/'d3'/k)==v for k,v in m3['counts_sha256'].items())and digest(td/'d3/design.json')==m3['design_sha256']and b3['predicted_se_total']>0
    check_bundle_against(P3,td/'d3',eta);check_optimizer(P3,td/'d3',eta)  # A-DES-2 and the optimizer at d = 3
    J2=D.jacobian_rows(P3,D.read_two_loop(X.pkg/'inputs/two_loop.json'),1.)
    assert any(not np.allclose(P3.J8[L],J2[L])for L in range(3,9)),'the d = 3 Jacobian equals the d = 2 one'
    # ---- A-DES-6 (b): a 1/8 subsample of the L8 graphs, exact power laws, the imputed variance share = the hand value
    A,beta,Cc,gam=2e-2,0.35,3e-8,0.5
    sig_pl=lambda c,s,L,r:A*r['addends']**beta;cst_pl=lambda c,s,L,r:(1.5 if c=='b'else 1.)*Cc*r['addends']**gam
    sub=lambda c,s,L,r:L<8 or (r['id']%8==0)
    P8=synth_pilot(D,inv,dict(meta,seed=6161),sigma=sig_pl,cost=cst_pl,piloted=sub,exact=True)
    bi=D.freeze_core(P8,fargs(D,td/'imp',target_se=1e30))
    pr8,stats8,counts8,r8,s8,K8=check_bundle_against(P8,td/'imp',eta,impute_fit=True)
    true_sig={(c,s,L,r['id']):sig_pl(c,s,L,r)for c in 'ab'for s in ('free','power')for L in range(3,9)for r in inv[s][str(L)]}
    worst=max(abs(stats8[k]['sigma']/true_sig[k]-1)for k in stats8)
    assert worst<1e-9,worst  # the imputation recovers the exact power law
    hand=predict({k:dict(v,sigma=true_sig[k])for k,v in stats8.items()},counts8,r8,s8,K8,1.5,eta)['imputed_variance_share']
    n_imp=sum(1 for v in stats8.values()if not v['piloted'])
    assert close(bi['imputed_variance_share'],hand,1e-9)and bi['imputed_graphs']==n_imp>0,(bi['imputed_variance_share'],hand)
    check_optimizer(P8,td/'imp',eta,impute_fit=True)
    # ---- A-DES-6 (c): nested point counts, Var ~ n^(-2 alpha) with alpha = 0.7
    alpha=0.7;n1,n2=4096,16384
    sig_n=lambda n:(lambda c,s,L,r:1e-2*(1+r['id']%5)*(n/n1)**(0.5-alpha))
    Pn1=synth_pilot(D,small,dict(meta),points=n1,sigma=sig_n(n1),cost=cst,exact=True);Pn2=synth_pilot(D,small,dict(meta),points=n2,sigma=sig_n(n2),cost=cst,exact=True)
    rn=D.report(Pn1,D.Opts(),D.C8_MAGNITUDE,nested=Pn2);al=[x['alpha']for x in rn['strata'].values()if x['alpha']is not None]
    assert al and all(abs(a-alpha)<0.02 for a in al)and rn['alpha_note']is None,al
    ok('A-DES-6_d3_vendored_B2_subsample_imputation_nested_alpha',imputed_share=bi['imputed_variance_share'],hand_share=hand,imputed_graphs=n_imp,alphas=sorted(set(round(a,6)for a in al)))
    w12_batches(X,small,meta,td)  # Stage-6 fix round 4
    zc=z_bundle_setup(X,inv,meta,td,eta)  # Stage-6 fix round 3: Z10, Z9, Z12
    z10_synthetic(X,zc);z9_synthetic(X,zc);z12_nested(X,small,meta)
    tail_rules(X)
    rate_rule_synthetic(X)
    route_b_synthetic(X,inv,meta,td,eta)

def w12_batches(X:Pkg,small:dict,meta:dict,td:Path):
    """W12 (Stage-6 fix round 4, S6D-R4-03): the minimum-batch search is no longer capped at Opts.max_batches = 64 when
    --batches asks for more, a search limit is told apart from infeasibility, and the explicitly selected allocation is
    checked against every cap. A synthetic pilot (3 graphs per (sector, L), uniform sigma, 0.25 s per point: 256-point
    tasks, so the task count follows r x s) at a target 10x below the minimum design's SE under a per-campaign task cap
    of 1.2x the minimum design's tasks needs K_min = 92 batches (independently: --batches 91 refused naming K = 92).
    Before the fix: 'no batch count up to 64' with and without --batches 128."""
    D=X.D;w=td/'w12';w.mkdir()
    P=synth_pilot(D,small,dict(meta,seed=1212),sigma=lambda c,s,L,r:1e-2,cost=lambda c,s,L,r:0.25,exact=True)
    D.freeze_core(P,fargs(D,w/'min',target_se=1e30));se0=load(w/'min/design_meta.json')['predictions']['se_total'];c0=load(w/'min/design.json')['caps']
    t0=max(c0['tasks_per_campaign'].values());cap=int(1.2*t0);target=se0/10
    # without --batches: the search limit (the minimum design of one batch meets the caps), not infeasibility
    try:D.freeze_core(P,fargs(D,w/'limit',target_se=target,max_tasks=cap));raise AssertionError('accepted')
    except ValueError as e:assert 'no batch count up to 64'in str(e)and 'the search limit'in str(e)and 'not infeasibility'in str(e)and not (w/'limit').exists(),str(e)
    # --batches 128: the search runs past 64 and finds K_min; the bundle has 128 batches, every cap held, the target met
    b=D.freeze_core(P,fargs(D,w/'k128',target_se=target,max_tasks=cap,batches=128));dj=load(w/'k128/design.json')
    kmin=b['batches_minimum'];assert b['batches']==128 and 64<kmin<128 and dj['batches']==128 and dj['batches_minimum']==kmin,(b['batches'],kmin)
    assert dj['caps']['ok']and dj['caps']['task_ok']and all(v<=cap for v in dj['caps']['tasks_per_campaign'].values())and b['predicted_se_total']<=target*(1+1e-12)
    for k in (kmin-1,70):  # independently: no batch count below K_min meets the caps (searched up to the request, past 64)
        try:D.freeze_core(P,fargs(D,w/'k_low',target_se=target,max_tasks=cap,batches=k));raise AssertionError('accepted')
        except ValueError as e:assert str(e).startswith(f'--batches {k} is below the minimum batch count: no batch count up to {k}')and not (w/'k_low').exists(),str(e)
    try:D.freeze_core(P,fargs(D,w/'k_low',target_se=target,max_tasks=cap,batches=32));raise AssertionError('accepted')  # below 64: searched up to 64
    except ValueError as e:assert str(e).startswith('--batches 32 is below the minimum batch count: no batch count up to 64')and not (w/'k_low').exists(),str(e)
    bk=D.freeze_core(P,fargs(D,w/'k_min',target_se=target,max_tasks=cap,batches=kmin));assert bk['batches']==bk['batches_minimum']==kmin
    # infeasibility: a cap the minimum design of one batch breaks, whatever the batch count
    try:D.freeze_core(P,fargs(D,w/'infeasible',target_se=target,max_tasks=t0-1,batches=128));raise AssertionError('accepted')
    except ValueError as e:assert str(e).startswith('infeasible: even the minimum design of one batch')and not (w/'infeasible').exists(),str(e)
    # the explicitly selected allocation is validated: an optimizer result for K = --batches that breaks the task cap
    # (every s x 4: powers of two within the replicate bounds, so check_allocation alone would publish it) is refused
    real=D.optimize
    def bad(S,K,opts,*a,**k):
        r,s,ev=real(S,K,opts,*a,**k)
        return (r,{x:4*v for x,v in s.items()},ev)if K==100 else(r,s,ev)
    with mock.patch.object(D,'optimize',bad):
        try:D.freeze_core(P,fargs(D,w/'k100',target_se=target,max_tasks=cap,batches=100));raise AssertionError('accepted a cap-breaking --batches allocation')
        except ValueError as e:assert str(e).startswith('--batches 100: the design of one batch breaks the per-batch caps')and not (w/'k100').exists(),str(e)
    ok('W12_batch_search_past_64_with_batches_limit_vs_infeasible_selected_allocation_checked',K_min=kmin,cap=cap,minimum_tasks=t0)

def rewrite_bundle(src:Path,dst:Path,edit,repin:bool=False)->Path:
    """a copy of the bundle src with edit(dst) applied; repin: design_meta.json then pins the edited design.json and
    counts files again (the meta's own sha256 changes, as a re-frozen bundle's would)"""
    shutil.copytree(src,dst);edit(dst)
    if repin:
        m=load(dst/'design_meta.json');m['design_sha256']=digest(dst/'design.json');m['counts_sha256']={k:digest(dst/k)for k in m['counts_sha256']}
        (dst/'design_meta.json').write_text(json.dumps(m,indent=1)+'\n')
    return dst

def z_bundle_setup(X:Pkg,inv,meta,td:Path,eta)->dict:
    """Stage-6 fix round 3, in-process: a synthetic pilot (the first 12 inventory graphs of each sector and loop, every
    third graph unpiloted, exact power-law variances, so the log-linear and the median imputation differ) and its bundle
    frozen with --variance-margin 2 and --impute median, its prediction equal to the independent recomputation
    (graph_stats, predict) at margin 2 with the median; and the report's own settings (1.5, addends) giving a clearly
    different SE. Shared by z10_synthetic and z9_synthetic."""
    D=X.D;sub={s:{str(L):inv[s][str(L)][:12]for L in range(3,9)}for s in ('free','power')}
    A,beta,Cc,gam=2e-2,0.35,3e-8,0.5
    Pz=synth_pilot(D,sub,dict(meta,seed=7171,manifest_sha256='7'*64),sigma=lambda c,s,L,r:A*r['addends']**beta,cost=lambda c,s,L,r:Cc*r['addends']**gam,
                   piloted=lambda c,s,L,r:r['id']%3!=0,exact=True)
    zd=td/'z10';zd.mkdir()
    b=D.freeze_core(Pz,fargs(D,zd/'m2med',target_se=1e30,variance_margin=2.,impute='median'))
    fm=load(zd/'m2med/design_meta.json');fd=load(zd/'m2med/design.json');cnt=counts_of(zd/'m2med')
    r={k:int(v)for k,v in fd['replicates'].items()};s={k:int(v['s'])for k,v in fd['strata'].items()};K=int(fd['batches'])
    hand_med=predict(graph_stats(Pz,False),cnt,r,s,K,2.,eta)['se_total'];hand_fit=predict(graph_stats(Pz,True),cnt,r,s,K,1.5,eta)['se_total']
    assert close(hand_med,fm['predictions']['se_total'])and close(b['predicted_se_total'],hand_med)and fm['imputed']['impute']=='median',(hand_med,fm['predictions'])
    assert abs(hand_fit/hand_med-1)>0.2,(hand_fit,hand_med)  # the report's own settings give a clearly different SE
    return dict(Pz=Pz,zd=zd,fm=fm,sub=sub,meta=meta,hand_med=hand_med,hand_fit=hand_fit,shape=(A,beta,Cc,gam))

def z10_synthetic(X:Pkg,zc:dict):
    """Stage-6 fix round 3, Z10 (S6D-R3-03), in-process (z_bundle_setup's bundle): a bundle frozen with
    --variance-margin 2 and --impute median is reported by report() with its defaults (margin 1.5, imputation addends)
    at its FROZEN settings: the bundle SE equals the frozen prediction (before: the report's settings, 27% below it)
    and the independent recomputation (graph_stats, predict) at margin 2 with the median; requested other settings (1.5, addends) appear only as the labelled projection, equal to the
    independent recomputation at those settings; a report from another pilot (another manifest sha256) is labelled a
    projection that does not recompute the frozen prediction."""
    D=X.D;Pz,zd,fm,sub,meta,hand_med,hand_fit=(zc[k]for k in ('Pz','zd','fm','sub','meta','hand_med','hand_fit'));A,beta,Cc,gam=zc['shape']
    rep0=D.report(Pz,D.Opts(),D.C8_MAGNITUDE,bundle=zd/'m2med')['bundle']  # the report's defaults: margin 1.5, imputation addends
    assert close(rep0['se_total'],fm['predictions']['se_total'])and close(rep0['se_total'],hand_med),(rep0['se_total'],hand_med,hand_fit)
    assert rep0['projection']is None and rep0['agrees']is True and rep0['frozen_settings']=={'variance_margin':2.,'impute':'median'},rep0
    rep=D.report(Pz,D.Opts(),D.C8_MAGNITUDE,bundle=zd/'m2med',bundle_projection={'variance_margin':1.5,'impute':'addends'})['bundle']
    assert close(rep['se_total'],fm['predictions']['se_total'])and rep['agrees']is True,rep
    pj=rep['projection'];assert pj and 'PROJECTION'in pj['label']and close(pj['se_total'],hand_fit)and pj['variance_margin']==1.5 and pj['impute']=='addends',pj
    Po=synth_pilot(D,sub,dict(meta,seed=7172,manifest_sha256='8'*64),sigma=lambda c,s,L,r:2*A*r['addends']**beta,cost=lambda c,s,L,r:Cc*r['addends']**gam,
                   piloted=lambda c,s,L,r:r['id']%3!=0,exact=True)
    ro=D.report(Po,D.Opts(),D.C8_MAGNITUDE,bundle=zd/'m2med')['bundle']
    assert ro['pilot_is_the_frozen_pilot']is False and ro['agrees']is False and 'PROJECTION'in ro['kind'],ro
    ok('Z10_report_bundle_SE_at_its_frozen_margin_and_imputation_projection_labelled',frozen=fm['predictions']['se_total'],projection=pj['se_total'])

def z9_synthetic(X:Pkg,zc:dict):
    """Stage-6 fix round 3, Z9 (S6D-R3-02), in-process (z_bundle_setup's bundle): report refuses, before designing
    anything, copies of the bundle with one graph's count doubled (the finding), design.json's batches changed, a counts
    file unpinned, each without the digest updated, and, with the digests re-pinned, a repeated graph line, a count of 0,
    a count written +n and a bundle of another schema; a byte-identical copy is accepted."""
    D=X.D;Pz,zd,fm=zc['Pz'],zc['zd'],zc['fm']
    def double_first(name):
        def f(d):
            p=d/name;lines=p.read_text().splitlines();g,n=lines[0].split();lines[0]=f'{g} {2*int(n)}';p.write_text('\n'.join(lines)+'\n')
        return f
    def batches_plus(d):x=load(d/'design.json');x['batches']+=1;(d/'design.json').write_text(json.dumps(x,indent=1)+'\n')
    def unpin(d):m=load(d/'design_meta.json');m['counts_sha256'].pop('counts/b_power_L5.txt');(d/'design_meta.json').write_text(json.dumps(m,indent=1)+'\n')
    def dup_line(d):p=d/'counts/a_free_L6.txt';t=p.read_text();p.write_text(t+t.splitlines()[0]+'\n')
    def zero(d):p=d/'counts/a_power_L4.txt';lines=p.read_text().splitlines();lines[0]=lines[0].split()[0]+' 0';p.write_text('\n'.join(lines)+'\n')
    def plus(d):p=d/'counts/b_free_L3.txt';lines=p.read_text().splitlines();g,n=lines[0].split();lines[0]=f'{g} +{n}';p.write_text('\n'.join(lines)+'\n')
    def other_schema(d):
        for f in ('design_meta.json','design.json'):x=load(d/f);x['schema']='c8-d3-design-1';(d/f).write_text(json.dumps(x,indent=1)+'\n')
    cases=(('one graph count doubled, digest unchanged (the finding)',double_first('counts/a_free_L8.txt'),False,'differs from the digest'),
           ('design.json batches + 1, digest unchanged',batches_plus,False,'differs from the digest'),
           ('a counts file unpinned',unpin,False,'exactly the 24 counts files'),
           ('a repeated graph line (re-pinned)',dup_line,True,'of a new graph'),('a count of 0 (re-pinned)',zero,True,'positive count'),
           ('a count written +n (re-pinned)',plus,True,'positive count'),('a c8-d3 bundle read as c8-d2 (re-pinned)',other_schema,True,'c8-d2-design-1'))
    seen=[]
    for i,(name,edit,repin,needle) in enumerate(cases):
        bad=rewrite_bundle(zd/'m2med',zd/f'bad{i}',edit,repin)
        try:D.report(Pz,D.Opts(),D.C8_MAGNITUDE,bundle=bad);raise AssertionError(f'Z9: report accepted a bundle with {name}')
        except ValueError as e:assert needle in str(e),(name,str(e));seen.append(name)
    same=rewrite_bundle(zd/'m2med',zd/'copy',lambda d:None)
    assert close(D.report(Pz,D.Opts(),D.C8_MAGNITUDE,bundle=same)['bundle']['se_total'],fm['predictions']['se_total'])
    ok('Z9_report_reads_the_bundle_through_the_verified_reader',refused=seen)

def z12_nested(X:Pkg,small,meta):
    """Stage-6 fix round 3, Z12 (S6D-R3-05): nested_alpha keeps every graph's own point ratio. The finding's case (two
    graphs of replicate variance 1 at n, at 2n and 8n with exact variances 1/2 and 1/8: alpha 1/2; before, the last
    graph's ratio gave ln(16/5)/(2 ln 8) = 0.28), in both graph orders and with the pilot's counts above the nested
    one's for one graph; mixed ratios at alpha 0.7 recover 0.7, a common ratio the closed form (the old formula), equal
    point counts are left out and counted, alpha per ratio recorded; a nested pilot of another scientific identity
    (numerics, rates identity, inputs manifest, backend, two-loop jet) is refused by nested_alpha and by report."""
    D=X.D
    def ser(v,R=8):return math.sqrt(v*(R-1)/R)*np.array([1.,-1.]*(R//2))  # a replicate series of exact sample variance v
    def tables(rows):
        """rows: (graph, n_pilot, v_pilot, n_nested, v_nested) of one free L5 stratum"""
        T={('a','free',5):{g:dict(piloted=True,stratum='free_L5',n_pilot=n1,y=ser(v1))for g,n1,v1,_,_ in rows}}
        TN={('a','free',5):{g:dict(piloted=True,stratum='free_L5',n_pilot=n2,y=ser(v2))for g,_,_,n2,v2 in rows}}
        return T,TN
    idm=dict(meta,dimension=2,schema_prefix='c8-d2',half_d=1,two_loop_sha256='2'*64)
    P=D.Pilot({},{},dict(idm,campaign='P'));N=D.Pilot({},{},dict(idm,campaign='N'))
    n=4096;got={}
    for name,rows,want in (('the finding',[(1,n,1.,2*n,.5),(2,n,1.,8*n,1/8)],.5),('the finding, graphs reversed',[(1,n,1.,8*n,1/8),(2,n,1.,2*n,.5)],.5),
                           ('one graph with the nested count below the pilot\'s',[(1,2*n,.5,n,1.),(2,n,1.,8*n,1/8)],.5),
                           ('mixed ratios at alpha 0.7',[(g,n,v,n*k,v*k**(-1.4))for g,v,k in ((1,1.,2),(2,3.,4),(3,.2,16),(4,7.,2))],.7)):
        a=D.nested_alpha(P,N,*tables(rows))['free_L5'];got[name]=a['alpha']
        assert a['alpha']is not None and abs(a['alpha']-want)<1e-9 and a['graphs']==len(rows),(name,a)
    old=-0.5*math.log((1/2+1/8)/2)/math.log(8)
    assert abs(old-math.log(16/5)/(2*math.log(8)))<1e-12 and abs(old-.5)>.2  # the pre-fix value of the finding's case
    rows=[(g,n,v,4*n,v*4**(-1.2))for g,v in ((1,1.),(2,2.),(3,5.))]+[(9,n,1.,n,1.)]
    a=D.nested_alpha(P,N,*tables(rows))['free_L5']
    assert abs(a['alpha']-.6)<1e-12 and a['estimator']=='one ratio'and a['equal_points_left_out']==1 and a['ratios']==[4.]and a['graphs']==3,a
    a=D.nested_alpha(P,N,*tables([(1,n,1.,2*n,.5),(2,n,1.,8*n,1/8)]))['free_L5']
    assert a['estimator']=='pooled over ratios'and set(a['alpha_by_ratio'])=={'2','8'}and all(abs(x-.5)<1e-12 for x in a['alpha_by_ratio'].values()),a
    refused=[]
    for k,v in (('numerics','dd+mp256'),('rates_identity','f'*64),('inputs_manifest_sha256','9'*64),('backend','decimal'),('two_loop_sha256','3'*64)):
        Nx=D.Pilot({},{},dict(idm,campaign='Nx',**{k:v}))
        try:D.nested_alpha(P,Nx,*tables([(1,n,1.,2*n,.5)]));raise AssertionError(f'Z12: a nested pilot of another {k} accepted')
        except ValueError as e:assert 'scientific identity'in str(e)and k in str(e),str(e);refused.append(k)
    # through report, on synthetic pilots of the small inventory (the A-DES-6 nested pair, its nested one under dd+mp256)
    cst=lambda c,s,L,r:2e-7;sg=lambda c,s,L,r:1e-2*(1+r['id']%5)
    Pn1=synth_pilot(D,small,dict(meta),points=4096,sigma=sg,cost=cst,exact=True);Pn2=synth_pilot(D,small,dict(meta,numerics='dd+mp256'),points=16384,sigma=sg,cost=cst,exact=True)
    try:D.report(Pn1,D.Opts(),D.C8_MAGNITUDE,nested=Pn2);raise AssertionError('Z12: report accepted a nested pilot under another numerics')
    except ValueError as e:assert 'scientific identity'in str(e),str(e)
    ok('Z12_nested_alpha_per_graph_ratio_and_scientific_identity',alphas=got,refused=refused)

def z10_cli(X:Pkg,td:Path,pil:Path,common:list,T:float):
    """Stage-6 fix round 3, Z10 on the command line (the fake pilot of part 2): a bundle frozen with --variance-margin 2
    is reported at that margin by report without --variance-margin (before: at 1.5, 25% below the frozen prediction),
    and with --variance-margin 2; an explicit --variance-margin 1.5 adds the labelled projection (0.75 x the frozen SE)
    while the bundle SE stays the frozen one."""
    X.T('design.py','freeze','--pilot',pil,'--out',td/'B_m2','--target-se',T,*common,'--variance-margin',2)
    fse=load(td/'B_m2/design_meta.json')['predictions']['se_total']
    for name,extra,proj in (('default',(),None),('--variance-margin 2',('--variance-margin',2),None),('--variance-margin 1.5',('--variance-margin',1.5),1.5)):
        out=td/f'rep_m2_{len(extra)}_{proj}.json'
        r=X.T('design.py','report','--pilot',pil,'--bundle',td/'B_m2','--test-only','--json',out,*extra);b=load(out)['bundle']
        assert close(b['se_total'],fse)and b['agrees']is True and b['frozen_settings']['variance_margin']==2 and 'recomputed, agrees'in r.stdout,(name,b)
        if proj is None:assert b['projection']is None and 'PROJECTION'not in r.stdout,(name,b['projection'])
        else:assert close(b['projection']['se_total'],fse*proj/2)and 'PROJECTION'in r.stdout and 'PROJECTION'in b['projection']['label'],(name,b['projection'])
    ok('Z10_report_cli_frozen_margin_and_labelled_projection',frozen_se=fse)

def z9_cli(X:Pkg,td:Path,pil:Path):
    """Stage-6 fix round 3, Z9 on the command line: report --bundle refuses (exit 2, no JSON written) a copy of B1 with
    one graph's count doubled and its digest unchanged (the finding; before: exit 0 with a changed SE) and a copy whose
    design.json changed."""
    def double(d):
        p=d/'counts/a_free_L8.txt';lines=p.read_text().splitlines();g,n=lines[0].split();lines[0]=f'{g} {2*int(n)}';p.write_text('\n'.join(lines)+'\n')
    def batches(d):x=load(d/'design.json');x['batches']=7;(d/'design.json').write_text(json.dumps(x,indent=1)+'\n')
    for name,edit in (('a doubled count (the finding)',double),('design.json changed',batches)):
        bad=rewrite_bundle(td/'B1',td/f'B1_z9_{edit.__name__}',edit)
        r=X.T('design.py','report','--pilot',pil,'--bundle',bad,'--test-only','--json',td/f'rep_z9_{edit.__name__}.json',expect=2)
        assert 'differs from the digest in design_meta.json'in r.stderr and not (td/f'rep_z9_{edit.__name__}.json').exists(),(name,r.stderr[-400:])
    ok('Z9_report_cli_refuses_damaged_bundles')

def z9_class_cli(X:Pkg,td:Path,pil:Path,pr_:Path,prov:Path,T:float,common:list):
    """Z9's class (Stage-6 fix round 3): freeze --rates-bundle reads the provisional bundle through the verified reader
    (a copy whose rates.json changed after design.py rates is refused, exit 2, nothing created; before: frozen), and
    rates --source-bundle verifies the source bundle (a copy of B1 with one count changed is refused; before: a
    provisional bundle recording the damaged source)."""
    badp=rewrite_bundle(prov,td/'PROV_bad',lambda d:(d/'rates.json').write_bytes((d/'rates.json').read_bytes()+b' '))
    r=X.T('design.py','freeze','--pilot',pr_,'--rates-bundle',badp,'--out',td/'F_badp','--target-se',T,*common,expect=2)
    assert 'rates.json differs from the digest'in r.stderr and not (td/'F_badp').exists(),r.stderr[-400:]
    badsrc=rewrite_bundle(td/'B1',td/'B1_bad',lambda d:(d/'counts/a_free_L8.txt').write_text((d/'counts/a_free_L8.txt').read_text().replace(' ',' 1',1)))
    r=X.T('design.py','rates','--pilot',pil,'--source-bundle',badsrc,'--spec',td/'spec.json','--out',td/'PROV_badsrc',expect=2)
    assert 'differs from the digest'in r.stderr and not (td/'PROV_badsrc').exists(),r.stderr[-400:]
    ok('Z9_class_rates_bundle_and_source_bundle_verified')

def route_b_synthetic(X:Pkg,inv,meta,td,eta):
    """Route (b) in-process (design.py freeze --numerics, profile_recost): an approved profile for a bundle frozen from
    an EXACT pilot, re-costed with a cost model measured under the profile (here a non-uniform speed-up per (sector, L),
    so the allocation changes), the pilot's sigma kept. F13 keep-cheaper (check_route_b_choice): both candidates
    recomputed independently and the cheaper feasible one kept; the re-optimized branch (this profile) has counts, r,
    s, predicted SE and cost equal to the independent recomputation with the profile's costs and is a lattice local
    optimum never costlier than either old rule (check_optimizer); a second profile (a 10x speed-up for the graphs with
    id = 1 mod 7, L8 0.4x) keeps the exact allocation at one target and re-optimizes at a tighter one. Its SE
    recomputed from its counts (report --bundle) is the frozen one; the record (profile, approval, allow-list
    reference, gate sha256 and job, exact pilot, cost model, both candidates) is complete; report re-costs the table
    and names the branch. Refused, creating nothing: a profile outside the approved set, no approval,
    a cost model of another numerics or rates identity or missing a graph, no cost model, no gate, a gate that did not
    pass, is of another profile, a development build, not full scale, or named twice, lacks the Stage-6 fix round 1
    evidence (no F1 coverage, one sector, an unmet promotion quota, no build binding, an executable not reproduced, F5
    team sizes not verified), lacks the fix round 4 input-set identity or names other inputs (W18), a cost model measured with a
    build no gate passed (Stage 6: cost_model.executable_gated enforced), a pilot under a profile, a rate map, a c8-d3
    pilot, and route-(b) options on the exact path."""
    D,prod=X.D,X.prod
    sig=lambda c,s,L,r:1e-2*(1+(r['id']%7))*(1.+.2*(L-3))
    cst=lambda c,s,L,r:(1.5 if c=='b'else 1.)*2e-7*math.sqrt(max(1,r['addends']))
    # the profile's speed-up per point: by stratum (L8 0.4x, L7 0.35x, power L <= 6 0.6x, free L <= 6 1x, primitives 0.9x)
    # and, within each stratum, 0.7x for odd graph ids, so that the base counts change too
    kf=lambda s,L,r:(0.7 if r['id']%2 else 1.)*(0.9 if (s=='free'and L==8 and r.get('primitive'))else(0.4 if L==8 else 0.35 if L==7 else 0.6 if s=='power'else 1.0))
    P=synth_pilot(D,inv,dict(meta,seed=5353,manifest_sha256='3'*64),sigma=sig,cost=cst,exact=True)
    rows=[(c,s,L,r)for c in 'ab'for s in ('free','power')for L in range(3,9)for r in inv[s][str(L)]]
    spp={f'{c}:{s}:{L}:{r["id"]}':kf(s,L,r)*cst(c,s,L,r)for c,s,L,r in rows};costs={(c,s,L,r['id']):kf(s,L,r)*cst(c,s,L,r)for c,s,L,r in rows}
    rb=td/'route_b';rb.mkdir();cm=rb/'cm_dd.json';cm.write_text(json.dumps(cost_model_doc('dd+mp256',spp)))
    IM=meta['inputs_manifest_sha256'];gate=gate_record(rb/'clflag.990001.0/jflag_dd+mp256/numerics_flags.json','dd+mp256','e'*64,'0'*64,inv,inputs=IM)
    rbk=dict(numerics='dd+mp256',approved_numerics_change=APPR_B,cost_model=cm,numerics_gate=[gate])
    se0=D.freeze_core(P,fargs(D,rb/'ex0',target_se=1e30))['predicted_se_total'];T=se0/2
    ex=D.freeze_core(P,fargs(D,rb/'EX',target_se=T));b=D.freeze_core(P,fargs(D,rb/'RB',target_se=T,**rbk))
    chosen,kept,reo=check_route_b_choice(P,rb/'RB',rb/'EX',eta,costs);assert chosen=='reoptimized'and b['route_b_chosen']==chosen,(chosen,kept,reo)
    pr,stats,counts,r,s_map,K=check_bundle_against(P,rb/'RB',eta,costs=costs);optb=check_optimizer(P,rb/'RB',eta,costs=costs)
    assert b['numerics']=='dd+mp256'and pr['se_total']<=T*(1+1e-12)
    rep_=D.report(P,D.Opts(),D.C8_MAGNITUDE,bundle=rb/'RB');assert close(rep_['bundle']['se_total'],b['predicted_se_total'])  # sigma: the exact pilot's
    assert counts_of(rb/'RB')!=counts_of(rb/'EX')and (b['replicates'],b['s'])!=(ex['replicates'],ex['s'])and b['allocated_core_hours_total']<0.8*ex['allocated_core_hours_total'],(b,ex)
    # F13 keep-cheaper on a second profile: the exact allocation kept at T (strictly cheaper), re-optimized at T/2.5
    kf2=lambda s,L,r:(0.1 if r['id']%7==1 else 1.)*(0.4 if L==8 else 1.)
    spp2={f'{c}:{s}:{L}:{r["id"]}':kf2(s,L,r)*cst(c,s,L,r)for c,s,L,r in rows};costs2={(c,s,L,r['id']):kf2(s,L,r)*cst(c,s,L,r)for c,s,L,r in rows}
    cm2=rb/'cm_dd2.json';cm2.write_text(json.dumps(cost_model_doc('dd+mp256',spp2)));rbk2=dict(rbk,cost_model=cm2);branches={}
    for name,tt,exb in (('RB2',T,rb/'EX'),('RB3',T/2.5,rb/'EX3')):
        if not exb.exists():D.freeze_core(P,fargs(D,exb,target_se=tt))
        b2=D.freeze_core(P,fargs(D,rb/name,target_se=tt,**rbk2));branches[name]=check_route_b_choice(P,rb/name,exb,eta,costs2)
        assert b2['route_b_chosen']==branches[name][0]
        if branches[name][0]=='kept_exact_allocation':assert counts_of(rb/name)==counts_of(exb)and b2['replicates']==load(exb/'design.json')['replicates']
        else:check_bundle_against(P,rb/name,eta,costs=costs2);check_optimizer(P,rb/name,eta,costs=costs2)
    assert [branches[n][0]for n in ('RB2','RB3')]==['kept_exact_allocation','reoptimized'],{n:v[0]for n,v in branches.items()}
    m2=load(rb/'RB2/design_meta.json')['route_b_choice'];assert m2['kept_exact_allocation']['cost_total_core_hours']<m2['reoptimized']['cost_total_core_hours']
    m=load(rb/'RB/design_meta.json');rec=m['profile_recost'];g=rec['gates'][0]
    assert m['numerics']=='dd+mp256'and m['pilot']['numerics']=='exact'and rec['route']=='b'and rec['profile']=='dd+mp256'and rec['approval']==APPR_B
    assert rec['approved_set']==sorted(prod.APPROVED_PROFILES)==['dd+mp256']and rec['approved_set_reference']==prod.APPROVED_PROFILES['dd+mp256']
    assert g['sha256']==digest(gate)and g['slurm_job']=='990001'and g['profile_executable_sha256']=='e'*64 and g['F2_total']['bound']==4.25e-16
    assert g['source_snapshot_sha256']==GATE_SNAPSHOT and g['F5_team_sizes_verified']is True and g['F1_coverage']['power']=={'binary128_accepted':50625,'mp_promoted':12568}
    assert g['inputs_manifest_sha256']==IM==m['inputs_manifest_sha256']  # W18: the gate entry carries the input set it ran on, the bundle's
    assert rec['cost_model']['sha256']==digest(cm)and rec['cost_model']['numerics']=='dd+mp256'and rec['cost_model']['executable_gated']is True
    assert rec['exact_pilot']['manifest_sha256']=='3'*64 and rec['exact_pilot']['numerics']=='exact'and rec['exact_pilot']['seed']==5353
    assert load(rb/'EX/design_meta.json')['profile_recost']is None and load(rb/'EX/design_meta.json')['numerics']=='exact'
    # report re-costed under the profile: every target cheaper than the exact table, the same sigma
    rc=D.profile_recost(P,NS(numerics='dd+mp256',cost_model=cm,schema_prefix='c8-d2'),freezing=False)
    rr=D.report(P,D.Opts(),D.C8_MAGNITUDE,recost=rc);r0=D.report(P,D.Opts(),D.C8_MAGNITUDE)
    assert rr['numerics']=='dd+mp256'and rr['profile_recost']['gates']==[]and all(x['allocated_core_hours']<y['allocated_core_hours']for x,y in zip(rr['targets'],r0['targets']))
    assert all(x['route_b_chosen']in ('reoptimized','kept_exact_allocation')for x in rr['targets'])and all('route_b_chosen'not in x for x in r0['targets'])
    # refusals: nothing is created
    def bad_cm(name,doc):f=rb/name;f.write_text(json.dumps(doc));return f
    spp_miss=dict(spp);spp_miss.pop(sorted(spp)[0])
    def gm(name,fn):return gate_record(rb/f'{name}/numerics_flags.json','dd+mp256','e'*64,'0'*64,inv,fn,inputs=IM)
    small={s:{str(L):v[:1]for L,v in inv[s].items()}for s in inv}
    cases=[('profile_dd',dict(rbk,numerics='dd'),'not in the user-approved set'),('profile_exp1',dict(rbk,numerics='dd+mp256+exp1'),'not in the user-approved set'),
           ('no_approval',dict(rbk,approved_numerics_change=None),'--approved-numerics-change'),('blank_approval',dict(rbk,approved_numerics_change='  '),'--approved-numerics-change'),
           ('cm_exact',dict(rbk,cost_model=bad_cm('cm_exact.json',cost_model_doc('exact',spp))),'numerics identity must equal the profile'),
           ('cm_rates',dict(rbk,cost_model=bad_cm('cm_rates.json',cost_model_doc('dd+mp256',spp,'f'*64))),'rates identity'),
           ('cm_missing',dict(rbk,cost_model=bad_cm('cm_miss.json',cost_model_doc('dd+mp256',spp_miss))),'inventory graphs missing'),
           ('cm_ungated',dict(rbk,cost_model=bad_cm('cm_ungated.json',dict(cost_model_doc('dd+mp256',spp),executable_sha256='d'*64))),
            'which none of the --numerics-gate records passed'),
           ('no_cm',dict(rbk,cost_model=None),'needs --cost-model'),('no_gate',dict(rbk,numerics_gate=None),'--numerics-gate'),
           ('gate_dev',dict(rbk,numerics_gate=[gm('g_dev',lambda x:x.update(development=['C8_DD_DEVELOPMENT']))]),'development options'),
           ('gate_other',dict(rbk,numerics_gate=[gm('g_other',lambda x:x.update(profile_name='dd'))]),"a gate of profile 'dd'"),
           ('gate_failed',dict(rbk,numerics_gate=[gm('g_failed',lambda x:x.update(status='failed'))]),"status 'failed'"),
           ('gate_f2',dict(rbk,numerics_gate=[gm('g_f2',lambda x:x['F2']['total'].update(passed=False))]),'F2 total gate'),
           ('gate_override',dict(rbk,numerics_gate=[gm('g_ov',lambda x:x['profile']['build_record'].update(parameter_overrides=['-DC8_MP256_RATIO=1e-30']))]),
            'development build'),
           ('gate_small',dict(rbk,numerics_gate=[gate_record(rb/'g_small/numerics_flags.json','dd+mp256','e'*64,'0'*64,small,inputs=IM)]),'not a full-scale gate'),
           ('gate_twice',dict(rbk,numerics_gate=[gate,gate]),'names one record twice'),
           # Stage-6 fix round 1: the gate evidence X1 (F1 coverage), X2 (build binding), X3 (F5 team sizes)
           ('gate_no_coverage',dict(rbk,numerics_gate=[gm('g_nocov',lambda x:x['F1'].pop('coverage'))]),'no F1 coverage record'),
           ('gate_one_sector',dict(rbk,numerics_gate=[gm('g_sector',lambda x:x['F1']['coverage']['sectors'].pop('power'))]),'not free and power'),
           ('gate_quota',dict(rbk,numerics_gate=[gm('g_quota',lambda x:x['F1']['coverage']['sectors']['free'].update(binary128_accepted=9999,need_met=False))]),'not the need'),
           ('gate_unbound',dict(rbk,numerics_gate=[gm('g_unbound',lambda x:x.pop('build_binding'))]),'no build binding'),
           ('gate_stale',dict(rbk,numerics_gate=[gm('g_stale',lambda x:x['build_binding']['executables']['profile'].update(reproduced=False))]),
            'the profile executable'),
           ('gate_team',dict(rbk,numerics_gate=[gm('g_team',lambda x:x['F5'].update(team_sizes_verified=False))]),'OpenMP team sizes'),
           # Stage-6 fix round 4 (W18): the gate's authenticated input set must be the pilot's
           ('gate_no_inputs',dict(rbk,numerics_gate=[gm('g_noinp',lambda x:x.pop('inputs'))]),'no authenticated input-set identity'),
           ('gate_other_inputs',dict(rbk,numerics_gate=[gm('g_othinp',lambda x:(x['inputs'].update(manifest_sha256='7'*64),x['f1_baseline'].update(inputs_manifest_sha256='7'*64)))]),
            'the gate ran on inputs manifest 777777777777..., not '+IM[:12]),
           ('gate_inputs_changed',dict(rbk,numerics_gate=[gm('g_chinp',lambda x:x['inputs'].update(verified_at_end=False))]),'at the start and at the end'),
           ('gate_inputs_incomplete',dict(rbk,numerics_gate=[gm('g_incinp',lambda x:x['inputs'].update(complete=False,skipped=['packs/free_L8.pack']))]),
            'incomplete input set'),
           ('rates_map',dict(rbk,rates_bundle=rb),'default-rate pilot'),
           ('d3',dict(rbk,dimension=3,half_d=1.5,schema_prefix='c8-d3',test_only=True),'approved for c8-d2 only'),
           ('exact_with_cm',dict(cost_model=cm),'belong(s) to --numerics'),('exact_with_gate',dict(numerics_gate=[gate]),'belong(s) to --numerics')]
    for name,kw,needle in cases:
        try:D.freeze_core(P,fargs(D,rb/f'bad_{name}',target_se=T,**kw));raise AssertionError(f'{name}: accepted')
        except ValueError as e:assert needle in str(e)and not (rb/f'bad_{name}').exists(),(name,str(e))
    P.meta['numerics']='dd+mp256'
    try:
        try:D.freeze_core(P,fargs(D,rb/'bad_pilot_profile',target_se=T,**rbk));raise AssertionError('a pilot under a profile accepted')
        except ValueError as e:assert 'EXACT pilot'in str(e)and not (rb/'bad_pilot_profile').exists(),str(e)
    finally:P.meta['numerics']='exact'
    ok('route_b_synthetic_freeze_recosted_sigma_kept_keep_cheaper_both_branches_recomputed_record_report_refusals',se=pr['se_total'],target=T,
       cost=pr['cost_total_core_hours'],exact_cost=ex['allocated_core_hours_total'],kept_candidate_cost=kept['cost_total_core_hours'],optimizer=optb,
       second_profile={n:dict(chosen=v[0],kept=v[1]['cost_total_core_hours'],reoptimized=v[2]['cost_total_core_hours'])for n,v in branches.items()},
       refusals=len(cases)+1)

def y10_options(X:Pkg,P,td:Path):
    """Y10 (S6D-R2-02): design.py validates the allocation options before designing (check_options) and the designed
    allocation before publishing (check_allocation). Production bounds: replicates powers of two in [32, 128], min <=
    max, --min-points a power of two >= 4096, margin >= 1; test-only bundles may reduce them, never below two
    replicates. Every refusal names Y10 and creates nothing."""
    D=X.D;nan=float('nan')
    bad=[(dict(min_replicates=1,max_replicates=1),'--min-replicates 1:'),(dict(min_replicates=16),'--min-replicates 16:'),
         (dict(min_replicates=48),'--min-replicates 48:'),(dict(max_replicates=256),'--max-replicates 256:'),
         (dict(min_replicates=64,max_replicates=32),'--max-replicates 32 < --min-replicates 64'),(dict(min_points=2048),'--min-points 2048:'),
         (dict(min_points=5000),'--min-points 5000:'),(dict(variance_margin=0.5),'--variance-margin 0.5:'),(dict(variance_margin=nan),'--variance-margin nan:'),
         (dict(target_se=nan),'--target-se nan:'),(dict(target_se=float('inf')),'--target-se inf:'),(dict(spent_core_hours=-1.),'--spent-core-hours -1.0:'),
         (dict(min_chunk=100),'--min-chunk 100:'),(dict(checkpoint_tasks=4,threads=8),'--checkpoint-tasks 4:'),(dict(batches=0),'--batches 0:'),
         (dict(test_only=True,min_replicates=1,max_replicates=16,min_points=64),'--min-replicates 1: a test-only bundle needs a power of two >= 2')]
    for kw in bad:
        kw,needle=kw;kw=dict(kw);kw.setdefault('target_se',1e30)
        try:D.freeze_core(P,fargs(D,td/'y10_bad',**kw));raise AssertionError(f'accepted {kw}')
        except ValueError as e:assert needle in str(e)and 'Y10'in str(e)and not (td/'y10_bad').exists(),(kw,str(e))
    D.freeze_core(P,fargs(D,td/'y10_test',target_se=1e30,test_only=True,min_replicates=8,max_replicates=16,min_points=64))
    dt=load(td/'y10_test/design.json');assert all(8<=v<=16 and v&(v-1)==0 for v in dt['replicates'].values())and load(td/'y10_test/design_meta.json')['test_only'],dt['replicates']
    real=D.design_for
    def one_rep(*a_,**k_):
        d=real(*a_,**k_);d['r']={k:1 for k in d['r']};return d
    with mock.patch.object(D,'design_for',one_rep):
        try:D.freeze_core(P,fargs(D,td/'y10_inj',target_se=1e30));raise AssertionError('published r = 1')
        except ValueError as e:assert 'outside its bounds'in str(e)and 'Y10'in str(e)and not (td/'y10_inj').exists(),str(e)
    ok('Y10_allocation_options_production_bounds_test_only_reduced_never_below_two_allocation_checked_before_publication',refusals=len(bad)+1)

def f11_case(X:Pkg,inv,meta,td,eta):
    """F11 (J-DES-5, design.py split()): a synthetic full-size pilot reproducing the finding. The 248 free L8 primitives
    are cheap (0.16x) with 2x the sigma, so at the target where the other free L8 graphs' multiplier is 35.1 theirs is
    about 7.8x larger. The old rule (r from the group's LARGEST multiplier) gives the free L8 group r = 128 and runs the
    dominant stratum at 128 where 32 would do; the fixed rule takes r from the SMALLEST multiplier (32) and lets the
    primitives take s > 1. Every expected value is computed here independently of tools/design.py: the strata sums, the
    multipliers, the r rule, the continuous Neyman optimum and the old rule's allocation and cost."""
    D=X.D;prim=lambda s,L,r:s=='free'and L==8 and bool(r.get('primitive'))
    sig=lambda c,s,L,r:(2. if prim(s,L,r)else 1.)*1e-2*(1+(r['id']%7))*(1.+.2*(L-3))
    cst=lambda c,s,L,r:(0.16 if prim(s,L,r)else 1.)*(1.5 if c=='b'else 1.)*2e-7*math.sqrt(max(1,r['addends']))
    P=synth_pilot(D,inv,dict(meta,seed=4747,manifest_sha256='2'*64),sigma=sig,cost=cst,exact=True)
    stats=graph_stats(P);V,C=strata_hand(stats,base_counts_hand(stats,4096,4096),eta)
    lam1=35.1/math.sqrt(V['free_L8']/C['free_L8']);W=sum(math.sqrt(V[k]*C[k])for k in V);target=1.5*math.sqrt(W/lam1)
    m,rr,cont=r_rule_hand(V,C,target,1)
    assert close(m['free_L8'],35.1,1e-9)and m['free_L8_primitive']>5*m['free_L8']and rr['free_L8']==32,(m,rr)
    b=D.freeze_core(P,fargs(D,td/'f11',target_se=target));d=load(td/'f11/design.json');mt=load(td/'f11/design_meta.json')
    pr,_,counts,r,s_map,K=check_bundle_against(P,td/'f11',eta);opt=check_optimizer(P,td/'f11',eta)
    assert K==1 and r['free_L8']==32 and s_map['free_L8_primitive']>=2,(r,s_map)
    assert b['predicted_se_total']<=target*(1+1e-12)and close(pr['se_total'],b['predicted_se_total'])
    rep_=D.report(P,D.Opts(),D.C8_MAGNITUDE,bundle=td/'f11');assert close(rep_['bundle']['se_total'],pr['se_total'])  # A-DES-2: the bundle SE from its counts
    # the dominant free L8 stratum no longer forced to the primitives' 128; the design within 1.2x of the continuous
    # optimum and no costlier than the F11 rule's greedy design (check_optimizer; the prune pass may take a stratum
    # below pow2_round(m) where the target allows it)
    p2=lambda x:1<<max(0,int(round(math.log2(x))))if x>1 else 1
    assert r['free_L8']*s_map['free_L8']<=2*p2(m['free_L8'])<128,(r,s_map)
    new_over_cont=pr['cost_total_core_hours']/cont;assert new_over_cont<1.2 and pr['cost_total_core_hours']<=opt['greedy_F11']*(1+1e-12),(new_over_cont,opt)
    # the old rule (r from the LARGEST multiplier of the group), by hand: it meets the target too, at well over twice
    # the cost (F11 reproduced)
    big={}
    for k,mk in m.items():g=k.replace('_primitive','');big[g]=max(big.get(g,0.),mk)
    r_old={g:min(128,max(32,2**math.floor(math.log2(v))))for g,v in big.items()}
    s_old={k:(p2(mk/r_old[k.replace('_primitive','')])if mk>r_old[k.replace('_primitive','')]else 1)for k,mk in m.items()}
    old=predict(stats,counts,r_old,s_old,1,1.5,eta)
    assert r_old['free_L8']==128 and old['se_total']<=target and old['cost_total_core_hours']>2*pr['cost_total_core_hours'],(r_old,old,pr)
    ok('F11_A-DES-1_2_r_from_smallest_multiplier_primitives_take_s_cost_near_continuous_optimum_old_rule_reproduced',
       target=target,m_free_L8=m['free_L8'],m_primitive=m['free_L8_primitive'],r_free_L8=r['free_L8'],s_primitive=s_map['free_L8_primitive'],
       cost=pr['cost_total_core_hours'],continuous=cont,new_over_continuous=new_over_cont,old_rule_cost=old['cost_total_core_hours'],
       old_over_continuous=old['cost_total_core_hours']/cont,se=pr['se_total'],old_se=old['se_total'],greedy_F11=opt['greedy_F11'],
       greedy_F11_over_continuous=opt['greedy_F11']/cont,optimizer_kept=opt['kept'])

# ---------------------------------------------------------------- F13 and the F11 follow-up: the optimizer
def old_rule_hand(S,K,rule,target_se=None,budget_ch=None,margin=1.5,min_reps=32,max_reps=128):
    """The Stage-3 integer allocation on stratum sums S, written independently of tools/design.py: Neyman multipliers
    of the active strata (graphs, V1 > 0), r of each (sector, L) from its smallest ('F11') or largest ('Stage5')
    positive multiplier (min_reps without one), s = pow2_round(m/r) when m > r else 1; then the target loop (double the
    s of the stratum removing the most variance per cost added) or the budget loop (halve the s losing the least
    precision per cost saved, then the r of the costliest group; None when the minimum design exceeds the budget).
    Every stratum with graphs counts, the zero-variance ones at s = 1. Returns (cost core-hours, SE) or None."""
    g=lambda k:k.replace('_primitive','');act=[k for k in S if S[k]['graphs']and S[k]['V1']>0]
    root=sum(math.sqrt(S[k]['V1']*S[k]['C1'])for k in act);lam=(margin**2*root/(K*target_se**2))if target_se is not None else budget_ch*3600/(K*root)
    m={k:lam*math.sqrt(S[k]['V1']/S[k]['C1'])for k in act};r={}
    for grp in {g(k)for k in S}:
        ms=[m[k]for k in act if g(k)==grp];x=(min if rule=='F11'else max)(ms)if ms else 0.
        r[grp]=min(max_reps,max(min_reps,2**math.floor(math.log2(x))))if x>=1 else min_reps
    s={k:(P2(m[k]/r[g(k)])if k in m and m[k]>r[g(k)]else 1)for k in S}
    ev=lambda:(K*sum(S[k]['C1']*r[g(k)]*s[k]for k in S if S[k]['graphs'])/3600,margin*math.sqrt(sum(S[k]['V1']/(r[g(k)]*s[k])for k in S if S[k]['graphs'])/K))
    if target_se is not None:
        while ev()[1]>target_se*(1+1e-12):k=max(act,key=lambda k:(S[k]['V1']/(2*r[g(k)]*s[k]))/(S[k]['C1']*r[g(k)]*s[k]));s[k]*=2
        return ev()
    while ev()[0]>budget_ch*(1+1e-12):
        cand=[k for k in act if s[k]>1]
        if cand:k=min(cand,key=lambda k:(S[k]['V1']/(r[g(k)]*s[k]))/(S[k]['C1']*r[g(k)]*s[k]/2));s[k]//=2;continue
        grps=[x for x in r if r[x]>min_reps]
        if not grps:return None
        x=max(grps,key=lambda x:sum(S[k]['C1']for k in S if g(k)==x));r[x]//=2
    return ev()

def random_strata(D,rng,dominant=True)->dict:
    """A random stratum set: every stratum of strata_names (each but free L8 and its primitives absent with
    probability 0.15; 3% of the others without variance, 2% without graphs), V1 in 10^U(-1, 5), C1 in 10^U(-2, 3);
    in half the sets free L8 dominant (V1 x 10^U(1, 3), as on J-SWEEP-2); the primitives' sqrt(V1/C1) 10^U(0, 1.2)
    times free L8's, so their multiplier is the larger one and the two split rules differ."""
    S={}
    for k in D.strata_names():
        full=k.startswith('free_L8')
        if not full and rng.random()<0.15:continue
        S[k]=dict(V1=10**rng.uniform(-1,5),C1=10**rng.uniform(-2,3),graphs=int(rng.integers(1,1000)),piloted=1,V1_imputed=0.)
        if not full:
            u=rng.random()
            if u<0.03:S[k]['V1']=0.
            elif u<0.05:S[k]['graphs']=0
    if dominant and rng.random()<0.5:S['free_L8']['V1']*=10**rng.uniform(1,3)
    q=math.sqrt(S['free_L8']['V1']/S['free_L8']['C1'])*10**rng.uniform(0,1.2);S['free_L8_primitive']['C1']=S['free_L8_primitive']['V1']/q**2
    return S

def optimizer_property(X:Pkg,n_target=2000,n_budget=600):
    """F13 / F11 follow-up, randomized (seed 20261005): on n_target random stratum sets at a random target (free L8's
    multiplier in [2, 500], K in {1, 1, 2, 4}) design.optimize is feasible (SE <= target, r a power of two in [32, 128],
    s >= 1) and never costlier than EITHER old rule's final design (old_rule_hand: the Stage-5 rule and the F11 rule
    with the greedy target loop), while the old F11 rule alone is costlier than the Stage-5 rule in some sets (the
    verifier's non-monotone finding reproduced); on n_budget sets at a random budget (10^U(-0.2, 2.5) x the minimum
    design) optimize stays within the budget and is never less precise than either old rule, and refuses (Infeasible)
    exactly when the old rules do. Deterministic: a second run of a sample gives the same designs."""
    D=X.D;o=D.Opts();rng=np.random.default_rng(20261005);worse=[];gain=[];t0=time.time();n_diff=0
    for i in range(n_target):
        S=random_strata(D,rng);K=int(rng.choice([1,1,2,4]))
        act=[k for k in S if S[k]['graphs']and S[k]['V1']>0];root=sum(math.sqrt(S[k]['V1']*S[k]['C1'])for k in act)
        lam=10**rng.uniform(0.3,2.7)/math.sqrt(S['free_L8']['V1']/S['free_L8']['C1']);target=o.margin*math.sqrt(root/(K*lam))
        a=old_rule_hand(S,K,'F11',target);b=old_rule_hand(S,K,'Stage5',target);info={}
        r,s,ev=D.optimize(S,K,o,target,info=info)
        if a!=b:n_diff+=1
        if a[0]>b[0]*(1+1e-12):worse.append(a[0]/b[0])
        assert ev['se_total']<=target*(1+1e-12)and ev['cost_total_core_hours']<=min(a[0],b[0])*(1+1e-12),(i,ev,a,b)
        assert all(v in (32,64,128)for v in r.values())and all(x>=1 and x&(x-1)==0 for x in s.values()),(i,r,s)
        gain.append(ev['cost_total_core_hours']/min(a[0],b[0]))
        if i<20:assert D.optimize(S,K,o,target)==(r,s,ev)  # deterministic
    assert worse,'the randomized set never reproduces the old F11 rule costing more than the Stage-5 rule'
    bg=[];inf=0
    for i in range(n_budget):
        S=random_strata(D,rng,dominant=False);K=int(rng.choice([1,2]))
        mind=D.evaluate_design(S,{D.rgroup(k):32 for k in S},{k:1 for k in S},K,o.margin)['cost_total_core_hours'];budget=mind*10**rng.uniform(-0.2,2.5)
        a=old_rule_hand(S,K,'F11',budget_ch=budget);b=old_rule_hand(S,K,'Stage5',budget_ch=budget)
        try:r,s,ev=D.optimize(S,K,o,budget_ch=budget)
        except D.Infeasible:assert a is None and b is None,(i,a,b);inf+=1;continue
        assert a is not None and b is not None and ev['cost_total_core_hours']<=budget*(1+1e-12)and ev['se_total']<=min(a[1],b[1])*(1+1e-12),(i,ev,a,b)
        bg.append(ev['se_total']/min(a[1],b[1]))
    ok('F13_F11_optimizer_randomized_never_costlier_than_either_old_rule_feasible_budget_dual',target_sets=n_target,rules_differ=n_diff,
       old_F11_costlier_than_Stage5=len(worse),old_F11_over_Stage5_max=max(worse),new_over_best_old_median=float(np.median(gain)),new_over_best_old_min=min(gain),
       budget_sets=len(bg),budget_infeasible=inf,budget_se_over_best_old_median=float(np.median(bg)),seconds=round(time.time()-t0,1))

ETA_LANE=0.9146050173698389   # J-SMK-4's lane eta_node (benchmarks/symmetry_2026-10-c8/stage5/des5)
def jdes5_records(X:Pkg):
    """F13 on J-DES-5's real strata, from the committed records of the pre-Stage-6 re-check (job 570241,
    benchmarks/symmetry_2026-10-c8/pre6/p6des.570241.0: the strata V1, C1 of the exact (p6x) and route-(b) (p6b)
    freezes at the four targets, the exact freeze's counts in bundles.tgz) and the profile cost model they used
    (9b0dfec6..., the job's copy p6des.570241.0/gmp_symmetry_amd_c8_dd+mp256.json), in lane core-hours (x eta_node / 0.9146): the records reproduce the
    frozen numbers (exact 1,738 / 5,856 / 23,423 / 76,623; route (b) 923 / 3,322 / 13,289 / 33,978; the old exact
    allocation kept under dd+mp256 669 / 2,309 / 9,236 / 30,067); design.optimize gives the exact path and the
    re-optimized route (b) at most those, the target met, the re-optimized route (b) at most the verifier's lattice
    optimum near its split (638 / 2,554 / 10,215 / 31,371); route (b)'s keep-cheaper (the new exact allocation
    re-costed per graph with the profile's c_g, by hand) chooses the cheaper, and its result is at most the old kept
    allocation's."""
    import tarfile
    D=X.D;E=ROOT/'benchmarks/symmetry_2026-10-c8/pre6/p6des.570241.0';inv=load(ROOT/'inputs/inventory.json')
    # the model 570241 used (9b0dfec6..., job 570240, build d5df32ac): its copy in the job's evidence folder (fix round 3
    # replaced cost_models/gmp_symmetry_amd_c8_dd+mp256.json by the model of the new profile build)
    KP=E/'gmp_symmetry_amd_c8_dd+mp256.json';kp=load(KP)['seconds_per_point'];assert digest(KP).startswith('9b0dfec6')
    prim={(s,int(L),r['id']):bool(r.get('primitive'))for s in inv for L in inv[s]for r in inv[s][L]};counts={}
    with tarfile.open(E/'bundles.tgz')as t:
        for mem in t.getmembers():
            q=Path(mem.name)
            if len(q.parts)>=4 and q.parts[1]=='p6x_1e-3'and q.parts[2]=='counts'and mem.isfile():
                c,s,L=q.stem.split('_')
                for ln in t.extractfile(mem).read().decode().splitlines():
                    if ln.strip():g,n=ln.split();counts[(c,s,int(L[1:]),int(g))]=int(n)
    assert len(counts)==48346
    old={'1e-3':(1738,923,669),'5e-4':(5856,3322,2309),'2.5e-4':(23423,13289,9236),'1.35e-4':(76623,33978,30067)}
    lattice_verifier={'1e-3':638,'5e-4':2554,'2.5e-4':10215,'1.35e-4':31371};table={}
    for T,(ox,ob,ok_) in old.items():
        dx=load(E/f'design_p6x_{T}.json');db=load(E/f'design_p6b_{T}.json');tse=load(E/f'design_meta_p6x_{T}.json')['target']['se'];eta=dx['eta_node'];o=D.Opts()
        lane=lambda e:e['cost_total_core_hours']*eta/ETA_LANE
        Sx={k:dict(v,V1_imputed=0.)for k,v in dx['strata'].items()};Sb={k:dict(v,V1_imputed=0.)for k,v in db['strata'].items()}
        Ck={k:0. for k in Sx}
        for (c,s,L,g),n in counts.items():Ck[D.stratum_of(s,L,prim[(s,L,g)])]+=kp[f'{c}:{s}:{L}:{g}']*n/(dx['eta_omp'][f'{c}_{s}_L{L}']*eta)
        Sk={k:dict(v,C1=Ck[k])for k,v in Sx.items()}
        sx0={k:v['s']for k,v in dx['strata'].items()};sb0={k:v['s']for k,v in db['strata'].items()}
        e0x=D.evaluate_design(Sx,dx['replicates'],sx0,1,1.5);e0b=D.evaluate_design(Sb,db['replicates'],sb0,1,1.5);e0k=D.evaluate_design(Sk,dx['replicates'],sx0,1,1.5)
        assert close(e0x['cost_total_core_hours'],dx['predicted']['cost_total_core_hours'])and close(e0b['cost_total_core_hours'],db['predicted']['cost_total_core_hours'])
        assert (round(lane(e0x)),round(lane(e0b)),round(lane(e0k)))==(ox,ob,ok_),(T,lane(e0x),lane(e0b),lane(e0k))
        ix={};rx,sx,ex=D.optimize(Sx,1,o,tse,info=ix);ib={};rb,sb,eb=D.optimize(Sb,1,o,tse,info=ib)
        ek=D.evaluate_design(Sk,rx,sx,1,1.5)   # the new exact allocation kept, re-costed under dd+mp256
        for e in (ex,eb,ek):assert e['se_total']<=tse*(1+1e-12),(T,e)
        assert ex['cost_total_core_hours']<=e0x['cost_total_core_hours']*(1+1e-12)and eb['cost_total_core_hours']<=e0b['cost_total_core_hours']*(1+1e-12)
        assert lane(eb)<=lattice_verifier[T]+0.5,(T,lane(eb))
        keep=ek['cost_total_core_hours']<eb['cost_total_core_hours']*(1-1e-12);fin=ek if keep else eb
        assert fin['cost_total_core_hours']<=min(e0b['cost_total_core_hours'],e0k['cost_total_core_hours'])*(1+1e-12),(T,lane(fin),ob,ok_)
        table[T]=dict(target_se=tse,exact_old=lane(e0x),exact_new=lane(ex),exact_new_se=ex['se_total'],exact_kept_start=ix['kept'],
                      route_b_old=lane(e0b),route_b_reoptimized=lane(eb),route_b_reoptimized_se=eb['se_total'],route_b_old_allocation_kept=lane(e0k),
                      route_b_new_allocation_kept=lane(ek),route_b_chosen='kept_exact_allocation'if keep else'reoptimized',route_b_final=lane(fin),
                      exact_r=rx,exact_s=sx)
    assert [table[T]['route_b_chosen']for T in old]==['reoptimized','kept_exact_allocation','kept_exact_allocation','kept_exact_allocation'],{T:v['route_b_chosen']for T,v in table.items()}
    ok('F13_J-DES-5_records_exact_and_route_b_recomputed_not_costlier_keep_cheaper',lane_eta=ETA_LANE,table=table)

def tail_rules(X:Pkg):
    """The heavy-tail rule of design.py report (C63d's rule, LRI_C8_D3_HPC_loop/PLAN.md C.3/E.6, RECON.md 6.3.6):
    the screen and the confirmation only for L8 graphs, L <= 7 as diagnostics without labels; an undefined replicate
    (fewer than 16 values, a 16th |t| <= 0, tail_sum <= 0, a non-finite value) makes the graph undefined, never
    compared with a threshold and never averaged over the remaining replicates; the sector P8 (action 4) pooled over
    the L8 graph-campaigns at 4,096 points only; the stratum P8 flag (action 5) on L8 strata only. Every expected value
    is computed here independently of tools/design.py."""
    D=X.D;rng=np.random.default_rng(20261004);R=8
    def reps(kind,n):
        out=[]
        for _ in range(R):
            v=rng.random(n)**(-1/1.5)if kind=='heavy'else np.abs(rng.standard_normal(n))
            out.append((n,[float(x)for x in np.sort(v)[::-1][:16]],float(v.sum())))
        return out
    hill=lambda t:sum(math.log(t[i]/t[15])for i in range(15))/15
    # graphs: 1 heavy, 2 light, 3 a replicate with 15 values, 4 a 16th |t| = 0, 5 tail_sum 0, 6 a non-finite value,
    # 7 heavy at 32,768 points (the confirmation length); the same tails at L7 (diagnostics) and at L8 (thresholds)
    spec={1:('heavy',4096),2:('light',4096),3:('heavy',4096),4:('heavy',4096),5:('heavy',4096),6:('heavy',4096),7:('heavy',32768)}
    groups={};data={}
    for c in ('a','b'):
        for s in ('free','power'):
            for L in (7,8):
                tails={}
                for g,(kind,n) in spec.items():
                    t=reps(kind,n)
                    if c=='a'and g==3:t[2]=(n,t[2][1][:15],t[2][2])
                    if c=='b'and g==4:t[0]=(n,t[0][1][:15]+[0.],t[0][2])
                    if c=='a'and g==5:t[1]=(n,t[1][1],0.)
                    if c=='a'and g==6:t[3]=(n,[math.inf]+t[3][1][1:],t[3][2])
                    tails[g]=t;data[(c,s,L,g)]=t
                gids=sorted(spec);groups[(c,s,L)]=D.GroupData(c,s,L,R,gids,{g:spec[g][1]for g in gids},np.zeros((R,len(gids),2*(9-L))),{},1.0,tails)
    P=D.Pilot(groups,{},{})
    rows,fl=D.tail_table(P);by={(x['campaign'],x['sector'],x['L'],x['graph']):x for x in rows}
    for (c,s,L,g),t in data.items():
        x=by[(c,s,L,g)];assert x['use']==('thresholds'if L==8 else'diagnostic'),x
        bad=(c,g)in(('a',3),('b',4),('a',5),('a',6))
        if bad:assert x['status'].startswith('undefined (replicate ')and x['xi_hat']is None and x['largest_share']is None,x  # no mean over the other replicates
        else:
            assert x['status']=='defined'and close(x['xi_hat'],sum(hill(r[1])for r in t)/R,1e-12)and close(x['largest_share'],max(r[1][0]/r[2]for r in t),1e-12),x
    for (c,g),needle in ((('a',3),'fewer than 16 tail values (15)'),(('b',4),'the 16th |t| is 0.0 (<= 0)'),(('a',5),'tail_sum is 0.0 (<= 0)'),(('a',6),'tail value not finite')):
        assert needle in by[(c,'free',8,g)]['status'],(c,g,by[(c,'free',8,g)]['status'])
    key=lambda xs:sorted((x['sector'],x['L'],x['graph'])for x in xs)
    heavy_screen=[(s,8,g)for s in ('free','power')for g in (1,7)]
    assert key(fl['screened'])==sorted(heavy_screen),key(fl['screened'])
    assert key(fl['confirmed'])==[('free',8,7),('power',8,7)]and all(x['label']=='possible infinite variance'for x in fl['confirmed'])
    assert key(fl['undefined'])==sorted((s,8,g)for s in ('free','power')for g in (3,4,5,6)),key(fl['undefined'])
    # the L7 copies of the screened and confirmed graphs carry the same statistics, but no label
    assert all(by[(c,s,7,g)]['xi_hat']>D.XI_SCREEN for c in 'ab'for s in ('free','power')for g in (1,7))
    assert not any(x['L']!=8 for k in ('screened','confirmed','undefined')for x in fl[k])
    dg=fl['diagnostics'];assert sorted(dg)==['free_L7','power_L7']
    for s in ('free','power'):
        x=dg[f'{s}_L7'];dfn=[by[(c,s,7,g)]for c in 'ab'for g in spec if by[(c,s,7,g)]['status']=='defined']
        assert x['graph_campaigns']==2*len(spec)and x['undefined']==4 and close(x['xi_hat_max'],max(d['xi_hat']for d in dfn),1e-12),x
        assert not any(k.startswith(('screen','confirm','flag'))for k in x),x
    # the sector P8 (action 4): L8 graph-campaigns at 4,096 points only; L7 graphs and L8 graphs at 8,192 points are
    # left out although their replicate values are wild (Cauchy); power L8 has 16 replicates (two blocks of 8)
    T={};hand={}
    for c in ('a','b'):
        for s in ('free','power'):
            for L in (7,8):
                TT={}
                for g in range(40):
                    if L==8 and g<30:y=(rng.standard_t(2.5,16)if s=='power'else rng.standard_normal(8));n=4096
                    else:y=rng.standard_cauchy(8);n=8192 if L==8 else 4096
                    TT[g]=dict(piloted=True,y=y,n_pilot=n,stratum=f'{s}_L{L}',sigma=1.)
                    if L==8 and n==4096:hand.setdefault(s,[]).extend(math.log(np.var(y[b:b+4],ddof=1)/np.var(y[b+4:b+8],ddof=1))for b in range(0,len(y),8))
                T[(c,s,L)]=TT
    sp=D.sector_p8(None,T)
    a=1/(2/7);p8g=math.exp(math.lgamma(a+.5)+math.lgamma(a-.5)-2*math.lgamma(a))
    for s in ('free','power'):
        q=hand[s];vq=float(np.var(q,ddof=1));p8=p8g*math.exp(0.0890*(vq-(math.pi**2-8)))
        x=sp[s];assert x['graph_campaigns']==60 and x['blocks']==len(q)==(120 if s=='power'else 60)and x['excluded_L8_other_points']==20 and x['excluded_L_le_7']==80,x
        assert close(x['varQ'],vq,1e-12)and close(x['P8'],p8,1e-12)and x['R16_advised']==(p8>1.13),(x,vq,p8)
    assert sp['power']['R16_advised'],sp['power']
    # the stratum P8 flag (action 5): >= 500 graph-campaigns and P8 > 1.196 flags an L8 stratum, never an L7 one
    T2={(c,'free',L):{g:dict(piloted=True,y=rng.standard_cauchy(8),n_pilot=4096,stratum=f'free_L{L}',sigma=1.)for g in range(300)}for c in 'ab'for L in (7,8)}
    sh=D.stratum_shape(None,T2)
    assert sh['free_L7']['graph_campaigns']==sh['free_L8']['graph_campaigns']==600 and sh['free_L7']['P8']>1.196 and sh['free_L8']['P8']>1.196
    assert sh['free_L8']['P8_flag']and not sh['free_L7']['P8_flag'],(sh['free_L7'],sh['free_L8'])
    ok('A-DES_tails_L8_thresholds_L7_diagnostics_undefined_sector_P8_L8_4096',screened=len(fl['screened']),confirmed=len(fl['confirmed']),undefined=len(fl['undefined']),
       P8_free=sp['free']['P8'],P8_power=sp['power']['P8'])

def rate_rule_synthetic(X:Pkg):
    """A-FLAG-6 (G4c D1a): design.one_step_rule on a synthetic pilot whose W_b^2/W_a^2 = k is exact per stratum (campaign
    b's sigma is sqrt(k) times a's at equal cost, sample variances exact): every branch of the rule, W and r against the
    hand values, the bootstrap (every resample gives k), a and b different everywhere; refusals."""
    D=X.D
    N={('free',3):5,('free',4):3,('free',5):3,('free',6):120,('free',7):130,('free',8):140,('power',3):1,('power',4):3,('power',5):3,('power',6):110,('power',7):101,('power',8):150}
    k={('free',3):0.5,('free',6):1.0,('free',7):0.8,('free',8):1.25,('power',6):0.95,('power',7):1.15,('power',8):0.7}
    want={('free',7):('.9','1'),('free',8):('.7','.8'),('power',7):('.7','.8'),('power',8):('.9','1')}   # every other stratum keeps .8 / .9
    inv={s:{str(L):[{'id':1000*L+i,'primitive':False,'addends':1+i,'cost':1+i}for i in range(N[(s,L)])]for L in range(3,9)}for s in ('free','power')}
    sig=lambda c,s,L,r:(1+(r['id']%3))*(math.sqrt(k.get((s,L),1.))if c=='b'else 1.)
    cst=lambda c,s,L,r:1e-6*(1+(r['id']%5))
    meta=dict(campaign='synthetic-rule',manifest_sha256='1'*64,seed=4343,executable_sha256='0'*64,numerics='exact',rates_identity='default',
              inputs_manifest_sha256='0'*64,test_only=True,backend='gmp')
    P=synth_pilot(D,inv,meta,reps=8,points=64,sigma=sig,cost=cst,exact=True)
    spec,rec=D.one_step_rule(P,boot=200)
    assert rec['name']=='one-step'and rec['min_graphs']==100 and rec['band']==0.1 and rec['step']=='.1'and rec['pilot']['manifest_sha256']=='1'*64 and rec['spec']==spec
    for x in rec['strata']:
        s,L=x['sector'],x['L'];rows=inv[s][str(L)];kk=k.get((s,L),1.)
        Wa=sum((1+(r['id']%3))*math.sqrt(1e-6*(1+(r['id']%5)))for r in rows)
        assert x['graphs']==len(rows)and close(x['W']['a'],Wa,1e-9)and close(x['W']['b'],math.sqrt(kk)*Wa,1e-9)and close(x['ratio_W2_b_over_a'],kk,1e-9),(s,L,x)
        a_,b_=want.get((s,L),('.8','.9'));assert (x['rate_a'],x['rate_b'])==(a_,b_)==(spec['a'][s][str(L)],spec['b'][s][str(L)]),(s,L,x['decision'])
        assert ('fewer than min_graphs'in x['decision'])==(len(rows)<100),(s,L,x['decision'])
        if len(rows)>1:assert all(close(v,kk,1e-9)for v in x['bootstrap_ratio_W2'].values()),x['bootstrap_ratio_W2']
        else:assert x['bootstrap_ratio_W2']is None
        assert spec['a'][s][str(L)]!=spec['b'][s][str(L)]
    # the band's edges and min_graphs: with min_graphs 1 the 5-graph free L3 (k = 0.5) steps up; band 0.3 keeps free L8
    s1,_=D.one_step_rule(P,min_graphs=1,boot=0);assert (s1['a']['free']['3'],s1['b']['free']['3'])==('.9','1')
    s2,_=D.one_step_rule(P,band=0.3,boot=0);assert (s2['a']['free']['8'],s2['b']['free']['8'])==('.8','.9')and (s2['a']['free']['7'],s2['b']['free']['7'])==('.8','.9')
    s3,_=D.one_step_rule(P,step='0.05',boot=0);assert (s3['a']['free']['7'],s3['b']['free']['7'])==('.85','.95')and (s3['a']['free']['8'],s3['b']['free']['8'])==('.75','.85')
    for kw,needle in ((dict(step='0.2'),'(0, 1]'),(dict(band=1.5),'--band'),(dict(min_graphs=0),'--min-graphs')):
        try:D.one_step_rule(P,boot=0,**kw);raise AssertionError(f'accepted {kw}')
        except ValueError as e:assert needle in str(e),(kw,str(e))
    P.meta['rates_identity']='ab'*32
    try:D.one_step_rule(P,boot=0);raise AssertionError('a pilot under a map accepted')
    except ValueError as e:assert 'default rates'in str(e)
    ok('A-FLAG-6_G4c_one_step_rule_branches_W_r_bootstrap_hand_values_refusals',strata=len(rec['strata']))

def rule_hand_W(run:Path,J8:dict)->dict:
    """W_c per (sector, L) and campaign from a merged campaign's own files (graph_replicates.csv, graph_costs.csv and the
    group configs), written independently of design.py; J8 the C8 row per L."""
    out={}
    for g in load(run/'manifest.json')['groups']:
        gd=run/'groups'/g['name'];cfg=load(gd/'config.json');R=cfg['replicates'];n={int(k):int(v)for k,v in cfg['counts'].items()}
        Y={}
        for line in (gd/'graph_replicates.csv').read_text().splitlines()[1:]:
            v=line.split(',');Y.setdefault(int(v[1]),[None]*R)[int(v[0])]=np.array([float(x)for x in v[2:]])
        head,*rows=(gd/'graph_costs.csv').read_text().splitlines();hk=head.split(',');sec={int(r.split(',')[hk.index('graph')]):float(r.split(',')[hk.index('row_seconds')])for r in rows}
        W=0.
        for gid,reps in Y.items():
            y=np.array([x@J8[cfg['L']]for x in reps]);W+=math.sqrt(n[gid]*float(np.var(y,ddof=1)))*math.sqrt(sec[gid]/(R*n[gid]))
        out.setdefault((cfg['sector'],cfg['L']),{})[cfg['campaign']]=W
    return out

def rates_rule_cli(X,td,pil,pr_):
    """A-FLAG-6 (G4c D1a) on the command line: design.py rates --rule one-step on the fake pilot."""
    X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--rule','one-step','--min-graphs',1,'--boot',50,'--out',td/'PROV_rule')
    pm=load(td/'PROV_rule/design_meta.json');rr=load(td/'PROV_rule/rates.json');P=X.D.load_pilot(pil)
    spec,rec=X.D.one_step_rule(P,min_graphs=1,boot=50);rr_=pm['rate_rule']
    assert sorted(x.name for x in (td/'PROV_rule').iterdir())==['design_meta.json','rates.json']and pm['provisional']is True and pm['rates_identity']==digest(td/'PROV_rule/rates.json')
    assert rr_['name']=='one-step'and rr_['spec']==spec and rr_['min_graphs']==1 and rr_['bootstrap']['resamples']==50 and rr_['pilot']['manifest_sha256']==digest(pil/'manifest.json')
    assert rr_['strata']==json.loads(json.dumps(rec['strata']))and rr['provenance']['rule']=='one-step'and rr['provenance']['spec']is None
    hand=rule_hand_W(pil,P.J8);inv=load(X.fixture/'inventory.json')
    for x in rr_['strata']:
        s,L=x['sector'],x['L'];Wa,Wb=hand[(s,L)]['a'],hand[(s,L)]['b'];r=(Wb/Wa)**2
        assert close(x['W']['a'],Wa,1e-9)and close(x['W']['b'],Wb,1e-9)and close(x['ratio_W2_b_over_a'],r,1e-9),(s,L)
        exp=('.9','1')if r<0.9 else(('.7','.8')if r>1/0.9 else('.8','.9'))
        assert (x['rate_a'],x['rate_b'])==exp,(s,L,r,x['decision'])
        for c,v in zip(('a','b'),exp):assert rr['rates'][c][s][str(L)]=={str(g['id']):v for g in inv[s][str(L)]},(c,s,L)
    for args,needle in ((('--rule','one-step','--spec',td/'spec.json'),'exactly one'),((),'exactly one'),(('--spec',td/'spec.json','--min-graphs',1),'belong'),
                        (('--rule','one-step','--step','0.2'),'(0, 1]')):
        r=X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1',*args,'--out',td/'PROV_rule_bad',expect=2)
        assert needle in r.stderr and not (td/'PROV_rule_bad').exists(),(args,r.stderr[-300:])
    r=X.T('design.py','rates','--pilot',pr_,'--source-bundle',td/'B1','--rule','one-step','--out',td/'PROV_rule_bad',expect=2)
    assert 'default rates'in r.stderr and not (td/'PROV_rule_bad').exists(),r.stderr[-300:]
    ok('A-FLAG-6_G4c_rates_rule_one_step_cli_map_record_recomputed_refusals',decisions=sorted({x['decision']for x in rr_['strata']}))

# ================================================================ part 2: fake campaigns on inputs_mini
def run_all(X,run,job=None,env=None):
    m=load(run/'manifest.json');e={**(env or{})}
    if job:e['SLURM_JOB_ID']=str(job)
    for j in m['jobs']:X.T('production.py','run',run,'--index',j['id'],'--threads',1,'--scratch',X.td/'scratch',env=e)

def lanes_run(X,run,job):
    X.T('lanes.py','queue',run);X.T('ledger.py','register',run,'--role','lane','--job',job)
    cp=X.T('lanes.py','worker',run,env={'SLURM_JOB_ID':str(job),'C8_LANE_SECONDS':'36000','C8_LANES':'2'});assert ', 0 failed'in cp.stdout,cp.stdout[-500:]
    X.T('production.py','status',run)

def eta_hand(X,run,jobs:dict)->float:
    """busy thread-seconds (sum over checkpoints of threads x integration_seconds) / allocated physical core-seconds"""
    busy=sum(float(load(f)['native']['integration_seconds'])*int(load(f)['native']['threads'])for f in run.rglob('checkpoints/*.json'))
    return min(1.0,busy/sum(e*c for e,c in jobs.values()))

def d3_view(X,src:Path,dst:Path,inp:Path)->Path:
    """A c8-d3 campaign view of a merged fake c8-d2 pilot, as C63d's package (or its design_adapter.py) presents one to
    the vendored design.py (H6): schemas c8-d3-production-1 / -group-1 / -merged-1, dimension 3, every pin re-made
    (group configs in the manifest, config and manifest hashes and the payload checksum in merged.json), its own
    inputs folder (inventory, the vendored d = 3 two-loop file, an L8 selection) with a manifest listing their sha256,
    and its own c8-d3-ledger-1 ledger (checkpoint review O11 residual): the copied c8-d2 ledger is replaced by the same
    allocations registered with `ledger.py register --schema-prefix c8-d3` (the same job ids, roles and restart counts,
    so the same sacct records and the same eta_node)."""
    from common import object_hash
    shutil.copytree(src,dst);inp.mkdir()
    shutil.copy2(X.fixture/'inventory.json',inp/'inventory.json');shutil.copy2(X.pkg/'vendor/c8_assembly/inputs_d3/two_loop.json',inp/'two_loop.json')
    inv=load(inp/'inventory.json');(inp/'selection.json').write_text(json.dumps({'L8':{s:[r['id']for r in inv[s]['8']]for s in ('free','power')}}))
    (inp/'manifest.json').write_text(json.dumps({'schema':'c8-d3-hpc-inputs-1','sha256':{n:digest(inp/n)for n in ('inventory.json','two_loop.json','selection.json')}}))
    m=load(dst/'manifest.json');m.update(schema='c8-d3-production-1',dimension=3,inputs_manifest_sha256=digest(inp/'manifest.json'));cfgs={}
    for g in m['groups']:
        f=dst/'groups'/g['name']/'config.json';cfg=load(f);cfg['schema']='c8-d3-group-1';f.write_text(json.dumps(cfg,indent=2)+'\n');g['sha256']=digest(f);cfgs[g['name']]=cfg
    (dst/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');mh=digest(dst/'manifest.json')
    for g in m['groups']:
        f=dst/'groups'/g['name']/'merged.json';d=load(f);d.update(schema='c8-d3-merged-1',config_hash=object_hash(cfgs[g['name']]),manifest_sha256=mh);d.pop('payload_sha256')
        d['payload_sha256']=object_hash(d);f.write_text(json.dumps(d,indent=2)+'\n')
    led2=[json.loads(l)for l in (dst/'submissions.jsonl').read_text().splitlines()if l.strip()]
    assert led2 and all(r['schema']=='c8-d2-ledger-1'for r in led2),led2
    (dst/'submissions.jsonl').unlink()
    for r in led2:
        if r.get('type')in('note','attempt'):continue
        X.T('ledger.py','register',dst,'--role',r['role'],'--job',r['jobid'],'--restart',r.get('restart_count','0'),'--schema-prefix','c8-d3')
    led3=[json.loads(l)for l in (dst/'submissions.jsonl').read_text().splitlines()if l.strip()]
    assert [r['schema']for r in led3]==['c8-d3-ledger-1']*len(led3)and [(r['jobid'],r['role'])for r in led3]==[(r['jobid'],r['role'])for r in led2
                                                                                                           if r.get('type')not in('note','attempt')],(led2,led3)
    return dst

def d3_workflow(X,pil:Path,td:Path,eta_n:float,common:list):
    """Checkpoint review O11: the documented C8(3) command line of the reused design.py (--dimension 3 --schema-prefix
    c8-d3 --half-d 1.5 --two-loop --inventory --selection) reads a c8-d3 pilot, takes eta_node from its own
    c8-d3-ledger-1 ledger (freeze and report; tools/accounting.py --schema-prefix c8-d3), and writes c8-d3 schemas;
    inconsistent or mismatched parameters, inputs that are not the pilot's own, a ledger or accounting prefix that is
    not the campaign's (a c8-d2 ledger under a c8-d3 campaign, one c8-d2 record in a c8-d3 ledger, a c8-d3 ledger under
    a c8-d2 campaign, registration with the wrong prefix), and a d = 2 plan of the c8-d3 bundle are refused."""
    D=X.D;inp=td/'inputs_d3';p3=d3_view(X,pil,td/'pilot_d3',inp)
    d3=['--dimension',3,'--schema-prefix','c8-d3','--half-d',1.5,'--two-loop',inp/'two_loop.json','--inventory',inp/'inventory.json','--selection',inp/'selection.json']
    X.T('design.py','freeze','--pilot',p3,'--out',td/'B_d3','--target-se',1e30,*common,*d3)
    mb=load(td/'B_d3/design_meta.json');db=load(td/'B_d3/design.json')
    assert mb['schema']==db['schema']=='c8-d3-design-1'and mb['parameters']['dimension']==3 and mb['parameters']['half_d']==1.5 and mb['parameters']['schema_prefix']=='c8-d3'
    assert mb['pilot']['schema_prefix']=='c8-d3'and mb['pilot']['dimension']==3 and close(mb['eta_node'],eta_n,1e-12)and 'accounting.py'in mb['eta_node_source'],mb['eta_node_source']
    assert close(db['eta_node'],eta_n,1e-12),db['eta_node']
    P3=D.load_pilot(p3,inp/'two_loop.json',1.5,inp/'inventory.json',inp/'selection.json',3,'c8-d3');P2=D.load_pilot(pil)
    assert any(not np.allclose(P3.J8[L],P2.J8[L])for L in range(3,9)),'the c8-d3 pilot was assembled with the d = 2 Jacobian'
    X.T('design.py','report','--pilot',p3,'--bundle',td/'B_d3','--test-only','--json',td/'report_d3.json',*d3)
    rj=load(td/'report_d3.json')
    assert rj['schema']=='c8-d3-design-report-1'and close(rj['eta_node'],eta_n,1e-12)and 'accounting.py'in rj['eta_source'],(rj['eta_node'],rj['eta_source'])
    # the accounting itself under the campaign's prefix: a c8-d3-accounting-1 record from the c8-d3 ledger, the same
    # allocations as the c8-d2 pilot's; the default prefix (c8-d2) is refused for this campaign (exit 2)
    a3=json.loads(X.T('accounting.py',p3,'--schema-prefix','c8-d3','--json').stdout);a2=json.loads(X.T('accounting.py',pil,'--json').stdout)
    assert a3['schema']=='c8-d3-accounting-1'and a3['ledger_schema']=='c8-d3-ledger-1'and a3['complete']and a2['schema']=='c8-d2-accounting-1',(a3['schema'],a2['schema'])
    assert a3['ledger_jobs']==a2['ledger_jobs']and close(a3['work_core_hours'],a2['work_core_hours'])and close(a3['eta_node'],a2['eta_node'],1e-12)
    assert close(min(1.,a3['eta_node']),eta_n,1e-12)
    r=X.T('accounting.py',p3,'--json',expect=2);assert r.returncode==2 and 'not a c8-d2-production-1 campaign'in r.stderr,(r.returncode,r.stderr[-300:])
    r=X.T('ledger.py','list',p3,expect=64);assert r.returncode==64 and 'not a c8-d2-production-1 campaign'in r.stderr,r.stderr[-300:]
    led3=(p3/'submissions.jsonl').read_bytes();led2=(pil/'submissions.jsonl').read_bytes();n3=len(led3.splitlines())
    assert [x['schema']for x in json.loads(X.T('ledger.py','list',p3,'--schema-prefix','c8-d3').stdout)]==['c8-d3-ledger-1']*n3
    # the prefix of a campaign must match its ledger: mismatches are refused at freeze and report, never skipped
    try:
        for i,(ledger_bytes,needle) in enumerate(((led2,'line 1 is not a c8-d3-ledger-1 record'),
                                                  (led3+led2,f'line {n3+1} is not a c8-d3-ledger-1 record'))):
            (p3/'submissions.jsonl').write_bytes(ledger_bytes)
            r=X.T('design.py','freeze','--pilot',p3,'--out',td/f'B_d3_led{i}','--target-se',1e30,*common,*d3,expect=2)
            assert needle in r.stderr and not (td/f'B_d3_led{i}').exists(),(i,r.stderr[-400:])
            r=X.T('design.py','report','--pilot',p3,'--test-only','--json',td/f'report_d3_led{i}.json',*d3,expect=2)
            assert needle in r.stderr and not (td/f'report_d3_led{i}.json').exists(),(i,r.stderr[-400:])
            r=X.T('accounting.py',p3,'--schema-prefix','c8-d3',expect=2);assert r.returncode==2 and needle in r.stderr,(i,r.returncode,r.stderr[-300:])
            r=X.T('ledger.py','register',p3,'--role','lane','--job',9999,'--schema-prefix','c8-d3',expect=64)
            assert r.returncode==64 and needle in r.stderr,(i,r.returncode,r.stderr[-300:])
            assert (p3/'submissions.jsonl').read_bytes()==ledger_bytes
    finally:(p3/'submissions.jsonl').write_bytes(led3)
    r=X.T('ledger.py','register',p3,'--role','lane','--job',9999,expect=64);assert 'not a c8-d2-production-1 campaign'in r.stderr,r.stderr[-300:]
    p2x=td/'pilot_d2_with_d3_ledger';shutil.copytree(pil,p2x);(p2x/'submissions.jsonl').write_bytes(led3)
    r=X.T('design.py','freeze','--pilot',p2x,'--out',td/'B_d2_d3led','--target-se',1e30,*common,expect=2)
    assert 'is not a c8-d2-ledger-1 record'in r.stderr and not (td/'B_d2_d3led').exists(),r.stderr[-400:]
    r=X.T('ledger.py','register',p2x,'--role','lane','--job',9999,'--schema-prefix','c8-d3',expect=64);assert 'not a c8-d3-production-1 campaign'in r.stderr
    assert (p3/'submissions.jsonl').read_bytes()==led3 and (p2x/'submissions.jsonl').read_bytes()==led3
    spec=td/'spec_d3.json';spec.write_text(json.dumps({'a':{s:{str(L):'.75'for L in range(3,9)}for s in ('free','power')}}))
    X.T('design.py','rates','--pilot',p3,'--source-bundle',td/'B_d3','--spec',spec,'--out',td/'PROV_d3',*d3[:10])
    assert load(td/'PROV_d3/rates.json')['schema']=='c8-d3-rates-1'and load(td/'PROV_d3/design_meta.json')['schema']=='c8-d3-design-1'
    bad=[((),'not a c8-d2-production-1 campaign'),(tuple(d3[:4])+('--half-d',1)+tuple(d3[6:]),'--half-d'),
         (('--dimension',3,'--schema-prefix','c8-d2','--half-d',1.5)+tuple(d3[6:]),'--schema-prefix'),
         (tuple(d3[:6])+tuple(d3[8:]),'needs --inventory and --two-loop'),
         (tuple(d3[:6])+('--two-loop',X.pkg/'inputs/two_loop.json')+tuple(d3[8:]),"is not the two_loop.json the pilot's inputs manifest"),
         (tuple(d3[:8])+('--inventory',X.fixture/'inventory.json')+tuple(d3[10:]),"not the pilot's inputs manifest")]
    for i,(args,needle) in enumerate(bad):
        r=X.T('design.py','freeze','--pilot',p3,'--out',td/f'B_d3_bad{i}','--target-se',1e30,*common,*args,expect=2)
        assert needle in r.stderr and not (td/f'B_d3_bad{i}').exists(),(i,needle,r.stderr[-400:])
    r=X.T('design.py','freeze','--pilot',pil,'--out',td/'B_d2_as_d3','--target-se',1e30,*common,*d3,expect=2);assert 'not a c8-d3-production-1 campaign'in r.stderr
    r=X.T('production.py','plan',td/'plan_d3_bundle','--design',td/'B_d3','--test-graphs',2,'--cost-model',td/'cm.json','--threads',1,'--checkpoint-tasks',64,'--seed',88040,expect=1)
    assert 'is not a c8-d2-design-1 design bundle'in r.stderr and not (td/'plan_d3_bundle').exists(),r.stderr[-300:]
    ok('O11_C8-3_command_line_freeze_report_rates_on_a_c8-d3_pilot_its_c8-d3_ledger_eta_node_schemas_follow_prefix_refusals',eta_node=eta_n)

def rates_extra_checks(X,td,pil):
    """A-FLAG-6 bullets added in Stage 4c (R7): design.py rates takes per-graph spec entries (the graphs not listed keep
    the campaign's default) and fills every graph of both campaigns; a spec that gives one graph equal rates in campaigns
    a and b is refused before anything is created; a pilot whose pinned tools changed after it was planned (J-SWEEP-1
    under the Stage-3 tools is the real case) is accepted, as load_pilot accepts it, and the change is recorded."""
    inv=load(X.fixture/'inventory.json');g0,g1=[str(r['id'])for r in inv['free']['3'][:2]]
    sp=td/'spec_graph.json';sp.write_text(json.dumps({'a':{'free':{'3':'.75'}},'b':{'free':{'3':{g0:'.95'}},'power':{'8':'1'}}}))
    X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',sp,'--out',td/'PROV_graph')
    rr=load(td/'PROV_graph/rates.json')['rates'];assert load(td/'PROV_graph/design_meta.json').get('accepted_tool_changes')is None
    assert rr['b']['free']['3'][g0]=='.95'and rr['b']['free']['3'][g1]=='.9'and set(rr['a']['free']['3'].values())=={'.75'},rr['b']['free']['3']
    assert set(rr['b']['power']['8'].values())=={'1'}and set(rr['a']['power']['8'].values())=={'.8'}and set(rr['a']['free']['8'].values())=={'.8'}
    for c in ('a','b'):
        for s in ('free','power'):
            for L in range(3,9):assert set(rr[c][s][str(L)])=={str(r['id'])for r in inv[s][str(L)]},(c,s,L)
    se=td/'spec_equal.json';se.write_text(json.dumps({'a':{'free':{'3':{g0:'.9'}}}}))
    r=X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',se,'--out',td/'PROV_equal',expect=2)
    assert 'equal rates'in r.stderr and not (td/'PROV_equal').exists(),r.stderr[-300:]
    lp=X.pkg/'tools/lanes.py';orig=lp.read_bytes()
    try:
        lp.write_bytes(orig+b'\n# a pinned tool changed after the pilot was planned (test_pipeline.py)\n')
        X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',sp,'--out',td/'PROV_toolchange')
        tm=load(td/'PROV_toolchange/design_meta.json');ch=tm.get('accepted_tool_changes')or{}
        assert list(ch)==['lanes.py']and ch['lanes.py']['current']==digest(lp)and ch['lanes.py']['planned']==load(pil/'manifest.json')['tool_sha256']['lanes.py'],tm
    finally:lp.write_bytes(orig)
    assert load(td/'PROV_toolchange/rates.json')['rates']==rr
    ok('A-FLAG-6_rates_per_graph_spec_equal_refused_source_unchanged_tool_change_recorded')

def rates_sweep_freeze(X,td,swr,prov,pr_,pil,sha):
    """A-FLAG-6 (Stage 4c R7): the sweep under the map (sweep.py --rates) feeds a fresh freeze, as the pilot under the map
    does: its manifest records its own labelled allocation, and the bundle equals an independent recomputation from the
    sweep. freeze --rates-bundle refuses a run measured under ANOTHER map (not only the default identity)."""
    ms=load(swr/'manifest.json');al=ms['allocation']
    assert ms['rates_identity']==sha and ms['test_only']and al['source']=='pilot'and al['points']==128 and al['replicates']==2 and sha in (al.get('label')or''),al
    args=('--test-only','--target-rel',1e-3,'--min-points',64,'--min-replicates',8,'--max-replicates',16)
    X.T('design.py','freeze','--pilot',swr,'--rates-bundle',prov,'--out',td/'FRESH_sweep',*args)
    fs=load(td/'FRESH_sweep/design_meta.json')
    assert fs['provisional']is False and fs['rates_identity']==sha and fs['rates_bundle']['meta_sha256']==digest(prov/'design_meta.json')and fs['pilot']['campaign']==str(swr.resolve())
    PS=X.D.load_pilot(swr);eta_s=eta_hand(X,swr,{'9005':(500,8)});assert close(fs['eta_node'],eta_s,1e-12),(fs['eta_node'],eta_s)
    _,_,cS,rS,sS,_=check_bundle_against(PS,td/'FRESH_sweep',lambda c,s,L:PS.groups[(c,s,L)].eta_omp*eta_s)
    dj=load(td/'b_sweep/design.json')
    assert (cS,rS,sS)!=(counts_of(td/'b_sweep'),{k:int(v)for k,v in dj['replicates'].items()},{k:int(v['s'])for k,v in dj['strata'].items()}),'the map sweep froze the default sweep\'s allocation'
    so=td/'spec_other.json';so.write_text(json.dumps({'a':{s:{str(L):'.7'for L in range(3,9)}for s in ('free','power')}}))
    X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',so,'--out',td/'PROV_other')
    for run in (pr_,swr):
        r=X.T('design.py','freeze','--pilot',run,'--rates-bundle',td/'PROV_other','--out',td/'F_other',*args,expect=2)
        assert 'R14'in r.stderr and not (td/'F_other').exists(),r.stderr[-300:]
    ok('A-FLAG-6_sweep_under_the_map_feeds_a_fresh_freeze_recomputed_another_map_refused',fresh_se=fs['predictions']['se_total'])

# ---------------------------------------------------------------- Stage-6 fix round 1 (G3): X15, X10, X14
def w10_calibration_checkpoints(X:Pkg,td:Path,sw:Path):
    """W10 (Stage-6 fix round 4, S6D-R4-01): calibrate.py measures only validated checkpoints. On copies of the bootstrap
    sweep: a timing changed without its checksum, a checkpoint of campaign b copied over campaign a's (same graphs,
    same block) and a checkpoint copied from another run are refused (exit 2, nothing written); a negative or string
    timing with the payload digest recomputed is refused by the timing check; the intact campaign calibrates to
    the hand value (sum of the validated rows' seconds over their proxy units); a NaN timing has no payload digest and
    is refused by the validation. Before the fix all of these were accepted and attributed to the campaign."""
    prod=X.prod;inv=load(X.fixture/'inventory.json')
    m=load(sw/'manifest.json');j=next(x for x in m['jobs']if x['group']=='a_free_L3');ck=f'groups/a_free_L3/checkpoints/{prod.block_name(j["shard"],0)}.json'
    cal=td/'w10_cal.json';X.T('calibrate.py',sw,'--update',cal)
    secs=units=0.
    for jj in m['jobs']:
        if jj['group']!='a_free_L3':continue
        for k in range(jj['blocks']):
            n=load(sw/'groups/a_free_L3/checkpoints'/f'{prod.block_name(jj["shard"],k)}.json')['native']
            cost={r['id']:max(1,int(r['cost']))for r in inv['free']['3']};secs+=math.fsum(float(r['seconds'])for r in n['rows']);units+=sum(cost[r['graph']]*(r['end']-r['begin'])for r in n['rows'])
    assert close(load(cal)['backends']['gmp']['a']['free']['3']['seconds_per_proxy_unit'],secs/units,1e-12)
    n_ref=0
    def refused(name,edit,needle):
        nonlocal n_ref
        c=td/f'w10_{name}';shutil.copytree(sw,c);edit(c);out=td/f'w10_{name}.json'
        r=X.T('calibrate.py',c,'--update',out,expect=2);assert needle in r.stderr and not out.exists(),(name,r.stderr[-600:]);n_ref+=1
    def timing(c,v,repin):
        d=load(c/ck);d['native']['rows'][0]['seconds']=v
        if repin:d['payload_sha256']=prod.object_hash(d['native'])
        (c/ck).write_text(json.dumps(d))
    refused('timing_changed',lambda c:timing(c,1e6,False),'payload corruption')
    ckb=ck.replace('a_free_L3','b_free_L3')
    refused('campaign_b_over_a',lambda c:shutil.copy2(c/ckb,c/ck),'checkpoint identity mismatch')
    other=td/'w10_other_run';X.T('production.py','plan',other,'--pilot','--points',128,'--replicates',2,'--test-graphs','all','--threads',1,'--seed',88009,
                                 '--bootstrap-chunk',128,'--shards',2);run_all(X,other)
    refused('another_run',lambda c:shutil.copy2(other/ck,c/ck),'checkpoint identity mismatch')
    refused('timing_nan',lambda c:timing(c,float('nan'),False),'not a valid checkpoint')  # no payload digest exists for a NaN (canon refuses it)
    refused('timing_negative',lambda c:timing(c,-1.0,True),'invalid timing')
    refused('timing_string',lambda c:timing(c,'0.5',True),'invalid timing')
    ok('W10_calibrate_validates_checkpoints_and_timings',refusals=n_ref,seconds_per_proxy_unit=secs/units)

def w11_rates_calibration(X:Pkg,td:Path,sw:Path,swr:Path,sha:str,prov:Path,appr:tuple):
    """W11 (Stage-6 fix round 4, S6D-R4-02): one measurement identity (numerics, rates identity) per calibration file, and
    tools/calibration.json holds only the exact default-rate rows. sweep.py --rates without --calibration (the package
    file) and with an exact file is refused before anything is planned (before the fix: planned, run and the map's rows
    written into the default calibration); calibrate.py --update refuses the map sweep's rows into tools/calibration.json
    or an exact file, the exact sweep's rows into the map's file, and a file mixing identities; the map's own file
    records its identity and takes its rows again."""
    pkg_cal=X.pkg/'tools/calibration.json';before=pkg_cal.read_bytes();n=0
    sw_args=('--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2,'--rates',prov/'rates.json',*appr)
    for name,extra in (('w11_sweep_default_cal',()),('w11_sweep_exact_cal',('--calibration',td/'calibration_scratch.json'))):
        r=X.T('sweep.py',td/name,'--seed',88006,*sw_args,'--cost-model-out',td/f'{name}.json',*extra,env={'SLURM_JOB_ID':'9007'},expect=1)
        assert 'W11'in r.stderr and 'nothing planned'in r.stderr and not (td/name).exists()and not (td/f'{name}.json').exists(),(name,r.stderr[-500:]);n+=1
    assert 'tools/calibration.json holds the exact path'in X.T('sweep.py',td/'w11_x','--seed',88006,*sw_args,expect=1).stderr
    exact_cal=td/'calibration_scratch.json';map_cal=td/'calibration_scratch2.json';snap={p:p.read_bytes()for p in (pkg_cal,exact_cal,map_cal)}
    assert load(map_cal)['identity']=={'numerics':'exact','rates_identity':sha}and load(exact_cal)['identity']=={'numerics':'exact','rates_identity':'default'}
    for run,dest,needle in ((swr,pkg_cal,'tools/calibration.json holds the exact path'),(swr,exact_cal,"rates identity 'default'"),(sw,map_cal,f"rates identity '{sha}'")):
        r=X.T('calibrate.py',run,'--update',dest,expect=2);assert needle in r.stderr and 'W11'in r.stderr and dest.read_bytes()==snap[dest],(dest.name,r.stderr[-400:]);n+=1
    mixed=td/'w11_mixed.json';doc=load(map_cal);doc.pop('identity');row=doc['backends']['gmp']['a']['free']['3'];row['source']=dict(row['source'],rates_identity='default')
    mixed.write_text(json.dumps(doc));mb=mixed.read_bytes()
    r=X.T('calibrate.py',swr,'--update',mixed,expect=2);assert 'mixes calibration measurements'in r.stderr and mixed.read_bytes()==mb,r.stderr[-400:];n+=1
    X.T('calibrate.py',swr,'--update',map_cal);assert load(map_cal)['identity']['rates_identity']==sha  # the same identity: accepted
    assert pkg_cal.read_bytes()==before
    ok('W11_calibration_one_identity_per_file_package_file_exact_default_only',refusals=n)

def w20_sweep_seed(X:Pkg,td:Path):
    """W20's class (Stage-6 fix round 4) in tools/sweep.py: the sweep's seed registration is one locked check and append
    (tools/seeds.py reserve). A sweep planned locally without a seed log (--plan-only), whose seed a campaign then
    registers, is refused when it is resumed with the log, before any index runs (before the fix: its seed was appended
    beside the other campaign's, and the sweep ran); a new sweep whose seed is logged is refused before anything is
    planned; a resumed sweep whose own entry is logged is 'present'."""
    log=td/'w20_seeds.json';X.T('seeds.py','init','--log',log);S=88070
    args=('--seed',S,'--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--plan-only')
    a=td/'w20_sweep_a';X.T('sweep.py',a,*args,env={'C8_SEEDS':''})  # local, unregistered
    X.T('seeds.py','add','--seed',S,'--label','another campaign (test_pipeline.py W20)','--log',log);before=log.read_bytes()
    r=X.T('sweep.py',a,*args,'--seeds-log',log,expect=1)
    assert 'could not be registered'in r.stderr and 'is a forbidden seed'in r.stderr and 'another campaign'in r.stderr and log.read_bytes()==before,r.stderr[-500:]
    b=td/'w20_sweep_b';r=X.T('sweep.py',b,*args,'--seeds-log',log,expect=1)
    assert 'nothing planned'in r.stderr and 'is a forbidden seed'in r.stderr and not b.exists()and log.read_bytes()==before,r.stderr[-500:]
    c=td/'w20_sweep_c';S2=88071;X.T('sweep.py',c,*args[:1],S2,*args[2:],'--seeds-log',log)
    r=X.T('sweep.py',c,*args[:1],S2,*args[2:],'--seeds-log',log);assert f'seed {S2} present'in r.stdout,r.stdout[-300:]
    assert [(e['seed'],e['source'])for e in load(log)['seeds']]==[(S,'another campaign (test_pipeline.py W20)'),(S2,str(c.resolve()))]
    ok('W20_sweep_seed_registration_one_locked_transaction')

def accounting_live(X:Pkg,td:Path,sw:Path):
    """X15 (S6D-05): accounting is complete only when every job's and array element's current sacct attempt is
    terminal. On a copy of the sweep with one more ledger job per case: a RUNNING, PENDING, COMPLETING, SUSPENDED or
    unknown current attempt, a requeue that is the current attempt, an earlier attempt RUNNING and a PENDING array range
    are incomplete (hours as lower bounds, eta_node null; design.py's eta_node refuses, the CLI exits 4); a requeued
    attempt followed by COMPLETED, 'CANCELLED by <uid>' and a range cancelled before it started are complete."""
    live=td/'sweep_live';shutil.copytree(sw,live);led0=(live/'submissions.jsonl').read_text();env={**os.environ,**X.env}
    def acc(jobs:list,lines:list)->dict:
        (live/'submissions.jsonl').write_text(led0+''.join(json.dumps({'schema':'c8-d2-ledger-1','source':'slurm_submit',**x})+'\n'for x in jobs))
        with X.sacct.open('a')as f:f.write(''.join(l+'\n'for l in lines))
        return X.acc.account(live,env=env)
    line=lambda raw,jid,state,el=100:f'{raw}|{jid}|{el}|8|exp-1-01|{state}|shared'
    live_cases=[('a RUNNING allocation',[{'jobid':'9701','role':'lane'}],[line(9701,9701,'RUNNING')],'job 9701: its current attempt is RUNNING'),
                ('a PENDING allocation',[{'jobid':'9702','role':'lane'}],[line(9702,9702,'PENDING',0)],'job 9702: its current attempt is PENDING'),
                ('a requeue as the current attempt',[{'jobid':'9704','role':'lane'}],[line(9704,9704,'COMPLETED'),line(9704,9704,'REQUEUED')],'is REQUEUED'),
                ('an unknown state',[{'jobid':'9706','role':'lane'}],[line(9706,9706,'WEIRDSTATE')],'is WEIRDSTATE'),
                ('an earlier attempt RUNNING',[{'jobid':'9707','role':'lane'}],[line(9707,9707,'RUNNING'),line(9707,9707,'COMPLETED')],'an earlier attempt is RUNNING'),
                ('a COMPLETING allocation',[{'jobid':'9708','role':'lane'}],[line(9708,9708,'COMPLETING')],'is COMPLETING'),
                ('a SUSPENDED allocation',[{'jobid':'9709','role':'lane'}],[line(9709,9709,'SUSPENDED')],'is SUSPENDED'),
                ('a PENDING array range',[{'jobid':'9710','role':'array','array':'0-2'}],
                 [line(9710,'9710_0','COMPLETED'),line(9710,'9710_1','COMPLETED'),'9710|9710_[2]|0|0|None assigned|PENDING|shared'],'array job 9710 element 2: its current attempt is PENDING')]
    for name,jobs,lines,needle in live_cases:
        r=acc(jobs,lines)
        assert r['complete']is False and r['eta_node']is None and r['hours_are'].startswith('lower bounds')and any(needle in x for x in r['incomplete']),(name,r['incomplete'])
    with mock.patch.dict(os.environ,X.env):
        try:X.D.eta_node(live,True,None);raise AssertionError('design.py accepted live accounting')
        except ValueError as e:assert 'eta_node unavailable'in str(e)and 'not terminal'in str(e),str(e)
    cp=X.T('accounting.py',live,expect=4);assert 'not terminal'in cp.stderr,cp.stderr[-400:]
    for name,jobs,lines in (('a requeued attempt then COMPLETED',[{'jobid':'9703','role':'lane'}],[line(9703,9703,'REQUEUED',50),line(9703,9703,'COMPLETED')]),
                            ('CANCELLED by a user',[{'jobid':'9705','role':'lane'}],[line(9705,9705,'CANCELLED by 1234')]),
                            ('an array range cancelled before it started',[{'jobid':'9711','role':'array','array':'0-2'}],
                             [line(9711,'9711_0','COMPLETED'),line(9711,'9711_1','TIMEOUT'),'9711|9711_[2]|0|0|None assigned|CANCELLED by 1|shared'])):
        r=acc(jobs,lines);assert r['complete']is True and r['hours_are']=='exact'and r['eta_node']is not None,(name,r['incomplete'])
    r=acc([{'jobid':'9703','role':'lane'}],[]);assert math.isclose(r['work_core_hours']*3600,(600+50+100)*8),r['work_core_hours']  # the requeued attempt stays in the sum
    ok('X15_live_allocations_incomplete_terminal_complete_requeue_in_sum',live_cases=len(live_cases),complete_cases=3)

def class_factor_numerics(X:Pkg,td:Path,sw:Path):
    """X10 (make_cost_model.py side, S6-C-03 / S6D-04 / S6-F-02): class_factors derives a CPU-class factor only between
    the same numerics. The exact sweep against its own (exact) cost model gives factors 1; the same model labelled
    dd+mp256, or without a numerics identity, is refused (in-process and by the class-factors command, exit 3)."""
    sys.modules.pop('make_cost_model',None);import make_cost_model as MCM
    model=load(td/'cm.json');assert model['numerics']=='exact'
    with mock.patch.object(MCM,'provenance',lambda run,m:{'cpu_models':['Fake CPU B'],'hosts':['fake'],'job_ids':['9001']}):
        out=MCM.class_factors(model,sw);f=out['cpu_class_factors']['Fake CPU B']
        assert f and all(abs(v-1)<1e-12 for c in f.values()for s in c.values()for v in s.values()),f
        for name,edit in (('dd+mp256',lambda m:m.update(numerics='dd+mp256')),('no numerics',lambda m:m.pop('numerics'))):
            m2=json.loads(json.dumps(model));edit(m2)
            try:MCM.class_factors(m2,sw);raise AssertionError(f'class factors accepted a model of {name}')
            except ValueError as e:assert 'class factors need the same numerics'in str(e),str(e)
    bad=td/'cm_dd_cf.json';bad.write_text(json.dumps(dict(model,numerics='dd+mp256')))
    cp=X.T('make_cost_model.py','class-factors',bad,sw,td/'cf_out.json',expect=3);assert 'same numerics'in cp.stderr and not (td/'cf_out.json').exists(),cp.stderr[-300:]
    ok('X10_class_factors_same_numerics_only',factors=sum(len(s)for c in f.values()for s in c.values()))

def own_overrides(X:Pkg,td:Path,pil:Path,P):
    """X14 (S6D-02): a c8-d2 pilot's --two-loop, --inventory and --selection are authenticated against its inputs
    manifest. The pinned files themselves are accepted (the same pilot: J8 and inventory equal); the d = 3 two-loop
    file (the finding's example), a two-loop file with one B2 entry changed, an inventory without one graph and any
    selection.json (not in a c8-d2 manifest) are refused, in-process and by design.py report and freeze (exit 2,
    nothing created)."""
    D=X.D;fx=X.fixture;tl=X.pkg/'inputs/two_loop.json'
    Pp=D.load_pilot(pil,two_loop=tl,inventory=fx/'inventory.json')
    assert all(np.array_equal(Pp.J8[L],P.J8[L])for L in P.J8)and Pp.inventory==P.inventory and Pp.meta['two_loop_sha256']==P.meta['two_loop_sha256']
    d3=X.pkg/'vendor/c8_assembly/inputs_d3/two_loop.json'
    t2=td/'two_loop_x14.json';doc=load(tl);doc['B2'][3]=doc['B2'][3][:-1]+('1'if doc['B2'][3][-1]!='1'else'2');t2.write_text(json.dumps(doc,indent=2))
    inv=load(fx/'inventory.json');inv['free']['3']=inv['free']['3'][1:];i2=td/'inventory_x14.json';i2.write_text(json.dumps(inv))
    sel=td/'selection_x14.json';sel.write_text(json.dumps({'L8':{s:[r['id']for r in load(fx/'inventory.json')[s]['8']]for s in ('free','power')}}))
    cases=[(dict(two_loop=d3),'is not the two_loop.json'),(dict(two_loop=t2),'is not the two_loop.json'),(dict(inventory=i2),'is not the inventory.json'),
           (dict(selection=sel),'lists no selection.json')]
    for kw,needle in cases:
        try:D.load_pilot(pil,**kw);raise AssertionError(f'load_pilot accepted {kw}')
        except ValueError as e:assert needle in str(e)and 'X14'in str(e),(kw,str(e))
    r=X.T('design.py','report','--pilot',pil,'--two-loop',d3,'--test-only','--eta-node',1,expect=2);assert 'is not the two_loop.json'in r.stderr,r.stderr[-400:]
    r=X.T('design.py','freeze','--pilot',pil,'--out',td/'b_x14','--test-only','--target-rel',1e-3,'--inventory',i2,'--min-points',64,'--min-replicates',8,'--max-replicates',16,expect=2)
    assert 'is not the inventory.json'in r.stderr and not (td/'b_x14').exists(),r.stderr[-400:]
    ok('X14_own_prefix_overrides_authenticated_pinned_accepted_others_refused',refusals=len(cases)+2)

def part2(X:Pkg):
    D,prod=X.D,X.prod;td=X.td/'p2';td.mkdir();(X.td/'scratch').mkdir(exist_ok=True)
    X.seedmod.add(X.seeds,1,'initial entry')  # the log exists; non-test plans pass it
    # ---- the bootstrap sweep (R13) inside a fake Slurm job: ledger, run, merge, cost model (A-ORC-9)
    sw=td/'sweep';X.sacct_add(9001,600,8)
    cp=X.T('sweep.py',sw,'--seed',88001,'--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2,
           '--cost-model-out',td/'cm.json','--calibration',td/'calibration_scratch.json',env={'SLURM_JOB_ID':'9001'})
    msw=load(sw/'manifest.json');assert msw['cost_basis']=='bootstrap'and msw['test_only']
    led=[json.loads(l)for l in (sw/'submissions.jsonl').read_text().splitlines()]
    assert [(x['jobid'],x['role'])for x in led]==[('9001','sweep')],led
    cm=load(td/'cm.json');assert cm['rates_identity']=='default'and len(cm['seconds_per_point'])==2*sum(len(v)for s in load(X.fixture/'inventory.json').values()for v in s.values())
    # O09: finalization resumes. A sweep stopped after the cost model was published and before the calibration was
    # updated (here: the calibration file removed) completes on a rerun, keeping the model (same bytes); a completed
    # sweep reruns successfully; an existing model that is not this campaign's is refused by name, unchanged.
    sweep_args=(sw,'--seed',88001,'--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2)
    cm_bytes=(td/'cm.json').read_bytes();(td/'calibration_scratch.json').unlink()
    r=X.T('sweep.py',*sweep_args,'--cost-model-out',td/'cm.json','--calibration',td/'calibration_scratch.json',env={'SLURM_JOB_ID':'9001'})
    cal=load(td/'calibration_scratch.json');row=cal['backends']['gmp']['a']['free']['3']
    assert (td/'cm.json').read_bytes()==cm_bytes and row['source']['manifest_sha256']==digest(sw/'manifest.json'),r.stdout[-400:]
    X.T('sweep.py',*sweep_args,'--cost-model-out',td/'cm.json','--calibration',td/'calibration_scratch.json',env={'SLURM_JOB_ID':'9001'})
    assert (td/'cm.json').read_bytes()==cm_bytes
    bad=json.loads(cm_bytes);k0=sorted(bad['seconds_per_point'])[0];bad['seconds_per_point'][k0]*=2;(td/'cm_other.json').write_text(json.dumps(bad))
    other=(td/'cm_other.json').read_bytes()
    r=X.T('sweep.py',*sweep_args,'--cost-model-out',td/'cm_other.json','--calibration',td/'calibration_scratch.json',env={'SLURM_JOB_ID':'9001'},expect=1)
    assert "is not this campaign's cost model"in r.stderr and 'seconds_per_point'in r.stderr and (td/'cm_other.json').read_bytes()==other,r.stderr[-500:]
    assert [(x['jobid'],x.get('type'))for x in map(json.loads,(sw/'submissions.jsonl').read_text().splitlines())]==[('9001',None)]  # reruns add no ledger job
    ok('O09_sweep_finalization_resumes_reuses_its_model_refuses_another')
    hand=eta_hand(X,sw,{'9001':(600,8)})
    out=X.T('design.py','freeze','--pilot',sw,'--out',td/'b_sweep','--test-only','--target-rel',1e-3,'--min-points',64,'--min-replicates',8,'--max-replicates',16)
    ms=load(td/'b_sweep/design_meta.json');assert close(ms['eta_node'],hand,1e-12)and 'accounting.py'in ms['eta_node_source'],(ms['eta_node'],hand)
    acc=X.T('accounting.py',sw,'--json');a1=json.loads(acc.stdout);assert close(a1['work_core_hours'],600*8/3600)and a1['ledger_jobs']==1
    noreg=td/'sweep_noreg';shutil.copytree(sw,noreg);(noreg/'submissions.jsonl').unlink()
    r=X.T('design.py','freeze','--pilot',noreg,'--out',td/'b_noreg','--test-only','--target-rel',1e-3,'--min-points',64,'--min-replicates',8,'--max-replicates',16,expect=2)
    assert 'allocation unknown'in r.stderr and not (td/'b_noreg').exists(),r.stderr[-300:]
    ok('A-ORC-9_bootstrap_sweep_ledger_accounting_eta_node_design_allocation_unknown',eta_node=hand,sweep_indices=len(msw['jobs']))
    accounting_live(X,td,sw);class_factor_numerics(X,td,sw)  # Stage-6 fix round 1: X15, X10
    w10_calibration_checkpoints(X,td,sw);w20_sweep_seed(X,td)  # Stage-6 fix round 4
    # ---- the pilot: plan --pilot with the measured cost model, lanes, merge --jobs; local checkpoints only test-only
    pil=td/'pilot';PSEED=88002
    X.T('production.py','plan',pil,'--pilot','--points',64,'--replicates',8,'--test-graphs',2,'--cost-model',td/'cm.json','--threads',1,'--checkpoint-tasks',64,'--seed',PSEED)
    lanes_run(X,pil,9002);X.sacct_add(9002,300,16);X.T('production.py','merge',pil,'--jobs',2)
    loc=td/'pilot_local';X.T('production.py','plan',loc,'--pilot','--points',64,'--replicates',8,'--test-graphs',2,'--cost-model',td/'cm.json','--threads',1,'--checkpoint-tasks',64,'--seed',88003)
    run_all(X,loc);X.T('production.py','merge',loc,'--jobs',2)
    try:D.eta_node(loc,False,None);raise AssertionError('a non-test freeze accepted local checkpoints')
    except ValueError as e:assert 'no Slurm id'in str(e)
    assert D.eta_node(loc,True,None)[0]==1.0
    X.T('design.py','freeze','--pilot',loc,'--out',td/'b_local','--test-only','--target-rel',1e-3,'--min-points',64,'--min-replicates',8,'--max-replicates',16)
    assert load(td/'b_local/design_meta.json')['eta_node']==1.0
    ok('A-ORC-9_local_checkpoints_accepted_only_by_test_only_freeze')
    # ---- the bundles: B0 the minimum design, B1 just below its SE (target T), two batches each
    P=D.load_pilot(pil);eta_n=eta_hand(X,pil,{'9002':(300,16)})
    own_overrides(X,td,pil,P)  # Stage-6 fix round 1: X14
    r=X.T('design.py','freeze','--pilot',pil,'--out',td/'b_y10','--test-only','--target-rel',1e-3,'--min-points',64,'--min-replicates',1,'--max-replicates',1,expect=2)
    assert 'Y10'in r.stderr and '--min-replicates 1'in r.stderr and not (td/'b_y10').exists(),r.stderr[-400:]  # never fewer than two, even test-only
    common=['--test-only','--min-points',64,'--min-replicates',8,'--max-replicates',16,'--batches',2]
    X.T('design.py','freeze','--pilot',pil,'--out',td/'B0','--target-se',1e30,*common)
    se0=load(td/'B0/design_meta.json')['predictions']['se_total'];T=0.98*se0
    X.T('design.py','freeze','--pilot',pil,'--out',td/'B1','--target-se',T,*common)
    m1=load(td/'B1/design_meta.json');assert m1['predictions']['se_total']<=T and close(m1['eta_node'],eta_n,1e-12)
    eff=lambda Pp,en:(lambda c,s,L:Pp.groups[(c,s,L)].eta_omp*en)
    for g in P.groups.values():
        md=load(pil/'groups'/f'{g.campaign}_{g.sector}_L{g.L}'/'merged.json');assert close(g.eta_omp,min(1.,md['row_seconds_sum']/md['thread_seconds_sum']),1e-12)
    pr1,st1,c1,r1,s1,K1=check_bundle_against(P,td/'B1',eff(P,eta_n))
    rep=X.T('design.py','report','--pilot',pil,'--bundle',td/'B1','--test-only','--json',td/'report_B1.json','--tails-out',td/'tails_B1.csv')
    rj=load(td/'report_B1.json');assert close(rj['bundle']['se_total'],pr1['se_total'])and 'target rel'in rep.stdout and 'tails:'in rep.stdout
    assert (td/'tails_B1.csv').read_text().startswith('campaign,sector,L,graph,points,replicates,xi_hat,largest_share,use,status\n')
    ok('A-DES-2_on_the_fake_pilot_bundle_recomputed_independently',se_total=pr1['se_total'],target=T)
    z10_cli(X,td,pil,common,T);z9_cli(X,td,pil)  # Stage-6 fix round 3
    d3_workflow(X,pil,td,eta_n,common)
    batches={}
    for name,bundle,seed,tg in (('b1',td/'B1',88011,2),('b2',td/'B1',88012,2),('c1',td/'B0',88013,2),('g1',td/'B1',88014,1)):
        d=td/f'batch_{name}';X.T('production.py','plan',d,'--design',bundle,'--test-graphs',tg,'--cost-model',td/'cm.json','--threads',1,'--checkpoint-tasks',64,'--seed',seed)
        run_all(X,d,job=None);X.T('production.py','merge',d,'--jobs',2);X.T('assemble.py',d,'--bootstrap',0);batches[name]=d
        m=load(d/'manifest.json');assert m['design']['meta_sha256']==digest(bundle/'design_meta.json')and m['test_only']
        cfg=load(d/'groups/a_free_L8/config.json');dj=load(bundle/'design.json');cc=counts_of(bundle)
        for g,n in cfg['counts'].items():
            row=next(x for x in load(X.fixture/'inventory.json')['free']['8']if x['id']==int(g));st='free_L8_primitive'if row.get('primitive')else'free_L8'
            assert int(n)==cc[('a','free',8)][int(g)]*int(dj['strata'][st]['s'])
        assert cfg['replicates']==dj['replicates']['free_L8']
    # combine: final, partial, the chi-square by hand
    fin=X.T('combine.py',batches['b1'],batches['b2'],'--output',td/'final','--test-only','--bootstrap',64);res=load(td/'final/C8_test_final.json')
    tp=res['test_partial'];assert tp['batches']['count']==2 and tp['final']is True and res.get('C8_full')is None
    per=[load(batches[b]/'C8_test_result.json')['test_partial']for b in ('b1','b2')]
    chi=sum((x['C8_full']-tp['C8_full'])**2/x['sampling_standard_error']**2 for x in per)
    assert close(chi,tp['batches']['chi2_about_combined'],1e-10),(chi,tp['batches']['chi2_about_combined'])
    assert not X.vr.verify(json.loads(json.dumps(res)))
    t=json.loads(json.dumps(res));t['test_partial']['C8_full']+=1e-3;assert X.vr.verify(t)
    t=json.loads(json.dumps(res));t['test_partial'].pop('gates',None)if 'gates'in t['test_partial']else t.pop('gates',None);assert X.vr.verify(t)
    t=json.loads(json.dumps(res));t['extra_key']=1;assert X.vr.verify(t)
    X.T('combine.py',batches['b1'],'--output',td/'partial','--test-only','--partial','--bootstrap',0);pp=load(td/'partial/C8_test_partial.json')['test_partial']
    assert pp['final']is False and pp['batches']['count']==1 and 'PARTIAL'in pp['status']
    # rejected combinations
    def refused(*dirs,needle,extra=()):
        r=X.T('combine.py',*dirs,'--output',td/'rej','--test-only','--bootstrap',0,*extra,expect=2);assert needle in r.stderr,(needle,r.stderr[-400:]);assert not (td/'rej/C8_test_final.json').exists()
    refused(batches['b1'],needle='the frozen design has 2 batches')
    refused(batches['b1'],batches['c1'],needle='differ in design_sha256')
    rep_seed=td/'batch_b1_copy';shutil.copytree(batches['b1'],rep_seed);refused(batches['b1'],rep_seed,needle='group seed repeats')
    miss=td/'batch_b2_missing_group';shutil.copytree(batches['b2'],miss);shutil.rmtree(miss/'groups/a_free_L8');refused(batches['b1'],miss,needle='a_free_L8')
    refused(batches['b1'],batches['g1'],needle='different graph sets')
    # a different numerics profile: plan --design pins the bundle's numerics, so two batches of one bundle cannot differ;
    # the refusal itself is reached on the loaded batch records with one profile changed
    lb=[X.comb.load_batch(batches['b1'],True),X.comb.load_batch(batches['b2'],True)];lb[1]['numerics']='dd'
    try:X.comb.combine_batches(lb,2,test_only=True,bootstrap=0);raise AssertionError('accepted')
    except ValueError as e:assert 'differ in numerics'in str(e)
    ok('A-ASM-6_combine_final_partial_chi2_hand_verify_result_and_rejections',chi2=chi,C8_test=tp['C8_full'])
    route_b_cli_test_only(X,td,pil,P,eff(P,eta_n),common,T,batches['b1'],cm)
    # ---- R14/R19: the provisional rates bundle and the measurement under its map
    spec=td/'spec.json';spec.write_text(json.dumps({'a':{s:{str(L):'.75'for L in range(3,9)}for s in ('free','power')}}))
    src_bytes=lambda:{str(f.relative_to(td/'B1')):f.read_bytes()for f in sorted((td/'B1').rglob('*'))if f.is_file()};b1_before=src_bytes()
    X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',spec,'--out',td/'PROV')
    assert src_bytes()==b1_before,'design.py rates changed the source bundle'  # A-FLAG-6: the source bundle stays byte-unchanged
    prov=td/'PROV';pm=load(prov/'design_meta.json');sha=digest(prov/'rates.json')
    assert sorted(x.name for x in prov.iterdir())==['design_meta.json','rates.json']and pm['provisional']is True and pm['rates_identity']==sha
    assert pm['source_design_meta_sha256']==digest(td/'B1/design_meta.json')
    r=X.T('design.py','report','--pilot',pil,'--bundle',prov,'--test-only');assert 'unavailable (provisional)'in r.stdout
    r=X.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--spec',spec,'--out',td/'PROV',expect=2);assert 'never overwritten'in r.stderr
    rates_extra_checks(X,td,pil)
    for extra in (('--test-graphs',2,'--cost-model',td/'cm.json'),('--forbid-seeds-from',X.seeds,'--cost-model',td/'cm.json')):
        d=td/'plan_prov';r=X.T('production.py','plan',d,'--design',prov,'--threads',1,'--seed',88020,*extra,expect=1)
        assert 'provisional'in r.stderr and 'freeze --rates-bundle'in r.stderr and 'plan --pilot --rates'in r.stderr and not d.exists(),r.stderr[-400:]
    appr=('--approved-numerics-change','test approval (test_pipeline.py)')
    swr=td/'sweep_map';X.sacct_add(9005,500,8)
    X.T('sweep.py',swr,'--seed',88005,'--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2,
        '--rates',prov/'rates.json',*appr,'--cost-model-out',td/'cm_map.json','--calibration',td/'calibration_scratch2.json',env={'SLURM_JOB_ID':'9005'})
    cmm=load(td/'cm_map.json');assert cmm['rates_identity']==sha
    assert prod.load_cost_model(td/'cm_map.json','gmp',sha,test_only=False)['rates_identity']==sha
    try:prod.load_cost_model(td/'cm_map.json','gmp','default',test_only=False);raise AssertionError('accepted')
    except ValueError as e:assert 'rates identity'in str(e)
    ratio={k:cmm['seconds_per_point'][k]/cm['seconds_per_point'][k]for k in cm['seconds_per_point']};assert all(close(v,1.5,1e-9)for v in ratio.values())
    w11_rates_calibration(X,td,sw,swr,sha,prov,appr)  # Stage-6 fix round 4
    # the pilot under the map: same seed and arguments as the source pilot (so its jets differ only by the injected change)
    pr_=td/'pilot_map';X.T('production.py','plan',pr_,'--pilot','--points',64,'--replicates',8,'--test-graphs',2,'--cost-model',td/'cm_map.json','--threads',1,
                            '--checkpoint-tasks',64,'--seed',PSEED,'--rates',prov/'rates.json',*appr)
    mr=load(pr_/'manifest.json');assert mr['rates_identity']==sha and mr['allocation']['source']=='pilot'and mr['allocation']['points']==64 and mr['allocation']['replicates']==8 and sha in mr['allocation']['label']
    lanes_run(X,pr_,9006);X.sacct_add(9006,450,16);X.T('production.py','merge',pr_,'--jobs',2)
    # freeze --rates-bundle: refused for the source pilot (default identity) and without the bundle; a fresh bundle
    r=X.T('design.py','freeze','--pilot',pil,'--rates-bundle',prov,'--out',td/'F_bad','--target-se',T,*common,expect=2);assert 'R14'in r.stderr and not (td/'F_bad').exists()
    r=X.T('design.py','freeze','--pilot',pr_,'--out',td/'F_bad2','--target-se',T,*common,expect=2);assert '--rates-bundle'in r.stderr and not (td/'F_bad2').exists()
    z9_class_cli(X,td,pil,pr_,prov,T,common)  # Stage-6 fix round 3
    X.T('design.py','freeze','--pilot',pr_,'--rates-bundle',prov,'--out',td/'FRESH','--target-se',T,*common)
    fm=load(td/'FRESH/design_meta.json');assert fm['provisional']is False and fm['rates_identity']==sha and fm['rates_bundle']['meta_sha256']==digest(prov/'design_meta.json')
    PR=D.load_pilot(pr_);eta_r=eta_hand(X,pr_,{'9006':(450,16)});assert close(fm['eta_node'],eta_r,1e-12)
    prF,stF,cF,rF,sF,KF=check_bundle_against(PR,td/'FRESH',eff(PR,eta_r))
    assert prF['se_total']<=T and fm['batches']==KF==2
    rates_sweep_freeze(X,td,swr,prov,pr_,pil,sha)
    rates_rule_cli(X,td,pil,pr_)
    # the source allocation under the map: the SE misses T, the cost is 1.5x what the source bundle predicted
    reuse=predict(stF,c1,r1,s1,K1,1.5,eff(P,eta_n));src=pr1
    se_ratio=reuse['se_total']/src['se_total'];cost_ratio=reuse['cost_total_core_hours']/src['cost_total_core_hours']
    assert reuse['se_total']>T and 1.3<se_ratio<1.5 and close(cost_ratio,1.5,1e-9),(reuse,src,se_ratio,cost_ratio)
    assert (cF,rF,sF)!=(c1,r1,s1),'the fresh allocation equals the source allocation'
    # a budget freeze under the map: verdict and cost recomputed
    budget=math.ceil(prF['cost_total_core_hours']*1.2*1e6)/1e6
    X.T('design.py','freeze','--pilot',pr_,'--rates-bundle',prov,'--out',td/'FRESH_budget','--budget-core-hours',budget,*common)
    fb=load(td/'FRESH_budget/design_meta.json');prB=check_bundle_against(PR,td/'FRESH_budget',eff(PR,eta_r))[0];assert prB['cost_total_core_hours']<=budget and fb['budget_core_hours']==budget
    # a plan under the map accepts the fresh bundle; without the map it refuses
    d=td/'batch_map';X.T('production.py','plan',d,'--design',td/'FRESH','--test-graphs',2,'--cost-model',td/'cm_map.json','--threads',1,'--checkpoint-tasks',64,'--seed',88030,'--rates',prov/'rates.json',*appr)
    assert load(d/'manifest.json')['rates_identity']==sha
    r=X.T('production.py','plan',td/'batch_nomap','--design',td/'FRESH','--test-graphs',2,'--cost-model',td/'cm.json','--threads',1,'--checkpoint-tasks',64,'--seed',88031,expect=1)
    assert 'pins rates identity'in r.stderr and not (td/'batch_nomap').exists()
    # combine refuses a different rates identity: batches of the fresh bundle against batches of B1 (the bundle check
    # comes first), and, with the bundle identities made equal, the rates identity itself
    run_all(X,d);X.T('production.py','merge',d,'--jobs',2);X.T('assemble.py',d,'--bootstrap',0)
    refused(batches['b1'],d,needle='differ in design_sha256')
    lb=[X.comb.load_batch(batches['b1'],True),X.comb.load_batch(d,True)];lb[1]['design_sha256']=lb[0]['design_sha256']
    try:X.comb.combine_batches(lb,2,test_only=True,bootstrap=0);raise AssertionError('accepted')
    except ValueError as e:assert 'rates_identity'in str(e)
    ok('R14_R19_provisional_bundle_map_measurement_fresh_freeze_recomputed_source_allocation_misses',rates_identity=sha[:12],se_ratio=se_ratio,cost_ratio=cost_ratio,
       fresh_se=prF['se_total'],target=T)

def route_b_cli_test_only(X:Pkg,td:Path,pil:Path,P,eta,common:list,T:float,exact_batch:Path,cm:dict):
    """Route (b) on the command line, test-only, through combine: sweep.py --numerics measures a cost model under the
    profile (its numerics identity dd+mp256; the fake profile build costs 0.4x per point, C8_FAKE_SECONDS) and refuses
    no approval and the package calibration; design.py freeze --numerics re-costs the exact pilot's bundle with the
    profile model's cost for every graph (counts, r, s, SE and cost recomputed independently, the target met, the
    cost below the exact bundle's); plan --design runs, merges
    and assembles under the profile; combine refuses mixing that batch with an exact batch (different bundles, and
    with the bundle identities made equal, different numerics)."""
    appr=('--approved-numerics-change',APPR_B);exe=fake_profile_exe(X.pkg)
    sw=('--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2)
    r=X.T('sweep.py',td/'sweep_dd_noappr','--seed',88041,*sw,'--numerics','dd+mp256','--cost-model-out',td/'cm_x.json','--calibration',td/'cal_x.json',expect=1)
    assert '--approved-numerics-change'in r.stderr and not (td/'sweep_dd_noappr').exists(),r.stderr[-300:]
    r=X.T('sweep.py',td/'sweep_dd_cal','--seed',88042,*sw,'--numerics','dd+mp256',*appr,'--cost-model-out',td/'cm_y.json',expect=1)
    assert 'tools/calibration.json'in r.stderr and not (td/'sweep_dd_cal').exists(),r.stderr[-300:]
    X.sacct_add(9040,600,8)
    X.T('sweep.py',td/'sweep_dd','--seed',88040,*sw,'--numerics','dd+mp256',*appr,'--cost-model-out',td/'cm_dd.json','--calibration',td/'cal_dd.json',
        env={'SLURM_JOB_ID':'9040','C8_FAKE_SECONDS':'0.4'})
    cmd=load(td/'cm_dd.json');assert cmd['numerics']=='dd+mp256'and load(td/'sweep_dd/manifest.json')['numerics']=='dd+mp256'and cmd['executable_sha256']==digest(exe)
    assert set(cmd['seconds_per_point'])==set(cm['seconds_per_point'])and all(close(cmd['seconds_per_point'][k]/v,0.4,1e-9)for k,v in cm['seconds_per_point'].items())
    inv=load(X.fixture/'inventory.json');IM=load(pil/'manifest.json')['inputs_manifest_sha256']  # W18: the pilot's inputs
    gate=gate_record(td/'clflag.990002.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(X.pkg/'bin/c8d2_gmp'),inv,inputs=IM)
    pkg_gate=gate_record(td/'clflag.990004.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(X.pkg/'bin/c8d2_gmp'),inv,inputs=digest(X.pkg/'inputs/manifest.json'))
    r=X.T('design.py','freeze','--pilot',pil,'--out',td/'BRB_other_inputs','--target-se',T,*common,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json',
          '--numerics-gate',pkg_gate,expect=2)  # W18: a gate of the package's inputs is not one of this pilot's (the fixture's)
    assert f'the gate ran on inputs manifest {digest(X.pkg/"inputs/manifest.json")[:12]}..., not {IM[:12]}...'in r.stderr and not (td/'BRB_other_inputs').exists(),r.stderr[-500:]
    X.T('design.py','freeze','--pilot',pil,'--out',td/'BRB','--target-se',T,*common,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json','--numerics-gate',gate)
    mb=load(td/'BRB/design_meta.json');m1=load(td/'B1/design_meta.json')
    assert mb['numerics']=='dd+mp256'and mb['profile_recost']['gates'][0]['slurm_job']=='990002'and mb['profile_recost']['exact_pilot']['manifest_sha256']==digest(pil/'manifest.json')
    # the independent recomputation with the profile model's costs for EVERY graph (this pilot ran 2 graphs per group, so
    # the exact bundle B1 imputes the others' costs; route (b) uses the measured ones) and the exact pilot's sigma
    # F13: the exact bundle B1 (the same pilot and arguments) is the kept candidate; check_route_b_choice recomputes both
    cmc=costs_of(td/'cm_dd.json');chosen,kept,reo=check_route_b_choice(P,td/'BRB',td/'B1',eta,cmc)
    if chosen=='reoptimized':check_bundle_against(P,td/'BRB',eta,costs=cmc);check_optimizer(P,td/'BRB',eta,costs=cmc)
    prb=kept if chosen=='kept_exact_allocation'else reo
    assert prb['se_total']<=T*(1+1e-12)and prb['cost_total_core_hours']<m1['predictions']['cost_total_core_hours'],(prb,m1['predictions'])
    d=td/'batch_rb';X.T('production.py','plan',d,'--design',td/'BRB','--test-graphs',2,'--cost-model',td/'cm_dd.json','--threads',1,'--checkpoint-tasks',64,
                        '--seed',88050,'--numerics','dd+mp256',*appr)
    m=load(d/'manifest.json');nr=m['numerics_route']
    assert m['numerics']=='dd+mp256'and m['executable']=='c8d2_gmp_dd+mp256'and nr['route']=='b'and nr['executable_gated']is True and nr['plan_cost_model']['sha256']==digest(td/'cm_dd.json')
    run_all(X,d);X.T('production.py','merge',d,'--jobs',2);X.T('assemble.py',d,'--bootstrap',0)
    r=X.T('combine.py',exact_batch,d,'--output',td/'rej_rb','--test-only','--bootstrap',0,expect=2)
    assert 'differ in design_sha256'in r.stderr and not (td/'rej_rb/C8_test_final.json').exists(),r.stderr[-300:]
    lb=[X.comb.load_batch(exact_batch,True),X.comb.load_batch(d,True)];assert lb[1]['numerics']=='dd+mp256';lb[1]['design_sha256']=lb[0]['design_sha256']
    try:X.comb.combine_batches(lb,2,test_only=True,bootstrap=0);raise AssertionError('combine accepted an exact and a dd+mp256 batch')
    except ValueError as e:assert 'differ in numerics'in str(e),str(e)
    ok('route_b_cli_test_only_sweep_numerics_freeze_recosted_plan_run_assemble_combine_refuses_mixing',se=prb['se_total'],target=T,chosen=chosen,
       cost_ratio=prb['cost_total_core_hours']/m1['predictions']['cost_total_core_hours'],kept=kept['cost_total_core_hours'],reoptimized=reo['cost_total_core_hours'])

# ================================================================ part 3: a non-test plan of a fresh R7 bundle (G4c D1b)
def nontest_inputs(pkg:Path)->dict:
    """A minimal NON-test inputs/ for a scratch package: a non-test plan uses the package's inputs/ only and needs all
    twelve packs, whose L8 ones the Mac does not have. The scratch package's inputs/ gets the fixture's L8 packs and an
    inventory of the two cheapest graphs per (sector, L) of the fixture inventory (L3..L7 rows point into the package's
    own packs, L8 rows into the fixture's), and its manifest (no test_fixture) lists every file at its sha256."""
    fx=pkg/'tests/fixtures/inputs_mini';inv=load(fx/'inventory.json')
    small={s:{L:sorted(rows,key=lambda r:(r['cost'],r['id']))[:2]for L,rows in inv[s].items()}for s in inv}
    for s in ('free','power'):link_or_copy(fx/f'packs/{s}_L8.pack',pkg/f'inputs/packs/{s}_L8.pack')
    (pkg/'inputs/inventory.json').write_text(json.dumps(small,indent=1)+'\n')
    m=load(pkg/'inputs/manifest.json');assert not m.get('test_fixture')
    m['sha256']={name:digest(pkg/'inputs'/name)for name in m['sha256']};m['counts']={s:{L:len(v)for L,v in small[s].items()}for s in small}
    m['scope']='tests/test_pipeline.py part 3: a minimal non-test inputs folder of a scratch package (never the delivered inputs)'
    (pkg/'inputs/manifest.json').write_text(json.dumps(m,indent=1)+'\n');return small

def part3(X:Pkg):
    """G4c D1b (A-FLAG-6: "A non-test plan accepts it, given --approved-numerics-change and the sweep's cost model
    under the map (D15)"), end to end on a scratch package with minimal non-test inputs and the fake integrator."""
    Y=Pkg(X.td/'nt');small=nontest_inputs(Y.pkg);Y.env.pop('C8_INPUTS');Y.fixture=Y.pkg/'inputs'
    td=Y.td/'p3';td.mkdir();(Y.td/'scratch').mkdir(exist_ok=True);Y.seedmod.add(Y.seeds,1,'initial entry')
    appr=('--approved-numerics-change','test approval (test_pipeline.py part 3)')
    sweep=('--points',128,'--replicates',2,'--threads',1,'--procs',2,'--bootstrap-chunk',128,'--shards',2,'--merge-jobs',2)
    Y.sacct_add(9101,600,8)
    Y.T('sweep.py',td/'sweep','--seed',89001,*sweep,'--cost-model-out',td/'cm.json','--calibration',td/'cal.json',env={'SLURM_JOB_ID':'9101'});Y.T('seeds.py','add',td/'sweep')
    plan=lambda d,*extra,expect=0:Y.T('production.py','plan',d,'--forbid-seeds-from',Y.seeds,'--threads',1,'--checkpoint-tasks',64,*extra,expect=expect)
    # the non-test source pilot (default rates, 4,096 points), its non-test bundle
    pil=td/'pilot';plan(pil,'--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm.json','--seed',89002)
    m=load(pil/'manifest.json');assert m['test_only']is False and m['test_graphs']is None and m['inputs']=='inputs'and m['rates_identity']=='default'
    lanes_run(Y,pil,9102);Y.sacct_add(9102,300,16);Y.T('production.py','merge',pil,'--jobs',2);Y.T('seeds.py','add',pil)
    Y.T('design.py','freeze','--pilot',pil,'--out',td/'B1','--target-se',1e30)
    b1=load(td/'B1/design_meta.json');assert b1['test_only']is False and b1['provisional']is False and 89002 in b1['forbidden_seeds']
    y9_y10_nontest(Y,td,pil)  # Stage-6 fix round 2
    # the map by the one-step rule (every stratum has <= 2 graphs: --min-graphs 1 lets the rule decide), the sweep and
    # the non-test pilot under it, the fresh non-test bundle
    Y.T('design.py','rates','--pilot',pil,'--source-bundle',td/'B1','--rule','one-step','--min-graphs',1,'--boot',0,'--out',td/'PROV')
    prov=td/'PROV';pm=load(prov/'design_meta.json');sha=digest(prov/'rates.json');assert pm['test_only']is False and pm['rate_rule']['name']=='one-step'and pm['rates_identity']==sha
    Y.sacct_add(9105,500,8)
    Y.T('sweep.py',td/'sweep_map','--seed',89005,*sweep,'--rates',prov/'rates.json',*appr,'--cost-model-out',td/'cm_map.json','--calibration',td/'cal2.json',env={'SLURM_JOB_ID':'9105'})
    Y.T('seeds.py','add',td/'sweep_map');assert load(td/'cm_map.json')['rates_identity']==sha
    # R7 stays off (production.APPROVED_RATES is empty): every non-test plan under the map is refused; the acceptance
    # below runs plan with APPROVED_RATES monkeypatched to hold this map (plan_r7), as a user approval would
    r=plan(td/'pilot_map_unapproved','--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm_map.json','--seed',89006,'--rates',prov/'rates.json',*appr,expect=1)
    assert 'R7 is not approved'in r.stderr and 'APPROVED_RATES'in r.stderr and not (td/'pilot_map_unapproved').exists(),r.stderr[-400:]
    plan_r7=lambda d,*extra,expect=0,pilots=None:approved_rates_plan(Y,{sha:'test approval (test_pipeline.py part 3: APPROVED_RATES monkeypatched)'},d,'--forbid-seeds-from',
                                                                    Y.seeds,'--threads',1,'--checkpoint-tasks',64,*extra,expect=expect,pilots=pilots)
    # Stage 6: the pilot stays exact; a non-test measurement pilot under the (approved) map also needs its key in
    # production.APPROVED_PROFILE_PILOTS (empty; monkeypatched here as a user go would)
    mp_args=('--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm_map.json','--seed',89006,'--rates',prov/'rates.json',*appr)
    r=plan_r7(td/'pilot_map_nogo',*mp_args,expect=1)
    assert 'APPROVED_PROFILE_PILOTS'in r.stderr and 'stay exact'in r.stderr and not (td/'pilot_map_nogo').exists(),r.stderr[-400:]
    pm_=td/'pilot_map';plan_r7(pm_,*mp_args,pilots={('exact',sha):'test go (test_pipeline.py part 3: APPROVED_PROFILE_PILOTS monkeypatched)'})
    assert load(pm_/'manifest.json')['test_only']is False and load(pm_/'manifest.json')['rates_identity']==sha
    lanes_run(Y,pm_,9106);Y.sacct_add(9106,450,16);Y.T('production.py','merge',pm_,'--jobs',2);Y.T('seeds.py','add',pm_)
    Y.T('design.py','freeze','--pilot',pm_,'--rates-bundle',prov,'--out',td/'FRESH','--target-se',1e30)
    fm=load(td/'FRESH/design_meta.json')
    assert fm['test_only']is False and fm['provisional']is False and fm['rates_identity']==sha and fm['rates_bundle']['meta_sha256']==digest(prov/'design_meta.json')
    # the non-test plans of the fresh bundle: accepted with the approval and the cost model under the map; refused
    # without the approval, with the default-rates cost model (D15), without a cost model, and without the map
    bat=('--design',td/'FRESH','--seed',89010,'--rates',prov/'rates.json')
    r=plan(td/'batch_unapproved',*bat,*appr,'--cost-model',td/'cm_map.json',expect=1)
    assert 'R7 is not approved'in r.stderr and not (td/'batch_unapproved').exists(),r.stderr[-400:]
    d=td/'batch';plan_r7(d,*bat,*appr,'--cost-model',td/'cm_map.json');mb=load(d/'manifest.json')
    assert mb['test_only']is False and mb['rates_identity']==sha and mb['design']['meta_sha256']==digest(td/'FRESH/design_meta.json')and mb['approved_numerics_change']==appr[1]
    assert mb['allocation']['source']=='design'and mb['cost_model_sha256']==digest(td/'cm_map.json')
    bat=('--design',td/'FRESH','--seed',89012,'--rates',prov/'rates.json')  # Z15: the accepted plan registered 89010; refusals take a fresh seed
    for name,args,needle in (('no_approval',('--cost-model',td/'cm_map.json'),'--approved-numerics-change'),('default_cost_model',(*appr,'--cost-model',td/'cm.json'),'(D15)'),
                             ('no_cost_model',appr,'needs --cost-model'),('no_map',('--design',td/'FRESH','--seed',89011,*appr,'--cost-model',td/'cm_map.json'),'pins rates identity')):
        d=td/f'batch_{name}';r=plan_r7(d,*(bat if name!='no_map'else()),*args,expect=1)
        assert needle in r.stderr and not d.exists()and not list(td.glob(f'batch_{name}.tmp.*')),(name,r.stderr[-400:])
    ok('A-FLAG-6_G4c_non_test_plan_accepts_fresh_R7_bundle_with_approval_and_map_cost_model_refuses_without',rates_identity=sha[:12],
       graphs=sum(len(v)for s in small.values()for v in s.values()),decisions=sorted({x['decision']for x in pm['rate_rule']['strata']}),
       approved_rates='monkeypatched in plan_r7; the unpatched non-test pilot and batch under the map refused')
    route_b_nontest(Y,td,pil,plan,sweep,small)
    allow_list_nontest(Y,td,pil,plan,appr)
    pilot_exact_gated_nontest(Y,td,plan,small)

def y9_y10_nontest(Y:Pkg,td:Path,pil:Path):
    """Y10 (S6D-R2-02) on the command line with the NON-test pilot: the finding's --min-replicates 1 --max-replicates 1
    is refused by freeze and report (exit 2, nothing created). Y9 (S6D-R2-01): a copy of the merged non-test pilot with
    every checkpoint removed is refused by freeze and report (a production design never assumes an efficiency; before
    the fix eta_node was "assumed 1.0") and by eta_node in-process, and accepted by a --test-only freeze with the assumed
    1.0; a copy with ONE checkpoint removed is refused by a production freeze (missing evidence) and by a test-only one
    (incomplete accounting), and accounting.py exits 4 naming it; the intact pilot's accounting is complete."""
    r=Y.T('design.py','freeze','--pilot',pil,'--out',td/'B_y10','--target-se',1e30,'--min-replicates',1,'--max-replicates',1,expect=2)
    assert 'Y10'in r.stderr and 'a production bundle'in r.stderr and not (td/'B_y10').exists(),r.stderr[-400:]
    r=Y.T('design.py','report','--pilot',pil,'--min-replicates',1,'--max-replicates',1,expect=2);assert 'Y10'in r.stderr,r.stderr[-400:]
    gone=td/'pilot_no_checkpoints';shutil.copytree(pil,gone);ck=sorted(gone.glob('groups/*/checkpoints/*.json'));assert ck
    for f in ck:f.unlink()
    for cmd in (('freeze','--out',td/'B_gone','--target-se',1e30),('report',)):
        r=Y.T('design.py',cmd[0],'--pilot',gone,*cmd[1:],expect=2)
        assert 'Y9'in r.stderr and f'{len(ck)} checkpoint(s) of the merged pilot are missing'in r.stderr and not (td/'B_gone').exists(),(cmd[0],r.stderr[-400:])
    with mock.patch.dict(os.environ,Y.env):
        try:Y.D.eta_node(gone,False,None);raise AssertionError('eta_node assumed an efficiency for a production design')
        except ValueError as e:assert 'Y9'in str(e),str(e)
    Y.T('design.py','freeze','--pilot',gone,'--out',td/'B_gone_test','--test-only','--target-se',1e30)
    mt=load(td/'B_gone_test/design_meta.json');assert mt['test_only']and mt['eta_node']==1.0 and 'assumed'in mt['eta_node_source'],mt['eta_node_source']
    one=td/'pilot_one_checkpoint_gone';shutil.copytree(pil,one);first=sorted(one.glob('groups/*/checkpoints/*.json'))[0];first.unlink()
    rel=str(first.relative_to(one))
    r=Y.T('design.py','freeze','--pilot',one,'--out',td/'B_one','--target-se',1e30,expect=2)
    assert 'Y9'in r.stderr and rel in r.stderr and not (td/'B_one').exists(),r.stderr[-400:]
    r=Y.T('design.py','freeze','--pilot',one,'--out',td/'B_one_test','--test-only','--target-se',1e30,expect=2)
    assert 'eta_node unavailable'in r.stderr and 'missing'in r.stderr and not (td/'B_one_test').exists(),r.stderr[-400:]
    r=Y.T('accounting.py',one,expect=4);assert rel in r.stderr and 'removed evidence'in r.stderr,r.stderr[-400:]
    a=json.loads(Y.T('accounting.py',pil,'--json').stdout);assert a['complete']and a['missing_checkpoints']==0,a['incomplete']
    ok('Y9_Y10_nontest_pilot_checkpoints_removed_refused_test_only_assumed_one_missing_incomplete_allocation_options_refused',checkpoints=len(ck))

PATCHED_PLAN='''import json,os,sys
sys.path.insert(0,sys.argv.pop(1))
import production
production.APPROVED_RATES=json.loads(os.environ['TEST_PIPELINE_APPROVED_RATES'])   # tests only: a user approval of R7, simulated
production.APPROVED_PROFILE_PILOTS={tuple(k):v for k,v in json.loads(os.environ.get('TEST_PIPELINE_APPROVED_PROFILE_PILOTS','[]'))}   # tests only: a profile pilot's go
production.main(sys.argv[1:])
'''
def approved_rates_plan(Y:Pkg,rates:dict,*args,expect=0,pilots:dict|None=None):
    """production.py plan with production.APPROVED_RATES monkeypatched to rates and production.APPROVED_PROFILE_PILOTS
    to pilots ({(numerics, rates identity): reference}; default empty) (a wrapper in the scratch folder imports the
    scratch package's production.py, sets the allow-lists and calls its main): the A-FLAG-6 non-test acceptance and the
    Stage-6 profile-pilot gate."""
    w=Y.td/'plan_approved_rates.py';w.write_text(PATCHED_PLAN)
    e={**os.environ,**Y.env,'TEST_PIPELINE_APPROVED_RATES':json.dumps(rates),'TEST_PIPELINE_APPROVED_PROFILE_PILOTS':json.dumps([[list(k),v]for k,v in (pilots or{}).items()])}
    cp=subprocess.run([PY,'-B',str(w),str(Y.pkg/'tools'),'plan',*map(str,args)],capture_output=True,text=True,env=e)
    if (cp.returncode==0)!=(expect==0):raise AssertionError(f'plan (APPROVED_RATES patched) {args}: exit {cp.returncode}, expected {expect}\n{cp.stderr[-2500:]}')
    return cp

def allow_list_nontest(Y:Pkg,td:Path,pil:Path,plan,appr:tuple):
    """The allow-list scope (Stage 6): every NON-test plan refuses numerics outside production.APPROVED_PROFILES
    ({dd+mp256}): plan --pilot --numerics dd | mp256 | exp1 | dd+exp1 | dd+mp256+exp1, and plan --design of a bundle
    frozen for such numerics (route (a): a bundle whose pilot ran under the profile, here the non-test bundle B1 with
    both numerics set to the profile), each with the approval and creating nothing; a test-only plan under dd is
    accepted (gates and sweeps keep working)."""
    seed=89040;n=0
    for prof in ('dd','mp256','exp1','dd+exp1','dd+mp256+exp1'):
        seed+=1;d=td/f'pilot_nx_{prof.replace("+","_")}'
        r=plan(d,'--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm.json','--seed',seed,'--numerics',prof,*appr,expect=1)
        assert 'not in the user-approved set'in r.stderr and 'non-test plan'in r.stderr and not d.exists()and not list(td.glob(f'{d.name}.tmp.*')),(prof,r.stderr[-400:]);n+=1
    for prof in ('dd','dd+mp256+exp1'):
        b=td/f'B1_route_a_{prof.replace("+","_")}';shutil.copytree(td/'B1',b);x=load(b/'design_meta.json');x['numerics']=prof;x['pilot']['numerics']=prof
        (b/'design_meta.json').write_text(json.dumps(x,indent=1)+'\n');seed+=1;d=td/f'batch_route_a_{prof.replace("+","_")}'
        r=plan(d,'--design',b,'--seed',seed,'--numerics',prof,*appr,'--cost-model',td/'cm.json',expect=1)
        assert 'not in the user-approved set'in r.stderr and not d.exists(),(prof,r.stderr[-400:]);n+=1
    exe=fake_profile_exe(Y.pkg,'dd');seed+=1
    try:
        d=td/'pilot_dd_test_only';plan(d,'--pilot','--points',4096,'--replicates',2,'--test-graphs',1,'--cost-model',td/'cm.json','--seed',seed,'--numerics','dd',*appr)
        assert load(d/'manifest.json')['numerics']=='dd'and load(d/'manifest.json')['test_only']is True
    finally:exe.unlink()
    ok('allow_list_non_test_plans_refuse_numerics_outside_APPROVED_PROFILES_pilot_and_route_a_design_test_only_accepted',refusals=n)

def pilot_exact_gated_nontest(Y:Pkg,td:Path,plan,small:dict):
    """Stage 6, the last policy gap (the user's decisions of 2026-10-05: dd+mp256 for production after the pilot; the
    smoke and the pilot stay exact): (i) a NON-test plan --pilot --numerics dd+mp256 is refused with the approval, with
    or without a gate record (production.APPROVED_PROFILE_PILOTS is empty); with the set monkeypatched (a user go) the
    pilot still needs --numerics-gate: refused without, with a gate of another build and with a failed gate, accepted
    with a gate of this build (numerics_route: route 'pilot', the go, the gate, executable_gated); (ii) a non-test
    plan --design of a route-(a) dd+mp256 bundle (its pilot ran under the profile) is refused without a gate and on a
    build no gate covers, accepted with the gate (route 'a'); (iii) --numerics-gate is refused on an exact plan and on
    a route-(b) bundle (which carries its own gates); (iv) a test-only dd+mp256 pilot is accepted without a gate (the
    J-FLAG gates and sweeps) and refused with the gate of another build. A refusal creates nothing."""
    appr=('--approved-numerics-change',APPR_B);exe=fake_profile_exe(Y.pkg);go='test go (test_pipeline.py: APPROVED_PROFILE_PILOTS monkeypatched)'
    IM=digest(Y.pkg/'inputs/manifest.json')  # W18: the non-test plan's inputs (the package's own)
    gate=gate_record(td/'clflag.990010.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(Y.pkg/'bin/c8d2_gmp'),small,inputs=IM)
    other=gate_record(td/'clflag.990011.0/jflag_dd+mp256/numerics_flags.json','dd+mp256','f'*64,digest(Y.pkg/'bin/c8d2_gmp'),small,inputs=IM)
    failed=gate_record(td/'clflag.990012.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(Y.pkg/'bin/c8d2_gmp'),small,lambda x:x.update(status='failed'),inputs=IM)
    stale=gate_record(td/'clflag.990013.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(Y.pkg/'bin/c8d2_gmp'),small,inputs='7'*64)
    pp=lambda d,*extra,expect=0,pilots=None:approved_rates_plan(Y,{},d,'--forbid-seeds-from',Y.seeds,'--threads',1,'--checkpoint-tasks',64,*extra,expect=expect,pilots=pilots)
    pil_args=lambda seed:('--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm_dd.json','--seed',seed,'--numerics','dd+mp256',*appr)
    gone=lambda d:not d.exists()and not list(td.glob(f'{d.name}.tmp.*'))
    n=0;seed=89060
    def refused(d,r,needle):
        nonlocal n;assert needle in r.stderr and gone(d),(d.name,needle,r.stderr[-500:]);n+=1
    # (i) the profile pilot: no go (unpatched), then the go but no or a bad gate, then accepted
    for extra in ((),('--numerics-gate',gate)):
        seed+=1;d=td/f'pilot_dd_mp256_nogo_{len(extra)}';refused(d,plan(d,*pil_args(seed),*extra,expect=1),'APPROVED_PROFILE_PILOTS')
    pg={('dd+mp256','default'):go}
    for name,extra,needle in (('nogate',(),'give --numerics-gate RECORD'),('other',('--numerics-gate',other),'is not the dd+mp256 build that the --numerics-gate record(s) passed'),
                              ('failed',('--numerics-gate',failed),"not a passed full-scale J-FLAG gate of the production build of dd+mp256: status 'failed'"),
                              ('stale_inputs',('--numerics-gate',stale),f'the gate ran on inputs manifest 777777777777..., not {IM[:12]}...')):  # W18
        seed+=1;d=td/f'pilot_dd_mp256_go_{name}';refused(d,pp(d,*pil_args(seed),*extra,expect=1,pilots=pg),needle)
    seed+=1;d=td/'pilot_dd_mp256_go';pp(d,*pil_args(seed),'--numerics-gate',gate,pilots=pg);m=load(d/'manifest.json');nr=m['numerics_route']
    assert m['test_only']is False and m['numerics']=='dd+mp256'and m['allocation']['source']=='pilot'and m['executable_sha256']==digest(exe)
    assert nr['route']=='pilot'and nr['profile']=='dd+mp256'and nr['pilot_approval']==go and nr['plan_approval']==APPR_B and nr['executable_gated']is True
    assert [g['sha256']for g in nr['gates']]==[digest(gate)]and nr['gates'][0]['slurm_job']=='990010'and nr['approved_set_reference']==Y.prod.APPROVED_PROFILES['dd+mp256']
    # (ii) route (a): the exact non-test bundle B1 relabelled as frozen from a dd+mp256 pilot
    b=td/'B1_route_a_dd_mp256';shutil.copytree(td/'B1',b);x=load(b/'design_meta.json');x['numerics']='dd+mp256';x['pilot']['numerics']='dd+mp256'
    (b/'design_meta.json').write_text(json.dumps(x,indent=1)+'\n')
    des=lambda seed:('--design',b,'--seed',seed,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json')
    for name,extra,needle in (('nogate',(),'give --numerics-gate RECORD'),('other',('--numerics-gate',other),'is not the dd+mp256 build that the --numerics-gate record(s) passed')):
        seed+=1;d=td/f'batch_route_a_{name}';refused(d,plan(d,*des(seed),*extra,expect=1),needle)
    seed+=1;d=td/'batch_route_a';plan(d,*des(seed),'--numerics-gate',gate);m=load(d/'manifest.json');nr=m['numerics_route']
    assert m['test_only']is False and m['allocation']['source']=='design'and nr['route']=='a'and nr['executable_gated']is True and nr['pilot_approval']is None
    assert [g['sha256']for g in nr['gates']]==[digest(gate)]
    # (iii) --numerics-gate where it does not belong
    seed+=1;d=td/'pilot_exact_gate'
    refused(d,plan(d,'--pilot','--points',4096,'--replicates',8,'--cost-model',td/'cm.json','--seed',seed,'--numerics-gate',gate,expect=1),'belongs to a plan under a numerics profile')
    seed+=1;d=td/'batch_rb_gate'
    refused(d,plan(d,'--design',td/'BRB','--seed',seed,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json','--numerics-gate',gate,expect=1),'carries its own gate records')
    # (iv) test-only pilots under the profile: no gate needed; a gate given must cover the build
    tst=lambda seed:('--pilot','--points',4096,'--replicates',2,'--test-graphs',1,'--cost-model',td/'cm_dd.json','--seed',seed,'--numerics','dd+mp256',*appr)
    seed+=1;d=td/'pilot_dd_mp256_test_only';plan(d,*tst(seed));m=load(d/'manifest.json')
    assert m['test_only']is True and m['numerics']=='dd+mp256'and m['numerics_route']is None
    seed+=1;d=td/'pilot_dd_mp256_test_only_other';refused(d,plan(d,*tst(seed),'--numerics-gate',other,expect=1),'is not the dd+mp256 build')
    ok('Stage6_non_test_pilot_exact_profile_pilot_needs_go_and_gate_route_a_gated_test_only_unchanged',refusals=n)

def route_b_nontest(Y:Pkg,td:Path,pil:Path,plan,sweep:tuple,small:dict):
    """Route (b), NON-test, on the scratch package of part 3: the exact non-test pilot, a cost model measured under
    dd+mp256 (sweep.py --numerics), a gate record of the profile build, a non-test route-(b) bundle; plan --design
    accepts it with every piece (--numerics dd+mp256, --approved-numerics-change, the profile cost model, a gated
    production build) and records the route; it refuses: no approval, a cost model of another numerics identity, no
    --numerics (an exact plan of the profile bundle), a development build, an ungated build, a profile outside the
    approved set and a bundle whose numerics differ from its pilot's without the route record. freeze refuses no
    approval, an exact cost model, a profile outside the set and no gate. Nothing is created by a refusal."""
    D=Y.D;appr=('--approved-numerics-change',APPR_B);exe=fake_profile_exe(Y.pkg)
    Y.sacct_add(9120,600,8)
    Y.T('sweep.py',td/'sweep_dd','--seed',89020,*sweep,'--numerics','dd+mp256',*appr,'--cost-model-out',td/'cm_dd.json','--calibration',td/'cal_dd.json',
        env={'SLURM_JOB_ID':'9120','C8_FAKE_SECONDS':'0.4'});Y.T('seeds.py','add',td/'sweep_dd')
    assert load(td/'cm_dd.json')['numerics']=='dd+mp256'
    IM=load(pil/'manifest.json')['inputs_manifest_sha256'];assert IM==digest(Y.pkg/'inputs/manifest.json')  # W18: the non-test pilot's inputs
    gate=gate_record(td/'clflag.990003.0/jflag_dd+mp256/numerics_flags.json','dd+mp256',digest(exe),digest(Y.pkg/'bin/c8d2_gmp'),small,inputs=IM)
    fz=('--pilot',pil,'--target-se',1e30)
    for name,args,needle in (('no_approval',('--numerics','dd+mp256','--cost-model',td/'cm_dd.json','--numerics-gate',gate),'--approved-numerics-change'),
                             ('cm_exact',('--numerics','dd+mp256',*appr,'--cost-model',td/'cm.json','--numerics-gate',gate),'numerics identity must equal the profile'),
                             ('profile_dd',('--numerics','dd',*appr,'--cost-model',td/'cm_dd.json','--numerics-gate',gate),'not in the user-approved set'),
                             ('no_gate',('--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json'),'--numerics-gate')):
        r=Y.T('design.py','freeze',*fz,'--out',td/f'BRB_{name}',*args,expect=2);assert needle in r.stderr and not (td/f'BRB_{name}').exists(),(name,r.stderr[-300:])
    Y.T('design.py','freeze',*fz,'--out',td/'BRB','--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json','--numerics-gate',gate)
    mb=load(td/'BRB/design_meta.json');rec=mb['profile_recost']
    assert mb['test_only']is False and mb['numerics']=='dd+mp256'and mb['pilot']['numerics']=='exact'and rec['approval']==APPR_B
    assert rec['gates'][0]['sha256']==digest(gate)and rec['gates'][0]['profile_executable_sha256']==digest(exe)and rec['cost_model']['sha256']==digest(td/'cm_dd.json')
    assert rec['exact_pilot']['manifest_sha256']==digest(pil/'manifest.json')and rec['cost_model']['executable_gated']is True
    assert counts_of(td/'BRB')==counts_of(td/'B1')and close(mb['predictions']['cost_total_core_hours'],0.4*load(td/'B1/design_meta.json')['predictions']['cost_total_core_hours'],1e-9)
    bat=('--design',td/'BRB','--seed',89030)
    d=td/'batch_rb';plan(d,*bat,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json');m=load(d/'manifest.json');nr=m['numerics_route']
    assert m['test_only']is False and m['numerics']=='dd+mp256'and m['approved_numerics_change']==APPR_B and m['executable_sha256']==digest(exe)
    assert nr['route']=='b'and nr['profile']=='dd+mp256'and nr['executable_gated']is True and nr['gates'][0]['sha256']==digest(gate)and nr['bundle_approval']==APPR_B
    assert nr['exact_pilot']['manifest_sha256']==digest(pil/'manifest.json')and nr['bundle_cost_model']['sha256']==digest(td/'cm_dd.json')==nr['plan_cost_model']['sha256']
    assert nr['approved_set_reference']==Y.prod.APPROVED_PROFILES['dd+mp256']and m['design']['meta_sha256']==digest(td/'BRB/design_meta.json')
    bat=('--design',td/'BRB','--seed',89033)  # Z15: batch_rb registered 89030; the refusals below take a fresh seed
    def tamper(name,fn):
        b=td/name;shutil.copytree(td/'BRB',b);x=load(b/'design_meta.json');fn(x);(b/'design_meta.json').write_text(json.dumps(x,indent=1)+'\n');return b
    mp=tamper('BRB_mp256',lambda x:(x.update(numerics='mp256'),x['profile_recost'].update(profile='mp256')))
    norec=tamper('BRB_norec',lambda x:x.update(profile_recost=None))
    cases=[('no_approval',(*bat,'--numerics','dd+mp256','--cost-model',td/'cm_dd.json'),None,'--approved-numerics-change'),
           ('cm_exact',(*bat,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm.json'),None,'cost model numerics identity'),
           ('exact_plan',(*bat,'--cost-model',td/'cm.json'),None,'frozen for numerics'),
           ('development',(*bat,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json'),{'C8_FAKE_DEVELOPMENT':'1'},'development build'),
           ('outside_set',('--design',mp,'--seed',89031,'--numerics','mp256',*appr,'--cost-model',td/'cm_dd.json'),None,'not in the user-approved set'),
           ('no_record',('--design',norec,'--seed',89032,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json'),None,'without a route-(b) record')]
    for name,args,env,needle in cases:
        d=td/f'batch_rb_{name}';r=Y.T('production.py','plan',d,'--forbid-seeds-from',Y.seeds,'--threads',1,'--checkpoint-tasks',64,*args,env=env,expect=1)
        assert needle in r.stderr and not d.exists()and not list(td.glob(f'batch_rb_{name}.tmp.*')),(name,r.stderr[-400:])
    data=exe.read_bytes();exe.write_bytes(data+b'\n# another build\n');fake_build_record(exe,'gmp','dd+mp256')  # another build, with its record
    try:
        d=td/'batch_rb_ungated';r=plan(d,*bat,'--numerics','dd+mp256',*appr,'--cost-model',td/'cm_dd.json',expect=1)
        assert 'not a dd+mp256 build that a J-FLAG gate of the bundle passed'in r.stderr and not d.exists(),r.stderr[-400:]
    finally:exe.write_bytes(data);fake_build_record(exe,'gmp','dd+mp256')
    ok('route_b_non_test_plan_accepts_recosted_bundle_with_all_pieces_records_route_refuses_without',refusals=len(cases)+5)

PARTS=(('part1',part1),('part2',part2),('part3',part3))

def main()->int:
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0]);ap.add_argument('--output',type=Path)
    ap.add_argument('--only',help='PART,... of: '+', '.join(n for n,_ in PARTS));a=ap.parse_args()
    only=None
    if a.only is not None:  # T-03: unknown names and an empty selection are refused before any setup (exit 2)
        only=[x.strip()for x in a.only.split(',')if x.strip()];unknown=sorted(set(only)-{n for n,_ in PARTS})
        if unknown:ap.error(f'--only: unknown part(s) {", ".join(unknown)}; the parts are {", ".join(n for n,_ in PARTS)}')
        if not only:ap.error(f'--only: no part named; the parts are {", ".join(n for n,_ in PARTS)}')
    executed=[]
    with tempfile.TemporaryDirectory(prefix='c8d2_pipe_')as td:
        X=Pkg(Path(td))
        for name,fn in PARTS:
            if only is not None and name not in only:continue
            executed.append(name);fn(X)
    if not executed:raise SystemExit('test_pipeline: no part executed')
    rec={'status':'passed','requested':[n for n,_ in PARTS if n in only]if only is not None else 'all','executed':executed,'tests':RESULTS,
         'python':sys.version.split()[0],'numpy':np.__version__,'platform':sys.platform}
    if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(rec,indent=1,default=str)+'\n')
    print(json.dumps({'status':'passed','executed':executed,'tests':len(RESULTS)}));return 0

if __name__=='__main__':sys.exit(main())
