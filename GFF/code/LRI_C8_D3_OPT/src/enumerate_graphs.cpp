#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <fstream>
#include <functional>
#include <iostream>
#include <map>
#include <numeric>
#include <set>
#include <string>
#include <vector>
using namespace std;
using Mat=array<array<int,9>,9>;
using Part=vector<vector<int>>;
int n;Mat a{};array<int,9>deg{},rem{};long long visited=0,accepted=0;
map<string,pair<Mat,int>> classes;
Part refine(Part p){
 bool again=true;while(again){again=false;Part q;
 for(auto &cell:p){map<vector<int>,vector<int>> groups;
 for(int v:cell){vector<int>s;for(auto &c:p){array<int,4>hist{};for(int w:c)if(v!=w)hist[a[v][w]]++;for(int x:hist)s.push_back(x);}groups[s].push_back(v);}
 if(groups.size()>1)again=true;for(auto &kv:groups)q.push_back(kv.second);
 }p=move(q);}return p;
}
string best;int aut;
void canon(Part p){
 p=refine(move(p));int pick=-1;for(int i=0;i<(int)p.size();i++)if(p[i].size()>1&&(pick<0||p[i].size()<p[pick].size()))pick=i;
 if(pick<0){string k;for(int i=0;i<n;i++)for(int j=i+1;j<n;j++)k+=char('0'+a[p[i][0]][p[j][0]]);if(best.empty()||k<best){best=k;aut=1;}else if(k==best)aut++;return;}
 auto cell=p[pick];for(int v:cell){Part q=p;vector<int>rest;for(int w:cell)if(w!=v)rest.push_back(w);q[pick]={v};q.insert(q.begin()+pick+1,rest);canon(move(q));}
}
bool connected_1pi(){
 array<int,9>disc{},low{};int timer=0;bool bridge=false;
 function<void(int,int)>dfs=[&](int v,int parent){disc[v]=low[v]=++timer;for(int w=0;w<n;w++)if(a[v][w]){if(!disc[w]){dfs(w,v);low[v]=min(low[v],low[w]);if(low[w]>disc[v]&&a[v][w]==1)bridge=true;}else if(w!=parent||a[v][w]>1)low[v]=min(low[v],disc[w]);}};
 dfs(0,-1);return timer==n&&!bridge;
}
void terminal(){
 visited++;if(!connected_1pi())return;accepted++;
 map<int,vector<int>>dc;for(int i=0;i<n;i++)dc[deg[i]].push_back(i);Part p;for(auto&kv:dc)p.push_back(kv.second);best.clear();aut=0;canon(move(p));
 classes.try_emplace(best,a,aut);
 if(visited%1000000==0)cerr<<"leaves "<<visited<<" classes "<<classes.size()<<"\n";
}
void row(int i);
void edge(int i,int j,int need){
 if(j==n){if(need==0)row(i+1);return;}
 int cap=min({3,rem[j],need});int lo=0;
 if(j>i+1&&deg[j]==deg[j-1]){bool same=true;for(int k=0;k<i;k++)if(a[k][j]!=a[k][j-1])same=false;if(same)lo=a[i][j-1];}
 for(int x=lo;x<=cap;x++){
  rem[j]-=x;a[i][j]=a[j][i]=x;
  int available=0;bool okay=true;for(int k=j+1;k<n;k++)available+=min(3,rem[k]);
  if(need-x>available)okay=false;
  for(int k=i+1;k<=j;k++)if(rem[k]>3*(n-i-2))okay=false;
  if(okay)edge(i,j+1,need-x);
  rem[j]+=x;a[i][j]=a[j][i]=0;
 }
}
void row(int i){
 if(i==n-1){if(rem[i]==0)terminal();return;}
 int need=rem[i];rem[i]=0;int total=0,mx=0;for(int j=i+1;j<n;j++){total+=rem[j];mx=max(mx,rem[j]);}
 if(total>=need&&mx<=(total+need-mx))edge(i,i+1,need);rem[i]=need;
}
int main(int argc,char**argv){
 if(argc!=3){cerr<<"usage enumerate n output.json\n";return 2;}n=stoi(argv[1]);if(n<3||n>9)return 2;
 auto t=chrono::steady_clock::now();
 for(int n2=0;n2<=2;n2++){int n3=4-2*n2;if(n2+n3>n)continue;int k=0;for(int j=0;j<n2;j++)deg[k++]=2;for(int j=0;j<n3;j++)deg[k++]=3;while(k<n)deg[k++]=4;rem=deg;row(0);cerr<<"pattern "<<n2<<" leaves "<<visited<<" accepted "<<accepted<<" classes "<<classes.size()<<"\n";}
 ofstream f(argv[2]);f<<"[\n";int id=0;for(auto&[key,data]:classes){auto &[m,autom]=data;long long den=autom;int s=0;array<int,9>d{};vector<pair<int,int>>ed;
 for(int i=0;i<n;i++)for(int j=i+1;j<n;j++){for(int k=0;k<m[i][j];k++)ed.emplace_back(i,j);d[i]+=m[i][j];d[j]+=m[i][j];if(m[i][j]==2)den*=2;else if(m[i][j]==3)den*=6;}
 for(int i=0;i<n;i++){int e=4-d[i];s+=e*(e-1);if(e==2)den*=2;}
 if(id)f<<",\n";f<<"{\"id\":"<<id++<<",\"L\":"<<n-1<<",\"canonical\":\""<<key<<"\",\"automorphisms\":"<<autom<<",\"denominator\":"<<den<<",\"mass_numerator\":"<<s<<",\"edges\":[";
 for(size_t j=0;j<ed.size();j++){if(j)f<<',';f<<'['<<ed[j].first<<','<<ed[j].second<<']';}f<<"]}";}
 f<<"\n]\n";cerr<<"total "<<classes.size()<<" time "<<chrono::duration<double>(chrono::steady_clock::now()-t).count()<<" s\n";
}
