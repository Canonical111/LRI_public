/* Exact GMP rational scalar for endpoint recurrences. No numerical approximation. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <gmp.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
typedef struct {PyObject_HEAD mpq_t v; Py_hash_t hash;} QObj;
static PyTypeObject QType;
static PyObject *to_int(mpz_srcptr z){
 if(mpz_fits_slong_p(z))return PyLong_FromLong(mpz_get_si(z));
 char *s=mpz_get_str(NULL,10,z); if(!s)return PyErr_NoMemory();
 PyObject *out=PyLong_FromString(s,NULL,10);void (*freefn)(void*,size_t);mp_get_memory_functions(NULL,NULL,&freefn);freefn(s,strlen(s)+1);return out;
}
static int from_int(mpz_ptr z,PyObject *x){
 if(!PyLong_Check(x))return 0;
 int over=0;long a=PyLong_AsLongAndOverflow(x,&over);
 if(!over&&!PyErr_Occurred()){mpz_set_si(z,a);return 1;}
 if(PyErr_Occurred())PyErr_Clear();
 PyObject *s=PyObject_Str(x);if(!s)return -1;const char *p=PyUnicode_AsUTF8(s);if(!p){Py_DECREF(s);return -1;}
 int err=mpz_set_str(z,p,10);Py_DECREF(s);if(err){PyErr_SetString(PyExc_ValueError,"invalid integer");return -1;}return 1;
}
static int convert(mpq_ptr v,PyObject *x){
 if(PyObject_TypeCheck(x,&QType)){mpq_set(v,((QObj*)x)->v);return 1;}
 if(PyLong_Check(x)){int r=from_int(mpq_numref(v),x);mpz_set_ui(mpq_denref(v),1);return r;}
 if(PyUnicode_Check(x)){
  const char *s=PyUnicode_AsUTF8(x);if(!s)return -1;
  if(mpq_set_str(v,s,10)!=0){PyErr_SetString(PyExc_ValueError,"invalid rational string");return -1;}
  if(!mpz_sgn(mpq_denref(v))){PyErr_SetString(PyExc_ZeroDivisionError,"zero rational denominator");return -1;}
  mpq_canonicalize(v);return 1;
 }
 PyObject *a=PyObject_GetAttrString(x,"numerator");
 if(!a){PyErr_Clear();return 0;}
 PyObject *b=PyObject_GetAttrString(x,"denominator");if(!b){Py_DECREF(a);PyErr_Clear();return 0;}
 int r=from_int(mpq_numref(v),a),s=from_int(mpq_denref(v),b);Py_DECREF(a);Py_DECREF(b);
 if(r<0||s<0)return -1;if(!r||!s)return 0;
 if(!mpz_sgn(mpq_denref(v))){PyErr_SetString(PyExc_ZeroDivisionError,"zero rational denominator");return -1;}
 mpq_canonicalize(v);return 1;
}
static QObj *allocq(void){QObj *out=PyObject_New(QObj,&QType);if(!out)return NULL;mpq_init(out->v);out->hash=-1;return out;}
static PyObject *qnew(PyTypeObject *type,PyObject *args,PyObject *kw){
 PyObject *a=NULL,*b=NULL;static char *names[]={"numerator","denominator",NULL};
 if(!PyArg_ParseTupleAndKeywords(args,kw,"|OO:Q",names,&a,&b))return NULL;
 QObj *out=allocq();if(!out)return NULL;
 if(a){int r=convert(out->v,a);if(r!=1){Py_DECREF(out);if(!r)PyErr_SetString(PyExc_TypeError,"expected an exact rational");return NULL;}}
 if(b){mpq_t den;mpq_init(den);int r=convert(den,b);if(r!=1){mpq_clear(den);Py_DECREF(out);if(!r)PyErr_SetString(PyExc_TypeError,"expected an exact denominator");return NULL;}
  if(!mpq_sgn(den)){mpq_clear(den);Py_DECREF(out);PyErr_SetString(PyExc_ZeroDivisionError,"zero rational denominator");return NULL;}
  mpq_div(out->v,out->v,den);mpq_clear(den);}
 return (PyObject*)out;
}
static void qdel(QObj *x){mpq_clear(x->v);PyObject_Del(x);}
static PyObject *qstr(QObj *x){char *s=mpq_get_str(NULL,10,x->v);if(!s)return PyErr_NoMemory();PyObject *out=PyUnicode_FromString(s);void(*ff)(void*,size_t);mp_get_memory_functions(NULL,NULL,&ff);ff(s,strlen(s)+1);return out;}
static PyObject *qrepr(QObj *x){PyObject*s=qstr(x);if(!s)return NULL;PyObject*r=PyUnicode_FromFormat("Q('%U')",s);Py_DECREF(s);return r;}
static PyObject *binary(PyObject*a,PyObject*b,int op){
 if(PyObject_TypeCheck(a,&QType)&&PyObject_TypeCheck(b,&QType)){
  mpq_srcptr aa=((QObj*)a)->v,bb=((QObj*)b)->v;
  if((op==3||op==4)&&!mpq_sgn(bb)){PyErr_SetString(PyExc_ZeroDivisionError,"rational division by zero");return NULL;}
  QObj*out=allocq();if(!out)return NULL;
  switch(op){case 0:mpq_add(out->v,aa,bb);break;case 1:mpq_sub(out->v,aa,bb);break;case 2:mpq_mul(out->v,aa,bb);break;default:mpq_div(out->v,aa,bb);}
  if(op==4){mpz_t z;mpz_init(z);mpz_fdiv_q(z,mpq_numref(out->v),mpq_denref(out->v));PyObject*r=to_int(z);mpz_clear(z);Py_DECREF(out);return r;}
  return (PyObject*)out;
 }
 mpq_t aa,bb;mpq_init(aa);mpq_init(bb);int ra=convert(aa,a),rb=ra<0?-1:convert(bb,b);
 if(ra!=1||rb!=1){mpq_clear(aa);mpq_clear(bb);if(ra<0||rb<0)return NULL;Py_RETURN_NOTIMPLEMENTED;}
 if((op==3||op==4)&&!mpq_sgn(bb)){mpq_clear(aa);mpq_clear(bb);PyErr_SetString(PyExc_ZeroDivisionError,"rational division by zero");return NULL;}
 QObj*out=allocq();if(!out){mpq_clear(aa);mpq_clear(bb);return NULL;}
 switch(op){case 0:mpq_add(out->v,aa,bb);break;case 1:mpq_sub(out->v,aa,bb);break;case 2:mpq_mul(out->v,aa,bb);break;default:mpq_div(out->v,aa,bb);break;}
 mpq_clear(aa);mpq_clear(bb);
 if(op==4){mpz_t z;mpz_init(z);mpz_fdiv_q(z,mpq_numref(out->v),mpq_denref(out->v));PyObject*r=to_int(z);mpz_clear(z);Py_DECREF(out);return r;}
 return (PyObject*)out;
}
static PyObject *qadd(PyObject*a,PyObject*b){return binary(a,b,0);}static PyObject *qsub(PyObject*a,PyObject*b){return binary(a,b,1);}static PyObject *qmul(PyObject*a,PyObject*b){return binary(a,b,2);}static PyObject *qdiv(PyObject*a,PyObject*b){return binary(a,b,3);}static PyObject *qfloor(PyObject*a,PyObject*b){return binary(a,b,4);}
static PyObject *qneg(QObj*x){QObj*y=allocq();if(y)mpq_neg(y->v,x->v);return (PyObject*)y;}static PyObject*qpos(QObj*x){return Py_NewRef(x);}static PyObject *qabs(QObj*x){QObj*y=allocq();if(y)mpq_abs(y->v,x->v);return (PyObject*)y;}
static int qbool(QObj*x){return mpq_sgn(x->v)!=0;}
static PyObject *qfloat(QObj*x){return PyFloat_FromDouble(mpq_get_d(x->v));}
static PyObject *qint(QObj*x){mpz_t z;mpz_init(z);mpz_tdiv_q(z,mpq_numref(x->v),mpq_denref(x->v));PyObject*r=to_int(z);mpz_clear(z);return r;}
static PyObject *qpow(PyObject*a,PyObject*b,PyObject*m){
 if(m!=Py_None){Py_RETURN_NOTIMPLEMENTED;}PyObject*ix=PyNumber_Index(b);if(!ix){PyErr_Clear();Py_RETURN_NOTIMPLEMENTED;}long n=PyLong_AsLong(ix);Py_DECREF(ix);if(PyErr_Occurred())return NULL;
 mpq_t aa;mpq_init(aa);int r=convert(aa,a);if(r!=1){mpq_clear(aa);if(r<0)return NULL;Py_RETURN_NOTIMPLEMENTED;}
 if(n<0&&!mpq_sgn(aa)){mpq_clear(aa);PyErr_SetString(PyExc_ZeroDivisionError,"zero to negative power");return NULL;}
 if(n==LONG_MIN){mpq_clear(aa);PyErr_SetString(PyExc_OverflowError,"exponent too large");return NULL;}
 if(n<0){mpq_inv(aa,aa);n=-n;}QObj*out=allocq();if(out){mpz_pow_ui(mpq_numref(out->v),mpq_numref(aa),(unsigned long)n);mpz_pow_ui(mpq_denref(out->v),mpq_denref(aa),(unsigned long)n);}mpq_clear(aa);return (PyObject*)out;
}
static PyObject *qcompare(PyObject*a,PyObject*b,int op){
 if(PyObject_TypeCheck(a,&QType)&&PyObject_TypeCheck(b,&QType)){
  int c=mpq_cmp(((QObj*)a)->v,((QObj*)b)->v),v=0;
  switch(op){case Py_LT:v=c<0;break;case Py_LE:v=c<=0;break;case Py_EQ:v=c==0;break;case Py_NE:v=c!=0;break;case Py_GT:v=c>0;break;case Py_GE:v=c>=0;}
  return PyBool_FromLong(v);
 }
 mpq_t aa,bb;mpq_init(aa);mpq_init(bb);int ra=convert(aa,a),rb=ra<0?-1:convert(bb,b);if(ra!=1||rb!=1){mpq_clear(aa);mpq_clear(bb);if(ra<0||rb<0)return NULL;Py_RETURN_NOTIMPLEMENTED;}int c=mpq_cmp(aa,bb);mpq_clear(aa);mpq_clear(bb);int v=0;switch(op){case Py_LT:v=c<0;break;case Py_LE:v=c<=0;break;case Py_EQ:v=c==0;break;case Py_NE:v=c!=0;break;case Py_GT:v=c>0;break;case Py_GE:v=c>=0;}return PyBool_FromLong(v);}
static Py_hash_t qhash(QObj*x){if(x->hash!=-1)return x->hash;
 mpz_t modulus,inv;mpz_inits(modulus,inv,NULL);mpz_set_ui(modulus,_PyHASH_MODULUS);
 Py_hash_t h;if(!mpz_invert(inv,mpq_denref(x->v),modulus))h=_PyHASH_INF;
 else {mpz_t v;mpz_init(v);mpz_abs(v,mpq_numref(x->v));mpz_mul(v,v,inv);h=(Py_hash_t)mpz_fdiv_ui(v,_PyHASH_MODULUS);mpz_clear(v);}
 if(mpq_sgn(x->v)<0)h=-h;if(h==-1)h=-2;mpz_clears(modulus,inv,NULL);x->hash=h;return h;
}
static PyObject*qnum(QObj*x,void*y){return to_int(mpq_numref(x->v));}static PyObject*qden(QObj*x,void*y){return to_int(mpq_denref(x->v));}
static PyObject *qratio(QObj*x,PyObject*unused){PyObject*a=to_int(mpq_numref(x->v)),*b=to_int(mpq_denref(x->v));if(!a||!b){Py_XDECREF(a);Py_XDECREF(b);return NULL;}PyObject*r=PyTuple_Pack(2,a,b);Py_DECREF(a);Py_DECREF(b);return r;}
static PyGetSetDef gets[]={{"numerator",(getter)qnum,NULL,NULL,NULL},{"denominator",(getter)qden,NULL,NULL,NULL},{NULL}};
static PyMethodDef methods[]={{"as_integer_ratio",(PyCFunction)qratio,METH_NOARGS,NULL},{NULL}};
static PyNumberMethods number={.nb_add=qadd,.nb_subtract=qsub,.nb_multiply=qmul,.nb_power=qpow,.nb_negative=(unaryfunc)qneg,.nb_positive=(unaryfunc)qpos,.nb_absolute=(unaryfunc)qabs,.nb_bool=(inquiry)qbool,.nb_int=(unaryfunc)qint,.nb_float=(unaryfunc)qfloat,.nb_floor_divide=qfloor,.nb_true_divide=qdiv};
static PyTypeObject QType={PyVarObject_HEAD_INIT(NULL,0) .tp_name="fast_fraction.Q",.tp_basicsize=sizeof(QObj),.tp_dealloc=(destructor)qdel,.tp_repr=(reprfunc)qrepr,.tp_str=(reprfunc)qstr,.tp_as_number=&number,.tp_hash=(hashfunc)qhash,.tp_flags=Py_TPFLAGS_DEFAULT,.tp_richcompare=qcompare,.tp_methods=methods,.tp_getset=gets,.tp_new=qnew};
static struct PyModuleDef module={PyModuleDef_HEAD_INIT,"fast_fraction",NULL,-1,NULL};
PyMODINIT_FUNC PyInit_fast_fraction(void){if(PyType_Ready(&QType)<0)return NULL;PyObject*m=PyModule_Create(&module);if(!m)return NULL;Py_INCREF(&QType);if(PyModule_AddObject(m,"Q",(PyObject*)&QType)<0){Py_DECREF(&QType);Py_DECREF(m);return NULL;}return m;}
