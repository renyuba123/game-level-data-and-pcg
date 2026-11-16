"""List large exact-colour regions in the raster embedded in the source AI."""
from collections import deque
from PIL import Image

im = Image.open('maps/ratking/depthmap_embedded.png').convert('RGB')
w, h = im.size
px = im.load()
colours = {(51, 136, 221), (34, 204, 221), (221, 51, 51), (221, 204, 34), (51, 51, 221)}
seen = bytearray(w * h)
for y in range(h):
    for x in range(w):
        i = y*w+x
        colour = px[x,y]
        if seen[i] or colour not in colours:
            continue
        seen[i]=1
        q=deque([(x,y)])
        n=sx=sy=0
        xmin=ymin=10**9
        xmax=ymax=-1
        while q:
            a,b=q.popleft()
            n+=1;sx+=a;sy+=b
            xmin=min(xmin,a);xmax=max(xmax,a);ymin=min(ymin,b);ymax=max(ymax,b)
            for c,d in ((a-1,b),(a+1,b),(a,b-1),(a,b+1)):
                if 0<=c<w and 0<=d<h:
                    j=d*w+c
                    if not seen[j] and px[c,d]==colour:
                        seen[j]=1;q.append((c,d))
        if n>1000:
            print(colour,n,(xmin,ymin,xmax,ymax),(round(sx/n,3),round(sy/n,3)))
