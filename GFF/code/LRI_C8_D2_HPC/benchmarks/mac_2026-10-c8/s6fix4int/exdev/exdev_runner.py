# runs a test file with os.link failing as across file systems (EXDEV), as on symmetry (BeeGFS export, node-local /tmp)
import errno,os,runpy,sys
def nolink(*a,**k):raise OSError(errno.EXDEV,'Invalid cross-device link')
os.link=nolink;sys.argv=sys.argv[1:];sys.path[0]=os.path.dirname(os.path.abspath(sys.argv[0]));runpy.run_path(sys.argv[0],run_name='__main__')
