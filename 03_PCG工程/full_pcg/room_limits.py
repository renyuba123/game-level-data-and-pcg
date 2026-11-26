"""Clear internal dimensions of the two user-marked DXF rooms (model metres)."""
from itertools import product
from shapely.geometry import box, Polygon, LineString
from shapely.affinity import scale

# Pairs of actual inner-face coordinates from the hash-pinned DXF wall inventory.
NORTH = (8.05568 - 4.86429, 8.43263 - 6.13882)
EAST_LOW = (14.01865 - 10.51274, -1.01731 - (-2.80885))
HALF_WALL = .09

def witness(poly, dims):
    # Test the full wall-inset rectangle, including concave boundaries.
    x0,y0,x1,y1 = poly.bounds
    for w,h in (dims, dims[::-1]):
        if x1-x0 < w or y1-y0 < h: continue
        vx,vy = zip(*poly.exterior.coords)
        xs = {x0,x1-w,(x0+x1-w)/2,*vx,*(x-w for x in vx)}
        ys = {y0,y1-h,(y0+y1-h)/2,*vy,*(y-h for y in vy)}
        for x,y in product(sorted(xs),sorted(ys)):
            if x<x0-1e-8 or x+w>x1+1e-8 or y<y0-1e-8 or y+h>y1+1e-8: continue
            r=box(x,y,x+w,y+h)
            if poly.covers(r): return [x,y,w,h]
    return None

def measure(name, cell):
    net=cell.buffer(-HALF_WALL,join_style="mitre")
    if net.geom_type!="Polygon" or net.is_empty: return None
    choices=[("north",NORTH),("east_low",EAST_LOW)]
    if name.startswith("north"): choices=choices[:1]
    if name=="east_low": choices=choices[1:]
    # Open at the shorter DXF width to expose thin blind extensions.
    r=EAST_LOW[1]/2-.0001
    opened=net.buffer(-r,join_style="mitre").buffer(r,join_style="mitre")
    remainder=net.difference(opened.buffer(.025))
    for part in getattr(remainder,"geoms",[remainder]):
        if part.area>.12 and part.length>1.6: return None
    for label,dims in choices:
        rect=witness(net,dims)
        if rect: return dict(reference=label,inside_rectangle=rect,net_area=net.area)
    return None
