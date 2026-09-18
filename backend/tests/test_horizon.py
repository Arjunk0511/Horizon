import os, tempfile, math
from pathlib import Path
os.environ['DATABASE_URL']='sqlite:///'+str(Path(tempfile.mkdtemp())/'test.db')
os.environ['JWT_SECRET_KEY']='test-only-secret-0123456789abcdef0123456789abcdef'
os.environ['DEMO_PASSWORD']='TestPassword123!'
os.environ['DEMO_MODE']='true'
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString
from app.main import app
from app.database import SessionLocal
from app.models import User,Token,Route,WeatherData,Comparison
from app.schemas import VesselInput,Policy
from app.utils.geo import haversine
from app.algorithms.astar import search
from app.algorithms.dijkstra import dijkstra
from app.algorithms.maritime_graph import land_geometry,graph_with_endpoints
from app.services.weather_service import WeatherService,weather_risk
from app.services.route_optimizer import optimize
from app.services.fuel_calculator import segment_metrics
from app.services.emission_calculator import calculate_co2

@pytest.fixture(scope='module')
def client():
    with TestClient(app) as client: yield client

def signin(c,email='planner@horizon.local'):
    r=c.post('/api/auth/login',json=dict(email=email,password='TestPassword123!'));assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token']}

def test_math_and_search():
    assert haversine((0,0),(0,1))==pytest.approx(111.195,abs=.01)
    assert haversine((1,2),(1,2))==0
    graph={'a':[('b',1),('c',5)],'b':[('c',2)],'c':[]}
    assert search(graph,'a','c',lambda u,v,d:d,lambda _:0)[0]==['a','b','c']
    assert dijkstra(graph,'a','c',lambda u,v,d:d)[1]==3
    with pytest.raises(ValueError):dijkstra(graph,'c','a',lambda u,v,d:d)
    v=VesselInput(name='Test').model_dump()
    calm=dict(wave_height=0,wind_speed=0,current_speed=0,current_direction=0)
    m=segment_metrics((0,0),(0,1),14*1.852*24,v,calm)
    assert m['hours']==pytest.approx(24)
    assert m['fuel']==pytest.approx(25)
    assert calculate_co2(25,'HFO')==pytest.approx(77.85)
    assert not weather_risk({**calm,'wave_height':5},v,Policy().model_dump())['safe']
    w=WeatherService();assert w.get_weather(14.5,74)==w.get_weather(14.5,74)

def test_auth_security(client):
    assert client.get('/api/vessels').status_code==401
    data=dict(name='New Planner',email='new@example.com',password='StrongPassword2026')
    r=client.post('/api/auth/register',json={**data,'role':'admin'});assert r.status_code==422
    r=client.post('/api/auth/register',json=data);assert r.status_code==201,r.text
    headers={'Authorization':'Bearer '+r.json()['access_token']}
    assert r.json()['user']['role']=='planner'
    assert client.post('/api/auth/register',json=data).status_code==409
    assert client.get('/api/admin/users',headers=headers).status_code==403
    assert client.get('/api/fleet',headers=headers).status_code==403
    assert client.put('/api/auth/profile',headers=headers,json={'name':'Updated Planner'}).status_code==200
    assert client.post('/api/auth/logout',headers=headers).status_code==200
    assert client.get('/api/auth/profile',headers=headers).status_code==401
    assert client.post('/api/auth/login',json={'email':data['email'],'password':'incorrect'}).status_code==401

