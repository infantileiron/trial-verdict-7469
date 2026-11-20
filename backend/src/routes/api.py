import os,json
from datetime import timezone
import redis
from fastapi import APIRouter,Depends,HTTPException,Response
from sqlalchemy.exc import IntegrityError
from src.config.database import db
from src.models.entities import User,Experiment,Event,Decision,Audit
from src.schemas.business import Login,ExperimentInput,EventInput,RunInput,RationaleInput,PublishInput
from src.middlewares.auth import current,editor,admin
from src.utils.security import verify,token
from src.services.business import audit,dump,utc
from src.controllers.business import experiment,decision,validate_event,snapshot,publish
router=APIRouter()
@router.post('/auth/login')
def login(data:Login,s=Depends(db)):
 u=s.query(User).filter_by(email=data.email).first()
 if not u or not verify(data.password,u.password):raise HTTPException(401,'账号或密码错误')
 return {'token':token(u),'user':dump(u)}
@router.get('/me')
def me(u=Depends(current)):return dump(u)
@router.get('/experiments')
def experiments(u=Depends(current),s=Depends(db)):
 return [{**dump(e),'exposures':s.query(Event).filter_by(experiment_id=e.id,kind='exposure').count()} for e in s.query(Experiment).order_by(Experiment.id.desc())]
@router.post('/experiments')
def create_experiment(data:ExperimentInput,u=Depends(editor),s=Depends(db)):
 d=data.model_dump();d['starts_at']=utc(data.starts_at);d['ends_at']=utc(data.ends_at);r=Experiment(**d);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'实验编号已存在')
 audit(s,u,'建立实验 '+r.code);return dump(r)
@router.put('/experiments/{i}')
def edit_experiment(i:int,data:ExperimentInput,u=Depends(editor),s=Depends(db)):
 r=experiment(s,i)
 if s.query(Event).filter_by(experiment_id=i).first():raise HTTPException(409,'已有事件，禁止事后修改实验定义；请建立新实验')
 d=data.model_dump();d['starts_at']=utc(data.starts_at);d['ends_at']=utc(data.ends_at)
 for k,v in d.items():setattr(r,k,v)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'实验编号已存在')
 audit(s,u,'修订实验 '+str(i));return dump(r)
@router.get('/events')
def events(experiment_id:int|None=None,u=Depends(current),s=Depends(db)):
 q=s.query(Event)
 if experiment_id:q=q.filter_by(experiment_id=experiment_id)
 return [dump(e) for e in q.order_by(Event.id.desc())]
@router.post('/events')
def create_event(data:EventInput,u=Depends(editor),s=Depends(db)):
 stamp=validate_event(s,data);d=data.model_dump();d['occurred_at']=stamp;r=Event(**d);s.add(r)
 try:s.commit()
 except IntegrityError:s.rollback();raise HTTPException(409,'该用户事件已存在')
 audit(s,u,'采集事件 '+str(r.id));return dump(r)
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
def audits(u=Depends(admin),s=Depends(db)):return [dump(r) for r in s.query(Audit).order_by(Audit.id.desc()).limit(100)]
