from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
class Strict(BaseModel): model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Register(Strict):
    name: str=Field(min_length=2,max_length=100)
    email: str=Field(min_length=5,max_length=254,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str=Field(min_length=10,max_length=128)
    @field_validator('email')
    @classmethod
    def lower(cls,v): return v.strip().lower()
class Login(Strict):
    email: str
    password: str=Field(max_length=128)
class Profile(Strict): name: str=Field(min_length=2,max_length=100)
class VesselInput(Strict):
    name: str=Field(min_length=2,max_length=100)
    imo: str | None=Field(default=None,pattern=r'^\d{7}$')
    vessel_type: str=Field(default='Container',max_length=40)
    length: float=Field(default=180,gt=0,le=500)
    beam: float=Field(default=30,gt=0,le=100)
    draft: float=Field(default=10,gt=0,le=30)
    cruising_speed: float=Field(default=14,ge=3,le=35)
    maximum_speed: float=Field(default=20,ge=3,le=45)
    fuel_consumption_rate: float=Field(default=25,gt=0,le=500)
    fuel_type: Literal['HFO','MDO','LNG']='HFO'
    maximum_wave_height: float=Field(default=4,ge=1,le=15)
    maximum_wind_speed: float=Field(default=22,ge=5,le=70)
    @model_validator(mode='after')
    def speed(self):
        if self.cruising_speed>self.maximum_speed: raise ValueError('Cruising speed exceeds maximum speed')
        return self
class VoyageInput(Strict):
    source_id: int
    destination_id: int
    vessel_id: int
    departure: datetime
    preference: Literal['Balanced','Safest','Fuel Efficient','Shortest']='Balanced'
    safety: Literal['Standard','Conservative']='Standard'
    algorithm: Literal['astar','dijkstra']='astar'
    mode: Literal['demo','live']='demo'
    @model_validator(mode='after')
    def different(self):
        if self.source_id==self.destination_id: raise ValueError('Choose different ports')
        if self.departure.tzinfo is None: raise ValueError('Departure must include a timezone')
        return self
class AdminUser(Strict):
    role: Literal['planner','manager','admin']
    active: bool=True
class Policy(Strict):
    maximum_wave_height: float=Field(default=4,ge=1,le=15)
    maximum_wind_speed: float=Field(default=22,ge=5,le=70)
    low: float=Field(default=.35,gt=0,lt=1)
    medium: float=Field(default=.65,gt=0,lt=1)
    high: float=Field(default=.85,gt=0,lt=1)
    weather_mode: Literal['demo','live']='demo'
    weights: dict[str,float]=Field(default_factory=lambda:dict(distance=.30,weather=.30,fuel=.20,time=.10,safety=.10))
    emission_factors: dict[str,float]=Field(default_factory=lambda:dict(HFO=3.114,MDO=3.206,LNG=2.750))
    @model_validator(mode='after')
    def validate_policy(self):
        if not self.low<self.medium<self.high: raise ValueError('Risk thresholds must be increasing')
        if set(self.weights)!={'distance','weather','fuel','time','safety'} or any(v<0 or v>1 for v in self.weights.values()) or abs(sum(self.weights.values())-1)>.0001: raise ValueError('Five nonnegative weights must sum to 1')
        if set(self.emission_factors)!={'HFO','MDO','LNG'} or any(v<=0 or v>5 for v in self.emission_factors.values()): raise ValueError('Provide valid HFO, MDO, LNG factors')
        return self
class Step(Strict): hours: float=Field(default=4,gt=0,le=48)
