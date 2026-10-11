from datetime import datetime, timezone
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
Status = Literal['ACTIVE','INACTIVE']

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
def valid_email(value:str):
    value=value.strip().lower()
    if len(value)>254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",value): raise ValueError('must be a valid email address')
    if not value.rsplit('@',1)[1].endswith('.invalid'): raise ValueError('synthetic customer emails must use the reserved .invalid domain')
    return value
class CustomerFields(BaseModel):
    first_name: str = Field(min_length=1,max_length=80)
    last_name: str = Field(min_length=1,max_length=80)
    email: str = Field(min_length=3,max_length=254)
    phone: str|None = Field(default=None,max_length=32)
    city: str = Field(min_length=1,max_length=100)
    state: str = Field(min_length=1,max_length=100)
    postal_code: str = Field(min_length=1,max_length=20)
    country: str = Field(default='US',pattern=r'^[A-Z]{2}$')
    @field_validator('first_name','last_name','city','state','postal_code')
    @classmethod
    def trim_required(cls,v):
        v=v.strip()
        if not v: raise ValueError('must not be blank')
        return v
    @field_validator('email')
    @classmethod
    def email_is_synthetic(cls,v): return valid_email(v)
    @field_validator('phone')
    @classmethod
    def phone_is_synthetic(cls,v):
        if v is not None:
            v=v.strip()
            if not re.fullmatch(r'\+1-555-01\d{2}',v): raise ValueError('synthetic phone must use the reserved +1-555-01xx range')
        return v
class CustomerCreate(CustomerFields):
    customer_id: str|None = Field(default=None,min_length=1,max_length=80)
    customer_status: Status = 'ACTIVE'
class CustomerPatch(BaseModel):
    model_config=ConfigDict(extra='forbid')
    first_name: str|None=Field(default=None,min_length=1,max_length=80)
    last_name: str|None=Field(default=None,min_length=1,max_length=80)
    email: str|None=Field(default=None,min_length=3,max_length=254)
    phone: str|None=Field(default=None,max_length=32)
    city: str|None=Field(default=None,min_length=1,max_length=100)
    state: str|None=Field(default=None,min_length=1,max_length=100)
    postal_code: str|None=Field(default=None,min_length=1,max_length=20)
    country: str|None=Field(default=None,pattern=r'^[A-Z]{2}$')
    customer_status: Status|None=None
    @model_validator(mode='after')
    def no_empty_patch(self):
        if not self.model_fields_set: raise ValueError('provide at least one field to update')
        return self
    @field_validator('email')
    @classmethod
    def email_is_synthetic(cls,v): return valid_email(v) if v is not None else v
    @field_validator('phone')
    @classmethod
    def phone_is_synthetic(cls,v):
        if v is not None:
            v=v.strip()
            if not re.fullmatch(r'\+1-555-01\d{2}',v): raise ValueError('synthetic phone must use the reserved +1-555-01xx range')
        return v
    @field_validator('first_name','last_name','city','state','postal_code')
    @classmethod
    def trim_optional(cls,v):
        if v is None:return v
        v=v.strip()
        if not v:raise ValueError('must not be blank')
        return v
class CustomerOut(BaseModel):
    customer_id:str
    first_name:str
    last_name:str
    email:str
    phone:str|None
    city:str
    state:str
    postal_code:str
    country:str
    customer_status:str
    created_at:str
    updated_at:str
    source_version:int
    change_seq:int
class CustomerPage(BaseModel):
    items:list[CustomerOut]
    limit:int
    offset:int
class ChangePage(BaseModel):
    items:list[CustomerOut]
    next_after_seq:int
