#!/usr/bin/env python3
"""Pilot -> Neyman design tool (PLAN component E; port of LRI_C8_HPC/tools/design8.py, reusable by C63d through its
parameters, H6). The pilot never enters an estimate, and its seeds are forbidden in production.

  design.py report --pilot RUN [--nested RUN_N] [--bundle B] [--target-se S] [--budget-core-hours B] [--json FILE]
                   [--tails-out FILE]
        The decision table: predicted SE against allocated core-hours for the relative targets 1e-3, 5e-4, 2.5e-4 and
        1.35e-4 of |C8| (--c8-magnitude, default 4.6e4), and --target-se / --budget-core-hours. Per stratum: the
        variance and cost per replicate, kurtosis, skewness, largest |z| and largest single-graph share of the replicate
        values, the split-half design penalty P8, and alpha when a nested pilot (--nested: the same graphs at more
        points) is given (otherwise alpha = 0.5 is assumed and the report says so; Z12, Stage-6 fix round 3: the nested
        pilot must share the pilot's scientific identity, NESTED_IDENTITY, and every graph keeps its own point ratio,
        ALPHA_RULE). With --bundle, the predicted SE of that frozen design recomputed from its counts: the bundle is read
        once through read_bundle (Z9: design.json and every counts file at its design_meta.json digest, only the
        verified bytes parsed) and the SE recomputed at the bundle's FROZEN variance margin and imputation (Z10), never
        the command's defaults; an explicit --variance-margin or --impute other than the frozen ones adds a separate,
        labelled projection. The per-graph heavy-tail diagnostics (plan addition (ii); C63d's
        rule, LRI_C8_D3_HPC_loop/PLAN.md C.3 and E.6, RECON.md section 6.3.6 and recon/cost_d3/tail_calib.py, same
        statistics and thresholds; the thresholds and actions apply to L8 only, as calibrated):
          - Hill tail index xi_hat per graph and campaign: the mean over the replicates of the Hill estimate from the
            16 largest |t| of the replicate (15 log-spacings above the 16th); xi = 1/a for P(|t| > x) ~ x^-a, and
            xi >= 1/2 means infinite variance. t is the weight-free base integrand of the class-B native fields;
          - largest share: the maximum over the replicates of max|t| / sum|t|;
          - undefined: a replicate with fewer than 16 tail values, a 16th |t| <= 0, tail_sum <= 0 or a value that is
            not finite makes the graph-campaign entry "undefined (<reason>)" (no mean over the other replicates), and
            a graph with an undefined entry in either campaign is listed and counted as undefined and never compared
            with a threshold;
          - screen (L8 only; pilot points, 4096): xi_hat > 0.38 or largest share > 0.05 in either campaign;
          - confirm (L8 only): a graph is "possible infinite variance" when the mean of its two campaigns' xi_hat at
            32,768 or more points per replicate exceeds 0.44 (the production monitor applies the same rule at
            n >> 32,768);
          - L <= 7: the same statistics per graph and campaign (--tails-out) and a summary per sector and loop, as
            diagnostics only: no threshold, no screen and no confirmation;
          - the split-half statistic Q = ln(s^2[replicates 1-4] / s^2[replicates 5-8]) of the C8-projected replicate
            values, per graph, campaign and disjoint block of 8 replicates; P8_hat = 1.0865 exp(0.0890 (Var(Q) -
            1.8696)), the R = 8 design penalty. Per sector (C63d's action 4, the R = 16 switch): Var(Q) pooled over
            the sector's L8 graph-campaigns at 4,096 points per replicate (this design flow has no separate stage A;
            its pilot's 4,096-point L8 graph-campaigns are the closest equivalent; L8 graph-campaigns at other point
            counts and every L <= 7 graph are left out and counted); R = 16 is advised for a sector with P8_hat >
            1.13. Per stratum (action 5): an L8 stratum with >= 500 graph-campaigns and P8_hat > 1.196 is flagged;
            L <= 7 strata report P8_hat as a diagnostic without the flag.
  design.py freeze --pilot RUN --out BUNDLE (--target-rel R | --target-se S | --budget-core-hours B) [--test-only]
                   [--batches K] [--spent-core-hours X] [--total-cap Y] [--variance-margin 1.5] [--min-points 4096]
                   [--min-replicates 32] [--max-replicates 128] [--seeds-log FILE] [--rates-bundle PROVISIONAL]
                   [--numerics PROFILE --approved-numerics-change TEXT --cost-model MODEL --numerics-gate RECORD ...]
        Per graph and campaign (D16): sigma_g^2 = n_g Var_rep(J_8 . jets_{rep,g}) from that campaign's merged
        graph_replicates.csv, J the order-8 complex-step Jacobian at the pilot means (the vendored module);
        c_g = sum of row seconds / points from the validated checkpoints (the merged graph_costs.csv); a sigma floor of
        3% of the stratum median; unpiloted graphs imputed per stratum (a log-linear fit on the inventory's addends, or
        the median), with the imputed share of the predicted variance recorded; base counts n_g ~ sigma_g/sqrt(c_g),
        powers of two, at least --min-points. Strata: free L3..L8, the free L8 primitives, power L3..L8. Stratum
        multipliers m ~ sqrt(V/C) (Neyman), split into replicates r in [32, 128], equal for campaigns a and b of one
        (sector, L) and taken from the group's SMALLEST multiplier (F11: r <= every multiplier, so no stratum is forced
        above its optimum; split()), and a power-of-two sample multiplier s >= 1 per stratum. The integer allocation
        (optimize(), F13 and the F11 follow-up, OPTIMIZER): from the F11 split and from the Stage-5 split (r from the
        LARGEST multiplier), the greedy loop to the target (or budget), a prune pass (target: halve an allocation r x s
        wherever the predicted SE still meets the target, to a fixed point) and a bounded local lattice search over the
        power-of-two allocations (boxes of a_k x 2^d, |d| <= 2, around the split point and the incumbent, solved exactly
        by meet in the middle, at most 32 boxes; least cost subject to SE <= target and every per-batch cap, or least SE
        subject to the budget and the caps); the better of the two starts is kept (F11's on ties), so the design is
        never costlier than either rule's greedy design at the same batch count K. design_meta.json records both starts
        (optimizer). The prune pass stops at the first best halving that fails a cap (it does not try the next one): a
        halving adds no task, checkpoint or replicate, so this happens only when the greedy design already misses a cap,
        and the lattice search (which skips cap failures) and the batch count K handle that case. Allocated
        cost = task seconds / (eta_omp,g x eta_node): eta_omp,g = row seconds / (threads x integration seconds) of the group, eta_node from
        tools/accounting.py over the work roles of the <prefix>-ledger-1 ledger (a pilot checkpoint naming an
        unregistered job refuses, "allocation unknown"; checkpoints without a Slurm id only for --test-only; Y9, Stage-6
        fix round 2: so is the assumed efficiency 1 of a pilot without Slurm accounting, and a pilot whose merged groups
        lack checkpoints is refused, since their Slurm ids can no longer be checked against the ledger). The
        predicted SE is multiplied by --variance-margin (1.5: C8(1)'s realized SE was 1.56x its pilot prediction)
        before it meets a target. An integer budget gate (--spent-core-hours, --total-cap). The minimum batch count K
        for which the optimized design of every batch meets the caps (tasks per campaign, checkpoints, replicates <=
        128, task seconds; the search can meet the caps at a smaller K than the old greedy designs did) is
        computed and a smaller --batches refused. W12 (Stage-6 fix round 4): the search runs up to 64 batches, and up to
        K with --batches K above 64; a search that finds no K says whether that was the search limit (the minimum
        design of one batch, r = --min-replicates and s = 1, meets the caps, so more batches would) or infeasibility
        (it does not); the allocation of an explicit --batches is checked against every cap before it is frozen.
        Y10 (Stage-6 fix round 2): the allocation options are validated before anything is designed (check_options): a
        production freeze keeps the plan's bounds (replicates r in [32, 128], the --min-replicates and --max-replicates
        powers of two; --min-points a power of two >= 4096; a variance margin >= 1); a --test-only bundle may reduce them
        (replicates powers of two >= 2, --min-points a power of two); and the designed allocation is checked against the
        same bounds before it is published (check_allocation). The bundle (design.json, counts/<campaign>_<sector>_L<L>.txt,
        design_meta.json) is published atomically and never overwritten; its design_meta.json pins the pilot, the
        executable, the numerics, the rates identity (one per freeze, R14), the inputs manifest, the forbidden seeds
        (the pilot seed and every seed of the seed log), the predictions, the efficiencies and the rule.
        Route (b), an approved numerics profile for a bundle frozen from an EXACT pilot (host decision 2026-10-05):
        --numerics P, P in the user-approved set production.APPROVED_PROFILES ({dd+mp256}; anything else refused), with
        --approved-numerics-change "<user approval reference>", --cost-model MODEL measured under P (tools/sweep.py
        --numerics P; its numerics identity must equal P, its rates identity and backend the pilot's, and it must cover
        every inventory graph of both campaigns) and --numerics-gate RECORD (repeatable): a passed, full-scale J-FLAG
        gate record of P's production build (tests/numerics_flags.py --profile P: status passed, no development option
        or parameter override, F1, F2 and F5 passed, F2 over every inventory graph, and since Stage-6 fix round 1 the
        evidence check_gate requires: the full F1 coverage (X1), the F1 tools bound to both executables by a byte-identical
        rebuild from one source snapshot (X2) and the F5 OpenMP teams observed as requested (X3); since fix round 3
        the libgmp provenance of both F1 tools (Z19); since fix round 4 the authenticated input set (W18): the gate
        ran on the pilot's inputs manifest, verified at its start and end, complete, with an F1 baseline of the same
        inputs; the bundle's gate entries record it as inputs_manifest_sha256); the cost model's
        executable must be one of the gated builds (cost_model.executable_gated). The pilot must be exact with the
        default rates (no --rates-bundle). sigma_g^2 stays the exact pilot's: the gate's F2 bounds the profile's change
        of C8 (dd+mp256: |dC8| + 3 SE_d = 4.25e-16, job 570210) far below any target SE. Every graph's c_g is the cost
        model's, so the base counts, multipliers, allocated cost and caps are re-costed under P; eta_omp,g and eta_node
        stay the exact pilot's. F13: the freeze designs both ways, (1) re-optimized under P's costs and (2) the exact
        path's design (its base counts, r, s and K) kept and re-costed under P, and keeps the cheaper feasible one (the
        target met and every cap held under P's costs; (2) only when strictly cheaper, or for a budget strictly more
        precise; ROUTE_B_KEEP); design_meta.json records both (route_b_choice). The bundle's numerics is P;
        design_meta.json records profile_recost: the profile, the
        approval, the allow-list reference, each gate (path, sha256, Slurm job, gated profile executable, F2 totals),
        the exact pilot's identity and the cost model's sha256 and identity. production.py plan --design accepts it
        only with --numerics P --approved-numerics-change and a cost model measured under P (and, non-test, an
        executable one of its gates passed). A bundle that keeps the exact design (2) records the exact path's minimum
        batch count (batches_minimum) and the exact search (optimizer); the re-optimized design (1) is recorded in
        route_b_choice (cost, SE, K, r, s, the start kept).
  design.py rates --pilot RUN --source-bundle B (--rule one-step [--step 0.1] [--band 0.10] [--min-graphs 100]
                  [--boot 1000] | --spec FILE) --out PROVISIONAL
        R7 only (opt-in): a NEW, provisional bundle holding the rate map rates.json (schema c8-d2-rates-1, every graph
        of both campaigns, a and b different) and a design_meta.json pinning its sha256, the source bundle's
        design_meta.json sha256 and the source rates identity, with "provisional": true. It carries no counts, no
        design.json and no multipliers (R19): every plan refuses it as an allocation source. Measure under the map
        (production.py plan --pilot --rates, or tools/sweep.py --rates), then freeze --rates-bundle PROVISIONAL.
        --rule one-step CHOOSES the rates from the pilot (A-FLAG-6; the rule that derived the Stage-4c map from
        J-SWEEP-1, moved here from benchmarks/expanse_2026-10-c8/stage4c/dev_r7/scripts/r7_spec.py): per (sector, L),
        W_c = sum_g sigma_g sqrt(c_g) of campaign c (sigma_g^2 = n_g Var_rep(J_8 . jet_g) at the pilot means, c_g =
        row seconds / (replicates x n_g)), the Neyman variance x cost W_c^2 of the stratum at its optimal allocation,
        and r = W_b^2 / W_a^2 (.9 over .8, the default rates the pilot ran at; a pilot under a map is refused): fewer
        than --min-graphs graphs, or 1 - band <= r <= 1 / (1 - band), keeps a .8, b .9; r < 1 - band steps up (a .9,
        b 1); r > 1 / (1 - band) steps down (a .7, b .8). a and b stay --step apart, so they differ for every graph. A
        graph bootstrap (--boot resamples of the stratum's graphs, a and b jointly, seed 7082026) gives 68% and 95%
        intervals of r for the record only. design_meta.json records the rule, its parameters and its inputs (the
        pilot's identity; per stratum the graphs, W, V, C, the ratios, the interval and the decision) as "rate_rule".
        --spec FILE is the explicit alternative: {campaign: {sector: {L: "rate" | {graph: "rate"}}}}; anything not
        named keeps the campaign's default (.8 / .9); "rate_rule" then records the file and its sha256. As in freeze
        and report, a pinned tool changed since the pilot was planned is accepted and recorded (accepted_tool_changes
        in design_meta.json).

Parameters for reuse (H6): --dimension D, --schema-prefix c8-dD (c8-d2), --half-d D/2 (1), --two-loop FILE, --inventory
FILE, --selection FILE (the L8 to-integrate sets of selection.json). The three must agree (prefix c8-d<D>, half-d D/2)
and name the pilot's own campaign (manifest <prefix>-production-1 of dimension D); every schema read or written
follows the prefix (O11): the pilot's group configs <prefix>-group-1 and merged tables <prefix>-merged-1, its ledger
<prefix>-ledger-1 and accounting <prefix>-accounting-1 (eta_node: tools/accounting.py --schema-prefix; a ledger record
of another prefix is refused, so the prefix of a campaign must match its ledger), the bundles <prefix>-design-1, the
rate maps <prefix>-rates-1, the report <prefix>-design-report-1. A pilot of this package (c8-d2) is verified as
production.py does (pinned tools, inputs, vendored assembly). A pilot of another package (the C8(3) campaign, c8-d3)
is read through the same campaign interface: its manifest, the group configs at the manifest's sha256 pins, every
merged.json validated against its config and manifest hashes and its tables at their digests, its own ledger; its
--inventory and --two-loop are required and must be the files the pilot's inputs manifest lists (the manifest.json
beside --inventory, at the pilot's inputs_manifest_sha256; --selection too when given). Nothing specific to d=2 is
hard-coded. A c8-d2 pilot takes its own inputs; --inventory, --two-loop and --selection are accepted for it only as the
very files its inputs manifest pins (same sha256; selection.json, which that manifest does not list, is refused), so no
override changes J8, the variances or the allocation under the pilot's inputs identity (X14, Stage-6 fix round 1).
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,re,shutil,sys
from dataclasses import dataclass,field
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import ROOT,digest,dump,load,pow2,replace_file,utc

TARGETS_REL=(1e-3,5e-4,2.5e-4,1.35e-4);C8_MAGNITUDE=4.6e4
CAMPAIGNS=('a','b');SECTORS=('free','power');LOOPS=tuple(range(3,9))
HILL_K=16;XI_SCREEN=0.38;SMAX_SCREEN=0.05;XI_CONFIRM_MEAN=0.44;SCREEN_POINTS=4096;CONFIRM_POINTS=32768
P8_C1=0.0890;P8_R16_SWITCH=1.13;P8_STRATUM_FLAG=1.196;P8_STRATUM_MIN=500
THRESHOLD_STRATA=('free_L8','power_L8')  # the tail and P8 thresholds apply to L8 only (the free L8 primitives included)
SIGMA_FLOOR=0.03;COST_FLOOR=1e-12
RULE=('per-graph Neyman base counts n_g ~ sigma_g/sqrt(c_g) per campaign and stratum (sigma floor 3% of the stratum median, '
      'powers of two, >= min-points), normalized to the pilot cost per replicate; stratum Neyman multiplier m ~ sqrt(V1/C1) '
      'split into replicates r in [min-replicates, max-replicates] (powers of two, equal for campaigns a and b of one sector '
      'and loop, the largest not above the smallest positive multiplier of the sector and loop: F11) and a power-of-two '
      'sample multiplier s >= 1 per stratum; integer allocation adjusted to the target (with the variance margin) or the '
      'budget by optimize(): from the F11 and the Stage-5 split, the greedy loop, a prune pass (target) and a bounded '
      'local lattice search over the power-of-two allocations held to the per-batch caps, the better start kept (F11 on '
      'ties; OPTIMIZER, recorded as optimizer); allocated cost = task seconds / (eta_omp,g x eta_node); minimum batch '
      'count from the per-batch caps')

OWN_PREFIX='c8-d2';OWN_DIMENSION=2

def check_reuse(dimension,half_d,schema_prefix)->None:
    """--dimension, --half-d and --schema-prefix agree (H6, O11): prefix c8-d<dimension>, half-d = dimension / 2."""
    import re
    if isinstance(dimension,bool)or not isinstance(dimension,int)or not 1<=dimension<=9:raise ValueError(f'--dimension {dimension!r} is not an integer dimension')
    if not isinstance(schema_prefix,str)or not re.fullmatch(r'c8-d[1-9]',schema_prefix)or schema_prefix!=f'c8-d{dimension}':
        raise ValueError(f'--schema-prefix {schema_prefix!r} does not match --dimension {dimension} (c8-d{dimension})')
    if float(half_d)!=dimension/2:raise ValueError(f'--half-d {half_d} is not d/2 = {dimension/2} for --dimension {dimension}')

def schemas(prefix:str)->dict:
    """Every schema design.py reads or writes, by the reuse prefix (O11)."""
    return {k:f'{prefix}-{v}'for k,v in (('production','production-1'),('group','group-1'),('merged','merged-1'),('design','design-1'),
                                         ('rates','rates-1'),('report','design-report-1'))}

def foreign_inputs(m:dict,inventory,two_loop,selection)->tuple[dict,Path]:
    """The inventory and the two-loop file of another package's pilot (H6, O11): both given, and both (and --selection
    when given) at the sha256 the pilot's own inputs manifest lists, that manifest being the manifest.json beside
    --inventory at the pilot's inputs_manifest_sha256."""
    if not inventory or not two_loop:raise ValueError('a pilot of another package needs --inventory and --two-loop: its own inputs/inventory.json and inputs/two_loop.json')
    imf=Path(inventory).resolve().parent/'manifest.json'
    if not imf.is_file()or digest(imf)!=m.get('inputs_manifest_sha256'):
        raise ValueError(f'--inventory {inventory}: the manifest.json beside it is not the pilot\'s inputs manifest (sha256 {str(m.get("inputs_manifest_sha256"))[:12]}...); '
                         'give the pilot\'s own inputs')
    listed=(json.loads(imf.read_bytes()).get('sha256')or{})
    for name,f in (('inventory.json',inventory),('two_loop.json',two_loop),('selection.json',selection)):
        if f is None:continue
        if listed.get(name)!=digest(f):raise ValueError(f'{f} is not the {name} the pilot\'s inputs manifest {imf} lists')
    return load(inventory),Path(two_loop)

