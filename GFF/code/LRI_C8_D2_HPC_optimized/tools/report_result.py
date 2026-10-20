#!/usr/bin/env python3
"""Create the run summary and LaTeX results fragment from an assembled C8 run."""
from __future__ import annotations
import argparse
import json
import math
import shlex
from pathlib import Path
from common import ROOT,load,digest

def number(x,n=9):return format(float(x),f'.{n}g')
def texnumber(x,n=8):
    s=number(x,n)
    if 'e' in s:
        a,b=s.split('e');return a+r'\times10^{'+str(int(b))+'}'
    return s

def rounded_pair(estimate,se):
    """Display the estimator at the decimal place of a two-digit sampling SE."""
    if se<=0:return number(estimate,12),'0'
    places=1-int(math.floor(math.log10(se)))
    return (f'{round(estimate,places):.{max(0,places)}f}',
            f'{round(se,places):.{max(0,places)}f}')


def finite_replicate_bootstrap(configs):
    """Explain the empirical-bootstrap variance factor without claiming bias control."""
    replicates=sorted({cfg['replicates'] for cfg in configs})
    if len(replicates)==1:
        R=replicates[0]
        expected=math.sqrt((R-1)/R)
        text=(f'With R = {R} randomized replicates per group, the linear empirical-bootstrap variance '
              f'is {(R-1)}/{R} of the unbiased covariance estimate, giving an expected SE ratio of '
              f'{number(expected,5)}. The observed ratio also has Monte Carlo variation from the finite '
              'number of resamples and may include nonlinear effects. Bootstrap resampling adds no '
              'independent integration observations.')
        tex=(f'With $R={R}$ randomized replicates per group, the linear empirical-bootstrap variance '
             f'has factor $(R-1)/R={R-1}/{R}$ relative to the unbiased covariance estimate. Its expected '
             f'SE ratio is $\\sqrt{{{R-1}/{R}}}={number(expected,5)}$. The observed ratio also has Monte '
             'Carlo variation from the finite number of resamples and may include nonlinear effects. '
             'Bootstrap resampling adds no independent integration observations.')
        return text,tex,expected
    text=('Each group with R randomized replicates contributes a factor (R-1)/R to its linear '
          'empirical-bootstrap variance relative to its unbiased covariance estimate; the aggregate '
          'SE ratio depends on the group variances. Bootstrap resampling adds no independent integration observations.')
    return text,text.replace('(R-1)/R',r'$(R-1)/R$'),None


def observed_tail_summary(diagnostics):
    """Describe observed leading-graph dispersion, without asserting a tail law."""
    if not diagnostics:return None
    graphs=(diagnostics.get('graph_variance_diagnostics') or {}).get('top_graphs') or []
    rows=[]
    for graph in graphs:
        campaigns=graph.get('campaigns') or {}
        if not campaigns:continue
        tag,item=max(campaigns.items(),key=lambda pair:pair[1].get('diagonal_sampling_variance',0.))
        share=(item.get('replicate_shape') or {}).get('largest_squared_deviation_share')
        if share is None or not math.isfinite(share) or not 0<=share<=1:continue
        rows.append({'sector':graph['sector'],'loop':graph['loop'],'graph':graph['graph'],
                     'campaign':tag,'largest_squared_deviation_share':share})
    if not rows:return None
    threshold=.8
    selected=[row for row in rows if row['largest_squared_deviation_share']>=threshold]
    if selected:
        example=selected[0]
        sector='power-free' if example['sector']=='free' else 'power-containing'
        text=(f'Among the {len(rows)} listed graphs with the largest estimated diagonal variances, '
              f'{len(selected)} have one randomized replicate accounting for at least 80% of the '
              "squared-deviation sum in the graph's campaign with larger estimated variance. "
              f'For example, {sector} graph {example["graph"]} at loop {example["loop"]}, campaign '
              f'{example["campaign"]}, has a share of {100*example["largest_squared_deviation_share"]:.1f}%. '
              'This describes the observed replicate dispersion and does not establish the distribution of unsampled regions.')
    else:
        example=max(rows,key=lambda row:row['largest_squared_deviation_share'])
        text=(f'Among the {len(rows)} listed graphs with the largest estimated diagonal variances, '
              'none has one replicate accounting for 80% or more of the squared-deviation sum in its campaign '
              f'with larger estimated variance; the largest observed share is '
              f'{100*example["largest_squared_deviation_share"]:.1f}%. '
              'This statistic describes only the observed replicates and cannot establish coverage of unsampled regions.')
    return {'listed_graphs':len(rows),'threshold':threshold,'graphs_at_or_above_threshold':len(selected),
            'campaign_selection':'larger estimated diagonal variance within each listed graph',
            'example':example,'text':text}


