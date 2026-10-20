#!/usr/bin/env python3
"""Bounded, frozen native replay and performance comparisons.

Preparation reads graph packs by verified offsets; it does not change a production
campaign. Profiles instrument private copies of the original sources. Actual
speed comparisons always use uninstrumented executables and identical tasks.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import shlex
import shutil
import statistics
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCIENCE = ("uid", "rep", "graph", "begin", "end", "total", "values", "quad", "mp", "max_abs")
HEADER = ("schema", "order", "L", "seed", "layout", "bits", "rate", "sum_mode",
          "long_double_bits", "mp_backend", "mp_digits10")


def load(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for part in iter(lambda:f.read(1024*1024), b""): h.update(part)
    return h.hexdigest()


def run(command, *, env=None, cwd=ROOT, timeout=600):
    start=time.perf_counter()
    p=subprocess.run(list(map(str,command)), cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
    wall=time.perf_counter()-start
    if p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {shlex.join(list(map(str,command)))}\n{p.stdout}\n{p.stderr}")
    return p,wall


def compare(reference, candidate):
    for key in HEADER:
        if reference.get(key)!=candidate.get(key):
            raise AssertionError(f"Scientific header differs: {key}: {reference.get(key)!r} != {candidate.get(key)!r}")
    if len(reference["rows"])!=len(candidate["rows"]):
        raise AssertionError("Row counts differ")
    for a,b in zip(reference["rows"],candidate["rows"]):
        if len(a["values"])!=len(b["values"]):
            raise AssertionError(f"Jet widths differ at uid={a['uid']}")
        for key in SCIENCE:
            if a.get(key)!=b.get(key):
                raise AssertionError(f"Exact scientific replay differs at uid={a['uid']}, graph={a['graph']}, rep={a['rep']}, field={key}: {a.get(key)!r} != {b.get(key)!r}")
    return {"exact":True,"rows":len(reference["rows"]),
            "samples":sum(r["end"]-r["begin"] for r in reference["rows"]),
            "quad":sum(r["quad"] for r in reference["rows"]),"mp":sum(r["mp"] for r in reference["rows"])}


def module_from(path, name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def compile_instrumented(source, work, backend, build_record=None):
    script=ROOT/"optimization_work/baseline_profile/instrument_baseline.py"
    m=module_from(script,"private_instrumenter")
    instrumented=work/"instrumented";record=m.prepare(source,instrumented)
    record_path=build_record or source/f"bin/c8d2_{backend}.build.json"
    if not record_path.is_file():record_path=ROOT/f"bin/c8d2_{backend}.build.json"
    build=load(record_path);v=build["variables"]
    flags=[]
    for k in ("CPPFLAGS","OPTFLAGS","CXXFLAGS","REQUIRED"):flags+=shlex.split(v[k])
    if backend=="gmp":flags+=["-DC8_USE_GMP"]
    binary=work/f"profile_{backend}"
    command=shlex.split(v["CXX"])+flags+[str(instrumented/"c8d2_integrate.cpp")]
    command+=shlex.split(v["LDFLAGS"])+["-lquadmath"]+(["-lgmp"] if backend=="gmp" else [])+shlex.split(v["LDLIBS"])+["-o",str(binary)]
    # Build variables may contain dependency paths relative to the original root.
    p,wall=run(command,cwd=record_path.parent.parent)
    (work/"compile.log").write_text(p.stdout+p.stderr)
    record.update(command=command,compile_seconds=wall,executable_sha256=digest(binary),
                  toolchain_build_record_sha256=digest(record_path))
    save(work/"instrumented_build.json",record)
    return binary


def select_graphs(source, sector, L, rows):
    """Structural extremes, an observed promotion tail, and measured costly rows."""
    selected={}
    by_id={r["id"]:r for r in rows}
    def add(row,reason):
        selected.setdefault(row["id"],{"inventory":row,"reasons":[]})["reasons"].append(reason)
    ordered=sorted(rows,key=lambda r:(r["cost"],r["id"]))
    add(ordered[0],"minimum monomials*terms")
    add(ordered[len(ordered)//2],"median monomials*terms")
    add(max(rows,key=lambda r:(r["monomials"],-r["id"])),"maximum monomials")
    add(max(rows,key=lambda r:(r["terms"],-r["id"])),"maximum forest terms")
    primitive=[r for r in rows if r.get("primitive")]
    if primitive:add(primitive[len(primitive)//2],"primitive graph")
    pilot=load(source/f"verification/native_cost_pilot/{sector}_L{L}.json")
    stats=defaultdict(lambda:{"samples":0,"mp":0,"seconds":0.0})
    for row in pilot["rows"]:
        s=stats[row["graph"]];s["samples"]+=row["end"]-row["begin"];s["mp"]+=row["mp"];s["seconds"]+=row["seconds"]
    for name,metric in [("highest measured pilot MP fraction",lambda s:s["mp"]/s["samples"]),
                        ("slowest measured pilot per point",lambda s:s["seconds"]/s["samples"])]:
        gid=max(stats,key=lambda g:(metric(stats[g]),-g));add(by_id[gid],name)
    observed={}
    if L>=7:
        # Bounded subset: the first checkpoint of each completed campaign-a shard.
        directory=source/f"results/precision_complete_03/groups/a_{sector}_L{L}/checkpoints"
        for path in sorted(directory.glob("s*_p000000.json")):
            checkpoint=load(path);native=checkpoint.get("native",checkpoint)
            for row in native["rows"]:
                s=observed.setdefault(row["graph"],{"seconds":0.0,"samples":0,"checkpoints":[]})
                s["seconds"]+=row["seconds"];s["samples"]+=row["end"]-row["begin"]
                if path.name not in s["checkpoints"]:s["checkpoints"].append(path.name)
        for gid in sorted(observed,key=lambda g:(observed[g]["seconds"],-g),reverse=True)[:3]:
            add(by_id[gid],"largest observed graph task time in bounded production checkpoint subset")
            selected[gid]["production_observation"]=observed[gid]
    return [dict(id=k,**selected[k]) for k in sorted(selected)],pilot


def write_tasks(path,L,ids,points,replicates=2,begin=0,total=None,split=None):
    total=total or points;lines=[];uid=0
    for rep in range(replicates):
        for gid in ids:
            intervals=[(begin,begin+points)] if split is None else [(begin,begin+split),(begin+split,begin+points)]
            for a,b in intervals:
                lines.append(f"{uid} {rep} {gid} {a} {b} {total}");uid+=1
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(f"C8D2TASKS1 {L} {len(lines)}\n"+"\n".join(lines)+"\n")


def prepare_manifest(args):
    source=args.source.resolve();work=args.output.resolve();work.mkdir(parents=True,exist_ok=True)
    manifest_path=work/"manifest.json"
    if manifest_path.exists():raise FileExistsError(f"Frozen manifest already exists: {manifest_path}")
    inventory=load(source/"inputs/inventory.json");cases=[]
    shutil.copy2(source/"inputs/gamma_d2_8.txt",work/"gamma_d2_8.txt")
    for sector in ("free","power"):
        for L in range(3,9):
            selected,pilot=select_graphs(source,sector,L,inventory[sector][str(L)])
            name=f"{sector}_L{L}";directory=work/"fixtures"/name;graph_root=directory/"graphs";(graph_root/f"L{L}").mkdir(parents=True,exist_ok=True)
            with (source/f"inputs/packs/{sector}_L{L}.pack").open("rb") as pack:
                for item in selected:
                    row=item["inventory"];pack.seek(row["offset"]);payload=pack.read(row["length"])
                    if len(payload)!=row["length"] or hashlib.sha256(payload).hexdigest()!=row["sha256"]:
                        raise RuntimeError(f"Packed graph integrity failure: {name} G{row['id']}")
                    (graph_root/f"L{L}/G{row['id']}.txt").write_bytes(payload)
            points=args.low_points if L<=6 else args.high_points
            tasks=directory/"base.tasks";write_tasks(tasks,L,[s["id"] for s in selected],points)
            net=directory/"pilot.net";shutil.copy2(source/f"verification/native_cost_pilot/{name}.net",net)
            cases.append(dict(name=name,sector=sector,L=L,selection=selected,points=points,replicates=2,
                seed=pilot["seed"],layout=0,bits=pilot["bits"],rate=".8",sum_mode="compensated",order=8,
                graphs=str(graph_root.relative_to(work)),tasks=str(tasks.relative_to(work)),net=str(net.relative_to(work)),grid="-",
                tasks_sha256=digest(tasks),net_sha256=digest(net),kind="base"))
    record={"schema":"c8-native-benchmark-fixtures-1","source_root":str(source),"created_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "selection_note":"bounded structural and measured-promotion strata; production selection observes first checkpoint per campaign-a shard, not every production row",
        "source_sha256":{str(p):digest(source/p) for p in [Path("src/kernel.hpp"),Path("src/c8d2_integrate.cpp"),Path("inputs/inventory.json")]},
        "gamma":"gamma_d2_8.txt","gamma_sha256":digest(work/"gamma_d2_8.txt"),"cases":cases}
    save(manifest_path,record)
    if args.matrix:add_matrix(manifest_path)
    print(f"Prepared {len(cases)} base groups, {sum(len(c['selection']) for c in cases)} distinct sector/loop graph fixtures: {manifest_path}",flush=True)
    return manifest_path


def add_matrix(path):
    manifest=load(path);work=path.parent;source=Path(manifest["source_root"])
    sys.path.insert(0,str(source/"tools"));production=module_from(source/"tools/production.py","baseline_net_export")
    added=[]
    for base in [c for c in manifest["cases"] if c["kind"]=="base"]:
        L=base["L"];name=base["name"];directory=work/"fixtures"/name
        ids=[base["selection"][0]["id"],base["selection"][-1]["id"]];ids=list(dict.fromkeys(ids))
        for layout in (1,2):
            case=dict(base,name=f"{name}_layout{layout}",layout=layout,points=32,rate=".9" if layout==1 else ".6",kind="layout_rate")
            tasks=directory/f"layout{layout}.tasks";write_tasks(tasks,L,ids,32)
            if layout==1:net=work/base["net"]
            else:
                net=directory/"layout2.net";case["net_record"]=production.make_net(net,2,2*L,52,90138017+L+(0 if base['sector']=='free' else 113),32)
            case.update(tasks=str(tasks.relative_to(work)),tasks_sha256=digest(tasks),net=str(net.relative_to(work)),net_sha256=digest(net))
            added.append(case)
        if L in (3,8):
            for bits in (32,60):
                case=dict(base,name=f"{name}_bits{bits}_seek",bits=bits,points=32,kind="absolute_seek")
                # Exercise Gray-code column31/59 and the native 64-bit index path.
                total=1<<bits;begin=(1<<(bits-1))-17
                net=directory/f"bits{bits}.net";case["net_record"]=production.make_net(net,2,4*L-1,bits,2411138+L+bits+(0 if base['sector']=='free' else 179),total)
                tasks=directory/f"bits{bits}.tasks";write_tasks(tasks,L,ids,32,begin=begin,total=total)
                case.update(tasks=str(tasks.relative_to(work)),tasks_sha256=digest(tasks),net=str(net.relative_to(work)),net_sha256=digest(net))
                added.append(case)
        if L in (3,8):
            # Unequal split checks independent absolute starts and deterministic merging.
            case=dict(base,name=f"{name}_split23",points=64,kind="split",parent_case=f"{name}_whole64")
            tasks=directory/"split23.tasks";write_tasks(tasks,L,ids,64,split=23)
            case.update(tasks=str(tasks.relative_to(work)),tasks_sha256=digest(tasks));added.append(case)
            case=dict(base,name=f"{name}_whole64",points=64,kind="whole")
            tasks=directory/"whole64.tasks";write_tasks(tasks,L,ids,64)
            case.update(tasks=str(tasks.relative_to(work)),tasks_sha256=digest(tasks));added.append(case)
    manifest["cases"]+=added;manifest["net_export_source_sha256"]=digest(source/"tools/production.py")
    save(path,manifest)


def validate_case(work,case):
    for key in ("tasks","net"):
        if digest(work/case[key])!=case[key+"_sha256"]:raise AssertionError(f"Frozen {key} changed: {case['name']}")
    for item in case["selection"]:
        path=work/case["graphs"]/f"L{case['L']}/G{item['id']}.txt"
        if digest(path)!=item["inventory"]["sha256"]:raise AssertionError(f"Frozen graph changed: {path}")


def execute(binary,manifest_path,manifest,case,output,threads,profile=None):
    work=manifest_path.parent;validate_case(work,case)
    if digest(work/manifest["gamma"])!=manifest["gamma_sha256"]:raise AssertionError("Frozen gamma changed")
    output.parent.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(OMP_DYNAMIC="FALSE",OMP_PROC_BIND="TRUE")
    if profile:env["C8_BENCH_PROFILE"]=str(profile.resolve())
    else:env.pop("C8_BENCH_PROFILE",None)
    cmd=[binary,work/case["graphs"],work/manifest["gamma"],work/case["net"],work/case["tasks"],output,
         case["seed"],case["layout"],case["rate"],threads,case["sum_mode"],case["grid"],case["order"]]
    # wait4 returns this child's own resource use. RUSAGE_CHILDREN in the parent
    # would instead retain the largest RSS of all previous benchmark children.
    usage_record=None
    if hasattr(os,"posix_spawn") and hasattr(os,"wait4"):
        command=list(map(str,cmd));started=time.perf_counter()
        log=output.with_suffix(".process.log")
        with log.open("wb") as stream:
            pid=os.posix_spawn(command[0],command,env,file_actions=[
                (os.POSIX_SPAWN_DUP2,stream.fileno(),1),(os.POSIX_SPAWN_DUP2,stream.fileno(),2)])
            while True:
                done,status,usage=os.wait4(pid,os.WNOHANG)
                if done:break
                if time.perf_counter()-started>600:
                    os.kill(pid,signal.SIGKILL);os.wait4(pid,0);raise TimeoutError("Native benchmark exceeded 600 seconds")
                time.sleep(.02)
        wall=time.perf_counter()-started
        if os.waitstatus_to_exitcode(status):
            raise RuntimeError(f"Native benchmark failed: {shlex.join(command)}\n{log.read_text()}")
        usage_record={"source":"wait4 child rusage","user_seconds":usage.ru_utime,"system_seconds":usage.ru_stime,
            "max_rss_kib":usage.ru_maxrss,"voluntary_context_switches":usage.ru_nvcsw,"involuntary_context_switches":usage.ru_nivcsw}
    else:_,wall=run(cmd,env=env)
    native=load(output)
    record={"wall_seconds":wall,"load_seconds":native["load_seconds"],"integration_seconds":native["integration_seconds"],
        "summed_task_seconds":sum(r["seconds"] for r in native["rows"]),"threads":threads,
        "samples":sum(r["end"]-r["begin"] for r in native["rows"]),"output":str(output),"output_sha256":digest(output)}
    if "performance" in native:record["native_performance"]=native["performance"]
    if usage_record:record["process_resources"]=usage_record
    return native,record


def profile(args):
    path=args.manifest.resolve();manifest=load(path);work=path.parent
    source=args.source.resolve() if args.source else Path(manifest["source_root"])
    binary=args.baseline.resolve() if args.baseline else source/f"bin/c8d2_{args.backend}";private=work/f"profile_{args.backend}"
    if not args.reuse_profile or not private.is_file():private=compile_instrumented(source,work,args.backend,args.build_record.resolve() if args.build_record else None)
    report={"schema":"c8-kernel-profile-report-1","manifest_sha256":digest(path),"baseline_sha256":digest(binary),"profile_sha256":digest(private),
        "threads":args.threads,"notes":["LD/Q/MP totals are inclusive of their named substages; do not sum totals and substages.",
        "Clock and allocator-hook overhead is measured; absolute speedups must use uninstrumented binaries.",
        "GMP requested bytes count allocation traffic, not live resident memory; peak RSS uses getrusage.",
        "Fixture strata deliberately stress promotion tails; production cost shares must weight performance conclusions."],"cases":[]}
    for case in manifest["cases"]:
        if case["kind"]!="base" or (args.case and case["name"] not in args.case):continue
        directory=work/"profiles"/case["name"]
        baseline,brec=execute(binary,path,manifest,case,directory/"baseline.json",args.threads)
        measured,prec=execute(private,path,manifest,case,directory/"instrumented.json",args.threads,directory/"stages.json")
        check=compare(baseline,measured);stages=load(directory/"stages.json")
        row={"name":case["name"],"exact_check":check,"baseline":brec,"instrumented":prec,"profile":stages,
             "instrumentation_time_ratio":prec["integration_seconds"]/brec["integration_seconds"]}
        report["cases"].append(row);save(work/"profile_report.json",report)
        totals={key:round(stages["stages"][key]["seconds"],4) for key in ("ld_total","quad_total","mp_total","mp_exp","mp_products","mp_ordered_sums")}
        print(case["name"],"exact",check,"seconds",totals,flush=True)
    print(f"Saved {work/'profile_report.json'}",flush=True)


def scaling(args):
    path=args.manifest.resolve();original=load(path);source=args.source.resolve() if args.source else Path(original["source_root"])
    base=next(c for c in original["cases"] if c["name"]==args.case);work=args.output.resolve()
    if (work/"manifest.json").exists():raise FileExistsError("Use a fresh scaling fixture directory")
    work.mkdir(parents=True,exist_ok=True);directory=work/"fixtures"/base["name"];directory.mkdir(parents=True,exist_ok=True)
    validate_case(path.parent,base)
    shutil.copytree(path.parent/base["graphs"],directory/"graphs")
    shutil.copy2(path.parent/original["gamma"],work/"gamma_d2_8.txt")
    sys.path.insert(0,str(source/"tools"));production=module_from(source/"tools/production.py","scaling_net_export")
    net=directory/"scaling.net";L=base["L"]
    net_record=production.make_net(net,args.replicates,4*L-1,52,args.net_seed,args.points)
    tasks=directory/"scaling.tasks";write_tasks(tasks,L,[s["id"] for s in base["selection"]],args.points,replicates=args.replicates)
    case=dict(base,name=base["name"]+"_scaling",points=args.points,replicates=args.replicates,seed=args.seed,kind="base",
        graphs=str((directory/"graphs").relative_to(work)),tasks=str(tasks.relative_to(work)),net=str(net.relative_to(work)),
        tasks_sha256=digest(tasks),net_sha256=digest(net),net_record=net_record)
    manifest=dict(original,source_root=str(source),cases=[case],gamma="gamma_d2_8.txt",gamma_sha256=digest(work/"gamma_d2_8.txt"),
        derived_from_sha256=digest(path),selection_note="Extended controlled scaling workload using exactly the selected graph set of "+base["name"],
        created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()))
    save(work/"manifest.json",manifest)
    tasks_count=len(base["selection"])*args.replicates
    print(f"Prepared scaling case {case['name']}: {tasks_count} tasks, {tasks_count*args.points} points; {work/'manifest.json'}",flush=True)


def merged_split_check(whole,split):
    pieces=defaultdict(list)
    for row in split["rows"]:pieces[row["rep"],row["graph"]].append(row)
    largest=Decimal(0)
    with localcontext() as ctx:
        ctx.prec=80
        for row in whole["rows"]:
            parts=sorted(pieces[row["rep"],row["graph"]],key=lambda r:r["begin"])
            if len(parts)!=2 or parts[0]["begin"]!=row["begin"] or parts[0]["end"]!=parts[1]["begin"] or parts[1]["end"]!=row["end"]:
                raise AssertionError("Split coverage mismatch")
            if any(p["total"]!=row["total"] for p in parts):raise AssertionError("Split normalization changed")
            if sum(p["quad"] for p in parts)!=row["quad"] or sum(p["mp"] for p in parts)!=row["mp"]:raise AssertionError("Split precision counts changed")
            if max(Decimal(p["max_abs"]) for p in parts)!=Decimal(row["max_abs"]):raise AssertionError("Split point extrema changed")
            for j,expected in enumerate(row["values"]):
                vals=[Decimal(p["values"][j]) for p in parts];scale=max(Decimal(1),abs(Decimal(expected)),sum(map(abs,vals)))
                error=abs(sum(vals)-Decimal(expected))/scale;largest=max(largest,error)
                if error>Decimal("5e-16"):raise AssertionError("Split merge rounding exceeds 5e-16 normalized")
    return str(largest)


def compare_binary(args):
    path=args.manifest.resolve();manifest=load(path);work=path.parent;source=Path(manifest["source_root"])
    baseline=args.baseline.resolve() if args.baseline else source/f"bin/c8d2_{args.backend}"
    candidate=args.candidate.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    if (output/"comparison.json").exists():raise FileExistsError("Use a fresh comparison output directory")
    report={"schema":"c8-native-benchmark-comparison-1","manifest_sha256":digest(path),"baseline_sha256":digest(baseline),
            "candidate_sha256":digest(candidate),"repeats":args.repeats,"thread_counts":args.threads,
            "timing_note":"Counterbalanced alternating AB/BA runs; median per executable. Scientific rows compared exactly, including promotion counts and all Taylor coefficients.",
            "process_affinity":sorted(os.sched_getaffinity(0)) if hasattr(os,"sched_getaffinity") else None,"cases":[],"split_checks":[]}
    completed={}
    for case in manifest["cases"]:
        if args.base_only and case["kind"]!="base":continue
        if args.case and case["name"] not in args.case:continue
        reference=None;rows=[];times=defaultdict(list)
        for threads in args.threads:
            # Timing repeats are useful only for base performance cases.
            repetitions=args.repeats if case["kind"]=="base" else 1
            for rep in range(repetitions):
                order=[("baseline",baseline),("candidate",candidate)]
                if rep%2:order.reverse()
                for tag,executable in order:
                    native,rec=execute(executable,path,manifest,case,output/case["name"]/f"{tag}_t{threads}_r{rep}.json",threads)
                    if reference is None:reference=native
                    check=compare(reference,native);rec.update(executable=tag,repeat=rep,exact_check=check);rows.append(rec)
                    times[tag,threads].append(rec["integration_seconds"])
                    if tag=="candidate" and threads==args.threads[0] and rep==0:completed[case["name"]]=native
            speedup=statistics.median(times["baseline",threads])/statistics.median(times["candidate",threads])
            print(f"{case['name']} threads={threads}: exact; median integration speedup {speedup:.3f}x",flush=True)
        summary=[]
        for threads in args.threads:
            b=times["baseline",threads];c=times["candidate",threads]
            summary.append({"threads":threads,"baseline_median_seconds":statistics.median(b),"candidate_median_seconds":statistics.median(c),
                            "speedup":statistics.median(b)/statistics.median(c),"baseline_range_seconds":[min(b),max(b)],"candidate_range_seconds":[min(c),max(c)]})
        report["cases"].append({"name":case["name"],"kind":case["kind"],"sector":case["sector"],"L":case["L"],"summary":summary,"runs":rows})
        save(output/"comparison.json",report)
    for case in manifest["cases"]:
        if case["kind"]=="split" and case["name"] in completed and case["parent_case"] in completed:
            discrepancy=merged_split_check(completed[case["parent_case"]],completed[case["name"]])
            report["split_checks"].append({"case":case["name"],"max_normalized_merge_rounding":discrepancy,"tolerance":"5e-16"})
    report["status"]="passed";save(output/"comparison.json",report)
    print(f"Saved {output/'comparison.json'}",flush=True)


def direct(args):
    """Exact full-precision outputs on forced rare paths and every C8 jet width."""
    source=args.source.resolve();output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    if (output/"direct_comparison.json").exists():raise FileExistsError("Use a fresh direct comparison output directory")
    harness=ROOT/"tests/performance_harness.cpp";build=load(source/f"bin/c8d2_{args.backend}.build.json");v=build["variables"]
    flags=[]
    for key in ("CPPFLAGS","OPTFLAGS","CXXFLAGS","REQUIRED"):flags+=shlex.split(v[key])
    if args.backend=="gmp":flags.append("-DC8_USE_GMP")
    links=shlex.split(v["LDFLAGS"])+["-lquadmath"]+(["-lgmp"] if args.backend=="gmp" else [])+shlex.split(v["LDLIBS"])
    graph_list=output/"physical_graphs.txt"
    # Eight existing physical L8 fixtures; no new 450-digit all-graph campaign.
    original_list=source/"tests/fixtures/graphs.txt"
    paths=[]
    if original_list.is_file():
        for raw in original_list.read_text().split():
            path=Path(raw);paths.append(path if path.is_absolute() else source/path)
    graph_list.write_text("\n".join(str(p.resolve()) for p in paths)+"\n")
    report={"schema":"c8-direct-performance-comparison-1","harness_sha256":digest(harness),"backend":args.backend,
            "rounding_modes":args.rounding,"cases":[],"builds":{}}
    binaries={}
    for tag,header in (("baseline",source/"src/kernel.hpp"),("candidate",args.candidate_header.resolve())):
        binary=output/f"{tag}_direct";extra=args.candidate_flag if tag=="candidate" else []
        command=shlex.split(v["CXX"])+flags+extra+[f'-DC8_KERNEL_HEADER="{header}"',str(harness)]+links+["-o",str(binary)]
        compiled,seconds=run(command,cwd=source);(output/f"{tag}_compile.log").write_text(compiled.stdout+compiled.stderr)
        report["builds"][tag]={"command":command,"compile_seconds":seconds,"header_sha256":digest(header),"binary_sha256":digest(binary)};binaries[tag]=binary
    for rounding in args.rounding:
        values={}
        for tag,binary in binaries.items():
            p,wall=run([binary,graph_list,rounding],cwd=source)
            dest=output/f"{tag}_{rounding}.json";dest.write_text(p.stdout);values[tag]=load(dest)
        if values["baseline"]!=values["candidate"]:
            a,b=values["baseline"],values["candidate"]
            for i,(x,y) in enumerate(zip(a["rows"],b["rows"])):
                if x!=y:raise AssertionError(f"Direct exact replay changed row {i}, rounding={rounding}: {x!r} != {y!r}")
            raise AssertionError(f"Direct exact replay changed header or row count, rounding={rounding}")
        report["cases"].append({"rounding":rounding,"rows":len(values["baseline"]["rows"]),"exact":True,
            "coverage":["L2 K6 and L3/L7/L8 jets in all layouts","severe cancellation requiring MP","nonmoderate LD reference path","nonzero common log rescaling","physical L8 free/power graphs with shifted arguments","full Q value/error and 380-digit MP output"]})
        print(f"Direct replay {rounding}: {len(values['baseline']['rows'])} rows exact",flush=True)
        save(output/"direct_comparison.json",report)
    report["status"]="passed";save(output/"direct_comparison.json",report)


def build_baseline(args):
    source=ROOT/"optimization_work/baseline_profile/original"
    identity=load(source/"source_identity.json");parent=load(ROOT/"optimization_work/baseline_identity.json")
    for name,expected in identity["source_sha256"].items():
        if digest(source/name)!=expected or expected!=parent["source_sha256"][name]:raise AssertionError(f"Pristine reference source changed: {name}")
    record_path=args.build_record.resolve() if args.build_record else ROOT/f"bin/c8d2_{args.backend}.build.json"
    config=load(record_path);v=config["variables"];flags=[]
    for name in ("CPPFLAGS","OPTFLAGS","CXXFLAGS","REQUIRED"):flags+=shlex.split(v[name])
    if args.backend=="gmp":flags.append("-DC8_USE_GMP")
    output=args.output.resolve();output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError("Reference output already exists; choose a fresh output name")
    command=shlex.split(v["CXX"])+flags+[str(source/"src/c8d2_integrate.cpp")]
    command+=shlex.split(v["LDFLAGS"])+["-lquadmath"]+(["-lgmp"] if args.backend=="gmp" else [])+shlex.split(v["LDLIBS"])+["-o",str(output)]
    p,seconds=run(command,cwd=record_path.parent.parent)
    output.with_suffix(".compile.log").write_text(p.stdout+p.stderr)
    description,_=run([output,"--describe"])
    save(output.with_suffix(".build.json"),{"schema":"c8-native-benchmark-reference-build-1","status":"passed",
        "command":command,"working_directory":str(record_path.parent.parent),"source_sha256":identity["source_sha256"],
        "baseline_identity_sha256":digest(ROOT/"optimization_work/baseline_identity.json"),"toolchain_build_record_sha256":digest(record_path),
        "executable_sha256":digest(output),"compile_seconds":seconds,"native":json.loads(description.stdout)})
    print(f"Built pristine reference {output} ({digest(output)})",flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("prepare");a.add_argument("--source",type=Path,required=True,help="the original LRI_C8_D2_HPC package, named explicitly (no sibling default: on our machines that name is another package)");a.add_argument("--output",type=Path,default=ROOT/"optimization_work/baseline_profile/matrix");a.add_argument("--low-points",type=int,default=1024);a.add_argument("--high-points",type=int,default=128);a.add_argument("--matrix",action="store_true")
    a=sub.add_parser("profile");a.add_argument("--manifest",type=Path,required=True);a.add_argument("--source",type=Path);a.add_argument("--baseline",type=Path);a.add_argument("--build-record",type=Path);a.add_argument("--backend",choices=("gmp","decimal"),default="gmp");a.add_argument("--threads",type=int,default=1);a.add_argument("--case",action="append");a.add_argument("--reuse-profile",action="store_true")
    a=sub.add_parser("scaling");a.add_argument("--manifest",type=Path,required=True);a.add_argument("--source",type=Path);a.add_argument("--case",default="free_L8");a.add_argument("--output",type=Path,required=True);a.add_argument("--replicates",type=int,default=16);a.add_argument("--points",type=int,default=128);a.add_argument("--seed",type=int,default=712263119);a.add_argument("--net-seed",type=int,default=981284772)
    a=sub.add_parser("compare");a.add_argument("--manifest",type=Path,required=True);a.add_argument("--candidate",type=Path,required=True);a.add_argument("--baseline",type=Path);a.add_argument("--backend",choices=("gmp","decimal"),default="gmp");a.add_argument("--output",type=Path,required=True);a.add_argument("--threads",type=int,nargs="+",default=[1,2]);a.add_argument("--repeats",type=int,default=3);a.add_argument("--base-only",action="store_true");a.add_argument("--case",action="append")
    a=sub.add_parser("direct");a.add_argument("--source",type=Path,required=True,help="the original LRI_C8_D2_HPC package, named explicitly (no sibling default: on our machines that name is another package)");a.add_argument("--candidate-header",type=Path,required=True);a.add_argument("--candidate-flag",action="append",default=[]);a.add_argument("--backend",choices=("gmp","decimal"),default="gmp");a.add_argument("--rounding",nargs="+",choices=("nearest","downward","upward","towardzero"),default=["nearest","downward","upward","towardzero"]);a.add_argument("--output",type=Path,required=True)
    a=sub.add_parser("build-baseline");a.add_argument("--backend",choices=("gmp","decimal"),default="gmp");a.add_argument("--build-record",type=Path);a.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    if args.command=="prepare":
        if any(n<1 or n&(n-1) for n in (args.low_points,args.high_points)):p.error("Point counts must be positive powers of two")
        prepare_manifest(args)
    elif args.command=="profile":
        if args.threads<1:p.error("Thread count must be positive")
        profile(args)
    elif args.command=="compare":
        if args.repeats<1 or any(t<1 for t in args.threads):p.error("Positive repeats and thread counts required")
        compare_binary(args)
    elif args.command=="scaling":
        if args.replicates<2 or args.points<1 or args.points&(args.points-1):p.error("At least two replicates and a positive power-of-two point count required")
        scaling(args)
    elif args.command=="direct":direct(args)
    else:build_baseline(args)


if __name__=="__main__":main()
