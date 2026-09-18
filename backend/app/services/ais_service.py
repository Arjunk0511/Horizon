from datetime import datetime, timedelta
from app.utils.geo import haversine, bearing
from app.config import settings
import httpx

def position_at(route,distance,departure,hours):
    remaining=max(0,distance); points=route['points']; segment=route['segments'][-1]
    for i,(a,b) in enumerate(zip(points,points[1:])):
        d=haversine(a,b);segment=route['segments'][i]
        if remaining<=d:
            f=remaining/max(d,1e-9)
            return dict(latitude=a[0]+(b[0]-a[0])*f,longitude=a[1]+(b[1]-a[1])*f,speed_over_ground=segment['speed_knots'],course_over_ground=bearing(a,b),timestamp=(datetime.fromisoformat(departure)+timedelta(hours=hours)).isoformat(),mode='simulated',segment=i,weather=segment['weather'],risk=segment['level'])
        remaining-=d
    return dict(latitude=points[-1][0],longitude=points[-1][1],speed_over_ground=0,course_over_ground=0,timestamp=(datetime.fromisoformat(departure)+timedelta(hours=hours)).isoformat(),mode='simulated',segment=len(points)-2,weather=segment['weather'],risk=segment['level'])

def advance(route,distance,hours):
    remaining=hours;at=distance;before=0
    for s in route['segments']:
        end=before+s['distance']
        if at<end:
            available=end-max(at,before);speed=s['distance']/s['hours'];dt=available/speed
            take=min(dt,remaining);at+=take*speed;remaining-=take
            if remaining<=1e-9:break
        before=end
    return min(at,route['distance']),hours-remaining

def get_live_position(imo):
    # Configurable HTTPS gateway contract, not a claim of a paid AIS subscription.
    if not imo: raise ValueError('A vessel IMO is required for live AIS')
    if not settings.ais_url or not settings.ais_api_key: raise ValueError('Live AIS requires AIS_URL and AIS_API_KEY; simulator remains available')
    if not settings.ais_url.startswith('https://'):raise ValueError('AIS_URL must use HTTPS')
    with httpx.Client(timeout=15) as client:
        r=client.get(settings.ais_url,params={'imo':imo},headers={'Authorization':'Bearer '+settings.ais_api_key});r.raise_for_status();p=r.json()
    from pydantic import BaseModel, Field, field_validator
    class Position(BaseModel):
        latitude:float=Field(ge=-90,le=90);longitude:float=Field(ge=-180,le=180)
        speed_over_ground:float=Field(ge=0,le=100);course_over_ground:float=Field(ge=0,lt=360);timestamp:datetime
        @field_validator('timestamp')
        @classmethod
        def aware(cls,value):
            if value.tzinfo is None: raise ValueError('AIS timestamp needs a timezone')
            return value
    out=Position(**p).model_dump(mode='json');out['mode']='live';return out
