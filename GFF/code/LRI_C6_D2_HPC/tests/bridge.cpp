#include "../src/kernel.hpp"
#include <cstdio>
static Graph graph;static Scratch scratch;
extern "C" int load_single(const char*p){try{graph=load_graph(p,1);scratch.resize(graph);return graph.id;}catch(...){return -1;}}
// The value is returned as a long-double decimal string: scaled test points reach 1e-395, far below double range.
extern "C" int eval_check(int unused,const double*lx,int*level,char*out,int size){try{ld a[12],factor=0;for(int j=0;j<graph.E;++j){a[j]=lx[j];factor+=a[j]/2;}auto v=evaluate(graph,a,factor,scratch);*level=v.level;
    return std::snprintf(out,size,"%.25Le",v.y/graph.Z)<size?0:-2;}catch(...){*level=-1;return -1;}}
