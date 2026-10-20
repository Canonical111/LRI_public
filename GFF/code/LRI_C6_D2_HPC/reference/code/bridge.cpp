#include "kernel.hpp"
static vector<Graph> GR;
extern "C" int load_check(const char*k,const char*r){GR=load(k,r);return GR.size();}
extern "C" double eval_check(int i,const double*lx,int*level){vector<ld>x(GR.at(i).E);ld fac=0;for(int j=0;j<GR[i].E;j++){x[j]=lx[j];fac+=D/4.L*x[j];}auto y=evaluate(GR[i],x,fac);*level=y.level;return double(y.y/GR[i].Z);}
