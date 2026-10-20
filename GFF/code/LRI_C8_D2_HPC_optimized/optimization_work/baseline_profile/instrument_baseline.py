#!/usr/bin/env python3
"""Create private timing-instrumented copies; never rewrite production sources."""
from pathlib import Path
import hashlib
import json
import shutil


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise RuntimeError(f"Unsupported baseline: expected {count} occurrences of {old[:110]!r}; got {text.count(old)}")
    return text.replace(old, new)


def prepare(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    header = (source / "src/kernel.hpp").read_text()
    worker = (source / "src/c8d2_integrate.cpp").read_text()
    originals = {"kernel.hpp": header, "c8d2_integrate.cpp": worker}
    header = replace(header, "struct Term {", '#include "profiling_support.hpp"\nstruct Term {')
    header = replace(header, "    std::ifstream f(path);std::string magic;Graph g;int M=0,T=0,n=0;",
                     "    double profile_t=bench_profile::start(bench_profile::Parse);\n    std::ifstream f(path);std::string magic;Graph g;int M=0,T=0,n=0;")
    header = replace(header, 'rates(g,scale);prepare(g);return g;',
                     'bench_profile::stop(bench_profile::Parse,profile_t);profile_t=bench_profile::start(bench_profile::Rates);rates(g,scale);bench_profile::stop(bench_profile::Rates,profile_t);profile_t=bench_profile::start(bench_profile::Prepare);prepare(g);bench_profile::stop(bench_profile::Prepare,profile_t);bench_profile::graph(g);return g;')
    # Substage markers surround original expressions, without rewriting them.
    start = header.index("inline std::pair<ld,ld> calculate_products")
    end = header.index("// Shared fallbacks", start)
    code = header[start:end]
    code = replace(code, "    s.S=0;s.products[0]=1;s.sums[0]=0;", "    double profile_t=bench_profile::start(bench_profile::LDExp);\n    s.S=0;s.products[0]=1;s.sums[0]=0;")
    code = replace(code, "    for(size_t j=0;j<g.products.size();++j)", "    bench_profile::stop(bench_profile::LDExp,profile_t);profile_t=bench_profile::start(bench_profile::LDProducts);\n    for(size_t j=0;j<g.products.size();++j)")
    code = replace(code, "#ifndef NO_SUM_SHARING", "    bench_profile::stop(bench_profile::LDProducts,profile_t);profile_t=bench_profile::start(bench_profile::LDSums);\n#ifndef NO_SUM_SHARING")
    code = replace(code, "    for(size_t j=0;j<g.numerators.size();++j)", "    bench_profile::stop(bench_profile::LDSums,profile_t);profile_t=bench_profile::start(bench_profile::LDNum);\n    for(size_t j=0;j<g.numerators.size();++j)")
    code = replace(code, "    ld val=0,err=0;for(const auto&t:g.terms){ld U=", "    bench_profile::stop(bench_profile::LDNum,profile_t);profile_t=bench_profile::start(bench_profile::LDForest);\n    ld val=0,err=0;for(const auto&t:g.terms){ld U=", count=2)
    code = replace(code, "    return {val/s.S,err/s.S};", "    auto result=std::make_pair(val/s.S,err/s.S);bench_profile::stop(bench_profile::LDForest,profile_t);return result;")
    header = header[:start] + code + header[end:]
    start = header.index("std::pair<T,T> calculate_shared")
    end = header.index("inline Eval evaluate", start)
    code = header[start:end]
    code = replace(code, "    static thread_local PromotedScratch<T> scratch;", "    bench_profile::promoted<T>(g,shift);double profile_t=bench_profile::start(bench_profile::phase<T>(0));\n    static thread_local PromotedScratch<T> scratch;")
    code = replace(code, "    for(int j=0;j<g.E;++j)", "    bench_profile::stop(bench_profile::phase<T>(0),profile_t);profile_t=bench_profile::start(bench_profile::phase<T>(1));\n    for(int j=0;j<g.E;++j)")
    code = replace(code, "    for(size_t j=0;j<g.products.size();++j)", "    bench_profile::stop(bench_profile::phase<T>(1),profile_t);profile_t=bench_profile::start(bench_profile::phase<T>(2));\n    for(size_t j=0;j<g.products.size();++j)")
    code = replace(code, "    for(size_t j=0;j<g.segments.size();++j)", "    bench_profile::stop(bench_profile::phase<T>(2),profile_t);profile_t=bench_profile::start(bench_profile::phase<T>(3));\n    for(size_t j=0;j<g.segments.size();++j)")
    code = replace(code, "    for(size_t j=0;j<g.numerators.size();++j)", "    bench_profile::stop(bench_profile::phase<T>(3),profile_t);profile_t=bench_profile::start(bench_profile::phase<T>(4));\n    for(size_t j=0;j<g.numerators.size();++j)")
    code = replace(code, "    T val=0,err=0;", "    bench_profile::stop(bench_profile::phase<T>(4),profile_t);profile_t=bench_profile::start(bench_profile::phase<T>(5));\n    T val=0,err=0;")
    code = replace(code, "    return {val/S,NeedError?err/S:T(0)};", "    std::pair<T,T> result{val/S,NeedError?err/S:T(0)};bench_profile::stop(bench_profile::phase<T>(5),profile_t);return result;")
    header = header[:start] + code + header[end:]
    header = replace(header, "    ld shift=0;bool direct=true;", "    double profile_t=bench_profile::start(bench_profile::Preamble);ld shift=0;bool direct=true;")
    header = replace(header, "    auto v=moderate?", "    bench_profile::local.shifted+=shift!=0;bench_profile::local.nonmoderate+=!moderate;bench_profile::stop(bench_profile::Preamble,profile_t);profile_t=bench_profile::start(bench_profile::LDTotal);\n    auto v=moderate?")
    header = replace(header, "    ld ratio=", "    bench_profile::stop(bench_profile::LDTotal,profile_t);\n    ld ratio=")
    header = replace(header, "if(ratio<1e-9L){auto q=calculate_shared<Q>(g,lx,shift);", "if(ratio<1e-9L){profile_t=bench_profile::start(bench_profile::QTotal);auto q=calculate_shared<Q>(g,lx,shift);bench_profile::stop(bench_profile::QTotal,profile_t);")
    header = replace(header, "{auto m=calculate_shared<MP,false>(g,lx,shift);f=m.first.convert_to<ld>();", "{profile_t=bench_profile::start(bench_profile::MPTotal);auto m=calculate_shared<MP,false>(g,lx,shift);f=m.first.convert_to<ld>();bench_profile::stop(bench_profile::MPTotal,profile_t);")
    header = replace(header, "    ld y=f*expl(factor-shift)*g.Z;", "    profile_t=bench_profile::start(bench_profile::Scale);ld y=f*expl(factor-shift)*g.Z;")
    header = replace(header, 'throw std::runtime_error("nonfinite integrand");return {y,lev};', 'throw std::runtime_error("nonfinite integrand");bench_profile::stop(bench_profile::Scale,profile_t);return {y,lev};')
    header = replace(header, '    if(K<0 || K>6)', '    ++bench_profile::local.samples;double profile_t=bench_profile::start(bench_profile::Mapping);\n    if(K<0 || K>6)')
    header = replace(header, '    auto v=evaluate(g,s.lx.data(),fac,s);level=', '    bench_profile::stop(bench_profile::Mapping,profile_t);auto v=evaluate(g,s.lx.data(),fac,s);profile_t=bench_profile::start(bench_profile::Jet);level=')
    header = replace(header, 'out[j]*=v.y;return out;', 'out[j]*=v.y;bench_profile::stop(bench_profile::Jet,profile_t);return out;')
    worker = replace(worker, 'int main(int argc,char**argv){try {', 'int main(int argc,char**argv){bench_profile::install();try {')
    worker = replace(worker, '            Net net(', '            double profile_t=bench_profile::start(bench_profile::NetSetup);Net net(')
    worker = replace(worker, 't.begin);\n            std::array<ld,32>', 't.begin);bench_profile::stop(bench_profile::NetSetup,profile_t);\n            std::array<ld,32>')
    worker = replace(worker, 'for(uint64_t i=t.begin;i<t.end;++i){if(i>t.begin)', 'for(uint64_t i=t.begin;i<t.end;++i){profile_t=bench_profile::start(bench_profile::NetPoint);if(i>t.begin)')
    worker = replace(worker, '                int level;auto v=sample', '                bench_profile::stop(bench_profile::NetPoint,profile_t);int level;auto v=sample')
    worker = replace(worker, 'K,logs,level,layout,scratch);r.q+=', 'K,logs,level,layout,scratch);profile_t=bench_profile::start(bench_profile::Accumulate);r.q+=')
    worker = replace(worker, 'v[0]));}\n            for(int j=0;', 'v[0]));bench_profile::stop(bench_profile::Accumulate,profile_t);}\n            for(int j=0;')
    worker = replace(worker, '        }}\n    }\n    if(!error.empty())', '        }}\n        bench_profile::merge();\n    }\n    if(!error.empty())')
    worker = replace(worker, '    std::cerr<<"completed ', '    bench_profile::write();\n    std::cerr<<"completed ')
    (destination / "kernel.hpp").write_text(header)
    (destination / "c8d2_integrate.cpp").write_text(worker)
    support = Path(__file__).with_name("profiling_support.hpp")
    if support.resolve() != (destination / support.name).resolve():
        shutil.copy2(support, destination / support.name)
    record = {"original_root": str(source.resolve()), "original_source_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k,v in originals.items()},
              "instrumented_source_sha256": {k: hashlib.sha256((destination/k).read_bytes()).hexdigest() for k in ["kernel.hpp","c8d2_integrate.cpp","profiling_support.hpp"]},
              "method": "statement boundary clocks, inclusive tier totals, thread-local GMP allocator counters, getrusage; private copied sources only"}
    (destination / "source_record.json").write_text(json.dumps(record,indent=2)+"\n")
    return record


if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("source",type=Path);p.add_argument("destination",type=Path)
    a=p.parse_args();prepare(a.source,a.destination)
