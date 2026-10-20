#include <bits/stdc++.h>
#include <omp.h>
#include <filesystem>
using namespace std;
int main(int ac,char**av){if(ac!=2)return 1;ifstream in(av[1]);vector<pair<string,string>>jobs;string a,b;while(in>>a>>b)jobs.emplace_back(a,b);vector<string>records(jobs.size());atomic<int>done=0;double start=omp_get_wtime();
#pragma omp parallel for num_threads(3) schedule(dynamic,1)
for(size_t k=0;k<jobs.size();k++){
 ifstream f(jobs[k].first);string magic,wa,wb;int L,id,M,T;f>>magic>>L>>id>>wa>>wb>>M>>T;int E=2*L,ALL=(1<<E)-1;
 if(magic!="C7D2GRAPH1" && magic!="C7D3GRAPH1")abort();vector<unsigned>masks(M);for(auto&m:masks)f>>m;
 vector<vector<int>>basis(T),cos(T);for(int i=0;i<T;i++){int n;f>>n;basis[i].resize(n);for(int&v:basis[i])f>>v;cos[i].resize(E);for(int&v:cos[i])f>>v;}
 vector<int>positive(ALL+1,1000),raw(ALL+1,1000),pc(ALL+1);for(int s=0;s<=ALL;s++)pc[s]=__builtin_popcount(unsigned(s));
 for(int ti=0;ti<T;ti++){
  vector<int8_t>dist(ALL+1,100);for(int m:basis[ti])dist[masks[m]]=0;
  for(int bit=1;bit<=ALL;bit<<=1)for(int base=0;base<=ALL;base+=2*bit)for(int j=0;j<bit;j++){int s=base+j,t=s+bit,x=dist[s],y=dist[t];dist[s]=min(x,y+1);dist[t]=min(y,x+1);}
  unsigned supp=0;for(int j=0;j<E;j++)if(cos[ti][j])supp|=1u<<j;
  for(int s=1;s<ALL;s++){int h=(L-E+pc[s]+int(dist[ALL^s]))/2;int nuN=(supp&~s)?0:1;int p4=3*pc[s]+4*nuN-6*h;raw[s]=min(raw[s],p4);if(p4<=0){p4=(p4%4+4)%4;if(!p4)p4=4;}positive[s]=min(positive[s],p4);}
 }
 ofstream out(jobs[k].second);out<<setprecision(22)<<"C7D3GRAPH1 "<<L<<' '<<id<<' '<<wa<<' '<<wb<<' '<<M<<' '<<T<<'\n';for(auto m:masks)out<<m<<' ';out<<'\n';
 for(int i=0;i<T;i++){out<<basis[i].size();for(auto v:basis[i])out<<' '<<v;for(auto v:cos[i])out<<' '<<v;out<<'\n';}out<<ALL+1<<'\n';long clamped=0;int minp=1000;
 for(int s=0;s<=ALL;s++){if(s&&s<ALL){clamped+=raw[s]<=0;minp=min(minp,positive[s]);out<<positive[s]*.25L<<' ';}else out<<"0 ";}out<<'\n';
 records[k]="{\"file\":\""+jobs[k].second+"\",\"L\":"+to_string(L)+",\"id\":"+to_string(id)+",\"cancelled_nonpositive_subsets\":"+to_string(clamped)+",\"minimum_rate_quarters\":"+to_string(minp)+"}";
 int d=++done;if(d%100==0){
#pragma omp critical
 cerr<<d<<'/'<<jobs.size()<<" seconds "<<omp_get_wtime()-start<<'\n';}
}
cout<<"[";for(size_t i=0;i<records.size();i++){if(i)cout<<',';cout<<records[i];}cout<<"]\n";
}