def own_inputs(I,inventory,two_loop,selection)->tuple[dict,Path]:
    """X14: the inventory and the two-loop file of a pilot of this package (c8-d2). Without overrides, the files of the
    pilot's verified inputs manifest. An override (--inventory, --two-loop, --selection) is authenticated by the rule of
    foreign_inputs: it must be the very file the pilot's inputs manifest pins (same sha256), so an override can never
    change the scientific inputs (J8, the variances, the allocation) under the pilot's inputs identity; selection.json,
    which a c8-d2 inputs manifest does not list (its inventory holds the selected L8 sets), is refused. Different
    inputs need their own pilot (another inputs manifest, hence another identity)."""
    for name,f in (('inventory.json',inventory),('two_loop.json',two_loop),('selection.json',selection)):
        if f is None:continue
        if not I.has(name):raise ValueError(f'{f}: the pilot\'s inputs manifest ({I.rel}/manifest.json) lists no {name}, so it cannot be overridden; '
                                           'a pilot of this package uses its own inputs (X14)')
        if digest(f)!=I.sha(name):raise ValueError(f'{f} is not the {name} the pilot\'s inputs manifest ({I.rel}/manifest.json) pins: an override must be '
                                                  'the pinned file itself (X14); other inputs need a pilot planned on them')
    return (load(inventory)if inventory else load(I.where('inventory.json'))),(Path(two_loop)if two_loop else I.where('two_loop.json'))

def stratum_of(sector:str,L:int,primitive:bool)->str:
    return 'free_L8_primitive'if (sector=='free'and L==8 and primitive)else f'{sector}_L{L}'
def strata_names()->list[str]:return [f'free_L{L}'for L in LOOPS]+['free_L8_primitive']+[f'power_L{L}'for L in LOOPS]
def rgroup(stratum:str)->str:return stratum.replace('_primitive','')  # replicates are shared by the strata of one (sector, L)
def pow2_round(x:float)->int:return 1<<max(0,int(round(math.log2(x))))if x>1 else 1
def pow2_floor(x:float)->int:return 1<<max(0,int(math.floor(math.log2(x))))if x>=1 else 1

# ---------------------------------------------------------------- the split-half design penalty (tail_calib [B])
def _penalty_gamma(R:int,kex:float=0.)->float:
    from scipy.special import gammaln
    a=1/(2/(R-1)+kex/R);return math.exp(gammaln(a+.5)+gammaln(a-.5)-2*gammaln(a))
P8_GAUSS=None;VQ_GAUSS=math.pi**2-8  # Var(Q) of Gaussian replicate values: 2 psi'(3/2) = pi^2 - 8
def p8_of_varq(vq:float)->float:
    global P8_GAUSS
    if P8_GAUSS is None:P8_GAUSS=_penalty_gamma(8)
    return P8_GAUSS*math.exp(P8_C1*(vq-VQ_GAUSS))

