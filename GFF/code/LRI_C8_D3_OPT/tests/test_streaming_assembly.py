#!/usr/bin/env python3
"""Synthetic complete-plan fixtures for chunk streaming; no physics is estimated."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import assemble
import assemble_streaming as streaming
from campaign import LOOPS,SECTORS,SCHEMA
from io_utils import digest,object_hash

def put(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True)+"\n")

def fixture(root):
    run=root/"run";inventory={s:{str(L):[{"id":0},{"id":1}] for L in LOOPS} for s in SECTORS}
    put(root/"inputs/inventory.json",inventory)
    put(root/"inputs/coverage.json",{"complete":True,"inventory_sha256":digest(root/"inputs/inventory.json"),"synthetic_test_only":True})
    groups=[];jobs=[];evaluations=0
    for tag in ("a","b"):
        for sec in SECTORS:
            for L in LOOPS:
                name=f"{tag}_{sec}_L{L}";width=2*(9-L)
                groups.append({"name":name,"campaign":tag,"sector":sec,"L":L,"rate":.8,"bits":52,"seeds":{"shift":17},"graphs":[{"id":0,"points":16},{"id":1,"points":8}]})
                for begin in (0,4,8,12):
                    tasks=[];rows=[]
                    for rep in range(4):
                        for gid,total in ((0,16),(1,8)):
                            if begin>=total:continue
                            uid=len(tasks);t=[uid,rep,gid,begin,begin+4,total];tasks.append(t)
                            # Widely separated signed magnitudes test Decimal operation order.
                            value=("10000000000000000000000000000000000000000.00000001" if begin==0 else
                                   "-9999999999999999999999999999999999999999.99999999" if begin==4 else "0.000000000000000000001")
                            rows.append(dict(zip(("uid","rep","graph","begin","end","total"),t),quad=0,mp=0,seconds=.01,max_abs="1",values=[value]*width))
                            evaluations+=4
                    index=len(jobs);job={"index":index,"group":name,"L":L,"tasks":tasks}
                    native={"schema":"c8-d3-hpc-native-1","L":L,"seed":17,"bits":52,"layout":0,"sum_mode":"compensated","rate":".8","mp_backend":"gmp350","rows":rows}
                    put(run/"jobs"/f"{index:06d}.job.json",job);put(run/"jobs"/f"{index:06d}.native.json",native)
                    jobs.append({"index":index,"group":name,"sha256":object_hash(job)})
    manifest={"schema":SCHEMA,"campaign_weights":{"a":.5,"b":.5},"loops":list(LOOPS),"all_loops":True,"coverage_verified":True,
              "replicates":4,"groups":groups,"jobs":jobs,"evaluations":evaluations,"executable":{"description":{"mp_backend":"gmp350"}},
              "inputs":{n:digest(root/"inputs"/n) for n in ("inventory.json","coverage.json")},"synthetic_test_only":True}
    publish_manifest(run,manifest);return run,manifest

def publish_manifest(run,manifest):
    put(run/"manifest.json",manifest);mh=digest(run/"manifest.json")
    for entry in manifest["jobs"]:
        index=entry["index"]
        put(run/"jobs"/f"{index:06d}.done.json",{"manifest_sha256":mh,"job_sha256":entry["sha256"],"native_sha256":digest(run/"jobs"/f"{index:06d}.native.json")})

def compare(a,b):
    for sec in SECTORS:
        for tag in ("a","b"):
            for L in LOOPS:assert np.array_equal(a[0][sec][tag][L],b[0][sec][tag][L])
    assert a[1].keys()==b[1].keys()
    for key in a[1]:assert np.array_equal(a[1][key],b[1][key])
    assert a[2]==b[2] and a[3]==b[3] and a[4]==b[4]

def main():
    original0,original1=assemble.ROOT,streaming.ROOT
    try:
        with tempfile.TemporaryDirectory(prefix="c8_stream_fixture_") as tmp:
            root=Path(tmp);assemble.ROOT=streaming.ROOT=root
            run,manifest=fixture(root)
            a=assemble.read_replicates(run);b=streaming.read_replicates_streaming(run);compare(a,b)
            diagnostics=dict(streaming.LAST_DIAGNOSTICS)
            # Reordered but valid chunks remain supported by the original reader.
            manifest["jobs"][0],manifest["jobs"][1]=manifest["jobs"][1],manifest["jobs"][0]
            publish_manifest(run,manifest);assemble.read_replicates(run)
            rejected=False
            try:streaming.read_replicates_streaming(run)
            except ValueError as e:rejected="non-monotone" in str(e)
            assert rejected,"Out-of-order chunks were not explicitly rejected"
            # Missing work is never silently counted as complete.
            manifest["jobs"]=manifest["jobs"][1:];publish_manifest(run,manifest)
            rejected=False
            try:streaming.read_replicates_streaming(run)
            except ValueError:rejected=True
            assert rejected,"Missing work was accepted"
            result={"status":"passed","synthetic_test_only":True,"all_arrays_and_statistics_exact":True,
                    "heterogeneous_graph_net_sizes":True,"multi_chunk_decimal_order_preserved":True,
                    "out_of_order_and_missing_work_rejected":True,"diagnostics":diagnostics}
    finally:assemble.ROOT=original0;streaming.ROOT=original1
    path=original0/"verification/performance/streaming_unit_test.json";path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
