from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
backend=root/'backend'/'.env'
if not backend.exists():
    password=secrets.token_urlsafe(15)
    jwt=secrets.token_hex(48)
    text=(root/'backend'/'.env.example').read_text()
    text=text.replace('DEMO_PASSWORD=\n','DEMO_PASSWORD='+password+'\n').replace('JWT_SECRET_KEY=\n','JWT_SECRET_KEY='+jwt+'\n')
    backend.write_text(text)
    print('Local configuration created. Demo accounts: planner@horizon.local, manager@horizon.local, admin@horizon.local')
    print('Generated demo password (all three accounts): '+password)
else:
    print('Existing backend/.env preserved. Use its DEMO_PASSWORD for seeded accounts.')
values={}
for line in backend.read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        key,value=line.split('=',1);values[key]=value
frontend=root/'frontend'/'.env'
if not frontend.exists(): frontend.write_text((root/'frontend'/'.env.example').read_text())
compose=root/'.env'
if not compose.exists():
    compose.write_text('POSTGRES_PASSWORD='+secrets.token_urlsafe(24)+'\nJWT_SECRET_KEY='+values.get('JWT_SECRET_KEY',secrets.token_hex(48))+'\nDEMO_PASSWORD='+values.get('DEMO_PASSWORD','')+'\n')
print('Configuration ready. API credentials remain in backend/.env. Do not commit .env files.')
