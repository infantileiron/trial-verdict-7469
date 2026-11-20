from sqlalchemy import Column,Integer,String,Float,JSON,Text,UniqueConstraint,ForeignKey,Index
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True);password=Column(String(200));role=Column(String(20))
class Experiment(Base):
 __tablename__='experiments'
 # unit: user=个人随机（旧实验，双比例z检验）；enterprise=企业整群随机（簇稳健分析）
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True);name=Column(String(120));starts_at=Column(String(40));ends_at=Column(String(40));a_ratio=Column(Float);hypothesis=Column(Text);unit=Column(String(20),default='user')
class Enterprise(Base):
 __tablename__='enterprises'
 id=Column(Integer,primary_key=True);key=Column(String(80),unique=True);name=Column(String(120));created=Column(String(40))
class EnterpriseMember(Base):
 __tablename__='enterprise_members'
 __table_args__=(UniqueConstraint('user_key',name='uq_member_user_key'),)
 # 成员唯一归属企业；冻结期间不允许改挂，重试与并发均以该归属解析企业
 id=Column(Integer,primary_key=True);enterprise_id=Column(Integer,ForeignKey('enterprises.id'));user_key=Column(String(80));created=Column(String(40))
class EnterpriseAssignment(Base):
 __tablename__='enterprise_assignments'
 __table_args__=(UniqueConstraint('experiment_id','enterprise_id',name='uq_exp_enterprise'),)
 # 企业在某实验中的组别，于该企业首个曝光入库时锁定，之后跨组事件一律拒收
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));enterprise_id=Column(Integer,ForeignKey('enterprises.id'));group=Column(String(1));locked_at=Column(String(40));locked_by_event=Column(Integer,nullable=True)
class Event(Base):
 __tablename__='events'
 __table_args__=(UniqueConstraint('experiment_id','user_key','kind',name='uq_exp_user_kind'),
                 Index('ix_event_exp_enterprise','experiment_id','enterprise_id'))
 # 个人实验 enterprise_id 为空；企业实验每条事件带冻结企业，采集与计算口径一致
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));enterprise_id=Column(Integer,nullable=True);user_key=Column(String(80));group=Column(String(1));kind=Column(String(20));occurred_at=Column(String(40))
class Decision(Base):
 __tablename__='decisions'
 id=Column(Integer,primary_key=True);experiment_id=Column(Integer,ForeignKey('experiments.id'));state=Column(String(20),default='queued');snapshot=Column(JSON);result=Column(JSON,nullable=True);error=Column(Text,default='');rationale=Column(Text,default='');action=Column(String(30),default='');published_by=Column(String(100),default='');published_at=Column(String(40),default='')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
