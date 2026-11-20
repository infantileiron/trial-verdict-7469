import os,json
from datetime import datetime,timezone
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Experiment,Event,Decision,Audit,Enterprise,EnterpriseMember,EnterpriseAssignment
from src.schemas.business import (Login,ExperimentInput,EventInput,RunInput,RationaleInput,
 PublishInput,EnterpriseInput,MemberInput)
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump,utc
from src.controllers.business import experiment,decision,enterprise,validate_event,create_event_row,snapshot,publish
router=APIRouter()
def _now():return datetime.now(timezone.utc).isoformat()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/experiments')
def experiments(u=Depends(current),s=Depends(db)):
 out=[]
 for e in s.query(Experiment).order_by(Experiment.id.desc()).all():
  row={**dump(e),'exposures':s.query(Event).filter_by(experiment_id=e.id,kind='exposure').count()}
  if (e.unit or 'user')=='enterprise':
   row['enterprise_count']=s.query(EnterpriseAssignment).filter_by(experiment_id=e.id).count()
  out.append(row)
 return out
@router.post('/experiments')
def create_experiment(data:ExperimentInput,u=Depends(editor),s=Depends(db)):
 d=data.model_dump();d['starts_at']=utc(data.starts_at);d['ends_at']=utc(data.ends_at);r=Experiment(**d);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'实验编号已存在')
 audit(s,u,'建立实验 '+r.code+' / 单位 '+(r.unit or 'user'));return dump(r)
@router.put('/experiments/{i}')
def edit_experiment(i:int,data:ExperimentInput,u=Depends(editor),s=Depends(db)):
 r=experiment(s,i)
 if s.query(Event).filter_by(experiment_id=i).first():raise HTTPException(409,'已有事件，禁止事后修改实验定义；请建立新实验')
 d=data.model_dump();d['starts_at']=utc(data.starts_at);d['ends_at']=utc(data.ends_at)
 for k,v in d.items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'实验编号已存在')
 audit(s,u,'修订实验 '+str(i));return dump(r)
# ---------- 企业与成员归属（成员唯一归属企业，采集沿用该归属） ----------
@router.get('/enterprises')
def enterprises(u=Depends(current),s=Depends(db)):
 rows=[]
 for e in s.query(Enterprise).order_by(Enterprise.id).all():
  members=s.query(EnterpriseMember).filter_by(enterprise_id=e.id).count()
  rows.append({**dump(e),'members':members})
 return rows
@router.post('/enterprises')
def create_enterprise(data:EnterpriseInput,u=Depends(editor),s=Depends(db)):
 r=Enterprise(key=data.key,name=data.name,created=_now());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'企业键已存在')
 audit(s,u,'登记企业 '+r.key);return dump(r)
@router.post('/enterprises/members')
def add_member(data:MemberInput,u=Depends(editor),s=Depends(db)):
 ent=enterprise(s,data.enterprise_key)
 if s.query(EnterpriseMember).filter_by(user_key=data.user_key).first():
  raise HTTPException(409,'该成员已归属企业，冻结期间不可改挂')
 r=EnterpriseMember(enterprise_id=ent.id,user_key=data.user_key,created=_now());s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'成员归属冲突')
 audit(s,u,'成员归属 '+data.user_key+' -> '+ent.key);return dump(r)
@router.get('/experiments/{i}/coverage')
def coverage(i:int,u=Depends(current),s=Depends(db)):
 """企业覆盖核对：锁定组别、企业/成员/曝光/激活分布，供页面核对采集口径。"""
 exp=experiment(s,i)
 if (exp.unit or 'user')!='enterprise':
  return {'unit':'user','message':'个人随机实验不适用企业覆盖视图'}
 assignments=s.query(EnterpriseAssignment).filter_by(experiment_id=exp.id).all()
 groups={'A':[],'B':[]}
 for a in assignments:groups[a.group].append(a.enterprise_id)
 def arm_stats(ent_ids):
  if not ent_ids:return dict(enterprises=0,members=0,exposures=0,activations=0)
  ev=s.query(Event).filter(Event.experiment_id==exp.id,Event.enterprise_id.in_(ent_ids)).all()
  members=s.query(EnterpriseMember).filter(EnterpriseMember.enterprise_id.in_(ent_ids)).count()
  return dict(enterprises=len(ent_ids),members=members,
   exposures=len({e.user_key for e in ev if e.kind=='exposure'}),
   activations=len({e.user_key for e in ev if e.kind=='activation'}))
 locked=[dict(enterprise_id=a.enterprise_id,group=a.group,locked_at=a.locked_at,
  locked_by_event=a.locked_by_event) for a in assignments]
 return {'unit':'enterprise','experiment':dump(exp),
  'arm_a':arm_stats(groups['A']),'arm_b':arm_stats(groups['B']),'locked':locked}
