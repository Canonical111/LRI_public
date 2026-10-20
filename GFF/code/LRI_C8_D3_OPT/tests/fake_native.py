#!/usr/bin/env python3
"""A stand-in for bin/c8d3_optimized in the Mac tests of the cluster workflow (tests/test_cluster.py).

It answers --describe like the real worker. The 11-argument form reads the task file and writes the native output
schema with deterministic, pseudo-random values in place of an integration. It is not a numerical model.
Test hooks (environment): FAKE_NATIVE_SLEEP seconds to sleep before writing; FAKE_NATIVE_FAIL makes it exit 2;
FAKE_NATIVE_LOG appends one JSON line per invocation.
"""
import hashlib
import json
import os
import sys
import time


def main(argv):
    if argv[1:] == ["--describe"]:
        print(json.dumps({"schema": "c8-d3-build-1", "dimension": 3, "order": 8, "compiler": "fake", "long_double_bits": 64,
                          "mp_backend": "gmp350", "mp_digits10": 350, "openmp": 0, "execution": "fake", "quad_add": "fake"}))
        return 0
    if len(argv) != 12:
        print("graphs_root gamma net tasks output seed layout rate threads sum_mode grid_or_dash", file=sys.stderr)
        return 1
    _, root, gamma, net, tasks_path, out, seed, layout, rate, threads, mode, grid = argv
    if os.environ.get("FAKE_NATIVE_LOG"):
        with open(os.environ["FAKE_NATIVE_LOG"], "a") as f:
            f.write(json.dumps({"pid": os.getpid(), "tasks": tasks_path, "time": time.time()}) + "\n")
    if os.environ.get("FAKE_NATIVE_SLEEP"):
        time.sleep(float(os.environ["FAKE_NATIVE_SLEEP"]))
    if os.environ.get("FAKE_NATIVE_FAIL"):
        print("fake failure", file=sys.stderr)
        return 2
    with open(tasks_path) as f:
        magic, L, n = f.readline().split()
        L, n = int(L), int(n)
        tasks = [list(map(int, f.readline().split())) for _ in range(n)]
    with open(net, "rb") as f:
        bits = int.from_bytes(f.read(12)[8:12], "little")
    rows = []
    for uid, rep, graph, begin, end, total in tasks:
        values = []
        for j in range(2 * (9 - L)):
            h = hashlib.sha256(f"{seed}|{rep}|{graph}|{begin}|{end}|{j}".encode()).digest()
            values.append(f"{(int.from_bytes(h[:6], 'little') / 2**48 - 0.5) * (end - begin):.18e}")
        rows.append({"uid": uid, "rep": rep, "graph": graph, "begin": begin, "end": end, "total": total, "quad": 0,
                     "mp": 0, "seconds": 0.0, "max_abs": "0", "values": values})
    doc = {"schema": "c8-d3-hpc-native-1", "L": L, "seed": int(seed), "layout": int(layout), "bits": bits, "rate": rate,
           "sum_mode": mode, "long_double_bits": 64, "mp_backend": "gmp350", "mp_digits10": 350, "threads": int(threads),
           "load_seconds": 0.0, "integration_seconds": 0.0, "graphs_loaded": len({t[2] for t in tasks}),
           "peak_graphs_resident": 1, "peak_graph_vector_bytes": 0, "graph_batch_limit": 8, "rows": rows}
    with open(out, "w") as f:
        json.dump(doc, f)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
