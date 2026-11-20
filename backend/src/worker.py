import os,time,json,logging
from pathlib import Path
import redis
from src.config.database import Base,engine,Session
from src.config.migrations import run_migrations
from src.models.entities import Decision
from src.services.analysis import calculate_for_snapshot
Base.metadata.create_all(engine);run_migrations(engine)
r=redis.Redis.from_url(os.environ['REDIS_URL'])
with Session() as recovery:
 for pending in recovery.query(Decision).filter(Decision.state.in_(['queued','running'])).all():pending.state='queued';r.rpush('trial:decisions',pending.id)
 recovery.commit()
while True:
 Path('/tmp/heartbeat').touch()
 try:
  item=r.blpop('trial:decisions',timeout=3)
  if not item:continue
  with Session() as s:
   row=s.get(Decision,int(item[1]))
   if not row or row.state!='queued':continue
   row.state='running';s.commit()
   try:
    # 始终基于入队时冻结的快照计算；失败重试也不重新采集，保证口径一致
    row.result=calculate_for_snapshot(row.snapshot);row.state='done'
    Path('/artifacts/trial-verdict-'+str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
   except Exception as e:row.state='failed';row.error=str(e)
   s.commit()
 except Exception:logging.exception('worker');time.sleep(2)
