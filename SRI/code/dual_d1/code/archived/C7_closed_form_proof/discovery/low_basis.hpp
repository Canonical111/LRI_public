#pragma once
#include "word_core.hpp"
struct QDef{int src;mpq_class inv;map<int,mpq_class>par;};
struct QBasis{
 vector<QP> basis;vector<QDef>defs;vector<string>labels;map<U,int>leads;
 pair<QP,map<int,mpq_class>>reduce(QP r){QP rem;map<int,mpq_class>weights;while(!r.empty()){auto it=prev(r.end());U m=it->first;mpq_class fac=it->second;auto p=leads.find(m);if(p==leads.end()){rem[m]=fac;r.erase(it);continue;}int j=p->second;weights[j]+=fac;for(auto[k,c]:basis[j])qadd(r,k,-fac*c);}return {rem,weights};}
 void insert(QP row,int src){auto[rem,weights]=reduce(move(row));if(rem.empty())return;U m=rem.rbegin()->first;mpq_class inv=1/rem.rbegin()->second;for(auto&[k,c]:rem)c*=inv;for(auto&[k,c]:weights)c*=-inv;leads[m]=basis.size();basis.push_back(move(rem));defs.push_back({src,inv,move(weights)});}
 void save(string file){ofstream o(file);o<<labels.size()<<" "<<basis.size()<<"\n";for(auto l:labels)o<<l<<"\n";for(int j=0;j<(int)basis.size();j++){auto&d=defs[j];o<<d.src<<" "<<d.inv<<" "<<d.par.size()<<" "<<basis[j].size()<<"\n";for(auto[i,c]:d.par)o<<i<<" "<<c<<"\n";for(auto[m,c]:basis[j])o<<m<<" "<<c<<"\n";}}
 void load(string file){ifstream f(file);int ns,nb;f>>ns>>nb;string l;getline(f,l);for(int i=0;i<ns;i++){getline(f,l);labels.push_back(l);}for(int j=0;j<nb;j++){int src,np,nr;string co;f>>src>>co>>np>>nr;mpq_class inv(co);inv.canonicalize();map<int,mpq_class>par;for(int i=0;i<np;i++){int k;f>>k>>co;mpq_class c(co);c.canonicalize();par[k]=c;}QP row;for(int i=0;i<nr;i++){U m;f>>m>>co;mpq_class c(co);c.canonicalize();row[m]=c;}leads[row.rbegin()->first]=j;basis.push_back(move(row));defs.push_back({src,inv,move(par)});}}
};
