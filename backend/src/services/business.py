from datetime import datetime,timezone
from src.models.entities import Audit
def utc(t):return t.astimezone(timezone.utc).isoformat()
def audit(s,u,action):s.add(Audit(actor=u.email,action=action,created=datetime.now(timezone.utc).isoformat()));s.commit()
def dump(obj):return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name!='password'}
