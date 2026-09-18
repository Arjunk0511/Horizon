from math import radians, sin, cos, atan2, sqrt, degrees
def haversine(a,b):
    lat1,lon1,lat2,lon2=map(radians,[*a,*b])
    q=sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.0088*2*atan2(sqrt(min(1,q)),sqrt(max(0,1-q)))
def bearing(a,b):
    x,y=map(radians,[a[0],b[0]]); dl=radians(b[1]-a[1])
    return (degrees(atan2(sin(dl)*cos(y),cos(x)*sin(y)-sin(x)*cos(y)*cos(dl)))+360)%360
