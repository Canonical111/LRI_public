#pragma once
#include <chrono>
#include <atomic>
#include <iostream>
namespace profiling {
constexpr int N=18;
inline thread_local unsigned long long ns[N]={},calls[N]={};
inline std::atomic<unsigned long long> all_ns[N]{},all_calls[N]{};
struct Guard {int id;std::chrono::steady_clock::time_point start;Guard(int i):id(i),start(std::chrono::steady_clock::now()){}~Guard(){ns[id]+=std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-start).count();++calls[id];}};
inline void collect(){for(int i=0;i<N;++i){all_ns[i]+=ns[i];all_calls[i]+=calls[i];ns[i]=calls[i]=0;}}
inline void dump(){collect();const char* names[]={"load_total","rates","prepare","sample_total","evaluate_total","long_double","quad","multiprecision","q_exp","q_products","q_sums","q_numerators","q_terms","mp_exp","mp_products","mp_sums","mp_numerators","mp_terms"};for(int i=0;i<N;++i)std::cerr<<"PROFILE "<<names[i]<<" "<<all_ns[i]<<" "<<all_calls[i]<<"\n";}
}
