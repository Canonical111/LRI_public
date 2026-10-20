// Numerical Laurent residues of five-loop LR phi^4 graphs in one dimension.
// Graph weights are integers scaled by 144; all position orderings are included.
// An ordered-gap sector and its reversal have equal graph sums, hence 60 sectors.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <string>
#include <vector>
#include <omp.h>
#include <immintrin.h>
struct DD{__m512d hi,lo;};
inline DD zeroDD(){return {_mm512_setzero_pd(),_mm512_setzero_pd()};}
inline DD addDD(DD a,DD b){
 __m512d s=_mm512_add_pd(a.hi,b.hi), bb=_mm512_sub_pd(s,a.hi);
 __m512d e=_mm512_add_pd(_mm512_sub_pd(a.hi,_mm512_sub_pd(s,bb)),_mm512_sub_pd(b.hi,bb));
 e=_mm512_add_pd(e,_mm512_add_pd(a.lo,b.lo));
 __m512d h=_mm512_add_pd(s,e);return{h,_mm512_sub_pd(e,_mm512_sub_pd(h,s))};
}
inline DD mulDD(DD a,DD b){
 __m512d p=_mm512_mul_pd(a.hi,b.hi),e=_mm512_fmsub_pd(a.hi,b.hi,p);
 e=_mm512_fmadd_pd(a.hi,b.lo,e);e=_mm512_fmadd_pd(a.lo,b.hi,e);e=_mm512_fmadd_pd(a.lo,b.lo,e);
 __m512d h=_mm512_add_pd(p,e);return{h,_mm512_sub_pd(e,_mm512_sub_pd(h,p))};
}
inline DD scaleDD(DD a,double v){
 __m512d b=_mm512_set1_pd(v),p=_mm512_mul_pd(a.hi,b),e=_mm512_fmsub_pd(a.hi,b,p);e=_mm512_fmadd_pd(a.lo,b,e);
 __m512d h=_mm512_add_pd(p,e);return{h,_mm512_sub_pd(e,_mm512_sub_pd(h,p))};
}
inline DD packDD(const long double*a){alignas(64)double h[8],l[8];for(int i=0;i<8;i++){h[i]=(double)a[i];l[i]=(double)(a[i]-(long double)h[i]);}return{_mm512_load_pd(h),_mm512_load_pd(l)};}
inline long double sumDD(DD a){alignas(64)double h[8],l[8];_mm512_store_pd(h,a.hi);_mm512_store_pd(l,a.lo);long double s=0;for(int i=0;i<8;i++)s+=(long double)h[i]+(long double)l[i];return s;}

