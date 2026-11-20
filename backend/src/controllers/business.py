from fastapi import HTTPException
from datetime import datetime,timezone
from src.models.entities import Experiment,Event,Decision
from src.services.business import dump,utc
from src.services.analysis import calculate
def experiment(s,i):
 r=s.get(Experiment,i)
 if not r:raise HTTPException(404,'实验不存在')
 return r
def decision(s,i):
 r=s.get(Decision,i)
 if not r:raise HTTPException(404,'裁决记录不存在')
 return r
def validate_event(s,data):
 exp=experiment(s,data.experiment_id);stamp=utc(data.occurred_at)
 if not (exp.starts_at<=stamp<=exp.ends_at):raise HTTPException(422,'事件时间必须落在实验预定区间内')
 if data.occurred_at>datetime.now(timezone.utc):raise HTTPException(422,'不能录入未来事件')
 prior=s.query(Event).filter_by(experiment_id=exp.id,user_key=data.user_key).all()
 if any(e.group!=data.group for e in prior):raise HTTPException(409,'同一用户不能跨组，需排查分流污染')
 if any(e.kind==data.kind for e in prior):raise HTTPException(409,'重复事件：同一实验/用户/事件类型只记一次')
 if data.kind=='activation':
  exposure=next((e for e in prior if e.kind=='exposure'),None)
  if not exposure:raise HTTPException(422,'先录入该用户曝光，再录入激活')
  if stamp<exposure.occurred_at:raise HTTPException(422,'激活时间不能早于曝光')
 return stamp
def snapshot(s,exp):
 return {'experiment':dump(exp),'events':[dump(e) for e in s.query(Event).filter_by(experiment_id=exp.id).order_by(Event.id).all()]}
def publish(s,item,action,user):
 if item.state!='done':raise HTTPException(409,'计算完成后才可发布')
 if item.published_at:raise HTTPException(409,'该裁决已发布，记录不可覆盖')
 if len(item.rationale)<10:raise HTTPException(409,'请先补充至少10字裁决理由')
 result=calculate(item.snapshot)
 if not result['release_eligible']:raise HTTPException(409,'；'.join(result['block_reasons']))
 if action=='publish_b' and not result['significant_positive']:raise HTTPException(409,'上线B需B−A为正且双侧p<0.05')
 item.action=action;item.published_by=user.email;item.published_at=datetime.now(timezone.utc).isoformat();s.commit();return item