# ---------- 事件采集 ----------
@router.get('/events')
def events(experiment_id:int|None=None,u=Depends(current),s=Depends(db)):
 q=s.query(Event)
 if experiment_id:q=q.filter_by(experiment_id=experiment_id)
 return [dump(e) for e in q.order_by(Event.id.desc())]
@router.post('/events')
def create_event(data:EventInput,u=Depends(editor),s=Depends(db)):
 stamp,ent,_group=validate_event(s,data)
 # 企业首曝存在并发竞态：败者回滚后按已锁定组别幂等重试，保证并发与失败重试结果一致
 for attempt in range(2):
  try:
   r,group=create_event_row(s,data,stamp,ent);s.commit();break
  except IntegrityError:
   s.rollback()
   if ent is None or attempt==1:raise HTTPException(409,'该用户事件已存在，请按冻结归属重试')
   stamp,ent,_group=validate_event(s,data)
 audit(s,u,'采集事件 '+str(r.id)+(' 企业组 '+group if ent else ' 组 '+group));return dump(r)
# ---------- 裁决排队、重试、发布 ----------
@router.get('/decisions')
def decisions(u=Depends(current),s=Depends(db)):return [dump(r) for r in s.query(Decision).order_by(Decision.id.desc())]
@router.post('/decisions')
def run(data:RunInput,u=Depends(editor),s=Depends(db)):
 exp=experiment(s,data.experiment_id)
 if s.query(Decision).filter(Decision.state.in_(['queued','running'])).count()>=10:raise HTTPException(429,'队列已满，请等待任务完成')
 r=Decision(experiment_id=exp.id,snapshot=snapshot(s,exp));s.add(r);s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('trial:decisions',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，恢复后重新提交';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'提交实验裁决 '+str(r.id));return dump(r)
@router.post('/decisions/{i}/retry')
def retry(i:int,u=Depends(editor),s=Depends(db)):
 """失败任务重试：复用原冻结快照重新排队，保证不混入重试后新采集的成员与事件。"""
 r=decision(s,i)
 if r.state!='failed':raise HTTPException(409,'仅失败任务可重试；进行中请等待，已完成请新建裁决')
 r.state='queued';r.error='';s.commit()
 try:redis.Redis.from_url(os.environ['REDIS_URL']).rpush('trial:decisions',r.id)
 except redis.RedisError:r.state='failed';r.error='队列暂不可用，恢复后重新提交';s.commit();raise HTTPException(503,r.error)
 audit(s,u,'重试失败裁决 '+str(i));return dump(r)
@router.get('/decisions/{i}')
def detail(i:int,u=Depends(current),s=Depends(db)):return dump(decision(s,i))
@router.put('/decisions/{i}/rationale')
def rationale(i:int,data:RationaleInput,u=Depends(editor),s=Depends(db)):
 r=decision(s,i)
 if r.published_at:raise HTTPException(409,'已发布裁决不可覆盖，请重新创建裁决')
 if r.state!='done':raise HTTPException(409,'计算完成后再填写裁决理由')
 r.rationale=data.rationale;s.commit();audit(s,u,'保存裁决理由 '+str(i));return dump(r)
@router.post('/decisions/{i}/publish')
def release(i:int,data:PublishInput,u=Depends(admin),s=Depends(db)):
 r=publish(s,decision(s,i),data.action,u);audit(s,u,'发布裁决 '+str(i)+' '+data.action);return dump(r)
@router.get('/decisions/{i}/export')
def export(i:int,u=Depends(current),s=Depends(db)):
 r=decision(s,i)
 if r.state!='done':raise HTTPException(409,'尚无成功结果')
 return Response(json.dumps(dump(r),ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="trial-verdict-{i}.json"'})
@router.get('/audits')
def audits(u=Depends(admin),s=Depends(db)):
 return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
