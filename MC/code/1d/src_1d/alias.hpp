#pragma once
#include <vector>
#include <cstdint>
#include <cmath>
#include <stdexcept>
#include <algorithm>
// Exact (up to binary64 roundoff) Walker distribution; power-of-two padding.
// Small core alias also has one tail category, preserving ALL interactions.
struct Alias {
    struct Entry {double p;uint32_t a;uint32_t value;};
    std::vector<Entry> t; uint64_t mask=0; int bits=0; double inv=1;
    void build(const std::vector<double>& w,const std::vector<uint32_t>& vals={}){
        size_t n=1;while(n<w.size())n*=2;
        long double acc=0;for(double x:w){if(x<0||!std::isfinite(x))throw std::runtime_error("invalid alias weight");acc+=x;}
        if(acc<=0)throw std::runtime_error("empty alias distribution");
        double sum=double(acc); t.resize(n);
        std::vector<uint32_t> lo,hi;lo.reserve(n);hi.reserve(n);
        for(size_t i=0;i<n;++i){t[i]={i<w.size()?w[i]*n/sum:0,0,vals.empty()?uint32_t(i):(i<vals.size()?vals[i]:0)};
            (t[i].p<1?lo:hi).push_back(uint32_t(i));}
        while(!lo.empty()&&!hi.empty()){
            uint32_t x=lo.back(),y=hi.back();lo.pop_back();hi.pop_back();
            t[x].a=y;t[y].p-=1-t[x].p;(t[y].p<1?lo:hi).push_back(y);
        }
        for(auto v:lo){t[v].p=1;t[v].a=v;}for(auto v:hi){t[v].p=1;t[v].a=v;}
        for(auto& e:t)e.a=t[e.a].value; // resolve destinations once, not in the hot loop
        mask=n-1;bits=0;while((1ULL<<bits)<n)++bits;inv=std::ldexp(1.0,-(64-bits));
    }
    template<class R> inline uint32_t draw(R& r)const{
        uint64_t v=r();uint32_t k=uint32_t(v&mask);
        const Entry& e=t[k];return double(v>>bits)*inv<e.p ? e.value : e.a;
    }
};
