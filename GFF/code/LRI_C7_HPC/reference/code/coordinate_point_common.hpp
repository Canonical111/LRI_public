#define main oldmain
#include "coordinate_integrate.cpp"
#undef main
#include <quadmath.h>
#include <boost/multiprecision/cpp_dec_float.hpp>
using MP=boost::multiprecision::cpp_dec_float_100;
template<class T>T sqrtt(T x){using std::sqrt;return sqrt(x);}template<>__float128 sqrtt(__float128 x){return sqrtq(x);}
template<class T>T logt(T x){using std::log;return log(x);}template<>__float128 logt(__float128 x){return logq(x);}
template<class T>T expt(T x){using std::exp;return exp(x);}template<>__float128 expt(__float128 x){return expq(x);}
struct OptTerm{vector<array<int,3>>e;};
struct OG{Graph g;vector<OptTerm>terms;};
struct Sec{int masks[28],bmax[6];LD alpha[6];};
Sec sector(const OG&g,int L,const array<unsigned char,8>&vp,const array<unsigned char,8>&gp,LD rate){int n=L+1,pos[8],rank[7],minr[28];for(int j=0;j<n;j++)pos[vp[j]]=j;for(int j=0;j<L;j++)rank[gp[j]]=j;Sec s{};int k=0;for(int a=0;a<n;a++)for(int b=a+1;b<n;b++){int lo=min(pos[a],pos[b]),hi=max(pos[a],pos[b]),mask=0;for(int j=lo;j<hi;j++)mask|=1<<rank[j];s.masks[k]=mask;minr[k]=__builtin_ctz(mask);k++;}for(auto&t:g.terms){int bs[6]={};for(auto&e:t.e)for(int j=0;j<minr[e[0]];j++)bs[j]+=e[1];for(int j=0;j<L-1;j++)s.bmax[j]=max(s.bmax[j],bs[j]);}for(int j=0;j<L-1;j++){LD p=L-1-j-s.bmax[j]/2.L;if(p<0)throw runtime_error("power in free graph");s.alpha[j]=rate*max(.5L,p);}return s;}
template<class T>array<T,7> point(const OG&g,int L,int K,const Sec&s,const LD*logtvals,LD*rat){int D=L-1,sz=1<<L;T gap[7];gap[0]=1;T weight=1;for(int j=0;j<D;j++){T tt=expt(T(logtvals[j]));gap[j+1]=gap[j]*tt;weight*=expt(T((D-j-s.alpha[j])*logtvals[j]))/T(s.alpha[j]);}T dist[128]={},iv[28],logs[28];for(int mask=1;mask<sz;mask++){int bit=__builtin_ctz(mask);dist[mask]=dist[mask^(1<<bit)]+gap[bit];}int NE=L*(L+1)/2;for(int k=0;k<NE;k++){iv[k]=1/sqrtt(dist[s.masks[k]]);logs[k]=logt(dist[s.masks[k]])/2;}array<T,7>sum{};T absum[7]={};for(auto&t:g.terms){T H=0,R=0,base=1,lv=0;for(auto&e:t.e){int k=e[0],m=e[1];H+=m*dist[s.masks[k]];R+=e[2]*dist[s.masks[k]];T v=iv[k];if(m==1)base*=v;else if(m==2)base*=v*v;else base*=v*v*v;lv+=m*logs[k];}if(R==0)continue;base*=R/H;lv-=L*logt(H);for(int j=0;j<=K;j++){sum[j]+=base;absum[j]+=base<0?-base:base;base*=lv/(j+1);}}if(rat){*rat=1;for(int j=0;j<=K;j++)if(absum[j]>0)*rat=min(*rat,abs((LD)(sum[j]/absum[j])));}for(int j=0;j<=K;j++)sum[j]*=weight;return sum;}
