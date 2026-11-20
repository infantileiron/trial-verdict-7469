"""增量、幂等的结构迁移。

项目用 SQLAlchemy metadata 初始化新库；对已落库的旧卷，create_all 不会补列，
因此这里按信息架构检查后做 additive ALTER。旧实验自动回填 unit='user'，
保证企业整群随机上线后历史实验仍走个人检验口径。
"""
from sqlalchemy import text,inspect

def _has_column(ins,table,column):
 return table in ins.get_table_names() and any(c['name']==column for c in ins.get_columns(table))

def run_migrations(engine):
 with engine.begin() as conn:
  ins=inspect(conn)
  if ins.has_table('experiments') and not _has_column(ins,'experiments','unit'):
   conn.execute(text("ALTER TABLE experiments ADD COLUMN unit VARCHAR(20) DEFAULT 'user'"))
  if ins.has_table('events') and not _has_column(ins,'events','enterprise_id'):
   conn.execute(text('ALTER TABLE events ADD COLUMN enterprise_id INT NULL'))
  # 历史实验全部回填为个人随机，新实验在创建时显式写入 unit
  if ins.has_table('experiments'):
   conn.execute(text("UPDATE experiments SET unit='user' WHERE unit IS NULL"))
