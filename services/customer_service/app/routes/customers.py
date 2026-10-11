from fastapi import APIRouter, Query
from ..schemas import CustomerCreate, CustomerOut, CustomerPage, CustomerPatch, ChangePage
from ..services import customers
router=APIRouter()
@router.post('/customers',response_model=CustomerOut,status_code=201)
def create_customer(payload:CustomerCreate):return customers.create(payload)
@router.get('/customers',response_model=CustomerPage)
def list_customers(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0)):
    return {'items':customers.list_customers(limit,offset),'limit':limit,'offset':offset}
@router.get('/customers/changes',response_model=ChangePage)
def get_changes(since:str|None=None,after_seq:int|None=Query(None,ge=0),limit:int=Query(500,ge=1,le=5000),offset:int=Query(0,ge=0),customer_id:str|None=None):
    return customers.changes(since,after_seq,limit,offset,customer_id=customer_id)
@router.get('/customers/{customer_id}',response_model=CustomerOut)
def get_customer(customer_id:str):return customers.get(customer_id)
@router.patch('/customers/{customer_id}',response_model=CustomerOut)
def patch_customer(customer_id:str,payload:CustomerPatch):return customers.patch(customer_id,payload)
