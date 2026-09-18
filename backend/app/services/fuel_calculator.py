from math import cos, radians
from app.utils.geo import bearing

def segment_metrics(a,b,distance,v,weather):
    # Simplified academic resistance model, not calibrated sea trials.
    resistance=1+.10*weather['wave_height']**2+.001*weather['wind_speed']**2
    through_water=v['cruising_speed']/resistance**.35
    along_current=(weather.get('current_speed') or 0)*3.6*cos(radians((weather.get('current_direction') or 0)-bearing(a,b)))
    ground=max(3,through_water*1.852+along_current)
    hours=distance/ground
    fuel=v['fuel_consumption_rate']/24*hours*resistance
    return dict(distance=distance,hours=hours,fuel=fuel,speed_knots=ground/1.852,resistance=resistance)