using namespace std;
using Real=long double;
using Clock=chrono::steady_clock;
struct Term{int l,r; Real a,b;};
struct Group{int id; vector<Term> terms;};
struct Sector{array<int,10> masks; vector<Group> groups;};
int main(int argc,char**argv){
 int N=argc>1?atoi(argv[1]):8; bool span=false;int nt=argc>3?atoi(argv[3]):4;omp_set_num_threads(nt);
 string root=argc>2?string(argv[2]):string("."); if(root.back()!='/')root+="/";
 FILE*f=fopen((root+"graphs6.bin").c_str(),"rb");if(!f)return 2;fseek(f,0,SEEK_END);long bytes=ftell(f);rewind(f);if(bytes%sizeof(array<int,17>))return 4;vector<array<int,17>> G(bytes/sizeof(array<int,17>));fread(G.data(),sizeof(G[0]),G.size(),f);fclose(f);
 int nnode=N+1,NP=nnode*nnode*nnode*nnode;
 vector<Real>qw(4*11*5*nnode);f=fopen((root+"qweights5_"+to_string(N)+".bin").c_str(),"rb");if(!f)return 3;fread(qw.data(),sizeof(Real),qw.size(),f);fclose(f);
 auto qwi=[&](int j,int b,int r,int i)->Real{return qw[(((j*11+b)*5+r)*nnode)+i];};
 vector<pair<int,int>>edges;for(int i=0;i<6;i++)for(int j=i+1;j<6;j++)edges.push_back({i,j});
 vector<int>nonadj;for(int i=0;i<15;i++)if(edges[i].second>edges[i].first+1)nonadj.push_back(i);
 vector<array<int,5>>left,right;map<array<int,5>,int>lm,rm;vector<pair<int,int>>lr;
 for(auto&g:G){array<int,5>a,b;for(int i=0;i<5;i++){a[i]=g[nonadj[i]];b[i]=g[nonadj[i+5]];}
 if(!lm.count(a)){lm[a]=left.size();left.push_back(a);}if(!rm.count(b)){rm[b]=right.size();right.push_back(b);}lr.push_back({lm[a],rm[b]});}
 map<array<int,4>,int> group_ids;vector<array<int,4>>bs;vector<Sector>sectors;
 array<int,5>perm{0,1,2,3,4};
 do{
 // Choose one representative from the reversal pair.
 array<int,5> rev;for(int i=0;i<5;i++)rev[i]=4-perm[i];if(perm>rev)continue;
 int rank[5];for(int i=0;i<5;i++)rank[perm[i]]=i;
 int mins[15],masks[15];for(int e=0;e<15;e++){int mask=0;for(int k=edges[e].first;k<edges[e].second;k++)mask|=1<<rank[k];masks[e]=mask;mins[e]=__builtin_ctz((unsigned)mask);}
 Sector sec;for(int i=0;i<10;i++)sec.masks[i]=masks[nonadj[i]];
 map<int,vector<Term>>groups;
 for(int gi=0;gi<(int)G.size();gi++){auto&g=G[gi];array<int,4>b{};for(int e=0;e<15;e++)for(int j=0;j<mins[e];j++)b[j]+=g[e];
 if(!group_ids.count(b)){group_ids[b]=bs.size();bs.push_back(b);}int id=group_ids[b];groups[id].push_back({lr[gi].first,lr[gi].second,Real(g[15]),Real(g[16])});}
 for(auto&kv:groups){auto&terms=kv.second;sort(terms.begin(),terms.end(),[](auto&a,auto&b){return a.l<b.l||(a.l==b.l&&a.r<b.r);});sec.groups.push_back({kv.first,move(terms)});}sectors.push_back(move(sec));
 }while(next_permutation(perm.begin(),perm.end()));
 int NG=bs.size(); for(auto b:bs)for(int j=0;j<4;j++)if(2*(3-j)-b[j]==-4){cerr<<"derivative rows not supported in combined SIMD driver";return 9;}cout<<"N="<<N<<" cutoffs=both"<<" nodes="<<NP<<" groups="<<NG<<" sectors="<<sectors.size()<<" left="<<left.size()<<" right="<<right.size()<<endl;
 auto t0=Clock::now();
 // At each point, precompute the Laurent coefficients of the tensor-product
 // quadrature functional. Row r is the coefficient of epsilon^(-r).
 
 // Pole quadrature weights vanish away from t_j=0, except for the rare
 // a=-2 resonance, whose residue is the derivative at t_j=0. Store the
 // nonzero Laurent rows sparsely by endpoint pattern.
 vector<array<int,342>> tailMap(16);int ntail[16]={};
 for(int mask=0;mask<16;mask++)for(int id=0;id<NG;id++){
  bool active=false;
  for(int j=0;j<4;j++){int a2=2*(3-j)-bs[id][j];
   if(a2==-4 || (a2==-2&&(mask&(1<<j))))active=true;}
  tailMap[mask][id]=active?ntail[mask]++:-1;
 }
 vector<int> zeroMask(NP);vector<size_t> offset(NP+1);
 for(int p=0;p<NP;p++){int v=p,mask=0;for(int j=3;j>=0;j--){if(v%nnode==N)mask|=1<<j;v/=nnode;}zeroMask[p]=mask;offset[p+1]=offset[p]+NG+4*ntail[mask];}
 vector<Real>W(offset[NP]);vector<Real>Q((size_t)NP*32*4);vector<Real>LH(NP);
 #pragma omp parallel for schedule(static)
 for(int p=0;p<NP;p++){
 int ind[4],v=p;Real t[4];for(int j=3;j>=0;j--){ind[j]=v%nnode;v/=nnode;t[j]=(1+cos(acosl(-1.L)*ind[j]/N))/2;if(ind[j]==0)t[j]=1;if(ind[j]==N)t[j]=0;}
 for(int mask=1;mask<32;mask++){
 int mini=__builtin_ctz((unsigned)mask);Real q=1,z=1;for(int r=mini+1;r<5;r++){z*=t[r-1];if(mask&(1<<r))q+=z;}
 Real*o=&Q[((size_t)p*32+mask)*4];o[0]=1/sqrt(q);o[1]=o[0]*o[0];o[2]=o[1]*o[0];o[3]=.5*log(q);if(mask==31)LH[p]=5*log(q);
 }
 for(int id=0;id<NG;id++){
 Real a[9]={0};a[4]=1;
 for(int j=0;j<4;j++){
 Real b[9]={0};for(int k=-j;k<=4-j;k++)if(a[k+4]!=0)for(int r=-1;r<=3;r++)if(k+r>=-j-1&&k+r<=3-j)b[k+r+4]+=a[k+4]*qwi(j,bs[id][j],r+1,ind[j]);
 memcpy(a,b,sizeof(a));}
 W[offset[p]+id]=a[4];
 int ti=tailMap[zeroMask[p]][id];if(ti>=0)for(int r=1;r<=4;r++)W[offset[p]+NG+4*ti+r-1]=a[4-r];
 }
 }
 cout<<"Precomputed in "<<chrono::duration<Real>(Clock::now()-t0).count()<<" s; W MB="<<W.size()*8./1e6<<endl;
  array<Real,11> total{};
 for(int si=0;si<(int)sectors.size();si++){
  auto&sec=sectors[si];vector<array<Real,11>>partials(nt);
  #pragma omp parallel
  {
   int tid=omp_get_thread_num();array<Real,11>sum{}; DD regular=zeroDD();
   vector<DD>lv(left.size()),rv(right.size());
   vector<array<Real,8>>vl(left.size()),vr(right.size()),ll(left.size()),rl(right.size());
   int NB=(NP+7)/8;
   #pragma omp for schedule(static)
   for(int ip=0;ip<NB;ip++){
    int pp=8*ip,lanes=min(8,NP-pp);
    for(int lane=0;lane<lanes;lane++){
     int p=pp+lane;Real powers[10][4],logs[10];
     for(int i=0;i<10;i++){auto*q=&Q[((size_t)p*32+sec.masks[i])*4];powers[i][0]=1;for(int j=1;j<=3;j++)powers[i][j]=q[j-1];logs[i]=q[3];}
     bool needlog=zeroMask[p]!=0;
     for(int h=0;h<(int)left.size();h++){Real z=1,l=0;for(int j=0;j<5;j++){int e=left[h][j];z*=powers[j][e];if(needlog)l+=e*logs[j];}vl[h][lane]=z;ll[h][lane]=l;}
     for(int h=0;h<(int)right.size();h++){Real z=1,l=0;for(int j=0;j<5;j++){int e=right[h][j];z*=powers[j+5][e];if(needlog)l+=e*logs[j+5];}vr[h][lane]=z;rl[h][lane]=l;}
    }
    for(int h=0;h<(int)left.size();h++){for(int k=lanes;k<8;k++)vl[h][k]=0;lv[h]=packDD(vl[h].data());}
    for(int h=0;h<(int)right.size();h++){for(int k=lanes;k<8;k++)vr[h][k]=0;rv[h]=packDD(vr[h].data());}
    DD reg=zeroDD();
    for(auto&group:sec.groups){
     DD a=zeroDD();
     for(auto&term:group.terms)a=addDD(a,scaleDD(mulDD(lv[term.l],rv[term.r]),double(term.a)));
     Real weights[8]={};for(int k=0;k<lanes;k++)weights[k]=W[offset[pp+k]+group.id];
     reg=addDD(reg,mulDD(packDD(weights),a));
    }
    regular=addDD(regular,reg);
    // All nonregular Laurent rows have endpoint support in the combined channel.
    for(int lane=0;lane<lanes;lane++){
     int p=pp+lane;if(zeroMask[p]==0)continue;
     Real psum[5]={};
     for(auto&group:sec.groups){
      int ti=tailMap[zeroMask[p]][group.id];if(ti<0)continue;
      Real w[5]={};for(int j=1;j<=4;j++)w[j]=W[offset[p]+NG+4*ti+j-1];
      int maxr=4;while(maxr>0&&w[maxr]==0)maxr--;if(!maxr)continue;
      Real moment[5]={};
      for(auto&term:group.terms){
       Real za=term.a*vl[term.l][lane]*vr[term.r][lane],k=ll[term.l][lane]+rl[term.r][lane],v=za;
       moment[0]+=v;for(int j=1;j<=maxr;j++){v*=k/j;moment[j]+=v;}
      }
      for(int r=0;r<=maxr;r++)for(int j=max(1,r);j<=maxr;j++)psum[r]+=w[j]*moment[j-r];
     }
     Real h=-LH[p],hp[5]={1,h,h*h/2,h*h*h/6,h*h*h*h/24};
     for(int r=0;r<=4;r++){sum[1+r]+=psum[r];for(int j=r;j<=4;j++)sum[6+r]+=psum[j]*hp[j-r];}
    }
   }
   sum[0]=sumDD(regular);partials[tid]=sum;
  }
  for(auto&a:partials)for(int i=0;i<11;i++)total[i]+=a[i];
  if((si+1)%5==0||si+1==(int)sectors.size())cout<<"Sector "<<si+1<<"/"<<sectors.size()<<" time "<<chrono::duration<double>(Clock::now()-t0).count()<<" s"<<endl;
 }
 for(int cut=0;cut<2;cut++){
  string filename=root+"combined5_"+(cut?"span":"maxgap")+"_"+to_string(N)+".json";ofstream out(filename);out<<setprecision(24)<<"{\n  \"H\": {";
  for(int r=4;r>=0;r--){if(r<4)out<<", ";out<<"\""<<-r-1<<"\": "<<(total[1+cut*5+r]+(r==0?total[0]:0))/360.L;}
  out<<"},\n  \"regular_simple\": "<<total[0]/360.L<<",\n  \"endpoint_simple\": "<<total[1+cut*5]/360.L<<"\n}\n";
  cout<<"Saved "<<filename<<endl;
 }
}