def split_half_q(y:np.ndarray)->list[float]:
    """Q = ln(s^2[1-4]/s^2[5-8]) for every disjoint block of 8 replicates of one graph-campaign series y."""
    out=[]
    for b in range(len(y)//8):
        x=y[8*b:8*b+8];v1=np.var(x[:4],ddof=1);v2=np.var(x[4:],ddof=1)
        if v1>0 and v2>0:out.append(math.log(v1/v2))
    return out

def hill(top:list[float])->float|None:
    """The Hill estimate of xi from the 16 largest |t| (descending): mean of the 15 log-spacings above the 16th. None
    when it is undefined (replicate_tail gives the reason)."""
    if len(top)<HILL_K or not all(math.isfinite(x)for x in top[:HILL_K])or top[HILL_K-1]<=0:return None
    t=top[:HILL_K];return sum(math.log(t[i]/t[HILL_K-1])for i in range(HILL_K-1))/(HILL_K-1)

def replicate_tail(top:list[float],total:float)->tuple[float|None,float|None,str|None]:
    """One replicate's Hill estimate and largest share max|t|/sum|t|, or (None, None, reason) when either is undefined
    (C63d's rule, LRI_C8_D3_HPC_loop/PLAN.md E.6 item 2): fewer than 16 tail values, a value that is not finite, a 16th
    |t| <= 0 (the top 16 hold a zero) or tail_sum <= 0. The reason never contains a comma (it goes into a CSV)."""
    if len(top)<HILL_K:return None,None,f'fewer than {HILL_K} tail values ({len(top)})'
    if not all(math.isfinite(x)for x in top[:HILL_K])or not math.isfinite(total):return None,None,'tail value not finite'
    if top[HILL_K-1]<=0:return None,None,f'the {HILL_K}th |t| is {top[HILL_K-1]!r} (<= 0)'
    if total<=0:return None,None,f'tail_sum is {total!r} (<= 0)'
    xi=hill(top);share=top[0]/total
    if xi is None or not (math.isfinite(xi)and math.isfinite(share)):return None,None,'statistic not finite'
    return xi,share,None

# ---------------------------------------------------------------- the pilot data
@dataclass
class GroupData:
    campaign:str;sector:str;L:int;reps:int
    graphs:list                       # piloted graph ids (ascending)
    points:dict                       # per-replicate points of each piloted graph
    Y:np.ndarray                      # (reps, graphs, 2(9-L)) per-graph replicate jets
    seconds:dict                      # sum of native row seconds over all replicates, per graph
    eta_omp:float=1.0
    tails:dict|None=None              # graph -> [(points, top list, sum) per replicate]

@dataclass
class Pilot:
    groups:dict                       # (campaign, sector, L) -> GroupData
    inventory:dict                    # sector -> str(L) -> rows (id, primitive, addends)
    meta:dict=field(default_factory=dict)
    J8:dict|None=None                 # L -> C8 row of the Jacobian at the pilot means
    eta_node:float=1.0;eta_source:str='assumed'

def pilot_means(P:Pilot)->dict:
    """Total (free + power) means per loop: the equal-weight campaign means of the replicate group sums."""
    out={}
    for L in LOOPS:
        tot=None
        for s in SECTORS:
            m=sum(P.groups[(c,s,L)].Y.sum(1).mean(0)for c in CAMPAIGNS)/2
            tot=m if tot is None else tot+m
        out[L]=tot
    return out

def jacobian_rows(P:Pilot,B2,half_d)->dict:
    import assemble as asm
    J=asm.vendored().jacobians(pilot_means(P),B2,8,half_d)
    return {L:np.asarray(J[L])[8].real.astype(float)for L in LOOPS}

def read_two_loop(path:Path)->np.ndarray:return np.asarray(json.loads(Path(path).read_bytes())['B2'],float)

def load_pilot(run:Path,two_loop:Path|None=None,half_d=1,inventory:Path|None=None,selection:Path|None=None,dimension:int=OWN_DIMENSION,
               schema_prefix:str=OWN_PREFIX)->Pilot:
    """A merged campaign as pilot data: per-graph replicate jets (graph_replicates.csv), costs (graph_costs.csv), tails
    (graph_tails.csv) and the group efficiencies, each table verified through merged.json. The campaign must be the
    dimension and schema prefix given (O11); a c8-d2 pilot is verified as production.py does (an input override must be
    the pinned file itself: own_inputs, X14), another package's pilot through the campaign interface and its own inputs
    (foreign_inputs)."""
    import production as prod
    check_reuse(dimension,half_d,schema_prefix);sch=schemas(schema_prefix)
    run=Path(run).resolve();mb=(run/'manifest.json').read_bytes();m0=json.loads(mb)
    if m0.get('schema')!=sch['production']or m0.get('dimension')!=dimension or m0.get('order')!=8:
        raise ValueError(f'{run} is a {m0.get("schema")} campaign of dimension {m0.get("dimension")}, not a {sch["production"]} campaign of dimension {dimension} '
                         '(--dimension and --schema-prefix name the pilot\'s own; H6)')
    if schema_prefix==OWN_PREFIX:
        # A pinned tool changed since the pilot was planned does not change its merged data (every table is verified
        # through merged.json); the change is recorded in the bundle as provenance.
        m,I,mh,changes=prod.verify_base(run,check_executable=False,accept_tool_change=True,vendored=True)
        inv,tl=own_inputs(I,inventory,two_loop,selection);verified='production.verify_base (pinned tools, inputs, vendored assembly)'
    else:
        m,mh,changes=m0,hashlib.sha256(mb).hexdigest(),None
        inv,tl=foreign_inputs(m,inventory,two_loop,selection)
        verified=f'campaign interface ({sch["production"]} manifest, group configs at their pins, validated {sch["merged"]} tables; inputs at the pilot\'s inputs manifest)'
    if selection:
        sel=json.loads(Path(selection).read_bytes())['L8']
        for s in SECTORS:inv[s]['8']=[r for r in inv[s]['8']if r['id']in set(sel[s])]
    groups={}
    for g in m['groups']:
        p,cfg=prod.group_of(run,m,g['name'],sch['group'])
        if not (p/'merged.json').exists():raise ValueError(f'the pilot group {g["name"]} is not merged')
        md=prod.validate_merged(p,cfg,m,mh,sch['merged']);reps=cfg['replicates'];dim=2*(9-cfg['L'])
        gids=sorted(int(k)for k in cfg['counts']);pos={x:i for i,x in enumerate(gids)};Y=np.zeros((reps,len(gids),dim))
        with (p/'graph_replicates.csv').open()as f:
            next(f)
            for line in f:
                v=line.rstrip('\n').split(',');Y[int(v[0]),pos[int(v[1])]]=[float(x)for x in v[2:]]
        sec={}
        with (p/'graph_costs.csv').open()as f:
            for r in csv.DictReader(f):sec[int(r['graph'])]=float(r['row_seconds'])
        tails={}
        with (p/'graph_tails.csv').open()as f:
            for r in csv.DictReader(f):
                n=int(r['tail_n']);tails.setdefault(int(r['graph']),[]).append((int(r['points']),[float(r[f'top_{i+1}'])for i in range(n)],float(r['tail_sum'])))
        eta=md['row_seconds_sum']/md['thread_seconds_sum']if md.get('thread_seconds_sum')else 1.0
        groups[(cfg['campaign'],cfg['sector'],cfg['L'])]=GroupData(cfg['campaign'],cfg['sector'],cfg['L'],reps,gids,{int(k):int(v)for k,v in cfg['counts'].items()},
                                                                Y,sec,min(1.0,eta),tails)
    B2=read_two_loop(tl)
    P=Pilot(groups,inv,{'campaign':str(run),'manifest_sha256':mh,'seed':m['seed'],'executable_sha256':m['executable_sha256'],'numerics':m['numerics'],
                        'rates_identity':m['rates_identity'],'inputs_manifest_sha256':m['inputs_manifest_sha256'],'test_only':m['test_only'],'backend':m['backend'],
                        'threads':m['threads'],'allocation':m['allocation'],'two_loop_sha256':hashlib.sha256(np.asarray(B2).tobytes()).hexdigest(),
                        'accepted_tool_changes':changes or None,'dimension':dimension,'schema_prefix':schema_prefix,'half_d':half_d,'verified_by':verified})
    P.J8=jacobian_rows(P,B2,half_d);return P

# ---------------------------------------------------------------- per-graph statistics, imputation, base counts
def graph_table(P:Pilot,impute:str='addends',costs:dict|None=None)->dict:
    """{(c, s, L): {graph: dict(sigma, cost, piloted, stratum)}} for EVERY inventory graph: piloted graphs from the
    pilot, the others imputed per (campaign, stratum); a sigma floor of 3% of the stratum median. With costs (route
    (b): {(c, s, L, graph): seconds per point} of a cost model measured under an approved profile, covering every
    inventory graph) every graph's cost is the model's; sigma (and its imputation) stays the pilot's."""
    out={};imputed_n=0
    for (c,s,L),G in P.groups.items():
        rows=P.inventory[s][str(L)];prim={r['id']:bool(r.get('primitive'))for r in rows};add={r['id']:max(1,int(r.get('addends')or r.get('cost')or 1))for r in rows}
        y=np.einsum('rgj,j->rg',G.Y,P.J8[L])if len(G.graphs)else np.zeros((G.reps,0))
        T={}
        for i,g in enumerate(G.graphs):
            n=G.points[g];var=float(np.var(y[:,i],ddof=1))if G.reps>1 else 0.
            T[g]=dict(sigma=math.sqrt(max(0.,n*var)),cost=max(COST_FLOOR,G.seconds.get(g,0.)/(G.reps*n)),piloted=True,stratum=stratum_of(s,L,prim.get(g,False)),n_pilot=n,
                      y=y[:,i])
        for st in {stratum_of(s,L,prim[r['id']])for r in rows}:
            mem=[r['id']for r in rows if stratum_of(s,L,prim[r['id']])==st];pil=[g for g in mem if g in T and T[g]['sigma']>0]
            miss=[g for g in mem if g not in T]
            if miss:
                if not pil:
                    # no piloted graph in this stratum: borrow the (sector, L) group's piloted graphs (never graphs
                    # imputed for another stratum)
                    pil=[g for g in T if T[g]['piloted']and T[g]['sigma']>0]
                if not pil:raise ValueError(f'{c}_{s}_L{L}: no piloted graph with nonzero variance to impute stratum {st} from')
                xs=np.log([add[g]for g in pil]);fit=impute=='addends'and len(pil)>=3 and np.ptp(xs)>0
                for key in ('sigma','cost'):
                    ys=np.log([T[g][key]for g in pil])
                    if fit:b,a=np.polyfit(xs,ys,1);f=lambda x,a=a,b=b:math.exp(a+b*math.log(x))
                    else:med=float(np.exp(np.median(ys)));f=lambda x,med=med:med
                    for g in miss:T.setdefault(g,dict(piloted=False,stratum=st,n_pilot=0,y=None))[key]=f(add[g])
                imputed_n+=len(miss)
            sig=[T[g]['sigma']for g in mem if T[g]['piloted']and T[g]['sigma']>0]
            med=float(np.median(sig))if sig else max([T[g]['sigma']for g in mem]+[1e-300])
            for g in mem:T[g]['sigma']=max(T[g]['sigma'],SIGMA_FLOOR*med)
        if costs is not None:
            for g in T:T[g]['cost']=max(COST_FLOOR,float(costs[(c,s,L,g)]))
        out[(c,s,L)]=T
    return out

def base_counts(P:Pilot,T:dict,min_points:int,pilot_points:int)->dict:
    """Per campaign and stratum: n_g ~ sigma_g/sqrt(c_g), normalized so that the stratum costs what the pilot did per
    replicate (pilot_points x sum of c_g), rounded to powers of two and floored at min_points."""
    out={}
    for key,TT in T.items():
        byst={}
        for g,x in TT.items():byst.setdefault(x['stratum'],[]).append(g)
        cnt={}
        for st,gs in byst.items():
            unit=pilot_points*sum(TT[g]['cost']for g in gs);den=sum(TT[g]['sigma']*math.sqrt(TT[g]['cost'])for g in gs)
            k=unit/den if den>0 else 0.
            for g in gs:cnt[g]=max(min_points,pow2_round(max(1.,k*TT[g]['sigma']/math.sqrt(TT[g]['cost']))))
        out[key]=cnt
    return out

def stratum_sums(P:Pilot,T:dict,b:dict)->dict:
    """V1 (C8 variance per replicate at s = 1, both campaigns at weight 1/2) and C1 (allocated core-seconds per replicate
    at s = 1) per stratum, with the imputed graphs' part of V1."""
    out={st:dict(V1=0.,C1=0.,V1_imputed=0.,graphs=0,piloted=0)for st in strata_names()}
    for (c,s,L),TT in T.items():
        G=P.groups[(c,s,L)];eta=max(1e-6,G.eta_omp*P.eta_node)
        for g,x in TT.items():
            o=out[x['stratum']];v=.25*x['sigma']**2/b[(c,s,L)][g];o['V1']+=v;o['C1']+=x['cost']*b[(c,s,L)][g]/eta;o['graphs']+=1
            if not x['piloted']:o['V1_imputed']+=v
            else:o['piloted']+=1
    return out

# ---------------------------------------------------------------- the optimizer
@dataclass
class Opts:
    min_points:int=4096;min_reps:int=32;max_reps:int=128;margin:float=1.5;task_seconds:float=60.;min_chunk:int=256;max_task_seconds:float=120.
    threads:int=8;checkpoint_tasks:int|None=None;index_hours:float=1.5;max_tasks:int=5*10**7;max_checkpoints:int=2*10**5;max_batches:int=64

def evaluate_design(S:dict,r:dict,s:dict,K:int,margin:float)->dict:
    var=sum(S[k]['V1']/(r[rgroup(k)]*s[k])for k in S if S[k]['graphs']);cost=sum(S[k]['C1']*r[rgroup(k)]*s[k]for k in S if S[k]['graphs'])
    vim=sum(S[k]['V1_imputed']/(r[rgroup(k)]*s[k])for k in S if S[k]['graphs'])
    return dict(variance_per_batch=var,se_raw_per_batch=math.sqrt(var),se_raw_total=math.sqrt(var/K),se_total=margin*math.sqrt(var/K),
                cost_per_batch_core_hours=cost/3600,cost_total_core_hours=K*cost/3600,imputed_variance_share=vim/var if var>0 else 0.)

SPLIT_RULES=('smallest','largest')   # F11 (the fixed rule, preferred on ties) and the Stage-5 rule
LATTICE_RADIUS=2;LATTICE_MAX_BOXES=32;LATTICE_CANDIDATES=64;CAPS_TRIES=16;REL_TOL=1e-12
OPTIMIZER=('F13 and the F11 follow-up (2026-10-05, Stage 6): for each split rule, the F11 rule (r from the smallest '
           'multiplier of the sector and loop) and the Stage-5 rule (r from the largest): split, the greedy loop (target: '
           'double the most efficient s until the target holds; budget: halve s, then r, until the budget holds), then '
           '(target only) a prune pass that halves one active stratum\'s allocation r x s while the predicted SE still '
           'meets the target (the halving saving the most, repeated to a fixed point; it stops at the first best halving '
           'that fails a per-batch cap), then a local lattice search over the '
           'active strata\'s power-of-two allocations a_k = r x s_k: every combination of a_k x 2^d, |d| <= 2, in a box '
           'around a centre (first the split point, then the incumbent, recentred after every improvement; at most 32 boxes), '
           'solved exactly per box by meet in the middle; target: least cost subject to SE <= target, budget: least SE '
           'subject to cost <= budget; ties by (the other quantity, then the box order); a candidate is accepted only if '
           'tools/design.py evaluate_design confirms it and it meets every per-batch cap (at most 16 cap failures per box). '
           'r of a (sector, L) is min(r after the greedy loop, the smallest allocation of its active strata) (a sector and loop '
           'with a zero-variance stratum keeps its r), s_k = a_k / r. The design kept is the better of the two rules (F11 on '
           'ties): never costlier (target) or less precise (budget) than either rule\'s greedy design at the same batch count '
           'K; its predicted SE is '
           'evaluate_design\'s, exact for the integer allocation')

def split(S:dict,m:dict,opts:Opts,rule:str='smallest')->tuple[dict,dict]:
    """Stratum multipliers m -> replicates r per (sector, L) group and a power-of-two sample multiplier s >= 1 per
    stratum (allocation r x s). rule 'smallest' (F11 fix): r follows the group's SMALLEST positive multiplier (the
    largest power of two in [min_reps, max_reps] not above it); 'largest' is the Stage-5 rule, kept as the second start
    of optimize(). Since s >= 1, r is a floor on every stratum's allocation of the group: a stratum with m_k < r is
    forced to r, i.e. over-allocated by rho = r/m_k, which inflates the design's variance x cost by
    1 + w_k (1 - w_k) (rho - 1)^2 / rho (w_k its share of sum sqrt(V1 C1)). With r <= min m_k nothing is forced and
    every stratum gets r x pow2_round(m_k / r) = pow2_round(m_k), its best power-of-two allocation, whatever r; the
    largest such r keeps the most replicates. Groups with one stratum (all but free L8) are the same under both rules.
    A group whose multipliers are all zero (no graph, or no variance) gets min_reps."""
    if rule not in SPLIT_RULES:raise ValueError(f'split rule {rule!r} is not one of {SPLIT_RULES}')
    r={};s={}
    for grp in sorted({rgroup(k)for k in S}):
        pos=[m[k]for k in S if rgroup(k)==grp and m[k]>0]
        mm=(min(pos)if rule=='smallest'else max(pos))if pos else 0.;rr=opts.min_reps
        while 2*rr<=opts.max_reps and mm/(2*rr)>=1:rr*=2
        r[grp]=rr
    for k in S:s[k]=pow2_round(m[k]/r[rgroup(k)])if m[k]>r[rgroup(k)]else 1
    return r,s

class _Space:
    """The allocation space of the lattice search: a_k = r x s_k of every active stratum (graphs and V1 > 0), powers of
    two. A design from allocations: r_g = min(r0_g, the smallest a_k of the group's active strata) and s_k = a_k / r_g,
    so s >= 1 and r stays a power of two in [min_reps, r0_g]; a group with a stratum of graphs but zero variance keeps
    r0_g (its fixed stratum's cost stays C1 r0_g) and its active strata stay at a_k >= r0_g. r0 is the design after the
    greedy loop."""
    def __init__(self,S:dict,act:list,r0:dict,s0:dict,opts:Opts):
        self.S=S;self.act=list(act);self.r0=dict(r0);self.s0=dict(s0)
        self.fixed={rgroup(k)for k in S if S[k]['graphs']and not S[k]['V1']>0}
        self.lo={k:(self.r0[rgroup(k)]if rgroup(k)in self.fixed else opts.min_reps)for k in self.act}
    def alloc(self,r:dict,s:dict)->dict:return {k:r[rgroup(k)]*s[k]for k in self.act}
    def design(self,a:dict)->tuple[dict,dict]:
        r=dict(self.r0);s=dict(self.s0)
        for g in self.r0:
            al=[a[k]for k in self.act if rgroup(k)==g]
            if al and g not in self.fixed:r[g]=min(self.r0[g],min(al))
        for k in self.act:s[k]=a[k]//r[rgroup(k)]
        return r,s
    def fixed_cost(self)->float:
        return sum(self.S[k]['C1']*self.r0[rgroup(k)]*self.s0[k]for k in self.S if self.S[k]['graphs']and k not in self.act)

def _better(mode:str,ev:dict,ref:dict)->bool:
    """ev strictly better than ref (relative 1e-12): cheaper for a target, more precise for a budget."""
    if mode=='target':return ev['cost_total_core_hours']<ref['cost_total_core_hours']*(1-REL_TOL)
    return ev['se_total']<ref['se_total']*(1-REL_TOL)

def _meets(mode:str,ev:dict,bound:float)->bool:
    """The design meets the target SE (with the margin) or the budget, as the freeze checks it (relative 1e-12)."""
    return ev['se_total']<=bound*(1+REL_TOL)if mode=='target'else ev['cost_total_core_hours']<=bound*(1+REL_TOL)

def _greedy_target(S,r,s,K,opts,target_se,act):
    """The Stage-3 target loop: double the s of the most efficient stratum (variance removed per cost added) until the
    predicted SE meets the target."""
    ev=evaluate_design(S,r,s,K,opts.margin)
    while act and ev['se_total']>target_se*(1+REL_TOL):
        k=max(act,key=lambda k:(S[k]['V1']/(2*r[rgroup(k)]*s[k]))/(S[k]['C1']*r[rgroup(k)]*s[k]))
        s[k]*=2;ev=evaluate_design(S,r,s,K,opts.margin)
    return r,s,ev

def _greedy_budget(S,r,s,K,opts,budget_ch,act):
    """The Stage-3 budget loop: halve the s of the stratum losing the least precision per cost saved, then the r of the
    costliest group, until the budget holds; Infeasible when the minimum design (r = min_reps, s = 1) exceeds it."""
    ev=evaluate_design(S,r,s,K,opts.margin)
    while ev['cost_total_core_hours']>budget_ch*(1+REL_TOL):
        cand=[k for k in act if s[k]>1]
        if cand:k=min(cand,key=lambda k:(S[k]['V1']/(r[rgroup(k)]*s[k]))/(S[k]['C1']*r[rgroup(k)]*s[k]/2));s[k]//=2
        else:
            grps=[g for g in r if r[g]>opts.min_reps]
            if not grps:raise Infeasible(evaluate_design(S,{g:opts.min_reps for g in r},{k:1 for k in S},K,opts.margin)['cost_total_core_hours'])
            g=max(grps,key=lambda g:sum(S[k]['C1']for k in S if rgroup(k)==g));r[g]//=2
        ev=evaluate_design(S,r,s,K,opts.margin)
    return r,s,ev

def _prune(sp:_Space,r,s,ev,K,opts,target_se,caps):
    """F13 (i): halve one active stratum's allocation (s, or r with the group's other strata at twice the s) wherever
    the predicted SE still meets the target; the halving saving the most cost first (ties: stratum order), repeated
    to a fixed point. A halving never adds tasks, checkpoints or replicates; caps is checked all the same, and the
    pass STOPS at the first best halving that fails a cap (the next-best halving is not tried): that happens only when
    the greedy design already misses a cap, which the lattice search (it skips cap failures) and the batch count K
    then handle. No cap binds at J-DES-5's sizes."""
    steps=0
    while True:
        a=sp.alloc(r,s);best=None
        for k in sp.act:
            if a[k]//2<sp.lo[k]:continue
            a2=dict(a);a2[k]//=2;r2,s2=sp.design(a2);ev2=evaluate_design(sp.S,r2,s2,K,opts.margin)
            if _meets('target',ev2,target_se)and (best is None or _better('target',ev2,best[0])):best=(ev2,r2,s2)
        if best is None or not _better('target',best[0],ev)or (caps is not None and not caps(best[1],best[2])):return r,s,ev,steps
        ev,r,s=best;steps+=1

def _box(sp:_Space,a:dict,K:int,margin:float,mode:str,bound:float)->list:
    """The best designs of one box: every combination of a_k x 2^d (|d| <= LATTICE_RADIUS, a_k x 2^d >= the stratum's
    floor) of the active strata around the centre a, by meet in the middle: the strata in two halves, the second half
    sorted by the constrained quantity (variance for a target, cost for a budget) with the running best objective, and
    for every combination of the first half its best feasible partner. Returned: up to LATTICE_CANDIDATES allocations,
    ordered by (objective, the other quantity, first-half index, second-half index); the box arithmetic only ranks
    them (evaluate_design decides)."""
    S=sp.S;keys=sp.act;opt={k:[d for d in range(-LATTICE_RADIUS,LATTICE_RADIUS+1)if a[k]*2.**d>=sp.lo[k]]for k in keys}
    h=len(keys)//2;A=keys[:h];B=keys[h:]
    def enum(ks):
        v=np.zeros(1);c=np.zeros(1)
        for k in ks:x=np.array([a[k]*2.**d for d in opt[k]]);v=np.add.outer(v,S[k]['V1']/x).ravel();c=np.add.outer(c,S[k]['C1']*x).ravel()
        return v,c
    vA,cA=enum(A);vB,cB=enum(B)
    if mode=='target':thr=K*(bound/margin)**2;keyA,keyB,objA,objB=vA,vB,cA,cB
    else:thr=bound*3600/K-sp.fixed_cost();keyA,keyB,objA,objB=cA,cB,vA,vB
    order=np.lexsort((np.arange(len(keyB)),objB,keyB));kB=keyB[order];oB=objB[order]
    run=np.minimum.accumulate(oB);new=np.empty(len(oB),bool);new[0]=True;new[1:]=oB[1:]<run[:-1]
    best=np.maximum.accumulate(np.where(new,np.arange(len(oB)),0))   # the first position of the running minimum
    j=np.searchsorted(kB,thr-keyA,side='right')-1;ia=np.nonzero(j>=0)[0]
    if not len(ia):return []
    jb=order[best[j[ia]]];rank=np.lexsort((jb,ia,keyA[ia]+keyB[jb],objA[ia]+objB[jb]))[:LATTICE_CANDIDATES]
    out=[];shA=[len(opt[k])for k in A];shB=[len(opt[k])for k in B]
    for q in rank:
        a2=dict(a)
        for ks,sh,i in ((A,shA,ia[q]),(B,shB,jb[q])):
            for k,x in zip(ks,np.unravel_index(int(i),sh)if ks else ()):d=opt[k][int(x)];a2[k]=a[k]<<d if d>=0 else a[k]>>-d
        out.append(a2)
    return out

def _lattice(sp:_Space,seed:dict,r,s,ev,K,opts,mode,bound,caps):
    """F13 (ii): the bounded local lattice search. Boxes around a centre (first the split point seed, then the
    incumbent, recentred after every improvement; never a centre twice; at most LATTICE_MAX_BOXES); in each box the
    candidates in order, the first that evaluate_design confirms (meets the target or budget, strictly better than the
    incumbent) and that meets every cap becomes the incumbent (at most CAPS_TRIES cap failures per box)."""
    boxes=0;moves=0;seen=set();centre=seed
    while sp.act and boxes<LATTICE_MAX_BOXES:
        boxes+=1;seen.add(tuple(sorted(centre.items())));fails=0
        for a2 in _box(sp,centre,K,opts.margin,mode,bound):
            r2,s2=sp.design(a2);ev2=evaluate_design(sp.S,r2,s2,K,opts.margin)
            if not _meets(mode,ev2,bound):continue
            if not _better(mode,ev2,ev):break
            if caps is not None and not caps(r2,s2):
                fails+=1
                if fails>=CAPS_TRIES:break
                continue
            r,s,ev=r2,s2,ev2;moves+=1;break
        centre=sp.alloc(r,s)
        if tuple(sorted(centre.items()))in seen:break
    return r,s,ev,boxes,moves

def optimize(S:dict,K:int,opts:Opts,target_se:float|None=None,budget_ch:float|None=None,caps=None,info:dict|None=None)->tuple[dict,dict,dict]:
    """Neyman multipliers for one batch of K, split into (r, s) and adjusted on the integer allocation: to the target
    (predicted SE with the margin <= target, at the least cost) or to the budget (total core-hours <= budget, at the
    least SE). For each split rule (SPLIT_RULES): split, the greedy loop, the prune pass (target), the lattice search
    (OPTIMIZER); the better design of the two is kept, the F11 rule's on ties (and when only it meets the caps). caps,
    when given, is a predicate (r, s) -> bool for the per-batch caps; info, when given, receives the record of both
    starts. Deterministic."""
    act=[k for k in S if S[k]['graphs']and S[k]['V1']>0];root=sum(math.sqrt(S[k]['V1']*S[k]['C1'])for k in act)
    if target_se is not None:lam=opts.margin**2*root/(K*target_se**2)
    else:lam=budget_ch*3600/(K*root)if root>0 else 0.
    m={k:(lam*math.sqrt(S[k]['V1']/S[k]['C1'])if k in act else 0.)for k in S}
    mode='target'if target_se is not None else'budget';bound=target_se if mode=='target'else budget_ch;res={}
    for rule in SPLIT_RULES:
        r,s=split(S,m,opts,rule);seed={k:r[rgroup(k)]*s[k]for k in act}
        r,s,ev=(_greedy_target(S,r,s,K,opts,target_se,act)if mode=='target'else _greedy_budget(S,r,s,K,opts,budget_ch,act))
        sp=_Space(S,act,r,s,opts);greedy=dict(ev);steps=0
        if mode=='target':r,s,ev,steps=_prune(sp,r,s,ev,K,opts,target_se,caps)
        r,s,ev,boxes,moves=_lattice(sp,seed,r,s,ev,K,opts,mode,bound,caps)
        res[rule]=dict(r=r,s=s,ev=ev,caps_ok=caps is None or bool(caps(r,s)),greedy=greedy,prune_steps=steps,boxes=boxes,moves=moves)
    pick='smallest';x,y=res['smallest'],res['largest']
    if y['caps_ok']and (not x['caps_ok']or _better(mode,y['ev'],x['ev'])):pick='largest'
    if info is not None:
        q=lambda e:dict(cost_total_core_hours=e['cost_total_core_hours'],se_total=e['se_total'])
        info.update(mode=mode,kept=pick,starts={rule:dict(split=('F11: r from the smallest multiplier'if rule=='smallest'else'Stage 5: r from the largest multiplier'),
                                                          greedy=q(v['greedy']),final=q(v['ev']),caps_ok=v['caps_ok'],prune_steps=v['prune_steps'],
                                                          lattice_boxes=v['boxes'],lattice_moves=v['moves'],
                                                          replicates={g:int(n)for g,n in sorted(v['r'].items())},s={k:int(n)for k,n in v['s'].items()})
                                                for rule,v in res.items()})
    z=res[pick];return z['r'],z['s'],z['ev']

class Infeasible(Exception):
    def __init__(self,minimum):super().__init__(f'the minimum design costs {minimum:.1f} core-hours');self.minimum=minimum

def caps_check(P:Pilot,T:dict,b:dict,r:dict,s:dict,opts:Opts)->dict:
    """Per-batch caps: tasks per campaign, checkpoints, replicates, predicted task seconds (chunking as production.py
    plan with measured costs) and the index walls of --index-hours sizing."""
    Tck=opts.checkpoint_tasks or max(16*opts.threads,256);tasks={c:0 for c in CAMPAIGNS};ckpt=0;maxtask=0.;worst=None;walls=0.
    for (c,sec,L),TT in T.items():
        n_g=0;secs=0.
        for g,x in TT.items():
            n=b[(c,sec,L)][g]*s[x['stratum']];cg=x['cost'];ch=pow2_floor(opts.task_seconds/cg)if opts.task_seconds>=cg else 1
            ch=min(max(opts.min_chunk,ch),n);rr=r[rgroup(x['stratum'])];n_g+=rr*(n//ch);secs+=rr*n*cg
            if ch*cg>maxtask:maxtask=ch*cg;worst=(c,sec,L,g)
        tasks[c]+=n_g;nshards=max(1,math.ceil(secs/(opts.index_hours*3600*opts.threads*0.9)));ckpt+=math.ceil(n_g/Tck)+nshards
        walls=max(walls,secs/nshards/(opts.threads*0.9))
    ok=all(v<=opts.max_tasks for v in tasks.values())and ckpt<=opts.max_checkpoints and max(r.values())<=opts.max_reps
    return dict(ok=ok,tasks_per_campaign=tasks,checkpoints=ckpt,max_replicates=max(r.values()),predicted_max_task_seconds=maxtask,worst_task=worst,
                predicted_max_index_wall_seconds=walls,task_ok=maxtask<=opts.max_task_seconds)

def design_for(P:Pilot,opts:Opts,target_se=None,budget_ch=None,batches=None,impute='addends',T=None,costs=None)->dict:
    """The whole freeze computation without I/O: per-graph table (costs: route (b), see graph_table), base counts,
    strata, the minimum batch count K and the integer design of one batch (r, s), its predictions and caps. The
    optimizer's search is held to the caps (caps_check, memoized); 'optimizer' records both starts (optimize)."""
    T=T or graph_table(P,impute,costs);pp=max([G.points[g]for G in P.groups.values()for g in G.graphs]+[opts.min_points])
    b=base_counts(P,T,opts.min_points,pp);S=stratum_sums(P,T,b);memo={}
    def cap(r,s):
        key=(tuple(sorted(r.items())),tuple(sorted(s.items())))
        if key not in memo:memo[key]=caps_check(P,T,b,r,s,opts)
        return memo[key]
    def run(K):
        info={};r,s,ev=optimize(S,K,opts,target_se,budget_ch,caps=lambda r,s:cap(r,s)['ok'],info=info);return r,s,ev,cap(r,s),info
    def broken(cp)->str:
        return (f'tasks per campaign {cp["tasks_per_campaign"]} (cap {opts.max_tasks:,}), checkpoints {cp["checkpoints"]:,} (cap {opts.max_checkpoints:,}), '
                f'replicates up to {cp["max_replicates"]} (cap {opts.max_reps}), longest task {cp["predicted_max_task_seconds"]:.1f} s (cap {opts.max_task_seconds:g} s)')
    # W12 (Stage-6 fix round 4, S6D-R4-03): the minimum-batch search runs up to Opts.max_batches (64) and, with an
    # explicit --batches K, up to K; a search that ends without a batch count meeting the caps says whether it was the
    # search limit (the minimum design of one batch meets the caps, so more batches would) or infeasibility (it does not).
    limit=max(opts.max_batches,batches or 0);kmin=None;out=None
    for K in range(1,limit+1):
        r,s,ev,cp,info=run(K)
        if not cp['task_ok']:raise ValueError(f'graph {cp["worst_task"]}: the shortest allowed task (--min-chunk {opts.min_chunk}) is predicted at {cp["predicted_max_task_seconds"]:.1f} s > {opts.max_task_seconds:g} s')
        if cp['ok']:kmin=K;out=(r,s,ev,cp,info);break
    if kmin is None:
        c0=cap({g:opts.min_reps for g in {rgroup(k)for k in S}},{k:1 for k in S})  # the per-batch minimum design (r = min_reps, s = 1), whatever K
        if not (c0['ok']and c0['task_ok']):
            raise ValueError(f'infeasible: even the minimum design of one batch (r = {opts.min_reps}, s = 1) breaks the per-batch caps ({broken(c0)}); '
                             'no batch count meets them (raise --max-tasks or --max-checkpoints, or lower --min-replicates)')
        if batches is not None:
            raise ValueError(f'--batches {batches} is below the minimum batch count: no batch count up to {limit} meets the per-batch caps (not infeasibility: '
                             'the minimum design of one batch meets them, so a larger batch count does); give a larger --batches')
        raise ValueError(f'no batch count up to {limit} meets the per-batch caps: the search limit (64, or --batches K to search up to K), not infeasibility '
                         f'(the minimum design of one batch meets them, so a larger batch count does); give --batches K above {limit}')
    if batches is not None:
        if batches<kmin:raise BatchesTooFew(kmin)
        out=run(batches);cp=out[3]
        if not (cp['ok']and cp['task_ok']):  # W12: the explicitly selected allocation is validated against every cap
            raise ValueError(f'--batches {batches}: the design of one batch breaks the per-batch caps ({broken(cp)}); nothing frozen')
    r,s,ev,cp,info=out
    return dict(T=T,b=b,S=S,r=r,s=s,ev=ev,caps=cp,K=batches or kmin,K_min=kmin,optimizer=dict(rule=OPTIMIZER,**info))

ROUTE_B_KEEP=('F13 (Stage 6): a route-(b) freeze designs both ways and keeps the better feasible design: (1) re-optimized, the '
              'base counts and the allocation designed with the profile cost model\'s c_g; (2) the exact path\'s design (base '
              'counts, r, s and K designed with the exact pilot\'s c_g) kept and re-costed with the profile cost model (its SE '
              'is the exact design\'s, sigma being the exact pilot\'s). Feasible: the target (or budget) met, every per-batch '
              'cap held under the profile\'s costs. Kept: (2) only when it is strictly cheaper (a target; strictly more precise '
              'for a budget) by relative 1e-12, else (1)')

def design_route_b(P:Pilot,opts:Opts,target_se=None,budget_ch=None,batches=None,impute='addends',costs=None,T_exact=None,T_profile=None)->dict:
    """Route (b) (F13): design_for with the profile's costs (re-optimized) and the exact path's design re-costed under
    them (kept); the better feasible one (ROUTE_B_KEEP) with 'route_b_choice' recording both (cost, SE, K, r, s,
    feasibility, the exact design's own cost). An exact path that cannot be designed (an infeasible budget, too few
    --batches, no batch count meeting the caps) leaves only the re-optimized design, and the record says why."""
    db=design_for(P,opts,target_se,budget_ch,batches,impute,T=T_profile,costs=costs);mode='target'if target_se is not None else'budget'
    bound=target_se if mode=='target'else budget_ch
    q=lambda d,ev:dict(cost_total_core_hours=ev['cost_total_core_hours'],se_total=ev['se_total'],batches=int(d['K']),replicates={g:int(n)for g,n in sorted(d['r'].items())},
                       s={k:int(n)for k,n in d['s'].items()})
    rec=dict(rule=ROUTE_B_KEEP,mode=mode,reoptimized=dict(q(db,db['ev']),feasible=True,optimizer_kept=db['optimizer']['kept']))
    try:dx=design_for(P,opts,target_se,budget_ch,batches,impute,T=T_exact or graph_table(P,impute))
    except (ValueError,Infeasible,BatchesTooFew)as e:
        rec.update(kept_exact_allocation=dict(feasible=False,reason=f'the exact path has no design: {e}'),chosen='reoptimized');return dict(db,route_b_choice=rec)
    Sk=stratum_sums(P,db['T'],dx['b']);evk=evaluate_design(Sk,dx['r'],dx['s'],dx['K'],opts.margin);cpk=caps_check(P,db['T'],dx['b'],dx['r'],dx['s'],opts)
    ok=bool(cpk['ok']and cpk['task_ok']and _meets(mode,evk,bound))
    rec['kept_exact_allocation']=dict(q(dx,evk),feasible=ok,caps_ok=bool(cpk['ok']and cpk['task_ok']),exact_cost_total_core_hours=dx['ev']['cost_total_core_hours'],
                                     exact_se_total=dx['ev']['se_total'],optimizer_kept=dx['optimizer']['kept'])
    if ok and _better(mode,evk,db['ev']):
        rec['chosen']='kept_exact_allocation'
        return dict(T=db['T'],b=dx['b'],S=Sk,r=dx['r'],s=dx['s'],ev=evk,caps=cpk,K=dx['K'],K_min=dx['K_min'],optimizer=dx['optimizer'],route_b_choice=rec)
    rec['chosen']='reoptimized';return dict(db,route_b_choice=rec)

class BatchesTooFew(Exception):
    def __init__(self,k):super().__init__(f'--batches is below the minimum batch count {k} for which every batch meets the caps');self.k=k

# ---------------------------------------------------------------- report
def stratum_shape(P:Pilot,T:dict)->dict:
    """Per stratum: kurtosis, skewness and largest |z| of the standardized replicate values (pooled over graphs and
    campaigns), the largest single-graph share of the stratum variance, and the split-half P8."""
    from scipy.stats import kurtosis,skew
    acc={st:dict(z=[],share=[],q=[],gc=0)for st in strata_names()}
    for (c,s,L),TT in T.items():
        for g,x in TT.items():
            if not x['piloted']or x['y']is None or len(x['y'])<3:continue
            y=x['y'];sd=np.std(y,ddof=1);o=acc[x['stratum']];o['gc']+=1
            if sd>0:o['z'].extend(((y-y.mean())/sd).tolist())
            o['share'].append(x['sigma']**2);o['q'].extend(split_half_q(y))
    out={}
    for st,o in acc.items():
        z=np.asarray(o['z']);q=o['q']
        out[st]=dict(graph_campaigns=o['gc'],kurtosis=float(kurtosis(z))if len(z)>3 else None,skewness=float(skew(z))if len(z)>2 else None,
                     max_abs_z=float(np.abs(z).max())if len(z)else None,largest_share=(max(o['share'])/sum(o['share'])if o['share']and sum(o['share'])>0 else None),
                     varQ=float(np.var(q,ddof=1))if len(q)>1 else None,blocks=len(q),P8=p8_of_varq(float(np.var(q,ddof=1)))if len(q)>1 else None)
        # action 5 applies to L8 strata only, as calibrated (C63d's E.6 item 3); L <= 7 strata report P8 as a diagnostic
        out[st]['P8_flag']=bool(st.startswith(THRESHOLD_STRATA)and out[st]['P8']is not None and o['gc']>=P8_STRATUM_MIN and out[st]['P8']>P8_STRATUM_FLAG)
    return out

def sector_p8(P:Pilot,T:dict)->dict:
    """The R = 16 switch per sector (C63d's action 4): Var(Q) pooled over the sector's L8 graph-campaigns at 4,096 points
    per replicate. C63d pools its stage-A graph-campaigns (the first eighth of its L8 pass, 4,096 points, R = 8; its
    nested graphs through their 4,096-point prefix rows). This design flow has no separate stage A: its pilot is one
    pass, so the closest equivalent is the pilot's L8 graph-campaigns at 4,096 points per replicate (the free L8
    primitives included). L8 graph-campaigns at any other point count are left out (P8's calibration is at 4,096
    points), as is every L <= 7 graph; both are counted in the record."""
    out={}
    for sec in SECTORS:
        q=[];gc=0;other=0;low=0
        for (c,s,L),TT in T.items():
            if s!=sec:continue
            for x in TT.values():
                if not x['piloted']or x['y']is None:continue
                if L!=8:low+=1;continue
                if x['n_pilot']!=SCREEN_POINTS:other+=1;continue
                gc+=1;q.extend(split_half_q(x['y']))
        vq=float(np.var(q,ddof=1))if len(q)>1 else None
        p=p8_of_varq(vq)if vq is not None else None
        out[sec]=dict(basis=f'L8 graph-campaigns at {SCREEN_POINTS} points per replicate (C63d action 4; stage-A equivalent)',graph_campaigns=gc,blocks=len(q),
                      excluded_L8_other_points=other,excluded_L_le_7=low,varQ=vq,P8=p,R16_advised=bool(p is not None and p>P8_R16_SWITCH))
    return out

def _campaign_tails(G:GroupData,g:int)->tuple[float|None,float|None,str|None]:
    """xi_hat (the mean of the replicates' Hill estimates) and the largest share (the maximum over the replicates) of
    one graph-campaign, or (None, None, 'undefined (<reason>)') when any replicate is undefined: never a mean over the
    remaining replicates."""
    reps=(G.tails or{}).get(g)or[]
    if len(reps)!=G.reps:return None,None,f'undefined (tail rows for {len(reps)} of {G.reps} replicates)'
    h=[];sh=[]
    for i,(_,top,tot) in enumerate(reps):
        xi,share,why=replicate_tail(top,tot)
        if why:return None,None,f'undefined (replicate {i}: {why})'
        h.append(xi);sh.append(share)
    return float(np.mean(h)),max(sh),None

def tail_table(P:Pilot)->tuple[list,dict]:
    """Per graph and campaign: xi_hat (mean replicate Hill index from the 16 largest |t|), largest share, points per
    replicate and status ('defined' or 'undefined (<reason>)'). The thresholds apply to L8 graphs only (C63d's rule,
    as calibrated): the screen (either campaign at the pilot count) and the confirmation (two-campaign mean xi_hat >
    0.44 at >= 32,768 points); an L8 graph with an undefined entry in either campaign is listed under 'undefined' and
    never compared with a threshold. L <= 7 graphs are diagnostics: a per-(sector, L) summary without thresholds."""
    rows=[];per={}
    for (c,s,L),G in sorted(P.groups.items()):
        for g in G.graphs:
            reps=(G.tails or{}).get(g)or[];xi,smax,why=_campaign_tails(G,g)
            rows.append(dict(campaign=c,sector=s,L=L,graph=g,points=reps[0][0]if reps else None,xi_hat=xi,largest_share=smax,replicates=len(reps),
                             status=why or'defined',use='thresholds'if L==8 else'diagnostic'))
            per.setdefault((s,L,g),{})[c]=rows[-1]
    flagged={'screened':[],'confirmed':[],'undefined':[],'diagnostics':{}}
    for (s,L,g),d in sorted(per.items()):
        if L!=8:continue
        if any(x['status']!='defined'for x in d.values()):
            flagged['undefined'].append(dict(sector=s,L=L,graph=g,status={c:d[c]['status']for c in d}));continue
        # The screen is calibrated at the pilot count (4096 points per replicate); fewer points are not screened.
        sc=any((x['points']or 0)>=SCREEN_POINTS and(x['xi_hat']>XI_SCREEN or x['largest_share']>SMAX_SCREEN)for x in d.values())
        both=[d[c]['xi_hat']for c in CAMPAIGNS if c in d]
        pts=min((d[c]['points']or 0)for c in d)
        conf=len(both)==2 and pts>=CONFIRM_POINTS and sum(both)/2>XI_CONFIRM_MEAN
        if sc:flagged['screened'].append(dict(sector=s,L=L,graph=g,xi_hat={c:d[c]['xi_hat']for c in d},largest_share={c:d[c]['largest_share']for c in d},points=pts))
        if conf:flagged['confirmed'].append(dict(sector=s,L=L,graph=g,xi_mean=sum(both)/2,points=pts,label='possible infinite variance'))
    for s in SECTORS:
        for L in LOOPS[:-1]:
            sel=[x for x in rows if x['sector']==s and x['L']==L];dfn=[x for x in sel if x['status']=='defined']
            if not sel:continue
            xs=[x['xi_hat']for x in dfn];ss=[x['largest_share']for x in dfn]
            flagged['diagnostics'][f'{s}_L{L}']=dict(graph_campaigns=len(sel),undefined=len(sel)-len(dfn),xi_hat_median=float(np.median(xs))if xs else None,
                                                    xi_hat_max=max(xs)if xs else None,largest_share_max=max(ss)if ss else None)
    return rows,flagged

# Z12 (Stage-6 fix round 3, S6D-R3-05): the scientific identity a nested pilot must share with the pilot (the inputs, the
# two-loop jet, the numerics, the rates and the backend, besides the reuse parameters), so that the two point counts
# estimate the same quantity
NESTED_IDENTITY=('dimension','schema_prefix','half_d','inputs_manifest_sha256','two_loop_sha256','numerics','rates_identity','backend')
ALPHA_RULE=('Var_rep(n) ~ n^(-2 alpha) of the C8-projected replicate values of each graph piloted in both campaigns at two point '
            'counts (oriented so that n_lo < n_hi; graphs at equal counts are left out and counted). One ratio rho = n_hi/n_lo in '
            'the stratum: alpha = -ln(sum v_hi / sum v_lo) / (2 ln rho). Several ratios: the pooled moment estimate, the root of '
            'sum_g v_lo,g rho_g^(-2 alpha) = sum_g v_hi,g (strictly decreasing in alpha; equal to the one-ratio formula when the '
            'ratios agree), with alpha per ratio recorded too')

def check_nested(P:Pilot,N:Pilot)->None:
    """Z12: the nested pilot N must share the pilot P's scientific identity (NESTED_IDENTITY): otherwise its variances
    are not those of the same quantity at more points."""
    diff=[f'{k} {P.meta.get(k)!r} vs {N.meta.get(k)!r}'for k in NESTED_IDENTITY if P.meta.get(k)!=N.meta.get(k)]
    if diff:raise ValueError(f'--nested {N.meta.get("campaign")}: not the scientific identity of the pilot ({"; ".join(diff)}): a nested pilot integrates the '
                             'same graphs of the same inputs under the same numerics, rates and backend at more points (Z12)')

def _alpha_root(pairs:list)->float|None:
    """The root alpha of sum v_lo rho^(-2 alpha) = sum v_hi over pairs (n_lo, v_lo, n_hi, v_hi), rho = n_hi/n_lo > 1: one
    ratio in closed form, several by bisection (the left side strictly decreases in alpha). None without a positive
    variance on both sides."""
    A=sum(p[1]for p in pairs);B=sum(p[3]for p in pairs);rhos={p[2]/p[0]for p in pairs}
    if not (A>0 and B>0):return None
    if len(rhos)==1:return -0.5*math.log(B/A)/math.log(rhos.pop())
    f=lambda a:sum(p[1]*(p[2]/p[0])**(-2*a)for p in pairs)-B
    lo,hi=-1.,2.
    for _ in range(64):
        if f(lo)>0:break
        lo-=4.
    for _ in range(64):
        if f(hi)<0:break
        hi+=4.
    if not (f(lo)>0>f(hi)):return None
    for _ in range(200):
        mid=(lo+hi)/2
        if mid in (lo,hi):break
        if f(mid)>0:lo=mid
        else:hi=mid
    return (lo+hi)/2

def nested_alpha(P:Pilot,N:Pilot,T:dict,TN:dict)->dict:
    """alpha per stratum from two point counts of the same graphs (ALPHA_RULE). Z12 (Stage-6 fix round 3, S6D-R3-05):
    the old estimate summed the variances over the stratum's graphs but took the point counts of the LAST graph, so
    graphs at different ratios gave a wrong alpha (two graphs of variance 1 at 2n and 8n with variances 1/2 and 1/8,
    alpha 1/2 exactly, gave ln(16/5)/(2 ln 8)). Now every graph keeps its own ratio, and the nested pilot must share the
    pilot's scientific identity (check_nested). Per stratum: alpha (None without a usable pair), the graphs used, the
    distinct ratios, alpha per ratio, the graphs at equal point counts left out, and the estimator."""
    check_nested(P,N)
    out={}
    for st in strata_names():
        pairs=[];equal=0
        for key in T:
            if key not in TN:continue
            for g,x in T[key].items():
                y=TN[key].get(g)
                if not x['piloted']or y is None or not y['piloted']or x['stratum']!=st:continue
                n1,n2=int(x['n_pilot']),int(y['n_pilot']);v1,v2=float(np.var(x['y'],ddof=1)),float(np.var(y['y'],ddof=1))
                if n1==n2:equal+=1;continue
                pairs.append((n1,v1,n2,v2)if n1<n2 else(n2,v2,n1,v1))
        by={}
        for p in pairs:by.setdefault(p[2]/p[0],[]).append(p)
        out[st]=dict(alpha=_alpha_root(pairs)if pairs else None,graphs=len(pairs),equal_points_left_out=equal,ratios=sorted(by),
                     alpha_by_ratio={f'{rho:g}':_alpha_root(ps)for rho,ps in sorted(by.items())},
                     point_pairs=sorted({(p[0],p[2])for p in pairs}),estimator=('one ratio'if len(by)==1 else'pooled over ratios')if by else None)
    return out

# ---------------------------------------------------------------- design bundles (Z9: one verified reader)
DEFAULT_MARGIN=1.5;DEFAULT_IMPUTE='addends'
COUNTS_LINE=re.compile(r'([0-9]+) ([0-9]+)')

def parse_counts(where,data:bytes)->dict:
    """Z9: a counts file's verified bytes as {graph: count}: exactly the newline-terminated lines freeze writes,
    f'{graph} {count}\\n', each a new graph with a positive count (no sign, no other separator, no duplicate graph, no
    unterminated last line). Shared by read_bundle and production.read_bundle (one reader of the format)."""
    cnt={};text=data.decode('latin-1')
    if text and not text.endswith('\n'):raise ValueError(f'{where}: not newline-terminated lines "<graph> <count>"')
    for i,line in enumerate(text.split('\n')[:-1]):
        m_=COUNTS_LINE.fullmatch(line)
        if not m_ or int(m_.group(2))<1 or int(m_.group(1))in cnt:raise ValueError(f'{where} line {i+1}: {line[:40]!r} is not "<graph> <positive count>" of a new graph')
        cnt[int(m_.group(1))]=int(m_.group(2))
    return cnt

def read_bundle(bundle,schema_prefix:str=OWN_PREFIX,allow_provisional:bool=False)->dict:
    """Z9 (Stage-6 fix round 3, S6D-R3-02): a design bundle read and verified once, by the schema of the reuse prefix
    (<prefix>-design-1, O11). Every file is read once, its sha256 checked against design_meta.json, and only those
    verified bytes are parsed: a frozen bundle's design.json (design_sha256; its schema and kind 'design') and exactly
    the 24 counts files counts/<campaign>_<sector>_L<L>.txt (counts_sha256; every line '<graph> <count>', distinct
    graphs, positive counts); a provisional bundle (design.py rates; refused unless allow_provisional) its rates.json
    (rates_sha256, equal to its rates_identity). Returns {'path', 'meta', 'meta_sha256' (of the bytes parsed),
    'provisional', and for a frozen bundle 'design' and 'counts' {(campaign, sector, L): {graph: count}}}. Before the
    fix report --bundle parsed design.json and the counts unchecked (a graph's count doubled without its digest changed
    the reported SE under the original meta sha256), as did the rates and freeze --rates-bundle readers of
    design_meta.json; production.read_bundle (c8-d2 only) verifies the same digests at plan."""
    bundle=Path(bundle).resolve();want=schemas(schema_prefix)['design']
    def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
    def js(name:str,data:bytes):
        try:return json.loads(data)
        except ValueError as e:raise ValueError(f'{bundle/name} is not JSON: {e}')
    mb=(bundle/'design_meta.json').read_bytes();meta=js('design_meta.json',mb)
    if not isinstance(meta,dict)or meta.get('schema')!=want or meta.get('kind')!='meta':
        raise ValueError(f'{bundle} is a {meta.get("schema")if isinstance(meta,dict)else type(meta).__name__} bundle, not a {want} design bundle (design_meta.json)')
    out=dict(path=bundle,meta=meta,meta_sha256=sha(mb),provisional=bool(meta.get('provisional')))
    if out['provisional']:
        if not allow_provisional:raise ValueError(f'{bundle} is a provisional rates bundle (design.py rates): no allocation')
        rb=(bundle/'rates.json').read_bytes()
        if not SHA256.fullmatch(str(meta.get('rates_sha256')))or sha(rb)!=meta['rates_sha256']or meta.get('rates_identity')!=meta['rates_sha256']:
            raise ValueError(f'{bundle/"rates.json"} differs from the digest in design_meta.json (rates_sha256 = rates_identity)')
        return out
    db=(bundle/'design.json').read_bytes()
    if not SHA256.fullmatch(str(meta.get('design_sha256')))or sha(db)!=meta['design_sha256']:raise ValueError(f'{bundle/"design.json"} differs from the digest in design_meta.json')
    d=js('design.json',db)
    if not isinstance(d,dict)or d.get('schema')!=want or d.get('kind')!='design':raise ValueError(f'{bundle/"design.json"} is not a {want} design')
    names={f'counts/{c}_{s}_L{L}.txt':(c,s,L)for c in CAMPAIGNS for s in SECTORS for L in LOOPS};cs=meta.get('counts_sha256')
    if not isinstance(cs,dict)or set(cs)!=set(names):
        raise ValueError(f'{bundle}: design_meta.json must pin exactly the {len(names)} counts files counts/<campaign>_<sector>_L<L>.txt '
                         f'(got {sorted(cs)[:3]if isinstance(cs,dict)else cs!r}...)')
    counts={}
    for name,key in sorted(names.items()):
        data=(bundle/name).read_bytes()
        if not SHA256.fullmatch(str(cs[name]))or sha(data)!=cs[name]:raise ValueError(f'{bundle/name} differs from the digest in design_meta.json')
        counts[key]=parse_counts(bundle/name,data)  # exactly the lines freeze writes, f'{graph} {count}\n'
    return dict(out,design=d,counts=counts)

def _bundle_se(T:dict,B:dict)->tuple[float,int]:
    """(sum of .25 sigma^2 / (count x s x r) over every graph, K) of the verified bundle B under the per-graph table T;
    the bundle's groups and graphs must be T's (the pilot's inventory)."""
    d=B['design'];var=0.
    if set(T)!=set(B['counts']):raise ValueError(f'{B["path"]}: the bundle\'s groups are not the pilot\'s')
    def pos(x,what):
        if not (_int(x)and x>=1):raise ValueError(f'{B["path"]}: {what} {x!r} is not a positive integer')
        return x
    for (c,s,L),TT in T.items():  # the old summation order (bundle SEs of valid bundles unchanged to the bit)
        cnt=B['counts'][(c,s,L)]
        if set(cnt)!=set(TT):raise ValueError(f'{B["path"]}: counts/{c}_{s}_L{L}.txt holds {len(cnt)} graphs, the pilot\'s inventory {len(TT)} (not this pilot\'s design)')
        rr=pos((d.get('replicates')or{}).get(f'{s}_L{L}'),f'replicates[{s}_L{L}]')
        for g,x in TT.items():var+=.25*x['sigma']**2/(cnt[g]*pos(((d.get('strata')or{}).get(x['stratum'])or{}).get('s'),f'strata[{x["stratum"]}].s')*rr)
    return var,pos(d.get('batches'),'batches')

def bundle_prediction(P:Pilot,B:dict,projection:dict|None=None)->dict:
    """The predicted SE of a frozen bundle (B from read_bundle: verified bytes, Z9) from its own counts x s, replicates r
    and batches K and the pilot's sigma: an independent recomputation of the freeze's prediction (A-DES-2). Z10
    (Stage-6 fix round 3, S6D-R3-03): at the bundle's FROZEN settings, its variance margin (design_meta.json
    parameters.variance_margin, equal to design.json predicted.variance_margin) and its imputation (imputed.impute),
    never the report command's (report used its own default margin 1.5 and imputation 'addends': a bundle frozen with
    --variance-margin 2 was reported 25% below its frozen prediction). It is the frozen prediction recomputed only for
    the pilot the bundle was frozen from (its manifest sha256; another pilot's sigma gives a labelled projection), and
    'agrees' says whether it equals the frozen SE to 1e-9. projection: explicitly requested settings
    {'variance_margin', 'impute'} other than the frozen ones, reported separately and labelled as a projection."""
    meta,d=B['meta'],B['design']
    fm=(meta.get('parameters')or{}).get('variance_margin');fi=(meta.get('imputed')or{}).get('impute')
    if not (_real(fm)and fm>0 and fm==(d.get('predicted')or{}).get('variance_margin')):
        raise ValueError(f'{B["path"]}: the frozen variance margin is not recorded consistently (design_meta parameters {fm!r}, design.json predicted '
                         f'{(d.get("predicted")or{}).get("variance_margin")!r})')
    if fi not in ('addends','median'):raise ValueError(f'{B["path"]}: the frozen imputation {fi!r} is not recorded (imputed.impute)')
    var,K=_bundle_se(graph_table(P,fi),B);fp=d.get('predicted')or{}
    same=(meta.get('pilot')or{}).get('manifest_sha256')==P.meta.get('manifest_sha256');se=fm*math.sqrt(var/K)
    rel=(se-fp['se_total'])/fp['se_total']if _real(fp.get('se_total'))and fp['se_total']>0 else None
    out=dict(bundle=str(B['path']),meta_sha256=B['meta_sha256'],batches=K,frozen_settings=dict(variance_margin=fm,impute=fi),
             se_raw_total=math.sqrt(var/K),se_total=se,frozen_prediction=fp,pilot_is_the_frozen_pilot=same,
             frozen_pilot_manifest_sha256=(meta.get('pilot')or{}).get('manifest_sha256'),
             kind=('the frozen prediction recomputed from the bundle\'s counts at its frozen margin and imputation'if same else
                   'a PROJECTION of the bundle under another pilot\'s sigma (not the frozen prediction: the bundle was frozen from another pilot)'),
             relative_difference=rel,agrees=bool(same and rel is not None and abs(rel)<=1e-9),projection=None)
    if projection:
        pm,pi=projection.get('variance_margin',fm),projection.get('impute',fi)
        if (pm,pi)!=(fm,fi):
            pv,_=_bundle_se(graph_table(P,pi),B)
            out['projection']=dict(label='PROJECTION at the requested settings, not the frozen prediction',variance_margin=pm,impute=pi,
                                   se_raw_total=math.sqrt(pv/K),se_total=pm*math.sqrt(pv/K))
    return out

def report(P:Pilot,opts:Opts,c8:float,target_se=None,budget=None,nested:Pilot|None=None,bundle=None,impute='addends',recost=None,
           bundle_projection:dict|None=None)->dict:
    """The decision table; with recost (route (b), profile_recost(..., freezing=False)) every cost is the profile cost
    model's and sigma the exact pilot's, and each row is the design a route-(b) freeze would keep (design_route_b: the
    re-optimized design or the exact path's re-costed, route_b_chosen). bundle: a path or read_bundle's record (Z9); its
    prediction at the bundle's frozen settings (bundle_prediction, Z10), with bundle_projection the explicitly requested
    other settings as a labelled projection."""
    B=(bundle if isinstance(bundle,dict)else read_bundle(bundle,P.meta.get('schema_prefix',OWN_PREFIX)))if bundle else None  # Z9: verified first
    if nested is not None:check_nested(P,nested)  # Z12
    T=graph_table(P,impute,recost['costs']if recost else None);table=[];Tx=graph_table(P,impute)if recost else None
    def des(**kw):
        if recost:return design_route_b(P,opts,impute=impute,costs=recost['costs'],T_exact=Tx,T_profile=T,**kw)
        return design_for(P,opts,T=T,**kw)
    ch=lambda d:{'route_b_chosen':d['route_b_choice']['chosen']}if d.get('route_b_choice')else{}
    for rel in TARGETS_REL:
        try:d=des(target_se=rel*c8);table.append(dict(target_rel=rel,target_se=rel*c8,batches=d['K'],predicted_se_with_margin=d['ev']['se_total'],
                                                     predicted_se_raw=d['ev']['se_raw_total'],allocated_core_hours=d['ev']['cost_total_core_hours'],
                                                     replicates=d['r'],s=d['s'],imputed_variance_share=d['ev']['imputed_variance_share'],
                                                     optimizer_kept=d['optimizer']['kept'],**ch(d)))
        except (ValueError,Infeasible)as e:table.append(dict(target_rel=rel,target_se=rel*c8,error=str(e)))
    extra=[]
    if target_se:d=des(target_se=target_se);extra.append(dict(target_se=target_se,batches=d['K'],allocated_core_hours=d['ev']['cost_total_core_hours'],predicted_se_with_margin=d['ev']['se_total'],**ch(d)))
    if budget:
        try:d=des(budget_ch=budget);extra.append(dict(budget_core_hours=budget,batches=d['K'],allocated_core_hours=d['ev']['cost_total_core_hours'],predicted_se_with_margin=d['ev']['se_total'],**ch(d)))
        except Infeasible as e:extra.append(dict(budget_core_hours=budget,error=f'infeasible: {e}'))
    base=design_for(P,opts,target_se=TARGETS_REL[0]*c8,T=T);shape=stratum_shape(P,T);rows,flags=tail_table(P)
    strata={st:{**{k:v for k,v in base['S'][st].items()},**shape[st]}for st in strata_names()}
    alpha=nested_alpha(P,nested,T,graph_table(nested,impute))if nested else{st:dict(alpha=None)for st in strata_names()}
    for st in strata:strata[st]['alpha']=alpha[st]['alpha']
    return dict(schema=schemas(P.meta.get('schema_prefix',OWN_PREFIX))['report'],pilot=P.meta,c8_magnitude=c8,variance_margin=opts.margin,eta_node=P.eta_node,
                eta_source=P.eta_source,numerics=recost['record']['profile']if recost else P.meta.get('numerics','exact'),
                profile_recost=recost['record']if recost else None,targets=table,extra=extra,strata=strata,
                alpha_note=None if nested else 'no nested pilot: alpha = 0.5 assumed (Monte Carlo scaling) for every stratum',
                nested=dict(campaign=nested.meta.get('campaign'),manifest_sha256=nested.meta.get('manifest_sha256'),identity_checked=list(NESTED_IDENTITY),
                            rule=ALPHA_RULE,strata=alpha)if nested else None,
                sector_P8=sector_p8(P,T),tails=dict(rule=dict(hill_k=HILL_K,xi_screen=XI_SCREEN,share_screen=SMAX_SCREEN,xi_confirm_two_campaign_mean=XI_CONFIRM_MEAN,
                                                             confirm_points=CONFIRM_POINTS,thresholds_apply_to='L8 only; L <= 7 statistics are diagnostics',
                                                             source='C63d: LRI_C8_D3_HPC_loop/PLAN.md C.3 and E.6, RECON.md 6.3.6, recon/cost_d3/tail_calib.py'),
                                                    screened=flags['screened'],confirmed=flags['confirmed'],undefined=flags['undefined'],
                                                    diagnostics_L_le_7=flags['diagnostics'],graph_campaigns=len(rows),
                                                    graph_campaigns_L8=sum(1 for x in rows if x['L']==8)),
                bundle=bundle_prediction(P,B,bundle_projection)if B else None,_tail_rows=rows)

def print_report(r:dict)->None:
    print(f'design report: pilot {r["pilot"].get("campaign")}; |C8| = {r["c8_magnitude"]:g}; margin x{r["variance_margin"]}; eta_node {r["eta_node"]:.3f} ({r["eta_source"]})')
    if r.get('profile_recost'):
        x=r['profile_recost'];print(f'numerics {x["profile"]} (route (b)): costs from the cost model {x["cost_model"]["sha256"][:12]} measured under {x["profile"]}; '
                                    f'sigma from the exact pilot; a freeze needs --approved-numerics-change and --numerics-gate')
    print(f'{"target rel":>10} {"target SE":>10} {"pred SE":>10} {"core-h":>12} {"batches":>7}')
    for t in r['targets']+r['extra']:
        if 'error'in t:print(f'{t.get("target_rel","-"):>10} {t.get("target_se",t.get("budget_core_hours","-")):>10}  {t["error"]}');continue
        print(f'{t.get("target_rel","-"):>10} {t.get("target_se","-"):>10} {t["predicted_se_with_margin"]:>10.4g} {t["allocated_core_hours"]:>12.1f} {t["batches"]:>7}'
              +(f'  route (b): {t["route_b_chosen"]}'if t.get('route_b_chosen')else''))
    if r['alpha_note']:print('note: '+r['alpha_note'])
    for st,x in r['strata'].items():
        if x['graphs']:print(f'  {st:18s} graphs {x["graphs"]:6d} piloted {x["piloted"]:6d} sd/rep {math.sqrt(x["V1"]):.4g} kurt {x["kurtosis"]} skew {x["skewness"]} max|z| {x["max_abs_z"]} share {x["largest_share"]} P8 {x["P8"]}{" FLAG"if x["P8_flag"]else""} alpha {x["alpha"]}')
    for sec,x in r['sector_P8'].items():print(f'  sector {sec}: P8 {x["P8"]} over {x["blocks"]} blocks of {x["graph_campaigns"]} L8 graph-campaigns at {SCREEN_POINTS} points'
                                              +(' -> R = 16 advised'if x['R16_advised']else''))
    t=r['tails'];print(f'tails: thresholds on L8 only; {len(t["screened"])} L8 graphs screened (xi > {XI_SCREEN} or share > {SMAX_SCREEN}), '
                       f'{len(t["confirmed"])} confirmed "possible infinite variance", {len(t["undefined"])} undefined')
    for x in t['confirmed'][:20]:print(f'  CONFIRMED {x["sector"]} L{x["L"]} graph {x["graph"]}: two-campaign mean xi {x["xi_mean"]:.3f} at {x["points"]} points')
    for x in t['undefined'][:20]:print(f'  UNDEFINED {x["sector"]} L{x["L"]} graph {x["graph"]}: '+'; '.join(f'{c}: {v}'for c,v in x['status'].items()))
    for k,x in t['diagnostics_L_le_7'].items():
        print(f'  diagnostic {k}: {x["graph_campaigns"]} graph-campaigns ({x["undefined"]} undefined), xi median {x["xi_hat_median"]} max {x["xi_hat_max"]}, '
              f'largest share max {x["largest_share_max"]}')
    if r['bundle']:
        b=r['bundle'];f=b['frozen_settings']
        print(f'bundle {b["bundle"]}: predicted SE {b["se_total"]:.6g} (raw {b["se_raw_total"]:.6g}) over {b["batches"]} batches at its frozen margin x{f["variance_margin"]} '
              f'and imputation {f["impute"]}; frozen {b["frozen_prediction"].get("se_total")!r}: '+('recomputed, agrees'if b['agrees']else f'DOES NOT AGREE ({b["kind"]})'))
        if b['projection']:x=b['projection'];print(f'  PROJECTION (not the frozen prediction) at margin x{x["variance_margin"]}, imputation {x["impute"]}: SE {x["se_total"]:.6g} (raw {x["se_raw_total"]:.6g})')

# ---------------------------------------------------------------- efficiencies (eta_node from the ledger)
def eta_node(run:Path,test_only:bool,override:float|None,schema_prefix:str=OWN_PREFIX)->tuple[float,str]:
    """eta_node of the pilot from tools/accounting.py over its <schema_prefix>-ledger-1 ledger (O11). The campaign and
    every ledger record must be of the prefix on every path (also a test-only override or a local pilot).
    Y9 (Stage-6 fix round 2, S6D-R2-01): an assumed efficiency (1.0, or --eta-node) is for test-only designs only. A
    production design needs complete accounting evidence: every checkpoint of the merged pilot present (a merge needs
    them all, so a missing one was removed afterwards and the Slurm ids of its work can no longer be checked against
    the ledger: accounting.missing_checkpoints), every checkpoint with a Slurm id, and complete accounting (which itself
    reports removed checkpoints as incomplete, so a test-only design with Slurm evidence refuses them too)."""
    import accounting,ledger
    run=Path(run).resolve();m=ledger.check_campaign(run,schema_prefix);ledger.read(run,schema_prefix)
    ids,with_id,local=accounting.checkpoint_ids(run,m)
    if override is not None:
        if not test_only:raise ValueError('--eta-node is for --test-only freezes; a production design takes eta_node from tools/accounting.py')
        return override,'--eta-node (test-only)'
    if not test_only:
        gone=accounting.missing_checkpoints(run,m)
        if gone:raise ValueError(f'{len(gone)} checkpoint(s) of the merged pilot are missing ({gone[0]}{", ..."if len(gone)>1 else""}): a production design takes '
                                 'eta_node from complete accounting evidence, and the Slurm ids of the work they record can no longer be checked against '
                                 'the ledger; restore them (Y9). Only a --test-only design may assume an efficiency')
    if local and not test_only:raise ValueError(f'{local} pilot checkpoints carry no Slurm id (unaccounted local work): only a --test-only freeze accepts them')
    if not with_id:
        if not test_only:raise ValueError('no pilot checkpoint carries a Slurm id: a production design takes eta_node from tools/accounting.py, never an '
                                          'assumed efficiency (Y9)')
        return 1.0,'assumed 1.0 (no Slurm accounting: test-only design)'
    try:acc=accounting.account(run,prefix=schema_prefix)
    except accounting.AllocationUnknown as e:raise ValueError(str(e))
    # O06: incomplete accounting (a ledger job, array element or recorded attempt without its sacct record, or an sacct
    # line that does not parse) makes eta_node unavailable; it is never computed from the records that did come back.
    if not acc['complete']:raise ValueError(f'eta_node unavailable: {acc["eta_node_unavailable"]}; nothing designed (rerun when sacct reports every '
                                            'allocation, or register the missing ones)')
    if acc['eta_node']is None:raise ValueError('accounting reports no allocated work core-seconds for the pilot')
    raw=acc['eta_node']
    # Complete accounting with eta_node > 1 (busy thread-seconds above the allocated physical core-seconds: SMT threads
    # counted on half as many cores) is capped at 1, which can only raise the allocated cost (conservative).
    return min(1.0,raw),f'tools/accounting.py ({acc["work_core_hours"]:.3f} work core-h, {acc["sacct_records"]} sacct records, complete'+\
           (f'; measured {raw:.4f} capped at 1'if raw>1 else'')+')'

# ---------------------------------------------------------------- freeze and rates (publication)
def _publish_bundle(out:Path,files:dict)->None:
    out=Path(out).resolve()
    if out.exists():raise FileExistsError(f'{out} exists: a design bundle is never overwritten')
    stage=out.with_name(out.name+f'.staging.{os.getpid()}')
    if stage.exists():shutil.rmtree(stage)
    try:
        for rel,data in files.items():p=stage/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        os.rename(stage,out)
    except BaseException:shutil.rmtree(stage,ignore_errors=True);raise

def seeds_from_log(path:Path|None)->list[int]:
    import production as prod
    p=path or (Path(os.environ['C8_SEEDS'])if os.environ.get('C8_SEEDS')else None)
    return sorted(prod.read_seed_file(p))if p and Path(p).exists()else[]

# ---------------------------------------------------------------- route (b): an approved profile for an exact pilot
GATE_SCHEMA='c8-d2-numerics-flags-1'
ROUTE_B_RULE=('route (b) (host decision 2026-10-05): an approved numerics profile (production.APPROVED_PROFILES) for a bundle '
              'frozen from an EXACT default-rate pilot. sigma_g^2 is the exact pilot\'s, kept because the profile\'s J-FLAG F2 '
              'gate bounds its change of C8 (|dC8| + 3 SE_d) far below any target SE (dd+mp256: 4.25e-16, job 570210); every '
              'graph\'s cost per point is the cost model\'s, measured under the profile (tools/sweep.py --numerics), so the '
              'base counts, the multipliers, the allocated cost and the caps are re-costed; eta_omp,g and eta_node are the '
              'exact pilot\'s (tasks are sized to the same seconds under either numerics); F13: the exact path\'s design '
              're-costed under the profile is designed too and kept when strictly cheaper and feasible (ROUTE_B_KEEP, '
              'route_b_choice)')
SHA256=re.compile(r'[0-9a-f]{64}')
# The F1 coverage a gate record must carry (X1; tests/numerics_flags.py F1_SAMPLE and F1_NEED, test_numerics_flags.py
# checks the two agree): per L, (graphs = heaviest + random, minimum points per graph); per sector, the exact path's
# binary128-accepted and MP-promoted points.
GATE_F1_SAMPLE={'7':(200,256),'8':(400,64)};GATE_F1_NEED=(10_000,1_000)
BINDING_SCHEMA='c8-d2-build-binding-1'

def _count(x)->bool:return isinstance(x,int)and not isinstance(x,bool)

def gate_f1_coverage(rec:dict)->list[str]:
    """X1: why the gate record's F1 coverage (F1.coverage, tests/numerics_flags.py f1_coverage) is not the full A-RPL-5
    coverage: complete, scale 1, the profile pass checked, both sectors, per sector need_met with at least GATE_F1_NEED
    binary128-accepted and MP points, per (sector, L) the prescribed graphs and at least the prescribed points per graph,
    and the profile's points equal to the baseline's = graphs x points per graph. Empty when it is."""
    cov=(rec.get('F1')or{}).get('coverage')if isinstance(rec.get('F1'),dict)else None
    if not isinstance(cov,dict):return ['no F1 coverage record (F1.coverage: sectors, loops, graphs, points and promotion counts, X1)']
    out=[]
    if cov.get('complete')is not True:out.append(f'F1 coverage incomplete ({" | ".join(map(str,(cov.get("why")or[])[:2]))or"complete is not true"})')
    if cov.get('scale')!=1 or cov.get('profile_checked')is not True:out.append(f'F1 coverage at scale {cov.get("scale")!r}, profile pass checked {cov.get("profile_checked")!r}')
    sec=cov.get('sectors')if isinstance(cov.get('sectors'),dict)else{}
    if set(sec)!=set(SECTORS):out.append(f'F1 covered the sectors {sorted(sec)}, not free and power')
    for s in SECTORS:
        x=sec.get(s)if isinstance(sec.get(s),dict)else{};q,m=x.get('binary128_accepted'),x.get('mp_promoted')
        if x.get('need_met')is not True or not _count(q)or not _count(m)or q<GATE_F1_NEED[0]or m<GATE_F1_NEED[1]:
            out.append(f'F1 {s}: {q!r} binary128-accepted and {m!r} MP points (need_met {x.get("need_met")!r}), not the need {GATE_F1_NEED[0]} and {GATE_F1_NEED[1]}')
        byL=x.get('by_L')if isinstance(x.get('by_L'),dict)else{}
        for L,(g,n)in GATE_F1_SAMPLE.items():
            y=byL.get(L)if isinstance(byL.get(L),dict)else{};ppg,pb,pp=y.get('points_per_graph'),y.get('points_baseline'),y.get('points_profile')
            if y.get('graphs')!=g or not _count(ppg)or ppg<n or pb!=g*ppg or pp!=pb:
                out.append(f'F1 {s} L{L}: {y.get("graphs")!r} graphs x {ppg!r} points (baseline {pb!r}, profile {pp!r}), not {g} graphs x >= {n} with every point evaluated')
    return out

def gate_binding(rec:dict)->list[str]:
    """X2: why the gate record does not bind its F1 tools to the gated executables (build_binding, tests/numerics_flags.py
    bind): the exact and the profile executable each rebuilt byte for byte from one source snapshot, the profile's F1 tool
    compiled from that snapshot, and the baseline's exact tool bound to the gated exact executable and compiled from the
    same snapshot (a reused --f1-baseline of other sources is refused). Empty when it does."""
    b=rec.get('build_binding')if isinstance(rec.get('build_binding'),dict)else{}
    if b.get('schema')!=BINDING_SCHEMA:return [f'no build binding (build_binding {BINDING_SCHEMA}: the executables reproduced from the source snapshot the F1 tools were compiled from, X2)']
    out=[];snap=(b.get('snapshot')or{}).get('sha256')if isinstance(b.get('snapshot'),dict)else None
    if not SHA256.fullmatch(str(snap or'')):out.append('the build binding names no source snapshot sha256')
    ex=b.get('executables')if isinstance(b.get('executables'),dict)else{}
    for role in ('exact','profile'):
        want=(rec.get(role)or{}).get('sha256')if isinstance(rec.get(role),dict)else None;e=ex.get(role)if isinstance(ex.get(role),dict)else{}
        if not SHA256.fullmatch(str(want or''))or e.get('reproduced')is not True or e.get('sha256')!=want or e.get('reproduced_sha256')!=want or e.get('snapshot_sha256')!=snap:
            out.append(f'the {role} executable {str(want)[:12]} is not reproduced byte for byte from the source snapshot')
    f1=rec.get('F1')if isinstance(rec.get('F1'),dict)else{}
    if f1.get('tool_snapshot_sha256')!=snap:out.append('the F1 tool of the profile was not compiled from the binding\'s source snapshot')
    bb=f1.get('baseline_binding')if isinstance(f1.get('baseline_binding'),dict)else{}
    if bb.get('reproduced')is not True or bb.get('sha256')!=(rec.get('exact')or{}).get('sha256'):out.append('the F1 baseline\'s exact tool is not bound to the gated exact executable')
    elif bb.get('snapshot_sha256')!=snap:out.append('the F1 baseline\'s exact tool was compiled from another source snapshot than the binding\'s (a reused baseline)')
    return out

def gate_gmp_library(rec:dict)->list[str]:
    """Z19 downstream (S6H3-01; fix round 3 integration): why the gate record does not show that both F1 tools ran with
    the libgmp of the executable they stand for. Each build record names its libgmp (build_record.gmp_library.sha256,
    Y1); the profile's F1 tool (F1.tool_gmp_library) and the baseline's exact tool (f1_baseline.tool_gmp_library, copied
    from baseline.json) must each say match, with want, tool and worker_now all that sha256; f1_baseline.reused must say
    whether the baseline was reused, and a reused baseline needs the reuse check of the exact executable as it resolves
    its library now (f1_baseline.reused_gmp_library, match, want and exact_now that sha256). A record made before fix
    round 3 (e.g. job 570373's) lacks these and is refused. Empty when complete."""
    d=lambda x:x if isinstance(x,dict)else{}
    def want(role):return d(d(d(rec.get(role)).get('build_record')).get('gmp_library')).get('sha256')
    def matched(t,w):
        t=d(t);return bool(SHA256.fullmatch(str(w or'')))and t.get('match')is True and t.get('want_sha256')==w and d(t.get('tool')).get('sha256')==w \
            and d(t.get('worker_now')).get('sha256')==w
    out=[];we,wp=want('exact'),want('profile')
    for role,w in (('exact',we),('profile',wp)):
        if not SHA256.fullmatch(str(w or'')):out.append(f'the {role} executable\'s build record names no libgmp sha256 (build_record.gmp_library, Y1)')
    if not matched(d(rec.get('F1')).get('tool_gmp_library'),wp):
        out.append('the profile\'s F1 tool is not shown to run with the profile executable\'s recorded libgmp (F1.tool_gmp_library, Y1)')
    fb=d(rec.get('f1_baseline'))
    if not matched(fb.get('tool_gmp_library'),we):
        out.append('the F1 baseline\'s exact tool is not shown to run with the exact executable\'s recorded libgmp (f1_baseline.tool_gmp_library, Z19)')
    if fb.get('reused')not in (True,False):out.append('f1_baseline does not say whether the baseline was reused (f1_baseline.reused, Z19)')
    elif fb.get('reused'):
        r=d(fb.get('reused_gmp_library'))
        if not (SHA256.fullmatch(str(we or''))and r.get('match')is True and r.get('want_sha256')==we and d(r.get('exact_now')).get('sha256')==we):
            out.append('the reused F1 baseline\'s libgmp is not checked against the exact executable as it resolves it now (f1_baseline.reused_gmp_library, Z19)')
    return out

INPUTS_SCHEMA='c8-d2-gate-inputs-1'  # tests/numerics_flags.py input_identity (W18)
def package_inputs_manifest_sha256()->str:
    """The sha256 of the package's own inputs/manifest.json: the inputs of every non-test plan (production.plan refuses
    another folder for one), so the expected input identity of a gate when the caller names none (W18)."""
    return digest(ROOT/'inputs/manifest.json')

def gate_inputs(rec:dict,want:str)->list[str]:
    """W18 (Stage-6 fix round 4, S6H4-01): why the gate record does not show that it ran on the input set `want` (an
    inputs manifest sha256: the pilot's for a freeze, the plan's for production): its inputs block (numerics_flags.py
    input_identity) must be of schema INPUTS_SCHEMA, verified at the start and again at the end of the run
    (verified_at_end), complete (every pack present, none skipped), and name want as its manifest_sha256; the F1
    baseline it used must have been made from the same manifest (f1_baseline.inputs_manifest_sha256). A record made
    before fix round 4 (e.g. jobs 570210, 570373, 570536) has none of this and is refused. Empty when it does."""
    d=lambda x:x if isinstance(x,dict)else{}
    x=d(rec.get('inputs'))
    if x.get('schema')!=INPUTS_SCHEMA or not SHA256.fullmatch(str(x.get('manifest_sha256')or'')):
        return [f'no authenticated input-set identity (inputs: {INPUTS_SCHEMA} with the inputs manifest sha256 the gate ran on, W18)']
    out=[];got=x['manifest_sha256']
    if x.get('verified')is not True or x.get('verified_at_end')is not True:
        out.append(f'the gate\'s inputs were not verified at the start and at the end of the run (verified {x.get("verified")!r}, at the end {x.get("verified_at_end")!r})')
    if x.get('complete')is not True or x.get('skipped'):out.append(f'the gate ran on an incomplete input set (skipped {x.get("skipped")!r})')
    if got!=want:out.append(f'the gate ran on inputs manifest {got[:12]}..., not {str(want)[:12]}... (the pilot\'s or the plan\'s): its F1 and F2 '
                            'measurements need not describe these kernels; re-run the gate on these inputs')
    fb=d(rec.get('f1_baseline'))
    if fb.get('inputs_manifest_sha256')!=got:
        out.append(f'the F1 baseline was made from inputs manifest {str(fb.get("inputs_manifest_sha256"))[:12]}..., not the gate\'s {got[:12]}...')
    return out

def check_gate(path:Path,profile:str,inv:dict,inputs_manifest_sha256:str|None=None)->dict:
    """A passed, full-scale J-FLAG gate record (tests/numerics_flags.py --profile P, schema c8-d2-numerics-flags-1) of
    P's production build: status passed, no development option, F1, F2 and F5 passed, F2's total gate passed and
    resolved, the profile build not a development build (no parameter override), F2 over at least every inventory graph
    of each (campaign, sector, L). Stage-6 fix round 1 adds, as evidence the record must carry: X1 the full F1 coverage
    (gate_f1_coverage), X2 the build binding of the F1 tools to both executables (gate_binding) and X3 the F5 OpenMP team
    sizes observed equal to the requested ones (F5.team_sizes_verified). A record without them (any record made before
    the fix round, e.g. job 570210's) is refused. Fix round 3 (Z19 downstream) adds the libgmp provenance of both F1
    tools (gate_gmp_library), so job 570373's record is refused too. Fix round 4 (W18) adds the authenticated input set
    (gate_inputs): the gate must have run on inputs_manifest_sha256, the pilot's (freeze) or the plan's (production;
    None: the package's own inputs/manifest.json, which every non-test plan uses), so job 570536's record is refused.
    Returns what the bundle records (path, sha256, the Slurm job of its evidence folder when the path names one, the
    gated profile and exact executables, host, CPU, compiler, F2 totals, the F1 coverage counts, the source snapshot,
    the libgmp sha256 of both executables, the inputs manifest sha256 the gate ran on)."""
    path=Path(path);data=path.read_bytes()
    try:rec=json.loads(data)
    except ValueError as e:raise ValueError(f'--numerics-gate {path} is not JSON: {e}')
    why=[]
    if not isinstance(rec,dict):rec={}
    if rec.get('schema')!=GATE_SCHEMA:why.append(f'schema {rec.get("schema")!r}, not {GATE_SCHEMA}')
    if rec.get('mode')!='profile'or rec.get('profile_name')!=profile:why.append(f'a gate of profile {rec.get("profile_name")!r} (mode {rec.get("mode")!r})')
    if rec.get('status')!='passed':why.append(f'status {rec.get("status")!r}')
    if rec.get('development'):why.append(f'development options {rec.get("development")}')
    v=rec.get('verdicts')or{}
    for part in ('F1','F2','F5'):
        if v.get(part)is not True:why.append(f'{part} not passed ({v.get(part)!r})')
    f2=rec.get('F2')or{};tot=f2.get('total')or{}
    if tot.get('passed')is not True or tot.get('resolved')is not True:why.append('the F2 total gate is not passed and resolved')
    pr=rec.get('profile')or{};br=pr.get('build_record')or{}
    if (pr.get('describe')or{}).get('numerics')!=profile:why.append(f'the profile executable describes numerics {(pr.get("describe")or{}).get("numerics")!r}')
    if br.get('development')or br.get('parameter_overrides'):why.append('the profile executable is a development build (parameter overrides or development)')
    if not SHA256.fullmatch(str(pr.get('sha256')or'')):why.append('no profile executable sha256')
    graphs=f2.get('graphs')or{}
    short=[f'{c}_{s}_L{L}'for c in CAMPAIGNS for s in SECTORS for L in LOOPS if int(graphs.get(f'{c}_{s}_L{L}')or 0)<len(inv[s][str(L)])]
    if short:why.append(f'F2 covered fewer graphs than the inventory in {len(short)} groups ({short[0]}, ...): not a full-scale gate')
    want=inputs_manifest_sha256 or package_inputs_manifest_sha256()
    why+=gate_f1_coverage(rec)+gate_binding(rec)+gate_gmp_library(rec)+gate_inputs(rec,want)
    if (rec.get('F5')if isinstance(rec.get('F5'),dict)else{}).get('team_sizes_verified')is not True:
        why.append('F5 records no verified OpenMP team sizes (every run and lane observed at its requested team, X3)')
    if why:raise ValueError(f'--numerics-gate {path}: not a passed full-scale J-FLAG gate of the production build of {profile}: '+'; '.join(why))
    job=re.search(r'\.(\d+)\.\d+$',path.resolve().parent.parent.name)or re.search(r'\.(\d+)\.\d+$',path.resolve().parent.name)
    env=rec.get('environment')or{}
    return dict(path=str(path.resolve()),sha256=hashlib.sha256(data).hexdigest(),slurm_job=job.group(1)if job else None,profile=profile,
                profile_executable_sha256=pr['sha256'],exact_executable_sha256=(rec.get('exact')or{}).get('sha256'),host=env.get('host'),
                cpu_model=env.get('cpu_model'),compiler=(pr.get('describe')or{}).get('compiler'),utc_start=rec.get('utc_start'),
                F2_total={k:tot.get(k)for k in ('dC8','se','bound','passed')},F1_violations=((rec.get('F1')or{}).get('verdict')or{}).get('violations'),
                F1_coverage={s:{k:x.get(k)for k in ('binary128_accepted','mp_promoted')}for s,x in rec['F1']['coverage']['sectors'].items()},
                source_snapshot_sha256=rec['build_binding']['snapshot']['sha256'],F5_team_sizes_verified=True,
                gmp_library={'exact':rec['exact']['build_record']['gmp_library']['sha256'],'profile':pr['build_record']['gmp_library']['sha256'],
                             'f1_baseline_reused':rec['f1_baseline']['reused']},
                inputs_manifest_sha256=rec['inputs']['manifest_sha256'])  # W18: preserved in the bundle's gate entries

def profile_recost(P:Pilot,a,freezing:bool=True)->dict|None:
    """Route (b), validated before anything is designed: None on the exact path (--numerics exact, the default; the
    route-(b) options are then refused). Otherwise {'costs': {(c, s, L, graph): seconds per point}, 'record': ...}.
    Refused: a profile outside the user-approved set production.APPROVED_PROFILES; a prefix other than c8-d2 (the
    allow-list is C8(2)'s); a pilot under a profile or a rate map (route (b) re-costs an EXACT default-rate pilot); a
    cost model of another numerics identity, backend or rates identity, or one missing an inventory graph; and, for a
    freeze, no --approved-numerics-change or no passed full-scale --numerics-gate record. report (freezing=False) takes
    --numerics and --cost-model only."""
    import production as prod
    prof=getattr(a,'numerics',None)or'exact'
    opts={'--cost-model':getattr(a,'cost_model',None),'--numerics-gate':getattr(a,'numerics_gate',None),
          '--approved-numerics-change':getattr(a,'approved_numerics_change',None)}
    if prof=='exact':
        extra=[k for k,v in opts.items()if v]
        if extra:raise ValueError(f'{", ".join(extra)} belong(s) to --numerics <approved profile> (route (b)); the exact path is costed from the pilot itself')
        return None
    if prof not in prod.APPROVED_PROFILES:
        raise ValueError(f'--numerics {prof!r} is not in the user-approved set {sorted(prod.APPROVED_PROFILES)} (route (b) allow-list, '
                         'production.APPROVED_PROFILES); every other profile is refused')
    if not freezing and (opts['--numerics-gate']or opts['--approved-numerics-change']):
        raise ValueError('report takes --numerics and --cost-model only; the approval and the gate record belong to freeze')
    if a.schema_prefix!=OWN_PREFIX:raise ValueError(f'route (b) is approved for {OWN_PREFIX} only (production.APPROVED_PROFILES); this is a {a.schema_prefix} pilot')
    if freezing and not (opts['--approved-numerics-change']or'').strip():
        raise ValueError(f'--numerics {prof} is a numerics change: it needs --approved-numerics-change "<user approval reference>" (D1, A-FLAG-2)')
    pm=P.meta
    if pm.get('numerics','exact')!='exact':
        raise ValueError(f'route (b) re-costs a bundle frozen from an EXACT pilot; {pm.get("campaign")} ran under numerics {pm.get("numerics")!r} '
                         '(a pilot measured under a profile is frozen without --numerics: route (a))')
    if pm.get('rates_identity','default')!='default'or getattr(a,'rates_bundle',None):
        raise ValueError('route (b) takes a default-rate pilot: an approved profile is not combined with a rate map (R7, not approved)')
    if not opts['--cost-model']:raise ValueError(f'--numerics {prof} needs --cost-model: a cost model measured under {prof} '
                                                 f'(tools/sweep.py --numerics {prof} --approved-numerics-change ...)')
    cb=Path(opts['--cost-model']).read_bytes()
    cm=prod.load_cost_model(opts['--cost-model'],pm['backend'],pm.get('rates_identity','default'),False,cb)
    if cm.get('numerics')!=prof:
        raise ValueError(f'the cost model {opts["--cost-model"]} was measured under numerics {cm.get("numerics")!r}, not {prof!r}: route (b) re-costs with a '
                         'cost model measured under the profile (its numerics identity must equal the profile)')
    spp=cm['seconds_per_point'];costs={};missing=[]
    for (c,s,L) in sorted(P.groups):
        for r in P.inventory[s][str(L)]:
            k=f'{c}:{s}:{L}:{r["id"]}'
            if k in spp:costs[(c,s,L,r['id'])]=float(spp[k])
            else:missing.append(k)
    if missing:raise ValueError(f'the cost model {opts["--cost-model"]} has no key {missing[0]} ({len(missing)} inventory graphs missing): a route-(b) '
                                'cost model covers every graph of both campaigns (tools/sweep.py measures all of them)')
    gates=[]
    if freezing:
        if not opts['--numerics-gate']:raise ValueError(f'--numerics {prof} needs --numerics-gate RECORD: the passed full-scale J-FLAG gate '
                                                        f'(tests/numerics_flags.py --profile {prof}) of the production build')
        gates=[check_gate(g,prof,P.inventory,pm['inputs_manifest_sha256'])for g in opts['--numerics-gate']]  # W18: the pilot's inputs
        if len({g['sha256']for g in gates})!=len(gates):raise ValueError('--numerics-gate names one record twice')
    gx={g['profile_executable_sha256']for g in gates}
    if freezing and cm.get('executable_sha256')not in gx:
        raise ValueError(f'the cost model {opts["--cost-model"]} was measured with the executable {cm.get("executable_sha256")!r}, which none of the --numerics-gate '
                         f'records passed ({", ".join(sorted(x[:12] for x in gx))}): a route-(b) freeze re-costs with a cost model of a gated {prof} build '
                         f'(measure it with that build, or gate the build it was measured with)')
    rec=dict(route='b',rule=ROUTE_B_RULE,profile=prof,approval=(opts['--approved-numerics-change']or'').strip()or None,
             approved_set=sorted(prod.APPROVED_PROFILES),approved_set_reference=prod.APPROVED_PROFILES[prof],gates=gates,
             exact_pilot={k:pm.get(k)for k in ('campaign','manifest_sha256','seed','executable_sha256','numerics','rates_identity','inputs_manifest_sha256',
                                                'backend','test_only')},
             cost_model=dict(path=str(Path(opts['--cost-model']).resolve()),sha256=hashlib.sha256(cb).hexdigest(),numerics=cm['numerics'],backend=cm['backend'],
                             rates_identity=cm['rates_identity'],executable_sha256=cm.get('executable_sha256'),cpu_models=cm.get('cpu_models'),
                             source_manifest_sha256=cm.get('source_manifest_sha256'),keys=cm.get('keys'),
                             executable_gated=(cm.get('executable_sha256')in gx)if gates else None),
             variance='sigma_g^2 of the exact pilot (unchanged; the gate F2 bounds the profile change of C8)',
             efficiencies='eta_omp,g and eta_node of the exact pilot')
    return dict(costs=costs,record=rec)

def freeze(a)->dict:
    """design.py freeze from a merged pilot campaign: the allocation options (Y10), rates identity (R14), eta_node from the
    ledger, then freeze_core."""
    check_options(a,bool(a.test_only))
    P=load_pilot(a.pilot,a.two_loop,a.half_d,a.inventory,a.selection,a.dimension,a.schema_prefix)
    if P.meta['test_only']and not a.test_only:raise ValueError(f'{a.pilot} is a test-only campaign: only a --test-only bundle may be frozen from it')
    prov=None
    if a.rates_bundle:
        RB=read_bundle(a.rates_bundle,a.schema_prefix,allow_provisional=True);pm=RB['meta']  # Z9's class: the bytes whose sha256 is recorded
        if not RB['provisional']:raise ValueError('--rates-bundle must be a provisional bundle of design.py rates')
        if P.meta['rates_identity']!=pm['rates_identity']:raise ValueError(f'the pilot was measured under rates identity {P.meta["rates_identity"]!r}, the provisional map is {pm["rates_identity"]}: '
                                                                           'freeze --rates-bundle needs a measurement campaign under that map (R14)')
        prov={'path':str(Path(a.rates_bundle).resolve()),'meta_sha256':RB['meta_sha256'],'rates_identity':pm['rates_identity']}
    elif P.meta['rates_identity']!='default':raise ValueError('a pilot measured under a frozen rate map is frozen with --rates-bundle (the provisional bundle of that map)')
    P.eta_node,P.eta_source=eta_node(a.pilot,a.test_only,a.eta_node,a.schema_prefix)
    return freeze_core(P,a,prov)

# ---------------------------------------------------------------- Y10: allocation options and the designed allocation
PROD_MIN_REPLICATES=32;PROD_MAX_REPLICATES=128;PROD_MIN_POINTS=4096;TEST_MIN_REPLICATES=2
def _int(x)->bool:return isinstance(x,int)and not isinstance(x,bool)
def _real(x)->bool:return isinstance(x,(int,float))and not isinstance(x,bool)and math.isfinite(x)

def check_options(a,test_only:bool)->None:
    """Y10 (Stage-6 fix round 2, S6D-R2-02): the allocation options, validated before anything is designed or published
    (ValueError naming every problem). Production (not test-only), the plan's bounds (PLAN component E, A-DES-1):
    --min-replicates a power of two >= 32, --max-replicates a power of two <= 128 and >= --min-replicates, so every r is
    a power of two in [32, 128]; --min-points a power of two >= 4096; --variance-margin >= 1. A test-only bundle (accepted
    only by test-only plans) may reduce them: replicates powers of two in [2, 128] (assemble needs two rows per group,
    and production.plan never accepts fewer than two), --min-points a power of two, a margin > 0. Always: --threads,
    --min-chunk (a power of two, as production.plan), --max-tasks and --max-checkpoints positive integers;
    --checkpoint-tasks in [1, 100000] and >= --threads (production.plan's rules); --task-seconds, --max-task-seconds,
    --index-hours and --c8-magnitude finite and positive; --target-rel, --target-se, --budget-core-hours and
    --total-cap finite and positive when given; --spent-core-hours finite and >= 0; --batches >= 1; --eta-node in (0, 1]."""
    why=[];g=lambda k:getattr(a,k,None)
    lo,hi,mp=g('min_replicates'),g('max_replicates'),g('min_points')
    rlo=TEST_MIN_REPLICATES if test_only else PROD_MIN_REPLICATES;plo=1 if test_only else PROD_MIN_POINTS
    what='a test-only bundle'if test_only else'a production bundle (the plan\'s bounds; reduced bounds only with --test-only)'
    if not(_int(lo)and pow2(lo)and lo>=rlo):why.append(f'--min-replicates {lo!r}: {what} needs a power of two >= {rlo}')
    if not(_int(hi)and pow2(hi)and hi<=PROD_MAX_REPLICATES):why.append(f'--max-replicates {hi!r}: a power of two <= {PROD_MAX_REPLICATES}')
    elif _int(lo)and hi<lo:why.append(f'--max-replicates {hi} < --min-replicates {lo}')
    if not(_int(mp)and pow2(mp)and mp>=plo):why.append(f'--min-points {mp!r}: {what} needs a power of two >= {plo}')
    m=g('variance_margin')
    if not(_real(m)and(m>0 if test_only else m>=1)):why.append(f'--variance-margin {m!r}: {"> 0" if test_only else ">= 1 (a margin below 1 would shrink the predicted SE)"}')
    for k in ('threads','max_tasks','max_checkpoints'):
        if not(_int(g(k))and g(k)>=1):why.append(f'--{k.replace("_","-")} {g(k)!r}: a positive integer')
    mc=g('min_chunk')
    if not(_int(mc)and pow2(mc)):why.append(f'--min-chunk {mc!r}: a power of two (production.plan\'s rule)')
    ck=g('checkpoint_tasks')
    if ck is not None and not(_int(ck)and 1<=ck<=100000 and(not _int(g('threads'))or ck>=g('threads'))):
        why.append(f'--checkpoint-tasks {ck!r}: an integer in [1, 100000] and >= --threads (production.plan\'s rules)')
    for k in ('task_seconds','max_task_seconds','index_hours','c8_magnitude'):
        if not(_real(g(k))and g(k)>0):why.append(f'--{k.replace("_","-")} {g(k)!r}: finite and positive')
    for k in ('target_rel','target_se','budget_core_hours','total_cap'):
        if g(k)is not None and not(_real(g(k))and g(k)>0):why.append(f'--{k.replace("_","-")} {g(k)!r}: finite and positive')
    sp=g('spent_core_hours')
    if sp is not None and not(_real(sp)and sp>=0):why.append(f'--spent-core-hours {sp!r}: finite and >= 0')
    b=g('batches')
    if b is not None and not(_int(b)and b>=1):why.append(f'--batches {b!r}: a positive integer')
    e=g('eta_node')
    if e is not None and not(_real(e)and 0<e<=1):why.append(f'--eta-node {e!r}: in (0, 1]')
    if why:raise ValueError('allocation options refused (Y10): '+'; '.join(why))

def check_allocation(d:dict,opts:Opts)->None:
    """Y10: the designed allocation, before it is published: every replicate count r a power of two in [--min-replicates,
    --max-replicates] (check_options bounded those), every sample multiplier s and base count powers of two (counts >=
    --min-points), and a batch count >= 1. A violation is a design bug; nothing is published."""
    why=[f'{k}: r = {v!r}'for k,v in sorted(d['r'].items())if not(_int(v)and pow2(v)and opts.min_reps<=v<=opts.max_reps)]
    why+=[f'{k}: s = {v!r}'for k,v in sorted(d['s'].items())if not(_int(v)and pow2(v))]
    why+=[f'{c}_{s}_L{L} graph {gid}: count {n!r}'for (c,s,L),cnt in sorted(d['b'].items())for gid,n in sorted(cnt.items())if not(_int(n)and pow2(n)and n>=opts.min_points)][:5]
    if not(_int(d['K'])and d['K']>=1):why.append(f'batches {d["K"]!r}')
    if why:raise ValueError(f'the designed allocation is outside its bounds (replicates in [{opts.min_reps}, {opts.max_reps}], powers of two; Y10): '+'; '.join(why[:8]))

def opts_from(a)->Opts:
    return Opts(a.min_points,a.min_replicates,a.max_replicates,a.variance_margin,a.task_seconds,a.min_chunk,a.max_task_seconds,a.threads,a.checkpoint_tasks,
                a.index_hours,a.max_tasks,a.max_checkpoints)

def freeze_core(P:Pilot,a,prov=None)->dict:
    """The freeze of a pilot (loaded or synthetic): route (b) validated (profile_recost), design_for, the budget gates,
    then the atomic bundle."""
    check_reuse(a.dimension,a.half_d,a.schema_prefix);DS=schemas(a.schema_prefix)['design']  # the bundle schema follows the prefix (O11)
    if P.meta.get('schema_prefix',a.schema_prefix)!=a.schema_prefix or P.meta.get('dimension',a.dimension)!=a.dimension:
        raise ValueError(f'the pilot was read as {P.meta.get("schema_prefix")} (dimension {P.meta.get("dimension")}), the freeze asks for {a.schema_prefix} (dimension {a.dimension})')
    check_options(a,bool(a.test_only))  # Y10: before anything is designed (also for an in-process freeze)
    recost=profile_recost(P,a);numerics=recost['record']['profile']if recost else P.meta['numerics']
    opts=opts_from(a)
    target=a.target_se if a.target_se else(a.target_rel*a.c8_magnitude if a.target_rel else None)
    if (target is None)==(a.budget_core_hours is None):raise ValueError('give exactly one of --target-rel, --target-se and --budget-core-hours')
    if a.budget_core_hours is not None and a.total_cap is not None and a.budget_core_hours+a.spent_core_hours>a.total_cap:
        raise ValueError(f'budget {a.budget_core_hours} + spent {a.spent_core_hours} core-h exceeds the total cap {a.total_cap}')
    try:d=(design_route_b(P,opts,target,a.budget_core_hours,a.batches,a.impute,recost['costs'])if recost else
           design_for(P,opts,target,a.budget_core_hours,a.batches,a.impute))
    except Infeasible as e:raise ValueError(f'infeasible budget: the minimum design (s = 1, r = {opts.min_reps}) costs {e.minimum:.1f} core-hours; minimum budget {math.ceil(e.minimum)} core-hours')
    except BatchesTooFew as e:raise ValueError(f'--batches {a.batches} < the minimum batch count K = {e.k} for which every batch meets the caps')
    check_allocation(d,opts)  # Y10: the designed allocation within its bounds before anything is published
    ev=d['ev']
    if a.total_cap is not None and ev['cost_total_core_hours']+a.spent_core_hours>a.total_cap:
        raise ValueError(f'the design costs {ev["cost_total_core_hours"]:.1f} core-h + spent {a.spent_core_hours} > the total cap {a.total_cap}; '
                         f'minimum {math.ceil(ev["cost_total_core_hours"]+a.spent_core_hours)} core-h of total cap for this target')
    files={}
    for (c,s,L),TT in sorted(d['T'].items()):
        files[f'counts/{c}_{s}_L{L}.txt']=''.join(f'{g} {d["b"][(c,s,L)][g]}\n'for g in sorted(TT)).encode()
    strata={st:dict(sector=st.split('_')[0],L=int(st.split('_')[1][1:]),primitive=True if st.endswith('primitive')else(False if st.startswith('free_L8')else None),
                    s=int(d['s'][st]),V1=d['S'][st]['V1'],C1=d['S'][st]['C1'],graphs=d['S'][st]['graphs'],piloted=d['S'][st]['piloted'])for st in strata_names()}
    design=dict(schema=DS,kind='design',strata=strata,replicates={k:int(v)for k,v in sorted(d['r'].items())},batches=int(d['K']),batches_minimum=int(d['K_min']),
                predicted=dict(ev,variance_margin=a.variance_margin),caps=d['caps'],eta_node=P.eta_node,eta_omp={f'{c}_{s}_L{L}':G.eta_omp for (c,s,L),G in sorted(P.groups.items())})
    files['design.json']=(json.dumps(design,indent=1,default=float)+'\n').encode()
    forb=sorted({int(P.meta['seed'])}|set(seeds_from_log(a.seeds_log)))
    meta=dict(schema=DS,kind='meta',test_only=bool(a.test_only),provisional=False,design_sha256=hashlib.sha256(files['design.json']).hexdigest(),
              counts_sha256={k:hashlib.sha256(v).hexdigest()for k,v in sorted(files.items())if k.startswith('counts/')},pilot=P.meta,
              numerics=numerics,profile_recost=recost['record']if recost else None,rates_identity=P.meta['rates_identity'],inputs_manifest_sha256=P.meta['inputs_manifest_sha256'],
              executable_sha256=P.meta['executable_sha256'],backend=P.meta['backend'],forbidden_seeds=forb,batches=int(d['K']),
              target=dict(se=target,rel=a.target_rel,c8_magnitude=a.c8_magnitude)if target else None,budget_core_hours=a.budget_core_hours,
              spent_core_hours=a.spent_core_hours,total_cap=a.total_cap,eta_node=P.eta_node,eta_node_source=P.eta_source,
              imputed=dict(variance_share=ev['imputed_variance_share'],graphs=sum(1 for TT in d['T'].values()for x in TT.values()if not x['piloted']),impute=a.impute),
              predictions=dict(ev),parameters=dict(dimension=a.dimension,schema_prefix=a.schema_prefix,half_d=a.half_d,two_loop=str(a.two_loop)if a.two_loop else None,
                                                   min_points=a.min_points,min_replicates=a.min_replicates,max_replicates=a.max_replicates,variance_margin=a.variance_margin),
              rates_bundle=prov,rule=RULE,optimizer=d['optimizer'],route_b_choice=d.get('route_b_choice'),frozen_utc=utc())
    files['design_meta.json']=(json.dumps(meta,indent=1,default=float)+'\n').encode()
    _publish_bundle(a.out,files)
    return dict(bundle=str(Path(a.out).resolve()),numerics=numerics,batches=d['K'],batches_minimum=d['K_min'],predicted_se_total=ev['se_total'],predicted_se_raw_total=ev['se_raw_total'],
                allocated_core_hours_total=ev['cost_total_core_hours'],replicates=d['r'],s=d['s'],imputed_variance_share=ev['imputed_variance_share'],eta_node=P.eta_node,
                imputed_graphs=meta['imputed']['graphs'],optimizer_kept=d['optimizer']['kept'],
                route_b_chosen=(d.get('route_b_choice')or{}).get('chosen'))

# ---------------------------------------------------------------- R7: the one-step rate rule (A-FLAG-6)
RULE_DEFAULTS={'a':'.8','b':'.9'}   # the rates a default pilot measured (production.DEFAULT_RATES)
RULE_STEP='0.1';RULE_BAND=0.10;RULE_MIN_GRAPHS=100;RULE_BOOT=1000;RULE_SEED=7082026
RULE_ONE_STEP=('one step toward the better measured rate, per (sector, L): W_c = sum_g sigma_g sqrt(c_g) of campaign c (sigma_g^2 = '
               'n_g Var_rep(J_8 . jet_g) at the pilot means, c_g = row seconds / (replicates x n_g)), the Neyman variance x cost '
               'W_c^2 of the stratum at its optimal allocation; r = W_b^2 / W_a^2 (.9 over .8); fewer than min_graphs graphs, or '
               '1 - band <= r <= 1 / (1 - band): keep a .8, b .9; r < 1 - band (.9 better): step up, a .9, b 1; r > 1 / (1 - band) '
               '(.8 better): step down, a .7, b .8; a and b stay one step apart, so they differ for every graph')

def _rate_text(x)->str:
    from decimal import Decimal
    s=format(Decimal(x).normalize(),'f');return s[1:]if s.startswith('0.')else s

def one_step_rule(P:Pilot,step:str=RULE_STEP,band:float=RULE_BAND,min_graphs:int=RULE_MIN_GRAPHS,boot:int=RULE_BOOT,seed:int=RULE_SEED)->tuple[dict,dict]:
    """The one-step rate rule of R7 (A-FLAG-6; scripts/r7_spec.py of benchmarks/expanse_2026-10-c8/stage4c/dev_r7 derived the
    Stage-4c map with it from J-SWEEP-1): (spec, record). spec is design.py rates' {campaign: {sector: {L: rate}}};
    record holds the rule, its parameters and its inputs per (sector, L). The pilot must have run at the default rates
    (.8 / .9): the rule compares those two measured rates."""
    from decimal import Decimal,InvalidOperation
    if P.meta.get('rates_identity','default')!='default':
        raise ValueError(f'the one-step rule compares the default rates (a .8, b .9) of a default-rate pilot; this pilot ran under rates identity '
                         f'{P.meta.get("rates_identity")!r} (give --spec, or a default-rate pilot)')
    try:st=Decimal(str(step))
    except InvalidOperation:raise ValueError(f'--step {step!r} is not a decimal')
    dflt={c:Decimal(v)for c,v in RULE_DEFAULTS.items()}
    if not (st>0 and all(Decimal(0)<dflt[c]+k*st<=Decimal(1)for c in CAMPAIGNS for k in (-1,1))):
        raise ValueError(f'--step {step}: a step from a .8, b .9 must keep every rate in (0, 1] (step <= 0.1)')
    if not 0<band<1:raise ValueError(f'--band {band} is not in (0, 1)')
    if min_graphs<1 or boot<0:raise ValueError('--min-graphs must be >= 1 and --boot >= 0')
    rng=np.random.default_rng(seed);spec={c:{s:{}for s in SECTORS}for c in CAMPAIGNS};rows=[]
    for s in SECTORS:
        for L in LOOPS:
            out={}
            for c in CAMPAIGNS:
                G=P.groups[(c,s,L)];y=np.einsum('rgj,j->rg',G.Y,P.J8[L]);n=np.array([G.points[g]for g in G.graphs],float)
                sig=np.sqrt(n*y.var(0,ddof=1))if G.reps>1 else np.zeros(len(G.graphs));cost=np.array([G.seconds.get(g,0.)for g in G.graphs])/(G.reps*n)
                out[c]=dict(graphs=list(G.graphs),sigma=sig,cost=cost,reps=G.reps,points=sorted(set(n.astype(int).tolist())))
            if out['a']['graphs']!=out['b']['graphs']:raise ValueError(f'{s} L{L}: campaigns a and b of the pilot hold different graphs')
            w={c:out[c]['sigma']*np.sqrt(out[c]['cost'])for c in CAMPAIGNS};W={c:float(w[c].sum())for c in CAMPAIGNS}
            V={c:float((out[c]['sigma']**2).sum())for c in CAMPAIGNS};C={c:float(out[c]['cost'].sum())for c in CAMPAIGNS}
            r=(W['b']/W['a'])**2 if W['a']>0 else math.inf;ng=len(out['a']['graphs']);qs=None
            if boot and ng>1:
                rs=[]
                for _ in range(boot):
                    i=rng.integers(ng,size=ng);wa=w['a'][i].sum()
                    if wa>0:rs.append(float((w['b'][i].sum()/wa)**2))
                if rs:qs={k:float(np.quantile(rs,q))for k,q in (('p2.5',.025),('p16',.16),('p50',.5),('p84',.84),('p97.5',.975))}
            if ng<min_graphs:dec='keep (fewer than min_graphs graphs)';shift=Decimal(0)
            elif r<1-band:dec='step up (.9 better than .8)';shift=st
            elif r>1/(1-band):dec='step down (.8 better than .9)'+(' (W_a = 0)'if W['a']<=0 else'');shift=-st
            else:dec='keep (within the band)';shift=Decimal(0)
            ra,rb=dflt['a']+shift,dflt['b']+shift
            if not (Decimal(0)<ra<=Decimal(1)and Decimal(0)<rb<=Decimal(1)and ra!=rb):raise ValueError(f'{s} L{L}: rates {ra}, {rb} out of (0, 1] or equal')
            spec['a'][s][str(L)]=_rate_text(ra);spec['b'][s][str(L)]=_rate_text(rb)
            fin=lambda x:x if math.isfinite(x)else None
            rows.append(dict(sector=s,L=L,graphs=ng,replicates=out['a']['reps'],points=out['a']['points'],W=W,W2={c:W[c]**2 for c in CAMPAIGNS},V=V,
                             C_seconds_per_point_sum=C,ratio_W2_b_over_a=fin(r),ratio_V_b_over_a=V['b']/V['a']if V['a']>0 else None,
                             ratio_C_b_over_a=C['b']/C['a']if C['a']>0 else None,bootstrap_ratio_W2=qs,decision=dec,rate_a=spec['a'][s][str(L)],
                             rate_b=spec['b'][s][str(L)]))
    tot={c:sum(x['W'][c]for x in rows)for c in CAMPAIGNS}
    keys=('campaign','manifest_sha256','seed','executable_sha256','numerics','rates_identity','inputs_manifest_sha256','test_only','backend','accepted_tool_changes')
    rec=dict(name='one-step',text=RULE_ONE_STEP,step=_rate_text(st),band=band,min_graphs=min_graphs,defaults=dict(RULE_DEFAULTS),
             bootstrap=dict(resamples=boot,seed=seed,use='record only; the decision uses r'),source='tools/design.py one_step_rule (from dev_r7/scripts/r7_spec.py, Stage 4c)',
             pilot={k:P.meta.get(k)for k in keys},strata=rows,neyman_total=dict(W_a=tot['a'],W_b=tot['b'],F_pilot=((tot['a']+tot['b'])/2)**2),spec=spec)
    return spec,rec

def rates(a)->dict:
    """design.py rates: a provisional bundle (rates.json + design_meta.json only; R14, R19), its schemas by the prefix;
    the rates from the one-step rule (--rule one-step) or an explicit --spec, recorded as rate_rule."""
    import production as prod
    check_reuse(a.dimension,a.half_d,a.schema_prefix);sch=schemas(a.schema_prefix)
    if (a.spec is None)==(a.rule is None):raise ValueError('give exactly one of --rule one-step (the rates chosen from the pilot) and --spec FILE')
    ropts={'--step':a.step,'--band':a.band,'--min-graphs':a.min_graphs,'--boot':a.boot}
    if a.rule is None and any(v is not None for v in ropts.values()):
        raise ValueError(f'{", ".join(k for k,v in ropts.items()if v is not None)} belong(s) to --rule one-step, not --spec')
    run=Path(a.pilot).resolve();m=load(run/'manifest.json');src=Path(a.source_bundle).resolve()
    if m.get('schema')!=sch['production']or m.get('dimension')!=a.dimension:
        raise ValueError(f'{run} is a {m.get("schema")} campaign of dimension {m.get("dimension")}, not {sch["production"]} of dimension {a.dimension}')
    SB=read_bundle(src,a.schema_prefix,allow_provisional=True);sm=SB['meta']  # Z9's class: the source bundle verified (its design and counts)
    if SB['provisional']:raise ValueError('the source bundle is itself provisional')
    changes=None
    if a.rule is not None:
        if m.get('rates_identity','default')!='default':
            raise ValueError(f'the one-step rule compares the default rates (a .8, b .9) of a default-rate pilot; {run} ran under rates identity '
                             f'{m.get("rates_identity")!r} (give --spec, or a default-rate pilot)')
        # load_pilot verifies the pilot as freeze and report do (a changed pinned tool accepted and recorded)
        P=load_pilot(run,a.two_loop,a.half_d,a.inventory,None,a.dimension,a.schema_prefix);inv=P.inventory;changes=P.meta.get('accepted_tool_changes')
        spec,rule_rec=one_step_rule(P,a.step if a.step is not None else RULE_STEP,a.band if a.band is not None else RULE_BAND,
                                    a.min_graphs if a.min_graphs is not None else RULE_MIN_GRAPHS,a.boot if a.boot is not None else RULE_BOOT)
    else:
        if a.schema_prefix==OWN_PREFIX:
            # As in load_pilot: a pinned tool changed since the pilot was planned (J-SWEEP-1 under the Stage-3 tools) does
            # not change the inputs the map is checked against; the change is recorded in design_meta.json.
            _,I,_,changes=prod.verify_base(run,check_executable=False,accept_tool_change=True);inv=load(a.inventory)if a.inventory else prod.load_inventory(I)
        else:inv,_=foreign_inputs(m,a.inventory,a.two_loop,None)
        spec=load(a.spec);rule_rec=dict(name='spec',spec_file=str(Path(a.spec).resolve()),spec_sha256=digest(a.spec),spec=spec,
                                        text='explicit --spec: the rates named by the file; every graph not named keeps its campaign default (.8 / .9)')
    table={c:{s:{}for s in SECTORS}for c in CAMPAIGNS}
    for c in CAMPAIGNS:
        for s in SECTORS:
            for L in LOOPS:
                v=((spec.get(c)or{}).get(s)or{}).get(str(L),prod.DEFAULT_RATES[c])
                if isinstance(v,dict):tab={str(r['id']):v.get(str(r['id']),prod.DEFAULT_RATES[c])for r in inv[s][str(L)]}
                else:tab={str(r['id']):v for r in inv[s][str(L)]}
                table[c][s][str(L)]=tab
    doc={'schema':sch['rates'],'inputs_manifest_sha256':m['inputs_manifest_sha256'],'rates':table,'provenance':{'rule':rule_rec['name'],'spec':str(a.spec)if a.spec else None,'pilot':str(run),'source_bundle':str(src),'derived_utc':utc()}}
    data=(json.dumps(doc,indent=1,sort_keys=True)+'\n').encode();prod.validate_rates(data,m['inputs_manifest_sha256'],inv,sch['rates'])
    sha=hashlib.sha256(data).hexdigest()
    meta=dict(schema=sch['design'],kind='meta',provisional=True,rates_identity=sha,rates_sha256=sha,source_bundle=str(src),
              source_design_meta_sha256=SB['meta_sha256'],source_rates_identity=sm.get('rates_identity','default'),
              inputs_manifest_sha256=m['inputs_manifest_sha256'],numerics=sm.get('numerics','exact'),test_only=bool(sm.get('test_only')),
              pilot=str(run),accepted_tool_changes=changes or None,rate_rule=rule_rec,
              note='PROVISIONAL (R14, R19): no counts, no design.json, no multipliers. Measure under this map (production.py plan --pilot --rates, '
                   'tools/sweep.py --rates), then freeze --rates-bundle this bundle.',frozen_utc=utc())
    _publish_bundle(a.out,{'rates.json':data,'design_meta.json':(json.dumps(meta,indent=1)+'\n').encode()})
    return dict(bundle=str(Path(a.out).resolve()),rates_identity=sha,provisional=True)

def common_args(p):
    p.add_argument('--dimension',type=int,default=2);p.add_argument('--schema-prefix',default='c8-d2');p.add_argument('--half-d',type=float,default=1.)
    p.add_argument('--two-loop',type=Path,help='B2 jet (default: the pilot\'s inputs/two_loop.json)');p.add_argument('--inventory',type=Path);p.add_argument('--selection',type=Path)
    p.add_argument('--min-points',type=int,default=4096);p.add_argument('--min-replicates',type=int,default=32);p.add_argument('--max-replicates',type=int,default=128)
    p.add_argument('--variance-margin',type=float,default=DEFAULT_MARGIN);p.add_argument('--task-seconds',type=float,default=60.);p.add_argument('--min-chunk',type=int,default=256)
    p.add_argument('--max-task-seconds',type=float,default=120.);p.add_argument('--threads',type=int,default=8);p.add_argument('--checkpoint-tasks',type=int)
    p.add_argument('--index-hours',type=float,default=1.5);p.add_argument('--max-tasks',type=int,default=5*10**7);p.add_argument('--max-checkpoints',type=int,default=2*10**5)
    p.add_argument('--c8-magnitude',type=float,default=C8_MAGNITUDE);p.add_argument('--impute',choices=['addends','median'],default=DEFAULT_IMPUTE)

def main(argv=None)->int:
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);sp=p.add_subparsers(dest='command',required=True)
    q=sp.add_parser('report');q.add_argument('--pilot',type=Path,required=True);q.add_argument('--nested',type=Path);q.add_argument('--bundle',type=Path)
    q.add_argument('--target-se',type=float);q.add_argument('--budget-core-hours',type=float);q.add_argument('--json',type=Path);q.add_argument('--tails-out',type=Path)
    q.add_argument('--eta-node',type=float,help='test-only pilots without Slurm accounting');q.add_argument('--test-only',action='store_true');common_args(q)
    q.add_argument('--numerics',default='exact',help='route (b): the table re-costed under an approved profile (needs --cost-model measured under it)')
    q.add_argument('--cost-model',type=Path,help='route (b): a cost model measured under --numerics')
    q.set_defaults(variance_margin=None,impute=None)  # Z10: an explicit --variance-margin or --impute is known (defaults applied in main)
    q=sp.add_parser('freeze');q.add_argument('--pilot',type=Path,required=True);q.add_argument('--out',type=Path,required=True);q.add_argument('--test-only',action='store_true')
    q.add_argument('--target-rel',type=float);q.add_argument('--target-se',type=float);q.add_argument('--budget-core-hours',type=float);q.add_argument('--batches',type=int)
    q.add_argument('--spent-core-hours',type=float,default=0.);q.add_argument('--total-cap',type=float);q.add_argument('--seeds-log',type=Path)
    q.add_argument('--rates-bundle',type=Path);q.add_argument('--eta-node',type=float,help='--test-only freezes without Slurm accounting');common_args(q)
    q.add_argument('--numerics',default='exact',help='route (b): an approved profile (production.APPROVED_PROFILES) for a bundle frozen from an exact pilot')
    q.add_argument('--approved-numerics-change',help='route (b): the user approval reference of the profile (D1, A-FLAG-2)')
    q.add_argument('--cost-model',type=Path,help='route (b): a cost model measured under --numerics (tools/sweep.py --numerics)')
    q.add_argument('--numerics-gate',type=Path,action='append',help='route (b): a passed full-scale J-FLAG gate record of the profile build (repeatable)')
    q=sp.add_parser('rates');q.add_argument('--pilot',type=Path,required=True);q.add_argument('--source-bundle',type=Path,required=True)
    q.add_argument('--rule',choices=['one-step'],help='choose the rates from the pilot (A-FLAG-6); exclusive with --spec')
    q.add_argument('--spec',type=Path,help='the explicit alternative: {campaign: {sector: {L: rate | {graph: rate}}}}')
    q.add_argument('--step',help=f'--rule: the step between rates (default {RULE_STEP})');q.add_argument('--band',type=float,help=f'--rule: the keep band (default {RULE_BAND})')
    q.add_argument('--min-graphs',type=int,help=f'--rule: strata with fewer graphs keep .8 / .9 (default {RULE_MIN_GRAPHS})')
    q.add_argument('--boot',type=int,help=f'--rule: graph-bootstrap resamples for the record (default {RULE_BOOT})')
    q.add_argument('--out',type=Path,required=True);q.add_argument('--dimension',type=int,default=OWN_DIMENSION);q.add_argument('--schema-prefix',default=OWN_PREFIX)
    q.add_argument('--half-d',type=float,default=1.);q.add_argument('--inventory',type=Path);q.add_argument('--two-loop',type=Path)
    a=p.parse_args(argv)
    try:
        if a.command=='freeze':print(json.dumps(freeze(a),indent=1,default=float));return 0
        if a.command=='rates':print(json.dumps(rates(a),indent=1));return 0
        # Z10: the settings given explicitly (a projection of a bundle when they differ from its frozen ones), then the defaults
        requested={k:v for k,v in (('variance_margin',a.variance_margin),('impute',a.impute))if v is not None}
        a.variance_margin=DEFAULT_MARGIN if a.variance_margin is None else a.variance_margin;a.impute=a.impute or DEFAULT_IMPUTE
        P=load_pilot(a.pilot,a.two_loop,a.half_d,a.inventory,a.selection,a.dimension,a.schema_prefix)
        B=None
        if a.bundle:
            B=read_bundle(a.bundle,a.schema_prefix,allow_provisional=True)  # Z9: every file at its digest, parsed once
            if B['provisional']:print('design report: the bundle is provisional (design.py rates): predictions unavailable (provisional)');return 0
        check_options(a,bool(a.test_only or P.meta['test_only']))  # Y10: the options of the designs the table shows
        rc=profile_recost(P,a,freezing=False)  # route (b): the table re-costed under an approved profile
        P.eta_node,P.eta_source=eta_node(a.pilot,a.test_only or P.meta['test_only'],a.eta_node,a.schema_prefix)
        N=load_pilot(a.nested,a.two_loop,a.half_d,a.inventory,a.selection,a.dimension,a.schema_prefix)if a.nested else None
        if N:N.J8=P.J8
        opts=opts_from(a)
        r=report(P,opts,a.c8_magnitude,a.target_se,a.budget_core_hours,N,B,a.impute,rc,bundle_projection=requested or None);rows=r.pop('_tail_rows')
        if a.tails_out:
            with a.tails_out.open('w')as f:
                f.write('campaign,sector,L,graph,points,replicates,xi_hat,largest_share,use,status\n')
                for x in rows:f.write(f'{x["campaign"]},{x["sector"]},{x["L"]},{x["graph"]},{x["points"]},{x["replicates"]},{x["xi_hat"]},{x["largest_share"]},{x["use"]},{x["status"]}\n')
        if a.json:dump(a.json,json.loads(json.dumps(r,default=float)))
        print_report(r);return 0
    except (ValueError,FileExistsError)as e:print(f'design: {e}',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
