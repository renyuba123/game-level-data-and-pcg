"""Endpoint-safe route adapter without changing the frozen Legacy module."""
import numpy as np
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import Point,LineString
def route(nav,start,end):
    if not nav.free.covers(Point(start)) or not nav.free.covers(Point(end)):return []
    a,b=nav.nearest(start),nav.nearest(end)
    for p,q in [(start,nav.points[a]),(end,nav.points[b])]:
        if np.linalg.norm(np.array(p)-q)>1e-7 and not nav.free.covers(LineString([p,q])):return []
    if b not in nav.fields:nav.fields[b]=dijkstra(nav.graph,directed=False,indices=b,return_predecessors=True)
    distances,previous=nav.fields[b]
    if not np.isfinite(distances[a]):return []
    path=[np.array(start),nav.points[a]]
    while a!=b:
        a=int(previous[a])
        if a<0:return []
        path.append(nav.points[a])
    path.append(np.array(end));return path
