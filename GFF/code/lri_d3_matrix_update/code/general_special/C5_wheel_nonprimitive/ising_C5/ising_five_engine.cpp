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
using namespace std;
using Clock=chrono::steady_clock;
struct Term{int l,r; double a,b;};
struct Group{int id; vector<Term> terms;};
struct Sector{array<int,10> masks; vector<Group> groups;};
int main(int argc,char**argv){
 int N=argc>1?atoi(argv[1]):8; bool span=false;int nt=argc>3?atoi(argv[3]):4;omp_set_num_threads(nt);
 string root=argc>2?string(argv[2]):string("."); if(root.back()!='/')root+="/";
 FILE*f=fopen((root+"graphs6.bin").c_str(),"rb");if(!f)return 2;fseek(f,0,SEEK_END);long bytes=ftell(f);rewind(f);if(bytes%sizeof(array<int,17>))return 4;vector<array<int,17>> G(bytes/sizeof(array<int,17>));fread(G.data(),sizeof(G[0]),G.size(),f);fclose(f);
 int nnode=N+1,NP=nnode*nnode*nnode*nnode;
 vector<double>qw(4*11*5*nnode);f=fopen((root+"qweights5_"+to_string(N)+".bin").c_str(),"rb");if(!f)return 3;fread(qw.data(),8,qw.size(),f);fclose(f);
 auto qwi=[&](int j,int b,int r,int i)->double{return qw[(((j*11+b)*5+r)*nnode)+i];};
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
 if(!group_ids.count(b)){group_ids[b]=bs.size();bs.push_back(b);}int id=group_ids[b];groups[id].push_back({lr[gi].first,lr[gi].second,double(g[15]),double(g[16])});}
 for(auto&kv:groups){auto&terms=kv.second;sort(terms.begin(),terms.end(),[](auto&a,auto&b){return a.l<b.l||(a.l==b.l&&a.r<b.r);});sec.groups.push_back({kv.first,move(terms)});}sectors.push_back(move(sec));
 }while(next_permutation(perm.begin(),perm.end()));
 int NG=bs.size();cout<<"N="<<N<<" cutoffs=both"<<" nodes="<<NP<<" groups="<<NG<<" sectors="<<sectors.size()<<" left="<<left.size()<<" right="<<right.size()<<endl;
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
 vector<double>W(offset[NP]);vector<double>Q((size_t)NP*32*4);vector<double>LH(NP);
 #pragma omp parallel for schedule(static)
 for(int p=0;p<NP;p++){
 int ind[4],v=p;double t[4];for(int j=3;j>=0;j--){ind[j]=v%nnode;v/=nnode;t[j]=(1+cos(M_PI*ind[j]/N))/2;if(ind[j]==0)t[j]=1;if(ind[j]==N)t[j]=0;}
 for(int mask=1;mask<32;mask++){
 int mini=__builtin_ctz((unsigned)mask);double q=1,z=1;for(int r=mini+1;r<5;r++){z*=t[r-1];if(mask&(1<<r))q+=z;}
 double*o=&Q[((size_t)p*32+mask)*4];o[0]=1/sqrt(q);o[1]=o[0]*o[0];o[2]=o[1]*o[0];o[3]=.5*log(q);if(mask==31)LH[p]=5*log(q);
 }
 for(int id=0;id<NG;id++){
 double a[9]={0};a[4]=1;
 for(int j=0;j<4;j++){
 double b[9]={0};for(int k=-j;k<=4-j;k++)if(a[k+4]!=0)for(int r=-1;r<=3;r++)if(k+r>=-j-1&&k+r<=3-j)b[k+r+4]+=a[k+4]*qwi(j,bs[id][j],r+1,ind[j]);
 memcpy(a,b,sizeof(a));}
 W[offset[p]+id]=a[4];
 int ti=tailMap[zeroMask[p]][id];if(ti>=0)for(int r=1;r<=4;r++)W[offset[p]+NG+4*ti+r-1]=a[4-r];
 }
 }
 cout<<"Precomputed in "<<chrono::duration<double>(Clock::now()-t0).count()<<" s; W MB="<<W.size()*8./1e6<<endl;
 array<long double,20>total{};
 for(int si=0;si<(int)sectors.size();si++){
 auto&sec=sectors[si];vector<array<long double,20>>partials(nt);
 #pragma omp parallel
 {
 int tid=omp_get_thread_num();array<long double,20>sum{};vector<double>lv(left.size()),rv(right.size()),ll(left.size()),rl(right.size());
 #pragma omp for schedule(static)
 for(int p=0;p<NP;p++){
 double powers[10][4],logs[10];for(int i=0;i<10;i++){auto*q=&Q[((size_t)p*32+sec.masks[i])*4];powers[i][0]=1;for(int j=1;j<=3;j++)powers[i][j]=q[j-1];logs[i]=q[3];}
 for(int h=0;h<(int)left.size();h++){double z=1,l=0;for(int j=0;j<5;j++){int e=left[h][j];z*=powers[j][e];l+=e*logs[j];}lv[h]=z;ll[h]=l;}
 for(int h=0;h<(int)right.size();h++){double z=1,l=0;for(int j=0;j<5;j++){int e=right[h][j];z*=powers[j+5][e];l+=e*logs[j+5];}rv[h]=z;rl[h]=l;}
 double delta=0; array<long double,10> psum{};
 for(auto&group:sec.groups){double ww[5]={W[offset[p]+group.id],0,0,0,0};
 int ti=tailMap[zeroMask[p]][group.id];if(ti>=0)for(int r=1;r<=4;r++)ww[r]=W[offset[p]+NG+4*ti+r-1];
 const double*w=ww;int maxr=4;while(maxr>0&&w[maxr]==0)maxr--;
 if(maxr==0){if(w[0]==0)continue;double a=0,b=0;for(auto&term:group.terms){double z=lv[term.l]*rv[term.r];a+=term.a*z;b+=term.b*z;}psum[0]+=(long double)w[0]*a;psum[5]+=(long double)w[0]*b;}
 else{
 double sa[5]={0},sb[5]={0};for(auto&term:group.terms){double z=lv[term.l]*rv[term.r],k=ll[term.l]+rl[term.r]+delta;
 double pp[5]={1,k,k*k*.5,k*k*k/6.,k*k*k*k/24.};double za=term.a*z,zb=term.b*z;
 for(int r=0;r<=maxr;r++){double pol=0;for(int j=r;j<=maxr;j++)pol+=w[j]*pp[j-r];sa[r]+=za*pol;sb[r]+=zb*pol;}}
 for(int r=0;r<=maxr;r++){psum[r]+=sa[r];psum[r+5]+=sb[r];}
 }
 }
 double h=-LH[p];double hp[5]={1,h,h*h/2,h*h*h/6,h*h*h*h/24};
 for(int ab=0;ab<2;ab++)for(int r=0;r<=4;r++){
   sum[ab*5+r]+=psum[ab*5+r];
   for(int j=r;j<=4;j++)sum[10+ab*5+r]+=psum[ab*5+j]*hp[j-r];
 }
 }
 partials[tid]=sum;
 }
 for(auto&a:partials)for(int i=0;i<20;i++)total[i]+=a[i];
 if((si+1)%5==0||si+1==(int)sectors.size())cout<<"Sector "<<si+1<<"/"<<sectors.size()<<" time "<<chrono::duration<double>(Clock::now()-t0).count()<<" s"<<endl;
 }
 // x2 for reversal, /144 for weights, /5 for overall scale pole.

 for(int cut=0;cut<2;cut++){
 string filename=root+"amplitude5_"+(cut?"span":"maxgap")+"_"+to_string(N)+".json";ofstream out(filename);out<<setprecision(18)<<"{\n";
 for(int ab=0;ab<2;ab++){out<<"  \""<<(ab?"B":"A")<<"\": {";for(int r=4;r>=0;r--){if(r<4)out<<", ";out<<"\""<<-r-1<<"\": "<<total[cut*10+r+5*ab]/360.L;}out<<"}"<<(ab?"\n":",\n");}out<<"}\n";out.close();
 cout<<"Saved "<<filename<<endl;for(int r=4;r>=0;r--)cout<<setprecision(17)<<"power "<<-r-1<<" A "<<total[cut*10+r]/360.L<<" B "<<total[cut*10+r+5]/360.L<<endl;
 }
}
