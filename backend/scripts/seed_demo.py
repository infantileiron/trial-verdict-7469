from datetime import datetime,timezone,timedelta
from src.config.database import Base,engine,Session
from src.models.entities import User,Experiment,Event,Enterprise,EnterpriseMember,EnterpriseAssignment
from src.utils.security import hash_password
from src.services.randomization import hash_group

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
    exp=Experiment(code=code,name=name,starts_at=(today-timedelta(days=7)).isoformat(),ends_at=ends.isoformat(),a_ratio=.5,hypothesis='更清晰的首次引导能提升首次激活率，预先固定观察期与分流比例',unit='user');s.add(exp);s.flush()
   if code.endswith('-A'):
    stamp=(datetime.fromisoformat(exp.starts_at)+timedelta(hours=12)).isoformat()
    for i in range(1200):
     group='A' if i<600 else 'B';key=f'LJ-U{i+1:04}';activated=(i<120 if group=='A' else i-600<180)
     for kind in ['exposure']+(['activation'] if activated else []):
      if not s.query(Event).filter_by(experiment_id=exp.id,user_key=key,kind=kind).first():s.add(Event(experiment_id=exp.id,user_key=key,group=group,kind=kind,occurred_at=stamp))
  # ---------- 企业整群随机演示：12 家企业（每臂 6 家），规模悬殊，已成熟 ----------
  ent_code='LJ-ENT-A';ent_exp=s.query(Experiment).filter_by(code=ent_code).first()
  if not ent_exp:
   ent_exp=Experiment(code=ent_code,name='企业协作空间 / 整群随机成熟实验',
    starts_at=(today-timedelta(days=14)).isoformat(),ends_at=(today-timedelta(days=1)).isoformat(),
    a_ratio=.5,hypothesis='面向企业客户的多人协作，按企业整群随机，避免按个人检验夸大试用效果',unit='enterprise')
   s.add(ent_exp);s.flush()
  # 选 12 个键使哈希分组恰好 6/6，规模从 3 到 120 体现企业大小悬殊
  chosen=[];ca=cb=0
  for i in range(400):
   if ca>=6 and cb>=6:break
   key=f'LJ-ENT{i+1:03d}'
   g=hash_group(ent_exp.code,ent_exp.starts_at,key,.5)
   if (g=='A' and ca<6) or (g=='B' and cb<6):
    chosen.append((key,g));ca+=g=='A';cb+=g=='B'
  sizes=[120,88,64,45,30,12,96,70,52,38,20,3]
  base_rate={'A':.24,'B':.42}
  stamp=(datetime.fromisoformat(ent_exp.starts_at)+timedelta(hours=20)).isoformat()
  for (key,g),n in zip(chosen,sizes):
   ent=s.query(Enterprise).filter_by(key=key).first()
   if not ent:
    ent=Enterprise(key=key,name='棱镜客户 '+key,created=stamp);s.add(ent);s.flush()
   if not s.query(EnterpriseAssignment).filter_by(experiment_id=ent_exp.id,enterprise_id=ent.id).first():
    s.add(EnterpriseAssignment(experiment_id=ent_exp.id,enterprise_id=ent.id,group=g,locked_at=stamp))
   rate=base_rate[g]
   for mi in range(n):
    uk=f'{key}-M{mi+1:03d}'
    if not s.query(EnterpriseMember).filter_by(user_key=uk).first():
     s.add(EnterpriseMember(enterprise_id=ent.id,user_key=uk,created=stamp))
    if not s.query(Event).filter_by(experiment_id=ent_exp.id,user_key=uk,kind='exposure').first():
     s.add(Event(experiment_id=ent_exp.id,enterprise_id=ent.id,user_key=uk,group=g,kind='exposure',occurred_at=stamp))
    if mi<round(n*rate) and not s.query(Event).filter_by(experiment_id=ent_exp.id,user_key=uk,kind='activation').first():
     s.add(Event(experiment_id=ent_exp.id,enterprise_id=ent.id,user_key=uk,group=g,kind='activation',occurred_at=stamp))
  s.commit()
  print({'users':s.query(User).count(),'experiments':s.query(Experiment).count(),
   'events':s.query(Event).count(),'enterprises':s.query(Enterprise).count(),
   'members':s.query(EnterpriseMember).count(),
   'enterprise_locks':s.query(EnterpriseAssignment).count()})
if __name__=='__main__':seed()
