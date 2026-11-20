from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from src.config.database import db
from src.models.entities import User
from src.utils.security import KEY
import jwt
bearer=HTTPBearer(auto_error=False)
def current(c:HTTPAuthorizationCredentials=Depends(bearer),s=Depends(db)):
 try:
  payload=jwt.decode(c.credentials,KEY,algorithms=['HS256']);u=s.get(User,int(payload['sub']))
  if not u:raise ValueError()
  return u
 except Exception:raise HTTPException(401,'登录已失效，请重新登录')
def editor(u=Depends(current)):
 if u.role=='viewer':raise HTTPException(403,'观察员只读，不能修改或提交实验计算')
 return u
def admin(u=Depends(current)):
 if u.role!='admin':raise HTTPException(403,'仅负责人可以签核')
 return u
