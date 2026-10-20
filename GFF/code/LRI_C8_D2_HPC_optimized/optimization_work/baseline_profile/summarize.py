#!/usr/bin/env python3
"""Create a compact, source-linked summary from completed benchmark records."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics

ROOT=Path(__file__).resolve().parents[2]


def load(p):return json.loads(Path(p).read_text())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def med(v):return statistics.median(v)
def limits(v):return [min(v),max(v)]
def relative(p):
    try:return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:return str(Path(p))


def evidence(path):
    return {"path":relative(path),"sha256":digest(path)}


def scaling_report(path,label,grow):
    raw=load(path)
    if raw.get("status")!="passed" or len(raw["cases"])!=1:raise AssertionError("A completed single-stratum scaling comparison is required")
    case=raw["cases"][0];runs=case["runs"]
    if any(not r["exact_check"]["exact"] for r in runs):raise AssertionError("An exact scientific check failed")
    row_count={r["exact_check"]["rows"] for r in runs};samples={r["samples"] for r in runs}
    if len(row_count)!=1 or len(samples)!=1:raise AssertionError("Workload changed between scaling runs")
    first_path=Path(runs[0]["output"])
    if not first_path.is_file():first_path=path.parent/case["name"]/first_path.name
    native=load(first_path)
    thread_counts=sorted({r["threads"] for r in runs});serial={}
    for tag in ("baseline","candidate"):
        serial[tag]=med([r["integration_seconds"] for r in runs if r["threads"]==1 and r["executable"]==tag])
    table=[]
    for threads in thread_counts:
        row={"requested_threads":threads}
        for tag in ("baseline","candidate"):
            selected=[r for r in runs if r["threads"]==threads and r["executable"]==tag]
            integration=[r["integration_seconds"] for r in selected]
            wall=[r["wall_seconds"] for r in selected]
            cpu=[r["process_resources"]["user_seconds"]+r["process_resources"]["system_seconds"] for r in selected]
            rss=[r["process_resources"]["max_rss_kib"] for r in selected]
            actual={r.get("native_performance",{}).get("actual_threads") for r in selected}
            if actual!={None} and actual!={threads}:raise AssertionError("Actual candidate team size differs from requested team size")
            stats={"repeats":len(selected),"integration_seconds_median":med(integration),"integration_seconds_range":limits(integration),
                "subprocess_wall_seconds_median":med(wall),"load_seconds_median":med([r["load_seconds"] for r in selected]),
                "child_cpu_seconds_median":med(cpu),"child_cpu_seconds_range":limits(cpu),"peak_rss_kib_median":med(rss),"peak_rss_kib_range":limits(rss),
                "cpu_per_integration_wall_median":med([c/t for c,t in zip(cpu,integration)]),
                "cpu_per_subprocess_wall_median":med([c/t for c,t in zip(cpu,wall)]),
                "summed_task_wall_seconds_median":med([r["summed_task_seconds"] for r in selected]),
                "task_slot_utilization_median":med([r["summed_task_seconds"]/(threads*r["integration_seconds"]) for r in selected]),
                "involuntary_context_switches_median":med([r["process_resources"]["involuntary_context_switches"] for r in selected]),
                "voluntary_context_switches_median":med([r["process_resources"]["voluntary_context_switches"] for r in selected]),
                "speedup_over_own_serial":serial[tag]/med(integration),"efficiency_over_own_serial":serial[tag]/med(integration)/threads,
                "actual_threads_reported":None if actual=={None} else threads,
                "runs":[{key:r[key] for key in ("repeat","integration_seconds","wall_seconds","load_seconds","summed_task_seconds","process_resources","exact_check")} for r in selected]}
            row[tag]=stats
        b,c=row["baseline"],row["candidate"]
        row["speedup_baseline_over_candidate"]=b["integration_seconds_median"]/c["integration_seconds_median"]
        row["fraction_less_integration_time"]=1-c["integration_seconds_median"]/b["integration_seconds_median"]
        row["fraction_less_peak_rss"]=1-c["peak_rss_kib_median"]/b["peak_rss_kib_median"]
        row["observed_ranges_overlap"]=max(b["integration_seconds_range"][0],c["integration_seconds_range"][0])<=min(b["integration_seconds_range"][1],c["integration_seconds_range"][1])
        row["interpretation"]="Median difference is unresolved by this small sample; observed timing ranges overlap." if row["observed_ranges_overlap"] else "Observed candidate timing range is separated from baseline in these three repetitions; this is not a formal confidence interval."
        table.append(row)
    return {"label":label,"grow_only_enabled":grow,"evidence":evidence(path),"manifest_sha256":raw["manifest_sha256"],
        "baseline_executable_sha256":raw["baseline_sha256"],"candidate_executable_sha256":raw["candidate_sha256"],
        "scope":{"sector":"free","L":8,"graphs":len({r["graph"] for r in native["rows"]}),"graph_ids":sorted({r["graph"] for r in native["rows"]}),
            "replicates":len({r["rep"] for r in native["rows"]}),"tasks_per_run":row_count.pop(),"samples_per_run":samples.pop(),
            "layout":native["layout"],"rate":native["rate"],"bits":native["bits"],"sum_mode":native["sum_mode"],
            "quad_calls_per_run":sum(r["quad"] for r in native["rows"]),"mp_calls_per_run":sum(r["mp"] for r in native["rows"]),
            "note":"Fixed deliberately stratified graph set, not a fresh complete C8 coefficient calculation or a uniform graph census."},
        "all_run_scientific_equality":True,"runs":len(runs),"compared_sample_evaluations_including_repeats":sum(r["samples"] for r in runs),
        "affinity_cpu_ids":raw["process_affinity"],"environment":{"OMP_DYNAMIC":"FALSE","OMP_PROC_BIND":"TRUE","machine":platform.machine()},
        "resource_note":"wait4 measures each native child's own CPU and peak RSS. CPU seconds include graph loading and output; CPU/integration-wall is therefore an approximate upper bound on CPU concurrency during integration. Affinity IDs are available logical CPUs, not a count of dedicated physical cores.",
        "schedule_inference":"Near-full task wall occupancy with lower CPU concurrency and many involuntary switches at high thread counts is consistent with scheduling/preemption constraints; the benchmark does not identify a particular quota or hardware topology.",
        "table":table}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--scaling",type=Path,required=True);p.add_argument("--label",required=True)
    p.add_argument("--grow-only",choices=("on","off"),required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--historical",type=Path)
    args=p.parse_args();primary=scaling_report(args.scaling.resolve(),args.label,args.grow_only=="on")
    result={"schema":"c8-native-performance-summary-1","status":"passed","primary":primary,"attribution":[],"correctness_evidence":[],
        "contract":{"preserved":"Point identities, loop/regulator order, graph weights, all native scientific output values and promotion counts.",
        "floating_exception_flags":"Outside the value-equivalence contract: the integer specialization may omit FE_INEXACT while preserving the rounded binary128 value.",
        "no_new_physics_estimate":True},
        "scope_limits":["Three counterbalanced repetitions provide measured ranges, not a formal confidence interval.",
        "Hard graph and promotion strata are useful for regressions and hotspot diagnosis; their runtime mix differs from a complete production campaign.",
        "An available affinity set is not evidence of exclusive physical cores; high-thread-count gains must be interpreted with child CPU and context-switch evidence.",
        "Peak RSS includes allocator/library/process overhead; cumulative GMP allocation traffic is not resident memory."]}
    if args.historical:result["historical_grow_enabled"]=scaling_report(args.historical.resolve(),"historical_combined_grow_enabled",True)
    for name in ("palette","scalar","grow","qadd"):
        path=ROOT/f"optimization_work/attribution_{name}/comparison.json"
        if not path.is_file():continue
        raw=load(path)
        if raw["status"]!="passed":raise AssertionError("Attribution did not pass")
        case=raw["cases"][0];summary=case["summary"][0];values={}
        for tag in ("baseline","candidate"):
            runs=[r for r in case["runs"] if r["executable"]==tag]
            values[tag]={"integration_seconds":[r["integration_seconds"] for r in runs],"peak_rss_kib":[r["process_resources"]["max_rss_kib"] for r in runs],
                         "child_cpu_seconds":[r["process_resources"]["user_seconds"]+r["process_resources"]["system_seconds"] for r in runs]}
        overlap=max(summary["baseline_range_seconds"][0],summary["candidate_range_seconds"][0])<=min(summary["baseline_range_seconds"][1],summary["candidate_range_seconds"][1])
        result["attribution"].append({"transition":name,"evidence":evidence(path),"summary":summary,"actual_runs":values,
            "all_run_scientific_equality":all(r["exact_check"]["exact"] for r in case["runs"]),"observed_ranges_overlap":overlap,
            "interpretation":"Individual timing benefit unresolved in this bounded attribution; do not multiply these medians to predict the combined gain." if overlap else "Separated ranges in this bounded three-repeat stratum."})
    result["attribution_conclusion"]={"palette":"Enabled: exact scaled-alpha representation substantially reduces graph storage. The incremental timing attribution is noisy.",
        "scalar_reuse":"Enabled: removes measured repeated GMP scalar allocations while retaining only a few scalar objects per thread. The incremental timing gain is unresolved.",
        "grow_only":"Opt-in: no demonstrated incremental benefit; its median was slightly slower with overlapping ranges. Retaining prior high-water vector objects is not justified as a default by this evidence.",
        "positive_quad_add":"Enabled: dominant baseline hotspot, exact-bit helper tests, full native/direct regression coverage, and measured combined-default comparison. No claim of an independently resolved gain from the short attribution alone."}
    for name in ["optimization_work/final_release_comparison/comparison.json","verification/final_native_release_checks.json",
                 "verification/final_default_kernel_checks.json","optimization_work/final_default_kernel_checks.json",
                 "optimization_work/qadd_combined_direct/direct_comparison.json","optimization_work/kernel_candidates/decimal_direct/direct_comparison.json",
                 "optimization_work/kernel_candidates/independent_points/verification.json",
                 "optimization_work/final_default_validation_sources/benchmark_native_source_mapping.json"]:
        path=ROOT/name
        if path.is_file():result["correctness_evidence"].append(evidence(path))
    result["baseline_profile_evidence"]=evidence(ROOT/"optimization_work/baseline_profile/matrix/profile_report.json")
    result["pristine_reference_source_evidence"]=evidence(ROOT/"optimization_work/baseline_profile/original/source_identity.json")
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    lines=[f"# Native C8 performance: {args.label}","", "The table compares identical frozen point workloads. Every run passed the exact scientific-output check.","",
        f"The primary workload has {primary['scope']['graphs']} free-L8 graphs, {primary['scope']['replicates']} replicates, {primary['scope']['tasks_per_run']} tasks and {primary['scope']['samples_per_run']:,} points per execution. Grow-only storage is {'enabled' if primary['grow_only_enabled'] else 'disabled'} in this measured candidate.","",
        "| Threads | Baseline seconds, median [range] | Candidate seconds, median [range] | Baseline/candidate | Candidate scaling from 1 thread |",
        "|---:|---:|---:|---:|---:|"]
    for row in primary["table"]:
        b,c=row["baseline"],row["candidate"]
        def timing(x):return f"{x['integration_seconds_median']:.4f} [{x['integration_seconds_range'][0]:.4f}, {x['integration_seconds_range'][1]:.4f}]"
        lines.append(f"| {row['requested_threads']} | {timing(b)} | {timing(c)} | {row['speedup_baseline_over_candidate']:.3f}× | {c['speedup_over_own_serial']:.3f}× |")
    lines += ["","| Threads | Baseline/candidate peak RSS, MiB | Baseline/candidate child CPU, seconds | Baseline/candidate CPU per integration-wall second |",
        "|---:|---:|---:|---:|"]
    for row in primary["table"]:
        b,c=row["baseline"],row["candidate"]
        lines.append(f"| {row['requested_threads']} | {b['peak_rss_kib_median']/1024:.2f} / {c['peak_rss_kib_median']/1024:.2f} | {b['child_cpu_seconds_median']:.3f} / {c['child_cpu_seconds_median']:.3f} | {b['cpu_per_integration_wall_median']:.2f} / {c['cpu_per_integration_wall_median']:.2f} |")
    lines += ["",primary["resource_note"],"",primary["schedule_inference"],"", "## Attribution and defaults",""]
    for text in result["attribution_conclusion"].values():lines.append("- "+text)
    lines += ["","Every short incremental attribution had overlapping measured timing ranges. The observed combined table is the application measurement; the individual ratios must not be multiplied together.","",
        "## Limits","","\n".join("- "+text for text in result["scope_limits"]),"", "The raw comparison and per-run resource records remain in "+relative(args.scaling)+". The authoritative structured summary is "+relative(args.output)+".",""]
    args.output.with_suffix(".md").write_text("\n".join(lines))
    print(f"Saved {args.output}")


if __name__=="__main__":main()
