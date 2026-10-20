import mpmath as m
m.mp.dps=60
def g(x):return m.gamma(x)/m.gamma(1-x)
def complex_selberg(n,a,b,r):
 return m.factorial(n)*m.fprod(g(a+j*r)*g(b+j*r)*g((j+1)*r)/(g(a+b+(n+j-1)*r)*g(r)) for j in range(n))
T=(m.gamma(m.mpf(1)/4)/m.gamma(m.mpf(3)/4))**4
for e in map(m.mpf,['.05','.02','.01','.005','.001']):
 u=(2-e)/4
 k7=complex_selberg(3,1-u,1-u,-u/2)
 print(e, m.nstr(k7,20), 'residue', m.nstr(e*k7,20),'subtract',m.nstr(k7-2*T/(3*e),20))
print('residue expectation',2*T/3)
