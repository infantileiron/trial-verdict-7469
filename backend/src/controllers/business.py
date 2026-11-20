from fastapi import HTTPException
from datetime import datetime,timezone
from src.models.entities import Experiment,Event,Decision,Enterprise,EnterpriseMember
from src.services.business import dump,utc
from src.services.analysis import calculate_for_snapshot
from src.services.grouping import resolve_member,assign_for_enterprise,locked_group
def experiment(s,i):
 r=s.get(Experiment,i)
 if not r:raise HTTPException(404,'实验不存在')
 return r
def decision(s,i):
 r=s.get(Decision,i)
 if not r:raise HTTPException(404,'裁决记录不存在')
 return r
def enterprise(s,key):
 r=s.query(Enterprise).filter_by(key=key).first()
 if not r:raise HTTPException(404,'企业不存在，请先登记企业与成员归属')
 return r
def _user_level_validate(s,exp,data,stamp):
 prior=s.query(Event).filter_by(experiment_id=exp.id,user_key=data.user_key).all()
 if any(e.group!=data.group for e in prior):raise HTTPException(409,'同一用户不能跨组，需排查分流污染')
 if any(e.kind==data.kind for e in prior):raise HTTPException(409,'重复事件：同一实验/用户/事件类型只记一次')
 if data.kind=='activation':
  exposure=next((e for e in prior if e.kind=='exposure'),None)
  if not exposure:raise HTTPException(422,'先录入该用户曝光，再录入激活')
  if stamp<exposure.occurred_at:raise HTTPException(422,'激活时间不能早于曝光')
def _enterprise_validate(s,exp,data,stamp):
 # 成员沿用企业归属：未登记企业的成员拒绝采集，避免个人口径混入整群实验
 member,ent=resolve_member(s,data.user_key)
 if not ent:raise HTTPException(422,'该成员尚未归属任何企业，企业实验拒绝个人口径事件')
 lock=locked_group(s,exp,ent)
 prior=s.query(Event).filter_by(experiment_id=exp.id,user_key=data.user_key).all()
 if lock:
  # 组别已锁定：客户端即使带组也以锁定组为准；显式冲突直接拒收
  if data.group is not None and data.group!=lock.group:
   raise HTTPException(409,f'企业 {ent.key} 已锁定 {lock.group} 组，跨组事件拒收')
  group=lock.group
  if any(e.kind==data.kind for e in prior):raise HTTPException(409,'重复事件：同一实验/用户/事件类型只记一次')
 else:
  # 该企业首次曝光才允许建立锁定；激活不能先于曝光，未锁定企业无组别可依
  if data.kind!='exposure':
   raise HTTPException(422,'企业尚未发生首次曝光，需先录入曝光以锁定企业组别')
  group=None
 if data.kind=='activation':
  exposure=next((e for e in prior if e.kind=='exposure'),None)
  if not exposure:raise HTTPException(422,'先录入该用户曝光，再录入激活')
  if stamp<exposure.occurred_at:raise HTTPException(422,'激活时间不能早于曝光')
 return ent,group
def validate_event(s,data):
 exp=experiment(s,data.experiment_id);stamp=utc(data.occurred_at)
 if not (exp.starts_at<=stamp<=exp.ends_at):raise HTTPException(422,'事件时间必须落在实验预定区间内')
 if data.occurred_at>datetime.now(timezone.utc):raise HTTPException(422,'不能录入未来事件')
 if (exp.unit or 'user')=='enterprise':
  ent,group=_enterprise_validate(s,exp,data,stamp)
  return stamp,ent,group
 if data.group is None:raise HTTPException(422,'个人随机实验必须指定组别 A/B')
 _user_level_validate(s,exp,data,stamp)
 return stamp,None,None
def create_event_row(s,data,stamp,ent):
 exp=experiment(s,data.experiment_id)
 if (exp.unit or 'user')=='enterprise':
  # 首曝在同一事务内 upsert 锁定；并发重复首曝由唯一约束收敛，重试得到同一组别
  group,is_new=assign_for_enterprise(s,exp,ent,None,stamp)
  row=Event(experiment_id=exp.id,enterprise_id=ent.id,user_key=data.user_key,
    group=group,kind=data.kind,occurred_at=stamp)
  s.add(row);s.flush()
  if is_new:
   lock=locked_group(s,exp,ent);lock.locked_by_event=row.id
  return row,group
 row=Event(experiment_id=exp.id,user_key=data.user_key,group=data.group,
   kind=data.kind,occurred_at=stamp)
 s.add(row);s.flush()
 return row,data.group
def snapshot(s,exp):
 base={'experiment':dump(exp),
  'events':[dump(e) for e in s.query(Event).filter_by(experiment_id=exp.id).order_by(Event.id).all()]}
 if (exp.unit or 'user')=='enterprise':
  # 冻结企业归属、成员与组别锁定：计算与并发采集共用同一份对应关系，重试不混入新成员
  base['enterprises']=[dump(e) for e in s.query(Enterprise).order_by(Enterprise.id).all()]
  base['members']=[dump(m) for m in s.query(EnterpriseMember).order_by(EnterpriseMember.id).all()]
  from src.models.entities import EnterpriseAssignment
  base['assignments']=[dump(a) for a in s.query(EnterpriseAssignment).filter_by(experiment_id=exp.id).order_by(EnterpriseAssignment.id).all()]
 return base
def publish(s,item,action,user):
 if item.state!='done':raise HTTPException(409,'计算完成后才可发布')
 if item.published_at:raise HTTPException(409,'该裁决已发布，记录不可覆盖')
 if len(item.rationale)<10:raise HTTPException(409,'请先补充至少10字裁决理由')
 # 用冻结快照复算，后加样本不改变旧裁决；算法按协议单位分派
 result=calculate_for_snapshot(item.snapshot)
 if not result['release_eligible']:raise HTTPException(409,'；'.join(result['block_reasons']))
 if action=='publish_b' and not result['significant_positive']:
  raise HTTPException(409,'上线B需B−A为正且通过对应随机化单位的显著性门禁')
 item.action=action;item.published_by=user.email;item.published_at=datetime.now(timezone.utc).isoformat();s.commit();return item