def comparison_context(comparison,configs):
    """Use checked counts and streams, rather than the existence of a comparison, for labels."""
    if not comparison:return None
    streams=comparison.get('fresh_stream_checks') or {}
    fresh=(streams.get('distinct_base_seeds') is True and streams.get('C8_hashed_stream_scheme') is True
           and streams.get('shared_native_seeds')==0 and streams.get('shared_net_seeds')==0
           and streams.get('primary_seed_reused_from_allocation_pilot') is False)
    if (not fresh or comparison.get('same_inputs_order_and_backend') is not True
            or comparison.get('primary_estimator_pooled_with_comparison') is not False):
        raise ValueError('Comparison lacks verified matching inputs and separate fresh streams; rerun inspect_result.py')
    rows=comparison.get('point_ratios_by_loop_sector') or []
    if not rows:raise ValueError('Comparison has no verified point-count ratios')
    minimum=min(row['minimum_point_ratio'] for row in rows)
    maximum=max(row['maximum_point_ratio'] for row in rows)
    if not math.isfinite(minimum) or not math.isfinite(maximum) or not 0<minimum<=maximum:
        raise ValueError('Invalid comparison point-count ratios')
    increased=maximum>1
    nondecreasing=minimum>=1
    if (bool(comparison.get('point_count_refinement_performed'))!=increased
            or bool(comparison.get('all_point_counts_nondecreasing'))!=nondecreasing):
        raise ValueError('Comparison refinement flags disagree with its actual point-count ratios')
    refinement=increased and nondecreasing
    adaptive=comparison.get('adaptive_allocation_based_on_comparison') is True
    baseline='Previous calculation' if adaptive else 'Comparison run'
    primary='Fresh refinement' if refinement else 'Current run'
    label='Independent refinement' if refinement else 'Independent numerical comparison'
    ratio_label='previous SE / current SE' if adaptive and refinement else 'comparison SE / current SE'
    minimum_L8_by_sector={sector:min(n for cfg in configs if cfg['L']==8 and cfg['sector']==sector
                                     for n in cfg['counts'].values())
                          for sector in ('free','power')}
    minimum_L8=min(minimum_L8_by_sector.values())
    if minimum>1:
        point_text=(f'Every graph has at least {number(minimum,6)} times as many points per randomized '
                    'replicate as in the comparison run. ')
        point_tex=(r'Every graph has at least $'+texnumber(minimum,6)+r'$ times as many points per '
                   'randomized replicate as in the comparison run. ')
    else:
        point_text=(f'The per-graph point ratios range from {number(minimum,6)} to {number(maximum,6)}. ')
        point_tex=(r'The per-graph point ratios range from $'+texnumber(minimum,6)+r'$ to $'+texnumber(maximum,6)+r'$. ')
    minimum_text=(f'The minimum eight-loop counts are {minimum_L8_by_sector["free"]:,} power-free '
                  f'and {minimum_L8_by_sector["power"]:,} power-containing points per graph per randomized replicate.')
    point_text+=minimum_text
    point_tex+=minimum_text
    allocation_text=('Sampling allocations were frozen before the current integration, using earlier '
                     'calculations for variance and timing estimates. Earlier samples are used only for '
                     'planning and comparisons; they are not pooled into the current coefficient. '
                     'The full frozen allocation is completed independently of intermediate coefficient '
                     'values or estimated errors.' if adaptive else
                     'The comparison uses separately sampled estimates with verified distinct native and Sobol seeds.')
    return {'refinement':refinement,'adaptive':adaptive,'baseline_label':baseline,'primary_label':primary,
            'section_label':label,'ratio_label':ratio_label,'minimum_point_ratio':minimum,
            'maximum_point_ratio':maximum,'minimum_L8_points':minimum_L8,
            'minimum_L8_points_by_sector':minimum_L8_by_sector,
            'point_text':point_text,'point_tex':point_tex,'allocation_text':allocation_text}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('directory',type=Path)
    ap.add_argument('--output-directory',type=Path,
                    help='write the three report files to this directory, leaving saved run reports and root documents untouched')
    args=ap.parse_args()
    directory=args.directory.resolve()
    run_path='results/'+directory.name
    r=load(directory/'C8_result.json');m=load(directory/'manifest.json')
    if r['test_only'] or r['C8_full'] is None:raise ValueError('A complete graph calculation is required')
    if r['source_manifest_sha256']!=digest(directory/'manifest.json'):raise ValueError('Result/manifest mismatch')
    diagnostics=load(directory/'result_diagnostics.json') if (directory/'result_diagnostics.json').exists() else None
    if diagnostics and diagnostics['source_result_sha256']!=digest(directory/'C8_result.json'):
        raise ValueError('Diagnostics/result mismatch')
    comparison=diagnostics.get('comparison') if diagnostics else None
    comparison_path='results/'+comparison['comparison_run'] if comparison else None
    configs=[load(directory/'groups'/g['name']/'config.json') for g in m['groups']]
    comparison_info=comparison_context(comparison,configs)
    if comparison and (comparison['C8_primary']!=r['C8_full']
                       or comparison['sampling_se_primary']!=r['sampling_standard_error']):
        raise ValueError('Comparison describes a different primary estimate')
    tail=observed_tail_summary(diagnostics)
    bootstrap_text,bootstrap_tex,bootstrap_expected_ratio=finite_replicate_bootstrap(configs)
    samples=sum(g['samples'] for g in configs)
    graph_replicates=sum(sum(n>0 for n in g['counts'].values())*g['replicates'] for g in configs)
    half=max(abs(x[8]-r['C8_full'])for x in r['half_streams'])
    diagnostic=max(4*r['sampling_standard_error'],half)
    ca,cb=(r['campaigns'][c]for c in ('a','b'))
    d=(ca['sampling_se']**2+cb['sampling_se']**2)**.5
    campaign_pull=(ca['C8']-cb['C8'])/d if d else None
    campaign_separation_tex=(r'Their separation is $'+texnumber(abs(campaign_pull),5)+
                             r'$ combined estimated sampling standard errors. ' if campaign_pull is not None else
                             'Their combined-SE separation is undefined. ')
    interpretation_text=('The covariance is estimated from finitely many randomized replicates; its calibration '
                         'depends on the observed replicate and graph dispersion. These diagnostics cannot exclude '
                         'influential integration regions absent from the samples. A smaller estimated sampling '
                         'standard error alone does not establish numerical convergence or a certified error bound.')
    boot=r.get('bootstrap')
    boot_ratio=boot['full_se'][8]/r['sampling_standard_error'] if boot and r['sampling_standard_error'] else None
    bias_ratio=boot['bias'][8]/r['sampling_standard_error'] if boot and r['sampling_standard_error'] else None
    estimate_display,se_display=rounded_pair(r['C8_full'],r['sampling_standard_error'])
    variance=r['sampling_standard_error']**2
    error_rows=[{'loop':int(L),'sector':s,'sampling_se':v,'variance_fraction':v*v/variance if variance else 0}
                for L,entries in r['error_by_loop'].items()for s,v in entries.items()]
    error_rows.sort(key=lambda row:row['variance_fraction'],reverse=True)
    meta={'schema':'c8-d2-run-report-1','purpose':r['purpose'],'result_sha256':digest(directory/'C8_result.json'),
          'samples':samples,'graph_replicates':graph_replicates,'replicates_per_campaign_group':configs[0]['replicates'],
          'C8':r['C8_full'],'sampling_se':r['sampling_standard_error'],
          'max_half_stream_displacement':half,'four_se_or_half_stream_diagnostic':diagnostic,
          'half_stream_definition':'First versus second half of randomized replicates; not a point-count refinement.',
          'campaign_difference_pull':campaign_pull,'publication_precision_established':False,
          'bootstrap_se_over_delta_se':boot_ratio,'bootstrap_bias_over_delta_se':bias_ratio,
          'bootstrap_linear_empirical_expected_se_ratio':bootstrap_expected_ratio if boot else None,
          'error_budget':error_rows,
          'comparison':comparison,
          'comparison_presentation':comparison_info,
          'observed_replicate_dispersion':tail,
          'scope':'The four-SE number is diagnostic; no allowance is adopted without convergence evidence.'}
    title=('Complete-coverage '+comparison_info['section_label'].lower() if comparison_info else
           ('Complete-coverage numerical pilot' if r['purpose']=='pilot' else 'Complete-coverage numerical campaign'))
    lines=[f'# C8(2): {title.lower()}','',
           f'**C8 estimator: {estimate_display}; estimated sampling standard error: {se_display}.**','',
           'This is the computed value from the supplied finite scheme with every required graph and regulator moment. '
           'A controlled numerical error bound has not been established. The displayed standard error '
           'is obtained by first-order propagation of covariance estimated from whole randomized replicates; '
           'it is not a rigorous error bound.','',
           f'Current run: `{run_path}`. The manifest purpose `{r["purpose"]}` identifies the sampling workflow; '
           'it does not certify numerical accuracy.','',
           f'The run used {samples:,} points and {graph_replicates:,} graph-replicate evaluations, '
           f'with two independent campaigns and {configs[0]["replicates"]} replicates in each loop/sector/campaign group.','',
           '## Coefficients from the same samples','',
           '| Order | Estimate | Sampling SE |','|---:|---:|---:|']
    for k,(v,se) in enumerate(zip(r['coefficients'],r['standard_errors'])):
        lines.append(f'| C{k} | {number(v,12)} | {number(se,6)} |')
    lines+=['','## Full and power-free assembly','',
            f'- Power-free C8: {number(r["power_free_C8"],12)}; SE {number(r["power_free_se"],6)}.',
            f'- Measured power correction: {number(r["power_correction"],12)}; SE {number(r["power_correction_se"],6)}.',
            f'- Their covariance: {number(r["power_free_correction_covariance"],12)}.',
            '','The correction is F(free+power)-F(free). Lower-loop nonlinear changes are included. '
            'It has not been constrained to vanish.','',
            '## Checks and numerical limits','',
            '| Check | Value |','|---|---:|',
            f'| Campaign a | {number(ca["C8"])} +/- {number(ca["sampling_se"],5)} |',
            f'| Campaign b | {number(cb["C8"])} +/- {number(cb["sampling_se"],5)} |',
            f'| Campaign difference / combined SE | {number(campaign_pull,5) if campaign_pull is not None else "undefined"} |',
            f'| Largest replicate-half displacement | {number(half,7)} |',
            f'| max(4 SE, half-stream displacement), diagnostic only | {number(diagnostic,7)} |','',
            'The half-stream comparison splits each group\'s randomized replicates into two halves. '
            'It does not increase the number of points per graph.','',
            '## Error budget and bootstrap','',
            '| Loop | Sector | Contribution to C8 SE | Share of C8 variance |','|---:|---|---:|---:|']
    for row in error_rows:
        lines.append(f'| {row["loop"]} | {row["sector"]} | {number(row["sampling_se"],6)} | {100*row["variance_fraction"]:.2f}% |')
    if boot:
        lines+=['',f'The {boot["replicates"]:,}-resample replicate bootstrap gives a C8 SE of '
                f'{number(boot["full_se"][8],6)} (ratio {number(boot_ratio,5)} to the propagated SE) '
                f'and a mean displacement of {number(boot["bias"][8],6)} '
                f'({number(bias_ratio,5)} propagated SE). This is a diagnostic of the sampled replicates; '
                'it cannot detect important integration regions absent from those samples.','',bootstrap_text]
    if tail:
        lines+=['','### Observed replicate dispersion','',tail['text']]
    lines+=['','## Lower-order comparisons','',
            '| Lower-order check | Estimate | Reference | Combined pull |','|---|---:|---:|---:|']
    for row in r['lower_order_checks']:
        lines.append(f'| C{row["order"]} | {number(row["estimate"],10)} | {number(row["reference"],10)} | {number(row["pull"],5) if row["pull"] is not None else "undefined"} |')
    lines+=['','These references come from the supplied manuscript and are checks only. '
            'No earlier physical coefficient was used to fit the result.','',
            'Agreement of C3–C7 does not independently check the newly required highest regulator '
            'moment at each lower loop; those moments first enter C8.','',
            interpretation_text+' The graph and field-theory framework is inherited.','']
    if comparison:
        lines+=['## '+comparison_info['section_label'],'',
                '| Run | C8 estimate | Estimated sampling SE |','|---|---:|---:|',
                f'| {comparison_info["baseline_label"]} (`{comparison_path}`) | {number(comparison["C8_comparison"],12)} | {number(comparison["sampling_se_comparison"],6)} |',
                f'| {comparison_info["primary_label"]} (`{run_path}`) | {number(comparison["C8_primary"],12)} | {number(comparison["sampling_se_primary"],6)} |','',
                f'The shift (current estimate minus comparison estimate) is {number(comparison["C8_difference"],7)}, or '
                f'{number(comparison["C8_difference_over_combined_sampling_se"],5)} combined estimated standard errors. '
                f'The {comparison_info["ratio_label"]} ratio is {number(comparison["sampling_se_improvement_factor"],5)}. '
                'The current run uses fresh native and Sobol seeds. Its estimate contains no samples from the comparison run.','',
                comparison_info['point_text'],'',
                '| Loop | Sector | Minimum point ratio | Median point ratio | Maximum point ratio |',
                '|---:|---|---:|---:|---:|']
        for row in comparison['point_ratios_by_loop_sector']:
            lines.append(f'| {row["loop"]} | {row["sector"]} | {number(row["minimum_point_ratio"],6)} | {number(row["median_point_ratio"],6)} | {number(row["maximum_point_ratio"],6)} |')
        lines+=['','Ratios refer to points per graph per randomized replicate. '+comparison_info['allocation_text']+' '
                'The comparison is a numerical diagnostic, not a calibrated confidence test or proof of convergence.','']
    top_count=len(((diagnostics or {}).get('graph_variance_diagnostics') or {}).get('top_graphs') or []) or 25
    inspect_command=f'python3 tools/inspect_result.py {shlex.quote(run_path)} --top {top_count}'
    if comparison:inspect_command+=' --comparison '+shlex.quote(comparison_path)
    lines+=['## Reproduce the saved calculation','',
            '```bash',f'python3 tools/assemble.py {shlex.quote(run_path)} --bootstrap {boot["replicates"] if boot else 0} \\',
            f'  --output {shlex.quote(run_path+"/C8_reassembled.json")}',
            inspect_command,f'python3 tools/report_result.py {shlex.quote(run_path)}','```','',
            'Reassembly writes a separate `C8_reassembled.json`, preserving the delivered result if numerical '
            'library versions differ. The inspection and report commands validate and describe the retained '
            '`C8_result.json` and its merged samples.','',
            f'Result SHA-256: `{digest(directory/"C8_result.json")}`.','',
            'The saved JSON contains full covariance, per-loop/sector errors, half streams, bootstrap diagnostics, '
            'input means, and provenance. Graph-level and between-run diagnostics are in `result_diagnostics.json`. '
            'The checkpoints and graph-replicate CSV files are retained.','']
    t=[r'\paragraph{Status.} '+title+'. Every active kernel is included. '
       r'A certified numerical error bound has not been established for $C_8(2)$. '
       r'The current run is \path{'+run_path+r'}. Its manifest purpose \texttt{'+r['purpose']+
       r'} identifies the sampling workflow; it does not certify numerical accuracy.',
       r'\begin{equation}\boxed{\widehat C_8(2)='+estimate_display+r',\qquad\widehat\sigma_{\rm sampling}='+se_display+r'.}\end{equation}',
       f'The run uses {samples:,} integration points and {graph_replicates:,} graph-replicate evaluations, '
       f'with two independent campaigns and {configs[0]["replicates"]} replicates per loop/sector/campaign group.',
       r'\begin{center}\begin{tabular}{@{}rrr@{}}\toprule Coefficient & Estimate & Sampling SE\\\midrule']
    for k in range(2,9):
        t.append(f'$C_{k}$ & ${texnumber(r["coefficients"][k],10)}$ & ${texnumber(r["standard_errors"][k],4)}$'+r'\\')
    t+=[r'\bottomrule\end{tabular}\end{center}',
        r'The power-free coefficient is $'+texnumber(r['power_free_C8'])+r'$ and the measured power correction is $'+texnumber(r['power_correction'])+r'$, with sampling SE $'+texnumber(r['power_correction_se'],4)+r'$. The correction includes the changes in lower-loop fixed-point terms and is not imposed to vanish.',
        r'The two campaign estimates are $'+texnumber(ca['C8'])+r'\pm'+texnumber(ca['sampling_se'],4)+r'$ and $'+texnumber(cb['C8'])+r'\pm'+texnumber(cb['sampling_se'],4)+r'$ (sampling SE). '+campaign_separation_tex+r'The largest replicate-half displacement is $'+texnumber(half,5)+r'$. This split compares the first and second halves of randomized replicates, not increased point counts. The policy expression $\max(4\widehat\sigma,\text{replicate-half displacement})$ gives $'+texnumber(diagnostic,5)+r'$ before upward rounding and is retained only as a diagnostic.',
        interpretation_text+r' Full covariance and bootstrap diagnostics are retained in \path{results/'+directory.name+r'/C8_result.json}.',
        r'\begin{center}\begin{tabular}{@{}lrr@{}}\toprule Eight-loop sector & Finite kernels & Integrated\\\midrule Power-free & 16,798 & 16,064\\ Power-containing & 4,891 & 4,336\\\bottomrule\end{tabular}\end{center}',
        r'There are 4,851 exact forest zeros and 1,289 further terminal channel zeros, so the 20,400 active classes exhaust the 26,540-class inventory after those exact exclusions. All 7,231 power-containing classes pass the independent edge-subgraph forest comparison.']
    if boot:
        t.append(r'The replicate bootstrap uses '+str(boot['replicates'])+r' resamples. Its $C_8$ sampling SE is $'+texnumber(boot['full_se'][8],5)+r'$ (ratio $'+texnumber(boot_ratio,4)+r'$ to the propagated SE), and its mean displacement is $'+texnumber(boot['bias'][8],5)+r'$ ($'+texnumber(bias_ratio,4)+r'$ propagated SE). These checks describe the sampled replicates and cannot establish coverage of unsampled rare regions.')
        t.append(bootstrap_tex)
    dominant=error_rows[:4]
    t.append(r'\paragraph{Leading error sources.} The largest propagated variance shares are '+
             ', '.join(f'loop {x["loop"]} '+('power-free' if x['sector']=='free' else 'power-containing')+f' ({100*x["variance_fraction"]:.1f}'+r'\%)' for x in dominant)+'.')
    if tail:
        t.append(r'\paragraph{Observed replicate dispersion.} '+tail['text'].replace('%',r'\%'))
    if comparison:
        t.append(r'\paragraph{'+comparison_info['section_label']+r'.} '+comparison_info['baseline_label']+
                 r': $'+texnumber(comparison['C8_comparison'])+
                 r'\pm'+texnumber(comparison['sampling_se_comparison'],4)+r'$; '+comparison_info['primary_label'].lower()+
                 r': $'+
                 texnumber(comparison['C8_primary'])+r'\pm'+texnumber(comparison['sampling_se_primary'],4)+
                 r'$ (estimated sampling SE). The source runs are \path{'+comparison_path+r'} and \path{'+run_path+
                 r'}, respectively. The shift (current minus comparison) is $'+texnumber(comparison['C8_difference_over_combined_sampling_se'],4)+
                 r'$ combined estimated standard errors. The '+comparison_info['ratio_label']+r' ratio is $'+
                 texnumber(comparison['sampling_se_improvement_factor'],4)+r'$. '+comparison_info['point_tex']+' '+
                 comparison_info['allocation_text']+' All current samples use fresh random streams; '
                 r'the primary estimate contains no samples from the comparison run. '
                 r'This comparison is a numerical diagnostic, not a calibrated confidence test or proof of production precision.')
    if args.output_directory:
        output=args.output_directory.resolve();output.mkdir(parents=True,exist_ok=True)
        report_path=output/'run_report.json';markdown_path=output/'RESULTS.md';fragment_path=output/'C8_results_fragment.tex'
    else:
        report_path=directory/'run_report.json';markdown_path=ROOT/'RESULTS.md';fragment_path=ROOT/'docs/C8_results_fragment.tex'
    report_path.write_text(json.dumps(meta,indent=2)+'\n')
    markdown_path.write_text('\n'.join(lines))
    fragment_path.write_text('\n\n'.join(t)+'\n')
    print(json.dumps(meta,indent=2))

if __name__=='__main__':main()
