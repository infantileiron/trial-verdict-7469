import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
engine=create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
Session=sessionmaker(bind=engine,expire_on_commit=False)
Base=declarative_base()
def db():
 with Session() as s: yield s
