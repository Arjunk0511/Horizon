import math
from app.algorithms.maritime_graph import graph_with_endpoints
from app.algorithms.astar import search
from app.algorithms.dijkstra import dijkstra
from app.utils.geo import haversine
from app.services.weather_service import WeatherService, weather_risk
from app.services.fuel_calculator import segment_metrics
from app.services.emission_calculator import calculate_co2

def optimize(start,end,v,departure,policy,preference='Balanced',safety='Standard',mode='demo',hazards=None,algorithm='astar'):
    points,graph=graph_with_endpoints(start,end)
    service=WeatherService(mode,departure,hazards);service.prepare(start,end)
    weights=dict(policy['weights'])
    if preference=='Safest': weights=dict(distance=.05,weather=.65,fuel=.05,time=.05,safety=.20)
    if preference=='Fuel Efficient': weights=dict(distance=.05,weather=.05,fuel=.80,time=.05,safety=.05)
    if preference=='Shortest': weights=dict(distance=1,weather=0,fuel=0,time=0,safety=0)
    cache={}
    def edge(u,z,d):
        key=(u,z)
        if key in cache:return cache[key]
        a,b=points[u],points[z]
        # Sample each segment at <= 10 km intervals, not just at endpoints.
        count=max(2,math.ceil(d/10)+1)
        samples=[]
        try:
            for i in range(count):
                f=i/(count-1);w=service.get_weather(a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f)
                samples.append((w,weather_risk(w,v,policy,safety)))
        except ValueError:
            cache[key]=None;return None
        worst=max(samples,key=lambda x:x[1]['risk']); w,risk=worst
        metrics=segment_metrics(a,b,d,v,w)
        cache[key]=(metrics,w,risk);return cache[key]
    def shortest(u,z,d): return d
    baseline,bc,be=(dijkstra(graph,'start','end',shortest) if algorithm=='dijkstra' else search(graph,'start','end',shortest,lambda n:haversine(points[n],end)))
    def cost(u,z,d):
        data=edge(u,z,d)
        if not data or not data[2]['safe']:return math.inf
        m,w,r=data
        normal_hours=d/(v['cruising_speed']*1.852)
        normal_fuel=v['fuel_consumption_rate']/24*normal_hours
        return d*(weights['distance']+weights['weather']*r['risk']+weights['fuel']*m['fuel']/max(normal_fuel,1e-9)+weights['time']*m['hours']/max(normal_hours,1e-9)+weights['safety']*r['risk']**4)
    optimized,oc,oe=(dijkstra(graph,'start','end',cost) if algorithm=='dijkstra' else search(graph,'start','end',cost,lambda n:weights['distance']*haversine(points[n],end)))
    def evaluate(path,cost_value,expanded):
        total=dict(distance=0,hours=0,fuel=0);segments=[];max_risk=0;safe=True;risk_distance=0
        for u,z in zip(path,path[1:]):
            d=haversine(points[u],points[z]);data=edge(u,z,d)
            if not data:raise ValueError('Weather coverage is incomplete along the baseline; choose a covered route or Demo')
            m,w,r=data
            for k in total:total[k]+=m[k]
            risk_distance+=d*r['risk'];max_risk=max(max_risk,r['risk']);safe=safe and r['safe']
            segments.append({**m,'weather':w,**r})
        result={**total,'co2':calculate_co2(total['fuel'],v['fuel_type'],policy['emission_factors']),'risk':risk_distance/max(total['distance'],1),'max_risk':max_risk,'safe':safe,'points':[points[n] for n in path],'segments':segments,'algorithm':algorithm,'cost':cost_value,'expanded_nodes':expanded,'mode':mode,'forecast_time':departure,'weather_model':'Departure-time static snapshot; refreshed on recalculation','weights':weights,'policy':policy,'hazards':service.hazards}
        return result
    return evaluate(baseline,bc,be),evaluate(optimized,oc,oe)
def comparison(a,b):
    return {'additional_distance':b['distance']-a['distance'],'time_difference':b['hours']-a['hours'],'fuel_saved':a['fuel']-b['fuel'],'co2_reduced':a['co2']-b['co2'],'risk_reduction':a['risk']-b['risk']}
