import json
from app.config import ROOT,settings
from app.database import SessionLocal,Base,engine
from app.models import User,Vessel,Port,SystemSetting
from app.schemas import Policy,VesselInput
from app.security import hasher

def initialize():
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.query(Port).first():
            for p in json.loads((ROOT/'data/ports/ports.json').read_text()):db.add(Port(**p))
        if not db.get(SystemSetting,'policy'):db.add(SystemSetting(key='policy',value=Policy(weather_mode='demo' if settings.demo_mode else 'live').model_dump()))
        db.commit()
        if settings.demo_mode and settings.demo_password:
            for email,name,role in [('planner@horizon.local','Arjun · Planner','planner'),('manager@horizon.local','Fleet Manager','manager'),('admin@horizon.local','System Administrator','admin')]:
                if not db.query(User).filter_by(email=email).first():
                    u=User(email=email,name=name,role=role,password_hash=hasher.hash(settings.demo_password));db.add(u);db.flush()
                    for ship in ['Horizon Pioneer','Arabian Explorer']:
                        db.add(Vessel(owner_id=u.id,**VesselInput(name=ship).model_dump()))
            db.commit()
if __name__=='__main__':initialize()
