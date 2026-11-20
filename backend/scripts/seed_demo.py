from datetime import datetime,timezone,timedelta
from src.config.database import Base,engine,Session
from src.models.entities import User,Experiment,Event
from src.utils.security import hash_password

def seed():
 Base.metadata.create_all(engine)
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   email=role+'@demo.local'
   if not s.query(User).filter_by(email=email).first():s.add(User(email=email,role=role,password=hash_password('Demo123!')))
  s.commit()
  today=datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)
  for code,name,ends in [('LJ-1115-A','首次引导文案 / 成熟对照',today-timedelta(days=1)),('LJ-1115-B','快捷模板入口 / 观察中',today+timedelta(days=3))]:
   exp=s.query(Experiment).filter_by(code=code).first()
   if not exp:
    exp=Experiment(code=code,name=name,starts_at=(today-timedelta(days=7)).isoformat(),ends_at=ends.isoformat(),a_ratio=.5,hypothesis='更清晰的首次引导能提升首次激活率，预先固定观察期与分流比例');s.add(exp);s.flush()
   if code.endswith('-A'):
    stamp=(datetime.fromisoformat(exp.starts_at)+timedelta(hours=12)).isoformat()
    for i in range(1200):
     group='A' if i<600 else 'B';key=f'LJ-U{i+1:04}';activated=(i<120 if group=='A' else i-600<180)
     for kind in ['exposure']+(['activation'] if activated else []):
      if not s.query(Event).filter_by(experiment_id=exp.id,user_key=key,kind=kind).first():s.add(Event(experiment_id=exp.id,user_key=key,group=group,kind=kind,occurred_at=stamp))
  s.commit();print({'users':s.query(User).count(),'experiments':s.query(Experiment).count(),'events':s.query(Event).count()})
if __name__=='__main__':seed()