def test_complete_workflow(client):
    h=signin(client)
    ports=client.get('/api/ports',headers=h).json();assert len(ports)==8
    ships=client.get('/api/vessels',headers=h).json()
    body=dict(source_id=1,destination_id=3,vessel_id=ships[0]['id'],departure='2026-09-18T10:00:00Z',mode='demo')
    r=client.post('/api/voyages',headers=h,json=body);assert r.status_code==201,r.text
    v=r.json();id=v['id'];a=v['baseline'];b=v['optimized']
    assert a['safe'] is False and b['safe'] is True
    assert b['risk']<a['risk'] and b['points']!=a['points']
    assert b['fuel']>0 and b['co2']==pytest.approx(b['fuel']*3.114)
    land=land_geometry().buffer(.025)
    for data in [a,b]:
        for p,q in zip(data['points'],data['points'][1:]):assert not land.intersects(LineString([(p[1],p[0]),(q[1],q[0])]))
    # Verify another planner cannot read or mutate this voyage.
    stranger=client.post('/api/auth/login',json={'email':'new@example.com','password':'StrongPassword2026'}).json()
    other={'Authorization':'Bearer '+stranger['access_token']}
    assert client.get(f'/api/voyages/{id}',headers=other).status_code==404
    assert client.post(f'/api/monitoring/{id}/hazard',headers=other).status_code==404
    assert client.post(f'/api/monitoring/{id}/step',headers=h,json={'hours':4}).status_code==409
    assert client.post(f'/api/monitoring/{id}/start',headers=h).status_code==200
    before=client.get(f'/api/monitoring/{id}',headers=h).json()
    step=client.post(f'/api/monitoring/{id}/step',headers=h,json={'hours':4});assert step.status_code==200
    after=step.json();assert after['remaining_distance']<before['remaining_distance'];assert after['mode']=='simulated'
    inject=client.post(f'/api/monitoring/{id}/hazard',headers=h);assert inject.status_code==200,inject.text
    recalc=client.post(f'/api/monitoring/{id}/recalculate',headers=h);assert recalc.status_code==200,recalc.text
    changed=recalc.json();assert changed['route_version']==2;assert len(changed['history'])==4
    assert haversine(changed['optimized']['points'][0],(after['latitude'],after['longitude']))<.001
    assert changed['optimized']['safe'];assert changed['optimized']['points']!=b['points']
    assert client.get(f'/api/routes/compare?voyage_id={id}',headers=h).status_code==200
    assert client.get(f'/api/voyages/{id}/report?format=json',headers=h).json()['id']==id
    pdf=client.get(f'/api/voyages/{id}/report?format=pdf',headers=h);assert pdf.status_code==200,pdf.text[:200] if not pdf.content.startswith(b'%PDF') else ''
    assert pdf.content.startswith(b'%PDF');Path('/tmp/horizon-test-report.pdf').write_bytes(pdf.content)
    for _ in range(10):
        m=client.post(f'/api/monitoring/{id}/step',headers=h,json={'hours':48}).json()
        if m['status']=='completed':break
    assert m['status']=='completed' and m['remaining_distance']==0
    assert client.get('/api/voyages',headers=h).json()[0]['status']=='completed'
    assert client.delete('/api/vessels/'+str(ships[0]['id']),headers=h).status_code==409
    assert client.get(f'/api/monitoring/{id}/live-ais',headers=h).status_code==502
    print('\nDEMO:',{'baseline_km':round(a['distance'],1),'optimized_km':round(b['distance'],1),'baseline_fuel':round(a['fuel'],1),'optimized_fuel':round(b['fuel'],1),'route_versions':len(changed['history'])})

def test_vessel_admin_and_persistence(client):
    h=signin(client);data=VesselInput(name='Test vessel').model_dump()
    r=client.post('/api/vessels',headers=h,json=data);assert r.status_code==201;id=r.json()['id']
    data['name']='Edited vessel';assert client.put(f'/api/vessels/{id}',headers=h,json=data).status_code==200
    assert client.delete(f'/api/vessels/{id}',headers=h).status_code==200
    admin=signin(client,'admin@horizon.local');manager=signin(client,'manager@horizon.local')
    assert client.get('/api/fleet',headers=manager).status_code==200
    p=Policy().model_dump();p['high']=.1;assert client.put('/api/admin/settings',headers=admin,json=p).status_code==422
    p=Policy().model_dump();p['maximum_wave_height']=3.8;assert client.put('/api/admin/settings',headers=admin,json=p).status_code==200
    assert client.get('/api/admin/settings',headers=admin).json()['policy']['maximum_wave_height']==3.8
    assert client.get('/api/admin/logs',headers=admin).json()
    assert client.get('/api/admin/users',headers=admin).json()
    with SessionLocal() as db:
        assert db.query(Route).count()>=4 and db.query(WeatherData).count()>=4 and db.query(Comparison).count()>=2
        assert db.query(User).filter_by(email='new@example.com').first().password_hash.startswith('$argon2id$')

def test_graph_connections_and_algorithms():
    import json
    from app.config import ROOT
    from app.algorithms.astar import search
    ports=json.loads((ROOT/'data/ports/ports.json').read_text())
    for port in ports[1:]:
        start=(ports[0]['approach_lat'],ports[0]['approach_lon']);end=(port['approach_lat'],port['approach_lon'])
        points,g=graph_with_endpoints(start,end)
        a=search(g,'start','end',lambda u,v,d:d,lambda n:haversine(points[n],end))
        b=dijkstra(g,'start','end',lambda u,v,d:d)
        assert a[1]==pytest.approx(b[1]),port['name']

def test_live_failure_is_not_mock():
    s=WeatherService('live','2000-01-01T00:00:00+00:00')
    with pytest.raises(ValueError,match='six days'):s.prepare((10,70),(12,72))
    with pytest.raises(ValueError):s.get_weather(10,70)
