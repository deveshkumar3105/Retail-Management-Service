import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from ..database import transaction, connect
from ..schemas import OrderCreate, OrderPatch, cents, money, now_iso

log = logging.getLogger(__name__)
TRANSITIONS = {
 'CREATED': {'CONFIRMED','CANCELLED'}, 'CONFIRMED': {'SHIPPED','CANCELLED'},
 'SHIPPED': {'DELIVERED'}, 'DELIVERED': set(), 'CANCELLED': set(),
}
def serialize(row, conn):
    items = conn.execute('SELECT * FROM order_items WHERE order_id=? ORDER BY order_item_id', (row['order_id'],)).fetchall()
    return {
      'order_id':row['order_id'],'customer_id':row['customer_id'],'order_status':row['order_status'],
      'order_timestamp':row['order_timestamp'],'currency':row['currency'],'order_total':money(row['order_total_cents']),
      'created_at':row['created_at'],'updated_at':row['updated_at'],'source_version':row['source_version'],
      'items':[{'order_item_id':i['order_item_id'],'product_id':i['product_id'],'quantity':i['quantity'],
       'unit_price':money(i['unit_price_cents']),'discount_amount':money(i['discount_amount_cents']),
       'line_total':money(i['line_total_cents'])} for i in items]
    }
def create(payload: OrderCreate, db: Path | None = None):
    order_id = payload.order_id or str(uuid.uuid4())
    timestamp = payload.order_timestamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z') if payload.order_timestamp else now_iso()
    created = now_iso()
    total = sum(cents(it.unit_price)*it.quantity - cents(it.discount_amount) for it in payload.items)
    try:
        with transaction(db) as conn:
            conn.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?)',(order_id,payload.customer_id,payload.order_status,timestamp,payload.currency,total,created,created,1))
            for item in payload.items:
                price, discount = cents(item.unit_price), cents(item.discount_amount)
                conn.execute('INSERT INTO order_items VALUES(?,?,?,?,?,?,?)',(str(uuid.uuid4()),order_id,item.product_id,item.quantity,price,discount,price*item.quantity-discount))
            row=conn.execute('SELECT * FROM orders WHERE order_id=?',(order_id,)).fetchone()
            result=serialize(row,conn)
        log.info('created order_id=%s',order_id)
        return result
    except sqlite3.IntegrityError as e:
        if 'orders.order_id' in str(e): raise HTTPException(409,'order_id already exists') from e
        raise HTTPException(422,'order violates a database constraint') from e

def get(order_id: str, db: Path | None = None):
    with connect(db) as conn:
        row=conn.execute('SELECT * FROM orders WHERE order_id=?',(order_id,)).fetchone()
        if row is None: raise HTTPException(404,'order not found')
        return serialize(row,conn)

def list_orders(limit:int, offset:int, db:Path|None=None):
    with connect(db) as conn:
        rows=conn.execute('SELECT * FROM orders ORDER BY order_timestamp, order_id LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [serialize(r,conn) for r in rows]

def patch(order_id:str, payload:OrderPatch, db:Path|None=None):
    with transaction(db) as conn:
        row=conn.execute('SELECT * FROM orders WHERE order_id=?',(order_id,)).fetchone()
        if row is None: raise HTTPException(404,'order not found')
        target=payload.order_status
        if target == row['order_status']:
            return serialize(row,conn)
        if target not in TRANSITIONS[row['order_status']]:
            raise HTTPException(409,f"invalid order status transition: {row['order_status']} -> {target}")
        updated=now_iso()
        conn.execute('UPDATE orders SET order_status=?,updated_at=?,source_version=source_version+1 WHERE order_id=?',(target,updated,order_id))
        return serialize(conn.execute('SELECT * FROM orders WHERE order_id=?',(order_id,)).fetchone(),conn)

def changes(since:str, limit:int, offset:int, db:Path|None=None):
    try:
        stamp=datetime.fromisoformat(since.replace('Z','+00:00'))
        if stamp.tzinfo is None: raise ValueError()
        since=stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    except ValueError as e: raise HTTPException(400,"since must be an ISO-8601 timestamp with timezone") from e
    with connect(db) as conn:
        rows=conn.execute('SELECT * FROM orders WHERE updated_at > ? ORDER BY updated_at, order_id LIMIT ? OFFSET ?',(since,limit,offset)).fetchall()
        return [serialize(r,conn) for r in rows]

def export_jsonl(since:str|None, db:Path|None=None):
    if since:
        try:
            stamp=datetime.fromisoformat(since.replace('Z','+00:00'))
            if stamp.tzinfo is None: raise ValueError()
        except ValueError as e: raise HTTPException(400,"since must be an ISO-8601 timestamp with timezone") from e
    with connect(db) as conn:
        if since:
            rows=conn.execute('SELECT * FROM orders WHERE updated_at > ? ORDER BY updated_at, order_id',(since,)).fetchall()
        else:
            rows=conn.execute('SELECT * FROM orders ORDER BY order_timestamp, order_id').fetchall()
        # Keep the complete read transaction consistent across order and item rows.
        return '\n'.join(json.dumps(serialize(row,conn),default=str,separators=(',',':')) for row in rows) + ('\n' if rows else '')
