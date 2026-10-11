from fastapi import APIRouter, Query
from ..schemas import OrderCreate, OrderOut, OrderPage, OrderPatch
from ..services import orders
router=APIRouter()
@router.post('/orders',response_model=OrderOut,status_code=201)
def create_order(payload:OrderCreate): return orders.create(payload)
@router.get('/orders',response_model=OrderPage)
def list_orders(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0)):
    return {'items':orders.list_orders(limit,offset),'limit':limit,'offset':offset}
@router.get('/orders/changes',response_model=list[OrderOut])
def changes(since:str,limit:int=Query(500,ge=1,le=5000),offset:int=Query(0,ge=0)):
    return orders.changes(since,limit,offset)
@router.get('/orders/{order_id}',response_model=OrderOut)
def get_order(order_id:str): return orders.get(order_id)
@router.patch('/orders/{order_id}',response_model=OrderOut)
def patch_order(order_id:str,payload:OrderPatch): return orders.patch(order_id,payload)
