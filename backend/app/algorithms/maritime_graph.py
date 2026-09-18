import json
from functools import lru_cache
from shapely.geometry import shape, Point, LineString, box
from shapely.ops import unary_union
from shapely.prepared import prep
from app.config import ROOT
from app.utils.geo import haversine
# Fixed academic coverage: Persian Gulf, Arabian Sea, Bay of Bengal, Malacca approaches.
BOUNDS=(45,-2,106,28)
@lru_cache(maxsize=1)
def land_geometry():
    data=json.loads((ROOT/'data/maritime/land.geojson').read_text())
    bounds=box(*BOUNDS)
    return unary_union([shape(f['geometry']).intersection(bounds) for f in data['features'] if shape(f['geometry']).intersects(bounds)])
@lru_cache(maxsize=1)
def base_graph():
    land=prep(land_geometry().buffer(.025))
    points={}; graph={}
    for iy in range(61):
        for ix in range(123):
            lat=-2+iy*.5; lon=45+ix*.5
            if not land.intersects(Point(lon,lat)):
                points[(iy,ix)]=(lat,lon); graph[(iy,ix)]=[]
    for key,a in points.items():
        for dy,dx in [(0,1),(1,-1),(1,0),(1,1)]:
            k=(key[0]+dy,key[1]+dx)
            if k in points:
                b=points[k]
                if not land.intersects(LineString([(a[1],a[0]),(b[1],b[0])])):
                    d=haversine(a,b);graph[key].append((k,d));graph[k].append((key,d))
    return points,graph

def graph_with_endpoints(start,end):
    points0,graph0=base_graph();points=dict(points0); graph={k:list(v) for k,v in graph0.items()}
    land=prep(land_geometry().buffer(.025))
    for name,p in [('start',tuple(start)),('end',tuple(end))]:
        if land.intersects(Point(p[1],p[0])): raise ValueError('Offshore approach/current position intersects buffered land')
        points[name]=p;graph[name]=[]
        nearby=sorted(((haversine(p,q),k) for k,q in points0.items()))
        for d,k in nearby:
            if d>180: break
            q=points[k]
            if not land.intersects(LineString([(p[1],p[0]),(q[1],q[0])])):
                graph[name].append((k,d));graph[k].append((name,d))
                if len(graph[name])==8: break
        if not graph[name]: raise ValueError('No navigable connection to the maritime grid')
    return points,graph
