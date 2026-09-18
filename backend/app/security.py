import secrets, time
from pathlib import Path
import jwt
from pwdlib import PasswordHash
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings, ROOT
from app.database import get_db
from app.models import User, Token
hasher=PasswordHash.recommended()
secret=settings.jwt_secret_key
if not secret:
    path=ROOT/'backend'/'.jwt-secret'
    if not path.exists():
        try:
            with path.open('x') as f: f.write(secrets.token_hex(48))
            path.chmod(0o600)
        except FileExistsError: pass
    secret=path.read_text().strip()
if len(secret)<32: raise RuntimeError('JWT secret must contain at least 32 characters')
bearer=HTTPBearer(auto_error=False)
def issue(db,user):
    tid=secrets.token_hex(24); expires=time.time()+8*3600
    db.add(Token(id=tid,user_id=user.id,expires=expires)); db.commit()
    return jwt.encode(dict(sub=str(user.id),jti=tid,exp=expires,iat=time.time(),iss='horizon',aud='horizon-ui'),secret,algorithm='HS256')
def current_user(credentials: HTTPAuthorizationCredentials=Depends(bearer),db:Session=Depends(get_db)):
    try:
        if not credentials: raise ValueError()
        payload=jwt.decode(credentials.credentials,secret,algorithms=['HS256'],issuer='horizon',audience='horizon-ui',options={'require':['sub','jti','exp','iat']})
        token=db.get(Token,payload['jti']); user=db.get(User,int(payload['sub']))
        if not token or token.revoked or token.expires<time.time() or token.user_id!=user.id or not user.active: raise ValueError()
        return user
    except (jwt.InvalidTokenError,ValueError,TypeError,AttributeError): raise HTTPException(401,'Session expired or invalid')
def admin(user=Depends(current_user)):
    if user.role!='admin': raise HTTPException(403,'Administrator access required')
    return user
def serialize(obj):
    return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name!='password_hash'}
