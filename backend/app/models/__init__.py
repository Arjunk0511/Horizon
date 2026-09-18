from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, JSON, Text
from app.database import Base
def now(): return datetime.now(timezone.utc).isoformat()
class User(Base):
    __tablename__='users'
    id=Column(Integer,primary_key=True)
    email=Column(String(254),unique=True,nullable=False)
    name=Column(String(100),nullable=False)
    password_hash=Column(Text,nullable=False)
    role=Column(String(20),default='planner',nullable=False)
    active=Column(Boolean,default=True)
    created_at=Column(String(40),default=now)
class Token(Base):
    __tablename__='sessions'
    id=Column(String(64),primary_key=True)
    user_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    expires=Column(Float,nullable=False)
    revoked=Column(Boolean,default=False)
class Vessel(Base):
    __tablename__='vessels'
    id=Column(Integer,primary_key=True)
    owner_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    name=Column(String(100),nullable=False)
    imo=Column(String(7),nullable=True)
    vessel_type=Column(String(40),default='Container')
    length=Column(Float); beam=Column(Float); draft=Column(Float)
    cruising_speed=Column(Float); maximum_speed=Column(Float)
    fuel_consumption_rate=Column(Float); fuel_type=Column(String(20))
    maximum_wave_height=Column(Float); maximum_wind_speed=Column(Float)
class Port(Base):
    __tablename__='ports'
    id=Column(Integer,primary_key=True); name=Column(String(100)); country=Column(String(80))
    latitude=Column(Float); longitude=Column(Float)
    approach_lat=Column(Float); approach_lon=Column(Float)
class Voyage(Base):
    __tablename__='voyages'
    id=Column(Integer,primary_key=True)
    owner_id=Column(Integer,ForeignKey('users.id'),nullable=False)
    vessel_id=Column(Integer,ForeignKey('vessels.id'),nullable=False)
    source_id=Column(Integer,ForeignKey('ports.id'),nullable=False)
    destination_id=Column(Integer,ForeignKey('ports.id'),nullable=False)
    name=Column(String(160)); departure=Column(String(40)); preference=Column(String(20)); safety=Column(String(20))
    status=Column(String(20),default='planned'); progress=Column(Float,default=0)
    travelled=Column(Float,default=0); simulation_hours=Column(Float,default=0)
    mode=Column(String(20)); hazards=Column(JSON,default=list); vessel_snapshot=Column(JSON)
    created_at=Column(String(40),default=now)
class Route(Base):
    __tablename__='routes'
    id=Column(Integer,primary_key=True); voyage_id=Column(Integer,ForeignKey('voyages.id'),nullable=False)
    kind=Column(String(20)); version=Column(Integer); data=Column(JSON); created_at=Column(String(40),default=now)
class RoutePoint(Base):
    __tablename__='route_points'
    id=Column(Integer,primary_key=True); route_id=Column(Integer,ForeignKey('routes.id'),nullable=False)
    sequence=Column(Integer); latitude=Column(Float); longitude=Column(Float)
class WeatherData(Base):
    __tablename__='weather_data'
    id=Column(Integer,primary_key=True); route_id=Column(Integer,ForeignKey('routes.id'),nullable=False); data=Column(JSON)
class AISPosition(Base):
    __tablename__='ais_positions'
    id=Column(Integer,primary_key=True); voyage_id=Column(Integer,ForeignKey('voyages.id'),nullable=False); data=Column(JSON)
class Alert(Base):
    __tablename__='alerts'
    id=Column(Integer,primary_key=True); voyage_id=Column(Integer,ForeignKey('voyages.id'),nullable=False)
    type=Column(String(20)); message=Column(Text); acknowledged=Column(Boolean,default=False); created_at=Column(String(40),default=now)
class SystemSetting(Base):
    __tablename__='system_settings'
    key=Column(String(80),primary_key=True); value=Column(JSON)
class Comparison(Base):
    __tablename__='route_comparisons'
    id=Column(Integer,primary_key=True); voyage_id=Column(Integer,ForeignKey('voyages.id'),nullable=False)
    baseline_id=Column(Integer,ForeignKey('routes.id')); optimized_id=Column(Integer,ForeignKey('routes.id')); data=Column(JSON)
class Log(Base):
    __tablename__='system_logs'
    id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id'),nullable=True)
    action=Column(String(100)); detail=Column(Text); created_at=Column(String(40),default=now)
