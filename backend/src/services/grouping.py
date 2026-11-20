"""企业分组落库与锁定：首曝 upsert，之后只读锁定组别。"""
from src.models.entities import Enterprise,EnterpriseMember,EnterpriseAssignment
from src.services.randomization import hash_group

def assign_hash(exp,enterprise_key):
 return hash_group(exp.code,exp.starts_at,enterprise_key,exp.a_ratio)

def resolve_member(s,user_key):
 member=s.query(EnterpriseMember).filter_by(user_key=user_key).first()
 if not member:return None,None
 enterprise=s.get(Enterprise,member.enterprise_id)
 return member,enterprise

def locked_group(s,exp,enterprise):
 return s.query(EnterpriseAssignment).filter_by(
  experiment_id=exp.id,enterprise_id=enterprise.id).first()

def assign_for_enterprise(s,exp,enterprise,event_id,now_iso):
 """返回企业在该实验的锁定组别；不存在则按哈希创建锁定（首曝调用）。"""
 row=locked_group(s,exp,enterprise)
 if row:return row.group,False
 group=assign_hash(exp,enterprise.key)
 row=EnterpriseAssignment(experiment_id=exp.id,enterprise_id=enterprise.id,
   group=group,locked_at=now_iso,locked_by_event=event_id)
 s.add(row)
 return group,True

def assignment_map(s,exp_id):
 return {a.enterprise_id:a.group for a in s.query(EnterpriseAssignment).filter_by(experiment_id=exp_id).all()}
