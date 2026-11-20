from datetime import datetime,timezone
from typing import Literal
from pydantic import BaseModel,Field,model_validator
class Login(BaseModel):
 email:str;password:str
class ExperimentInput(BaseModel):
 code:str=Field(min_length=1,max_length=60);name:str=Field(min_length=2,max_length=120)
 starts_at:datetime;ends_at:datetime;a_ratio:float=Field(default=.5,ge=.1,le=.9,allow_inf_nan=False)
 hypothesis:str=Field(min_length=5,max_length=2000)
 @model_validator(mode='after')
 def dates(self):
  if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:raise ValueError('时间必须带时区')
  if self.ends_at<=self.starts_at:raise ValueError('结束时间必须晚于开始时间')
  return self
class EventInput(BaseModel):
 experiment_id:int=Field(gt=0);user_key:str=Field(min_length=1,max_length=80);group:Literal['A','B'];kind:Literal['exposure','activation'];occurred_at:datetime
 @model_validator(mode='after')
 def dates(self):
  if self.occurred_at.tzinfo is None:raise ValueError('事件时间必须带时区')
  return self
class RunInput(BaseModel):
 experiment_id:int=Field(gt=0)
class RationaleInput(BaseModel):
 rationale:str=Field(min_length=10,max_length=3000)
class PublishInput(BaseModel):
 action:Literal['publish_b','keep_a']
