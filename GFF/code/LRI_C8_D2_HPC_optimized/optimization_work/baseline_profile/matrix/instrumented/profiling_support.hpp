#pragma once
// Instrumentation is compiled only into a private copy of the original kernel.
// Scientific arithmetic is unchanged. Timings are inclusive where documented.
#include <chrono>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <mutex>
#include <sys/resource.h>
#include <type_traits>
namespace bench_profile {
enum Stage { Parse, Rates, Prepare, NetSetup, NetPoint, Mapping, Preamble,
    LDTotal, LDExp, LDProducts, LDSums, LDNum, LDForest,
    QTotal, QSetup, QExp, QProducts, QSums, QNum, QForest,
    MPTotal, MPSetup, MPExp, MPProducts, MPSums, MPNum, MPForest,
    Jet, Accumulate, Scale, Other, StageCount };
inline const char* names[StageCount]={"load_parse","load_rates","load_prepare",
    "net_setup","net_point_grid","mapping","evaluate_preamble",
    "ld_total","ld_exp","ld_products","ld_ordered_sums","ld_numerators","ld_forest_divisions",
    "quad_total","quad_setup","quad_exp","quad_products","quad_ordered_sums","quad_numerators","quad_forest_divisions",
    "mp_total","mp_setup","mp_exp","mp_products","mp_ordered_sums","mp_numerators","mp_forest_divisions",
    "jet","accumulation","evaluate_scale","other"};
struct Stats {
    double seconds[StageCount]{};
    unsigned long long calls[StageCount]{}, allocs[StageCount]{}, reallocs[StageCount]{},
        frees[StageCount]{}, bytes[StageCount]{};
    unsigned long long shifted=0, nonmoderate=0, samples=0,
        mp_products=0,mp_addends=0,mp_segments=0,mp_numerators=0,mp_coefficients=0,mp_terms=0,
        quad_products=0,quad_addends=0,quad_segments=0,quad_numerators=0,quad_coefficients=0,quad_terms=0,
        mp_shifted=0,quad_shifted=0,load_graphs=0,graph_bytes=0,largest_graph_bytes=0;
};
inline thread_local Stats local;
inline thread_local Stage active=Other;
inline Stats total;
inline std::mutex mutex;
inline double clock(){return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();}
inline double start(Stage s){active=s;return clock();}
inline void stop(Stage s,double t){local.seconds[s]+=clock()-t;++local.calls[s];}
inline void merge(){std::lock_guard<std::mutex> lock(mutex);
    for(int i=0;i<StageCount;++i){total.seconds[i]+=local.seconds[i];total.calls[i]+=local.calls[i];
        total.allocs[i]+=local.allocs[i];total.reallocs[i]+=local.reallocs[i];total.frees[i]+=local.frees[i];total.bytes[i]+=local.bytes[i];}
    total.shifted+=local.shifted;total.nonmoderate+=local.nonmoderate;total.samples+=local.samples;
    total.mp_products+=local.mp_products;total.mp_addends+=local.mp_addends;total.mp_segments+=local.mp_segments;
    total.mp_numerators+=local.mp_numerators;total.mp_coefficients+=local.mp_coefficients;total.mp_terms+=local.mp_terms;
    total.quad_products+=local.quad_products;total.quad_addends+=local.quad_addends;total.quad_segments+=local.quad_segments;
    total.quad_numerators+=local.quad_numerators;total.quad_coefficients+=local.quad_coefficients;total.quad_terms+=local.quad_terms;
    total.mp_shifted+=local.mp_shifted;total.quad_shifted+=local.quad_shifted;
    total.load_graphs+=local.load_graphs;total.graph_bytes+=local.graph_bytes;
    total.largest_graph_bytes=std::max(total.largest_graph_bytes,local.largest_graph_bytes);local=Stats{};
}
template<class G> void graph(const G&g){
    unsigned long long bytes=sizeof(G)+g.masks.capacity()*sizeof(unsigned)+g.terms.capacity()*sizeof(typename decltype(g.terms)::value_type)
        +(g.alpha.capacity()+g.dp.capacity()+g.choice_total.capacity())*sizeof(ld)
        +g.products.capacity()*sizeof(std::pair<int,int>)+g.mon_ids.capacity()*sizeof(int)
        +g.segments.capacity()*sizeof(typename decltype(g.segments)::value_type)+g.addends.capacity()*sizeof(int)
        +g.numerators.capacity()*sizeof(typename decltype(g.numerators)::value_type);
    for(const auto&t:g.terms)bytes+=(t.ids.capacity()+t.co.capacity())*sizeof(int);
    for(const auto&n:g.numerators)bytes+=n.capacity()*sizeof(std::pair<int,int>);
    ++local.load_graphs;local.graph_bytes+=bytes;local.largest_graph_bytes=std::max(local.largest_graph_bytes,bytes);
}
template<class T,class G> void promoted(const G&g,ld shift){
    unsigned long long coeff=0;for(const auto&n:g.numerators)coeff+=n.size();
    if constexpr(std::is_same<T,Q>::value){local.quad_products+=g.products.size();local.quad_addends+=g.addends.size();
        local.quad_segments+=g.segments.size();local.quad_numerators+=g.numerators.size();local.quad_coefficients+=coeff;local.quad_terms+=g.terms.size();local.quad_shifted+=shift!=0;}
    else{local.mp_products+=g.products.size();local.mp_addends+=g.addends.size();local.mp_segments+=g.segments.size();
        local.mp_numerators+=g.numerators.size();local.mp_coefficients+=coeff;local.mp_terms+=g.terms.size();local.mp_shifted+=shift!=0;}
}
template<class T> constexpr Stage phase(int offset){return Stage((std::is_same<T,Q>::value?QSetup:MPSetup)+offset);}
#ifdef C8_USE_GMP
inline void* allocate(size_t n){++local.allocs[active];local.bytes[active]+=n;void*p=std::malloc(n);if(!p)std::abort();return p;}
inline void* reallocate(void*p,size_t,size_t n){++local.reallocs[active];local.bytes[active]+=n;p=std::realloc(p,n);if(!p)std::abort();return p;}
inline void deallocate(void*p,size_t){++local.frees[active];std::free(p);}
inline void install(){mp_set_memory_functions(allocate,reallocate,deallocate);}
#else
inline void install(){}
#endif
inline void write(){
    merge();const char* path=std::getenv("C8_BENCH_PROFILE");if(!path)return;
    struct rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::ofstream f(path);if(!f)throw std::runtime_error("cannot open profile sidecar");
    f<<std::setprecision(17)<<"{\"schema\":\"c8-private-kernel-profile-1\",\"stages\":{";
    for(int i=0;i<StageCount;++i){if(i)f<<',';f<<'"'<<names[i]<<"\":{\"seconds\":"<<total.seconds[i]<<",\"calls\":"<<total.calls[i]
        <<",\"gmp_allocations\":"<<total.allocs[i]<<",\"gmp_reallocations\":"<<total.reallocs[i]<<",\"gmp_frees\":"<<total.frees[i]<<",\"gmp_requested_bytes\":"<<total.bytes[i]<<'}';}
    f<<"},\"counts\":{\"samples\":"<<total.samples<<",\"shifted\":"<<total.shifted<<",\"nonmoderate\":"<<total.nonmoderate
        <<",\"mp_shifted\":"<<total.mp_shifted<<",\"quad_shifted\":"<<total.quad_shifted
        <<",\"mp_products\":"<<total.mp_products<<",\"mp_addends\":"<<total.mp_addends<<",\"mp_segments\":"<<total.mp_segments
        <<",\"mp_numerators\":"<<total.mp_numerators<<",\"mp_coefficients\":"<<total.mp_coefficients<<",\"mp_terms\":"<<total.mp_terms
        <<",\"quad_products\":"<<total.quad_products<<",\"quad_addends\":"<<total.quad_addends<<",\"quad_segments\":"<<total.quad_segments
        <<",\"quad_numerators\":"<<total.quad_numerators<<",\"quad_coefficients\":"<<total.quad_coefficients<<",\"quad_terms\":"<<total.quad_terms
        <<"},\"memory\":{\"max_rss_kib\":"<<usage.ru_maxrss<<",\"loaded_graphs\":"<<total.load_graphs
        <<",\"persistent_graph_capacity_bytes\":"<<total.graph_bytes<<",\"largest_graph_capacity_bytes\":"<<total.largest_graph_bytes
        <<",\"sizeof_long_double\":"<<sizeof(ld)<<",\"sizeof_quad\":"<<sizeof(Q)<<",\"sizeof_mp_object\":"<<sizeof(MP)
        <<"},\"process_cpu\":{\"user_seconds\":"<<usage.ru_utime.tv_sec+usage.ru_utime.tv_usec/1e6
        <<",\"system_seconds\":"<<usage.ru_stime.tv_sec+usage.ru_stime.tv_usec/1e6<<"}}\n";
    if(!f)throw std::runtime_error("profile sidecar write failed");
}
}
