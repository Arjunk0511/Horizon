from contextlib import asynccontextmanager
from datetime import datetime,timezone,timedelta
from io import BytesIO
import json, time, threading
from collections import defaultdict,deque
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from app.config import settings,ROOT
from app.database import get_db
from app.models import *
from app.schemas import Register,Login,Profile,VesselInput,VoyageInput,AdminUser,Policy,Step
from app.security import current_user,admin,issue,hasher,serialize,bearer,secret
from app.seed import initialize
from app.services.route_optimizer import optimize,comparison
from app.services.notification_service import notify,log
from app.services.ais_service import position_at,advance,get_live_position
from app.services.weather_service import WeatherService,weather_risk
from app.utils.geo import haversine
import jwt

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield
app=FastAPI(title='Horizon Maritime API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_credentials=False,allow_methods=['GET','POST','PUT','DELETE'],allow_headers=['Authorization','Content-Type'])
# A single-company prototype: managers/admins can view the company fleet; planners own their data.
def policy(db):return db.get(SystemSetting,'policy').value

def visible(query,model,user):return query if user.role in ['manager','admin'] else query.filter(model.owner_id==user.id)
def voyage_for(db,id,user,lock=False):
    query=db.query(Voyage).filter(Voyage.id==id)
    if lock:query=query.with_for_update()
    v=query.first()
    if not v or (v.owner_id!=user.id and user.role not in ['manager','admin']):raise HTTPException(404,'Voyage not found')
    return v

def vessel_for(db,id,user):
    v=db.get(Vessel,id)
    if not v or (v.owner_id!=user.id and user.role not in ['manager','admin']):raise HTTPException(404,'Vessel not found')
    return v

def latest(db,v,kind='optimized'):
    return db.query(Route).filter_by(voyage_id=v.id,kind=kind).order_by(Route.version.desc()).first()

def save_route(db,v,data,kind,version):
    row=Route(voyage_id=v.id,kind=kind,version=version,data=data);db.add(row);db.flush()
    for i,p in enumerate(data['points']):db.add(RoutePoint(route_id=row.id,sequence=i,latitude=p[0],longitude=p[1]))
    db.add(WeatherData(route_id=row.id,data={'mode':data['mode'],'forecast_time':data['forecast_time'],'observations':[s['weather'] for s in data['segments']]}))
    return row

def detail(db,v):
    base=latest(db,v,'baseline');opt=latest(db,v)
    return {**serialize(v),'source':serialize(db.get(Port,v.source_id)),'destination':serialize(db.get(Port,v.destination_id)),'vessel':v.vessel_snapshot,'baseline':base.data,'optimized':opt.data,'route_id':opt.id,'route_version':opt.version,'comparison':comparison(base.data,opt.data),'history':[{'id':r.id,'kind':r.kind,'version':r.version,'created_at':r.created_at,'distance':r.data['distance']} for r in db.query(Route).filter_by(voyage_id=v.id).order_by(Route.id)],'alerts':[serialize(a) for a in db.query(Alert).filter_by(voyage_id=v.id).order_by(Alert.id.desc())]}

attempts=defaultdict(deque);auth_lock=threading.Lock();voyage_lock=threading.RLock()
def rate_limit(request):
    key=request.client.host if request.client else 'local';nowt=time.monotonic()
    with auth_lock:
        q=attempts[key]
        while q and q[0]<nowt-60:q.popleft()
        if len(q)>=20:raise HTTPException(429,'Too many authentication attempts; wait one minute')
        q.append(nowt)

@app.get('/api/health')
def health():return dict(status='ok',app='Horizon',version='1.0.0',configured_mode='demo' if settings.demo_mode else 'live')
@app.post('/api/auth/register',status_code=201)
def register(data:Register,request:Request,db:Session=Depends(get_db)):
    rate_limit(request)
    u=User(email=data.email,name=data.name,password_hash=hasher.hash(data.password),role='planner');db.add(u)
    try:db.flush()
    except IntegrityError:db.rollback();raise HTTPException(409,'Email already registered')
    db.add(Vessel(owner_id=u.id,**VesselInput(name='My Horizon Vessel').model_dump()));log(db,u.id,'register');db.commit()
    return {'access_token':issue(db,u),'user':serialize(u)}
@app.post('/api/auth/login')
def login(data:Login,request:Request,db:Session=Depends(get_db)):
    rate_limit(request);u=db.query(User).filter_by(email=data.email.lower().strip()).first()
    if not u or not u.active or not hasher.verify(data.password,u.password_hash):raise HTTPException(401,'Invalid email or password')
    log(db,u.id,'login');return {'access_token':issue(db,u),'user':serialize(u)}
@app.post('/api/auth/logout')
def logout(user=Depends(current_user),credentials=Depends(bearer),db:Session=Depends(get_db)):
    p=jwt.decode(credentials.credentials,secret,algorithms=['HS256'],audience='horizon-ui',issuer='horizon')
    db.get(Token,p['jti']).revoked=True;db.commit();return {'message':'Logged out'}
@app.get('/api/auth/profile')
def profile(user=Depends(current_user)):return serialize(user)
@app.put('/api/auth/profile')
def edit_profile(data:Profile,user=Depends(current_user),db:Session=Depends(get_db)):
    user.name=data.name;db.commit();return serialize(user)
@app.get('/api/ports')
def ports(user=Depends(current_user),db:Session=Depends(get_db)):return [serialize(p) for p in db.query(Port).order_by(Port.id)]
@app.get('/api/geography')
def geography(user=Depends(current_user)):
    from app.algorithms.maritime_graph import land_geometry
    from shapely.geometry import mapping
    return {'type':'FeatureCollection','features':[{'type':'Feature','properties':{},'geometry':mapping(land_geometry().simplify(.015))}]}
@app.get('/api/vessels')
def vessels(user=Depends(current_user),db:Session=Depends(get_db)):return [serialize(v) for v in visible(db.query(Vessel),Vessel,user).order_by(Vessel.id)]
@app.post('/api/vessels',status_code=201)
def add_vessel(data:VesselInput,user=Depends(current_user),db:Session=Depends(get_db)):
    v=Vessel(owner_id=user.id,**data.model_dump());db.add(v);log(db,user.id,'create_vessel',data.name);db.commit();return serialize(v)
@app.put('/api/vessels/{id}')
def edit_vessel(id:int,data:VesselInput,user=Depends(current_user),db:Session=Depends(get_db)):
    v=vessel_for(db,id,user)
    for k,value in data.model_dump().items():setattr(v,k,value)
    log(db,user.id,'edit_vessel',str(id));db.commit();return serialize(v)
@app.delete('/api/vessels/{id}')
def delete_vessel(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    v=vessel_for(db,id,user)
    if db.query(Voyage).filter_by(vessel_id=id).first():raise HTTPException(409,'Vessel has voyage history; preserve it')
    db.delete(v);db.commit();return {'message':'Deleted'}
@app.post('/api/voyages',status_code=201)
@app.post('/api/routes/optimize',status_code=201)
def create_voyage(data:VoyageInput,user=Depends(current_user),db:Session=Depends(get_db)):
    vessel=vessel_for(db,data.vessel_id,user);s=db.get(Port,data.source_id);d=db.get(Port,data.destination_id)
    if not s or not d:raise HTTPException(404,'Port not found')
    departure=data.departure.astimezone(timezone.utc).isoformat();snap=serialize(vessel)
    try:a,b=optimize((s.approach_lat,s.approach_lon),(d.approach_lat,d.approach_lon),snap,departure,policy(db),data.preference,data.safety,data.mode,algorithm=data.algorithm)
    except ValueError as e:raise HTTPException(422,str(e))
    v=Voyage(owner_id=user.id,vessel_id=vessel.id,source_id=s.id,destination_id=d.id,name=f'{s.name} → {d.name}',departure=departure,preference=data.preference,safety=data.safety,mode=data.mode,vessel_snapshot=snap,hazards=[])
    db.add(v);db.flush();br=save_route(db,v,a,'baseline',1);op=save_route(db,v,b,'optimized',1)
    db.add(Comparison(voyage_id=v.id,baseline_id=br.id,optimized_id=op.id,data=comparison(a,b)))
    notify(db,v.id,'INFO','Voyage saved. Weather source: '+data.mode+'. Offshore approaches used; draft clearance is unverified.')
    if not a['safe']:notify(db,v.id,'WARNING','Baseline crosses vessel weather limits. Optimized route avoids those conditions.')
    log(db,user.id,'optimize',str(v.id));db.commit();return detail(db,v)
@app.get('/api/voyages')
def voyages(user=Depends(current_user),db:Session=Depends(get_db)):
    return [{**serialize(v),'vessel_name':v.vessel_snapshot['name'],'summary':latest(db,v).data | {'points':[],'segments':[]}} for v in visible(db.query(Voyage),Voyage,user).order_by(Voyage.id.desc())]
@app.get('/api/voyages/{id}')
def voyage(id:int,user=Depends(current_user),db:Session=Depends(get_db)):return detail(db,voyage_for(db,id,user))
@app.get('/api/routes/compare')
def compare(voyage_id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    v=voyage_for(db,voyage_id,user);return detail(db,v)['comparison']
@app.get('/api/routes/{id}')
def route(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    r=db.get(Route,id)
    if not r:raise HTTPException(404,'Route not found')
    voyage_for(db,r.voyage_id,user);return serialize(r)
@app.get('/api/weather')
def weather(lat:float,lon:float,mode:str='demo',timestamp:str|None=None,user=Depends(current_user),db:Session=Depends(get_db)):
    if not (-2<=lat<=28 and 45<=lon<=106) or mode not in ['demo','live']:raise HTTPException(422,'Unsupported coordinates or mode')
    s=WeatherService(mode,timestamp)
    try:s.prepare((lat,lon),(lat,lon));return s.get_weather(lat,lon)
    except ValueError as e:raise HTTPException(422,str(e))

def monitoring(db,v):
    r=latest(db,v).data;p=position_at(r,v.progress,v.departure,v.simulation_hours)
    if v.mode=='demo':
        w=WeatherService('demo',p['timestamp'],v.hazards).get_weather(p['latitude'],p['longitude'])
        p['weather']=w;p['risk']=weather_risk(w,v.vessel_snapshot,policy(db),v.safety)['level']
    remaining=max(0,r['distance']-v.progress)
    hours_left=0;distance_before=0
    for seg in r['segments']:
        available=max(0,min(seg['distance'],distance_before+seg['distance']-v.progress));hours_left+=seg['hours']*available/seg['distance'];distance_before+=seg['distance']
    return {**p,'status':v.status,'progress_percent':100*v.progress/r['distance'],'remaining_distance':remaining,'travelled_distance':v.travelled+v.progress,'simulation_hours':v.simulation_hours,'eta':(datetime.fromisoformat(v.departure)+timedelta(hours=v.simulation_hours+hours_left)).isoformat(),'route_version':latest(db,v).version,'alerts':[serialize(a) for a in db.query(Alert).filter_by(voyage_id=v.id,acknowledged=False).order_by(Alert.id.desc())]}
@app.get('/api/monitoring/{id}')
def get_monitoring(id:int,user=Depends(current_user),db:Session=Depends(get_db)):return monitoring(db,voyage_for(db,id,user))
@app.post('/api/monitoring/{id}/start')
def start(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    v=voyage_for(db,id,user)
    if v.status=='completed':raise HTTPException(409,'Voyage already completed')
    v.status='active';log(db,user.id,'start_voyage',str(id));db.commit();return monitoring(db,v)
@app.post('/api/monitoring/{id}/step')
def step(id:int,data:Step,user=Depends(current_user),db:Session=Depends(get_db)):
    with voyage_lock:
        v=voyage_for(db,id,user,True)
        if v.status!='active':raise HTTPException(409,'Start an active voyage before advancing')
        r=latest(db,v).data;v.progress,elapsed=advance(r,v.progress,data.hours);v.simulation_hours+=elapsed
        if v.progress>=r['distance']-1e-6:v.status='completed';notify(db,id,'INFO','Vessel reached destination offshore approach')
        p=monitoring(db,v);db.add(AISPosition(voyage_id=id,data=p));db.commit();return p
@app.get('/api/monitoring/{id}/live-ais')
def live_ais(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    v=voyage_for(db,id,user)
    try:p=get_live_position(v.vessel_snapshot.get('imo'));db.add(AISPosition(voyage_id=id,data=p));db.commit();return p
    except Exception as e:raise HTTPException(502,'Live AIS unavailable. Check the configured HTTPS gateway and credentials.') from e
@app.post('/api/monitoring/{id}/hazard')
def hazard(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    v=voyage_for(db,id,user)
    if v.mode!='demo' or v.status=='completed':raise HTTPException(409,'Hazard injection requires an unfinished demo voyage')
    r=latest(db,v).data;remaining=r['distance']-v.progress
    if remaining<80:raise HTTPException(409,'Too close to the destination to inject the prepared storm')
    ahead=min(180,remaining*.55);p=position_at(r,v.progress+ahead,v.departure,v.simulation_hours)
    h={'latitude':p['latitude'],'longitude':p['longitude'],'radius_km':min(85,ahead*.42),'wave_height':7.2,'wind_speed':32,'name':'Injected demo storm'}
    v.hazards=[*(v.hazards or []),h];notify(db,id,'CRITICAL',f'High wave conditions detected {ahead:.0f} km ahead. Peak wave height 7.2 m. Recalculate the remaining route.');log(db,user.id,'inject_demo_hazard',str(id));db.commit();return detail(db,v)

def recalculate(db,v,user):
    if v.status=='completed':raise HTTPException(409,'Voyage already completed')
    old=latest(db,v);p=position_at(old.data,v.progress,v.departure,v.simulation_hours)
    end=old.data['points'][-1];stamp=(datetime.fromisoformat(v.departure)+timedelta(hours=v.simulation_hours)).isoformat()
    try:a,b=optimize((p['latitude'],p['longitude']),end,v.vessel_snapshot,stamp,policy(db),v.preference,v.safety,v.mode,v.hazards,old.data['algorithm'])
    except ValueError as e:
        notify(db,v.id,'CRITICAL','Recalculation failed; previous route retained. '+str(e));db.commit();raise HTTPException(422,str(e))
    version=old.version+1;br=save_route(db,v,a,'baseline',version);op=save_route(db,v,b,'optimized',version)
    db.add(Comparison(voyage_id=v.id,baseline_id=br.id,optimized_id=op.id,data=comparison(a,b)))
    v.travelled+=v.progress;v.progress=0
    for alert in db.query(Alert).filter_by(voyage_id=v.id,acknowledged=False):alert.acknowledged=True
    notify(db,v.id,'INFO',f'Route version {version} calculated from current position. Comparison now covers the remaining voyage.');log(db,user.id,'recalculate',str(v.id));db.commit();return detail(db,v)
@app.post('/api/monitoring/{id}/recalculate')
def recalc(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    with voyage_lock:return recalculate(db,voyage_for(db,id,user,True),user)
@app.post('/api/monitoring/{id}/refresh')
def refresh(id:int,auto_recalculate:bool=True,user=Depends(current_user),db:Session=Depends(get_db)):
    v=voyage_for(db,id,user);r=latest(db,v).data;p=monitoring(db,v);s=WeatherService(v.mode,p['timestamp'],v.hazards)
    try:
        s.prepare((p['latitude'],p['longitude']),r['points'][-1]);danger=False
        for d in range(int(v.progress),int(r['distance'])+1,10):
            at=position_at(r,d,v.departure,v.simulation_hours);w=s.get_weather(at['latitude'],at['longitude'])
            if not weather_risk(w,v.vessel_snapshot,policy(db),v.safety)['safe']:danger=True;break
    except ValueError as e:raise HTTPException(422,str(e))
    if danger:
        notify(db,id,'WARNING','Updated weather exceeds safety limits on the remaining route.');db.commit()
        if auto_recalculate:return recalculate(db,v,user)
    return {'danger_detected':danger,'monitoring':monitoring(db,v)}
@app.get('/api/alerts')
def alerts(user=Depends(current_user),db:Session=Depends(get_db)):
    ids=[v.id for v in visible(db.query(Voyage),Voyage,user)]
    return [serialize(a) for a in db.query(Alert).filter(Alert.voyage_id.in_(ids)).order_by(Alert.id.desc()).limit(200)]
@app.put('/api/alerts/{id}/acknowledge')
def acknowledge(id:int,user=Depends(current_user),db:Session=Depends(get_db)):
    a=db.get(Alert,id)
    if not a:raise HTTPException(404,'Alert not found')
    voyage_for(db,a.voyage_id,user);a.acknowledged=True;db.commit();return serialize(a)
@app.get('/api/dashboard')
def dashboard(user=Depends(current_user),db:Session=Depends(get_db)):
    vs=visible(db.query(Voyage),Voyage,user).all();fuel=co2=saved=0
    for v in vs:
        b=db.query(Route).filter_by(voyage_id=v.id,kind='baseline',version=1).first().data
        o=db.query(Route).filter_by(voyage_id=v.id,kind='optimized',version=1).first().data
        fuel+=o['fuel'];co2+=o['co2'];saved+=b['fuel']-o['fuel']
    return dict(active=sum(v.status=='active' for v in vs),completed=sum(v.status=='completed' for v in vs),voyages=len(vs),vessels=visible(db.query(Vessel),Vessel,user).count(),fuel=fuel,co2=co2,fuel_saved=saved,statistics_basis='Initial planned route estimates; not measured consumption')
@app.get('/api/fleet')
def fleet(user=Depends(current_user),db:Session=Depends(get_db)):
    if user.role not in ['manager','admin']:raise HTTPException(403,'Fleet manager access required')
    return {'stats':dashboard(user,db),'voyages':voyages(user,db),'vessels':vessels(user,db)}
@app.get('/api/admin/users')
def users(user=Depends(admin),db:Session=Depends(get_db)):return [serialize(u) for u in db.query(User)]
@app.put('/api/admin/users/{id}')
def edit_user(id:int,data:AdminUser,user=Depends(admin),db:Session=Depends(get_db)):
    u=db.get(User,id)
    if not u:raise HTTPException(404,'User not found')
    if u.id==user.id and (data.role!='admin' or not data.active):raise HTTPException(409,'Cannot revoke your own administrator access')
    u.role=data.role;u.active=data.active
    for token in db.query(Token).filter_by(user_id=id):token.revoked=True
    log(db,user.id,'change_user',str(id));db.commit();return serialize(u)
@app.get('/api/admin/settings')
def get_policy(user=Depends(admin),db:Session=Depends(get_db)):
    return {'policy':policy(db),'weather_provider':'Open-Meteo (public endpoint; no API key required)','ais_configured':bool(settings.ais_url and settings.ais_api_key),'secrets':'Set API credentials in backend .env; never exposed by API'}
@app.put('/api/admin/settings')
def set_policy(data:Policy,user=Depends(admin),db:Session=Depends(get_db)):
    db.get(SystemSetting,'policy').value=data.model_dump();log(db,user.id,'change_policy');db.commit();return data
@app.get('/api/settings')
def public_settings(user=Depends(current_user),db:Session=Depends(get_db)):return policy(db)
@app.get('/api/admin/logs')
def logs(user=Depends(admin),db:Session=Depends(get_db)):return [serialize(l) for l in db.query(Log).order_by(Log.id.desc()).limit(200)]
@app.get('/api/voyages/{id}/report')
def report(id:int,format:str='json',user=Depends(current_user),db:Session=Depends(get_db)):
    data=detail(db,voyage_for(db,id,user))
    if format=='json':return Response(json.dumps(data,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename=horizon-voyage-{id}.json'})
    if format!='pdf':raise HTTPException(422,'Choose json or pdf')
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors
    from xml.sax.saxutils import escape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont('HorizonSans',str(ROOT/'backend/app/assets/DejaVuSans.ttf')))
    pdfmetrics.registerFont(TTFont('HorizonBold',str(ROOT/'backend/app/assets/DejaVuSans-Bold.ttf')))
    stream=BytesIO();doc=SimpleDocTemplate(stream);styles=getSampleStyleSheet();story=[]
    for name in ['BodyText','Title','Heading2']:styles[name].fontName='HorizonSans' if name=='BodyText' else 'HorizonBold'
    def para(s,style='BodyText'):story.append(Paragraph(escape(str(s)),styles[style]));story.append(Spacer(1,8))
    para('HORIZON | Voyage report','Title');para(f"{data['source']['name']} to {data['destination']['name']}",'Heading2')
    for k in ['departure','status','mode','preference','safety','route_version']:para(f'{k}: {data[k]}')
    para('Vessel: '+data['vessel']['name']);para('Selected route: weather-aware optimized. Comparisons for the latest remaining-route version. All values are estimates; offshore approaches, no draft clearance verification.')
    rows=[['Metric','Baseline','Optimized']]
    for k,unit in [('distance','km'),('hours','h'),('fuel','t'),('co2','t CO2'),('risk','0-1')]:rows.append([f'{k} ({unit})',f"{data['baseline'][k]:.3f}",f"{data['optimized'][k]:.3f}"])
    rows.append(['Weather safe',str(data['baseline']['safe']),str(data['optimized']['safe'])]);table=Table(rows,colWidths=[200,120,120]);table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#102b40')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('PADDING',(0,0),(-1,-1),8),('FONTNAME',(0,0),(-1,-1),'HorizonSans')]));story.append(table)
    para('Environmental conditions','Heading2');s=data['optimized']['segments'];para(f"Maximum sampled waves: {max(x['weather']['wave_height'] for x in s):.2f} m; wind: {max(x['weather']['wind_speed'] for x in s):.2f} m/s. {data['optimized']['weather_model']}")
    para('Alerts','Heading2')
    for alert in data['alerts']:para(alert['type']+': '+alert['message'])
    para('Route history','Heading2')
    for h in data['history']:para(f"{h['kind']} version {h['version']}: {h['distance']:.1f} km ({h['created_at']})")
    doc.build(story);return Response(stream.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=horizon-voyage-{id}.pdf'})
