from datetime import datetime, timezone
from math import exp, sin, radians
import httpx
from app.utils.geo import haversine
DEMO_HAZARD={'latitude':14.5,'longitude':74.0,'radius_km':170,'wave_height':6.5,'wind_speed':29,'name':'Arabian Sea demo storm'}
class WeatherService:
    def __init__(self,mode='demo',timestamp=None,hazards=None):
        self.mode=mode; self.timestamp=timestamp or datetime.now(timezone.utc).isoformat()
        self.hazards=[DEMO_HAZARD]+(hazards or []) if mode=='demo' else []
        self.samples=[]
    def prepare(self,start,end):
        if self.mode=='demo': return
        target=datetime.fromisoformat(self.timestamp).astimezone(timezone.utc)
        now=datetime.now(timezone.utc)
        if not -1 <= (target-now).total_seconds()/86400 <= 6: raise ValueError('Live forecast departure must be within the next six days')
        # Batch regional coarse snapshot. Sample provenance is preserved on each evaluation.
        south=max(-2,min(start[0],end[0])-5);north=min(28,max(start[0],end[0])+5)
        west=max(45,min(start[1],end[1])-5);east=min(106,max(start[1],end[1])+5)
        from app.algorithms.maritime_graph import land_geometry
        from shapely.geometry import Point
        land=land_geometry()
        anchors=[(round(south+(north-south)*i/5,3),round(west+(east-west)*j/5,3)) for i in range(6) for j in range(6)]
        anchors=[p for p in anchors if not land.intersects(Point(p[1],p[0]))]
        common=dict(latitude=','.join(str(p[0]) for p in anchors),longitude=','.join(str(p[1]) for p in anchors),timezone='UTC',forecast_days=7)
        try:
            with httpx.Client(timeout=25) as client:
                marine=client.get('https://marine-api.open-meteo.com/v1/marine',params={**common,'hourly':'wave_height,wave_direction,ocean_current_velocity,ocean_current_direction'});marine.raise_for_status()
                wind=client.get('https://api.open-meteo.com/v1/forecast',params={**common,'hourly':'wind_speed_10m,wind_direction_10m','wind_speed_unit':'ms'});wind.raise_for_status()
            ms=marine.json();ws=wind.json();ms=ms if isinstance(ms,list) else [ms];ws=ws if isinstance(ws,list) else [ws]
            for p,m,w in zip(anchors,ms,ws):
                mh=m['hourly'];wh=w['hourly']; requested=target.strftime('%Y-%m-%dT%H:00')
                i=mh['time'].index(requested);j=wh['time'].index(requested)
                wave=mh['wave_height'][i];speed=wh['wind_speed_10m'][j]
                if wave is None or speed is None: continue
                current=mh.get('ocean_current_velocity',[None]*len(mh['time']))[i]
                self.samples.append(dict(latitude=p[0],longitude=p[1],wave_height=wave,wind_speed=speed,wind_direction=wh['wind_direction_10m'][j],wave_direction=mh['wave_direction'][i],current_speed=None if current is None else current/3.6,current_direction=mh.get('ocean_current_direction',[None]*len(mh['time']))[i]))
            if not self.samples: raise ValueError('No complete marine/wind observations for the requested time')
        except (httpx.HTTPError,KeyError,IndexError,ValueError) as exc:
            raise ValueError('Live weather unavailable or incomplete; select Demo explicitly to continue') from exc
    def get_weather(self,lat,lon,time=None):
        if self.mode=='live':
            if not self.samples: raise ValueError('Live weather snapshot is not prepared')
            sample=min(self.samples,key=lambda s:haversine((lat,lon),(s['latitude'],s['longitude'])))
            separation=haversine((lat,lon),(sample['latitude'],sample['longitude']))
            if separation>450: raise ValueError('Route exceeds live weather sample coverage')
            values={**sample,'sample_latitude':sample['latitude'],'sample_longitude':sample['longitude'],'sample_distance_km':round(separation,2),'source':'Open-Meteo regional snapshot'}
        else:
            wave=.8+.2*abs(sin(radians(lat*7+lon*3)));wind=6+2*abs(sin(radians(lon*4)))
            for h in self.hazards:
                d=haversine((lat,lon),(h['latitude'],h['longitude']))
                strength=exp(-2*(d/h['radius_km'])**2)
                wave=max(wave,.8+(h['wave_height']-.8)*strength)
                wind=max(wind,6+(h['wind_speed']-6)*strength)
            values=dict(wave_height=round(wave,3),wind_speed=round(wind,3),wind_direction=225,wave_direction=225,current_speed=.2,current_direction=180,source='Deterministic demonstration')
        return {**values,'latitude':lat,'longitude':lon,'timestamp':self.timestamp,'mode':self.mode,'condition':'Rough' if values['wave_height']>3 else 'Moderate' if values['wave_height']>1.5 else 'Calm'}
    def get_weather_for_route(self,points): return [self.get_weather(*p) for p in points]
def weather_risk(w,v,policy,safety='Standard'):
    margin=.85 if safety=='Conservative' else 1
    wave_limit=min(v['maximum_wave_height'],policy['maximum_wave_height'])*margin
    wind_limit=min(v['maximum_wind_speed'],policy['maximum_wind_speed'])*margin
    ratio=max(w['wave_height']/wave_limit,w['wind_speed']/wind_limit)
    risk=min(1,ratio+.02*abs(w.get('current_speed') or 0))
    level='CRITICAL' if ratio>=1 or risk>=policy['high'] else 'HIGH' if risk>=policy['medium'] else 'MEDIUM' if risk>=policy['low'] else 'LOW'
    return dict(risk=risk,level=level,safe=ratio<1)
