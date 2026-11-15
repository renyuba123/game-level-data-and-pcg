import sys
sys.path.insert(0, '.tools')
from pypdf import PdfReader
from pypdf.generic import ContentStream

r=PdfReader('鼠王关玩家路线图001.ai')
p=r.pages[0]
props=p['/Resources']['/Properties']
layer=None; path=[]; n=0; ctm=(1,0,0,1,0,0); stack=[]
def mult(a,b):
    return (a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1], a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3], a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5])
def point(v): return (round(ctm[0]*v[0]+ctm[2]*v[1]+ctm[4],2),round(ctm[1]*v[0]+ctm[3]*v[1]+ctm[5],2))
for args,op in ContentStream(p['/Contents'],r).operations:
    if op==b'BDC': layer=str(props[args[1]].get_object().get('/Name'))
    elif op==b'EMC': layer=None
    elif layer=='Route':
        if op==b'q': stack.append(ctm)
        elif op==b'Q': ctm=stack.pop() if stack else (1,0,0,1,0,0)
        elif op==b'cm': ctm=mult(ctm,tuple(float(x) for x in args))
        if op in (b'm',b'l',b'c',b'h'):
            vals=[float(x) for x in args]
            path.append((op.decode(),point(vals[-2:]) if len(vals)>=2 else None))
        elif op in (b'S',b's',b'f',b'F',b'f*',b'B',b'B*',b'b',b'b*'):
            if path:
                n+=1
                print(n,op.decode(),len(path),path[0],path[-1])
            path=[]
        elif op==b'n': path=[]
