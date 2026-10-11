import json, logging, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException
from ..database import connect, transaction
from ..schemas import CustomerCreate, CustomerPatch, now_iso
log=logging.getLogger(__name__)
FIELDS=('customer_id','first_name','last_name','email','phone','city','state','postal_code','country','customer_status','created_at','updated_at','source_version','change_seq')
def serialize(row): return {key:row[key] for key in FIELDS}
def record_change(conn, customer_id:str, operation:str):
    row=conn.execute('SELECT * FROM customers WHERE customer_id=?',(customer_id,)).fetchone()
    cursor=conn.execute('INSERT INTO customer_changes(customer_id,operation,changed_at,source_version,snapshot_json) VALUES(?,?,?,?,?)',(customer_id,operation,row['updated_at'],row['source_version'],'{}'))
    seq=cursor.lastrowid
    conn.execute('UPDATE customers SET change_seq=? WHERE customer_id=?',(seq,customer_id))
    result=serialize(conn.execute('SELECT * FROM customers WHERE customer_id=?',(customer_id,)).fetchone())
    conn.execute('UPDATE customer_changes SET snapshot_json=? WHERE change_seq=?',(json.dumps(result,separators=(',',':')),seq))
    return result

def create(payload:CustomerCreate,db:Path|None=None):
    customer_id=payload.customer_id or str(uuid.uuid4()); now=now_iso()
    try:
        with transaction(db) as conn:
            conn.execute('INSERT INTO customers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(customer_id,payload.first_name,payload.last_name,payload.email,payload.phone,payload.city,payload.state,payload.postal_code,payload.country,payload.customer_status,now,now,1,1))
            result=record_change(conn,customer_id,'INSERT')
        log.info('created customer_id=%s source_version=1',customer_id)
        return result
    except sqlite3.IntegrityError as e:
        if 'customers.email' in str(e): raise HTTPException(409,'email already exists') from e
        if 'customers.customer_id' in str(e): raise HTTPException(409,'customer_id already exists') from e
        raise HTTPException(422,'customer violates a database constraint') from e

def get(customer_id:str,db:Path|None=None):
    with connect(db) as conn:
        row=conn.execute('SELECT * FROM customers WHERE customer_id=?',(customer_id,)).fetchone()
        if row is None:raise HTTPException(404,'customer not found')
        return serialize(row)
def list_customers(limit:int,offset:int,db:Path|None=None):
    with connect(db) as conn:
        rows=conn.execute('SELECT * FROM customers ORDER BY customer_id LIMIT ? OFFSET ?',(limit,offset)).fetchall()
        return [serialize(r) for r in rows]
def patch(customer_id:str,payload:CustomerPatch,db:Path|None=None):
    updates=payload.model_dump(exclude_unset=True)
    if not updates:raise HTTPException(422,'provide at least one field to update')
    if any(v is None for k,v in updates.items() if k!='phone'):
        raise HTTPException(422,'only phone may be cleared with null')
    try:
        with transaction(db) as conn:
            row=conn.execute('SELECT * FROM customers WHERE customer_id=?',(customer_id,)).fetchone()
            if row is None:raise HTTPException(404,'customer not found')
            changed={k:v for k,v in updates.items() if row[k]!=v}
            if not changed:return serialize(row)
            changed['updated_at']=now_iso(); changed['source_version']=row['source_version']+1
            sql=', '.join(f'{name}=?' for name in changed)
            conn.execute(f'UPDATE customers SET {sql} WHERE customer_id=?',(*changed.values(),customer_id))
            result=record_change(conn,customer_id,'UPDATE')
        log.info('updated customer_id=%s source_version=%s',customer_id,result['source_version'])
        return result
    except sqlite3.IntegrityError as e:
        if 'customers.email' in str(e):raise HTTPException(409,'email already exists') from e
        raise HTTPException(422,'customer violates a database constraint') from e

def _since_iso(since):
    try:
        stamp=datetime.fromisoformat(since.replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
        return stamp.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00','Z')
    except ValueError as e:raise HTTPException(400,'since must be an ISO-8601 timestamp with timezone') from e

def changes(since:str|None,after_seq:int|None,limit:int,offset:int,db:Path|None=None,customer_id:str|None=None):
    if (since is None)==(after_seq is None):raise HTTPException(400,'provide exactly one of since or after_seq')
    if after_seq is not None and after_seq<0:raise HTTPException(400,'after_seq must be >= 0')
    with connect(db) as conn:
        if since:
            where='changed_at > ?'; args=[_since_iso(since)]
        else:
            where='change_seq > ?'; args=[after_seq]
        if customer_id is not None:
            where += ' AND customer_id = ?'; args.append(customer_id)
        args.extend([limit,offset])
        rows=conn.execute(f'SELECT change_seq,snapshot_json FROM customer_changes WHERE {where} ORDER BY change_seq LIMIT ? OFFSET ?',args).fetchall()
        items=[json.loads(r['snapshot_json']) for r in rows]
        next_seq=rows[-1]['change_seq'] if rows else (after_seq or 0)
        return {'items':items,'next_after_seq':next_seq}

def export_jsonl(since:str|None,after_seq:int|None,db:Path|None=None):
    if since is not None and after_seq is not None:raise HTTPException(400,'provide only one of since or after_seq')
    with connect(db) as conn:
        if since is not None:
            stamp=_since_iso(since)
            rows=conn.execute('SELECT snapshot_json FROM customer_changes WHERE changed_at > ? ORDER BY change_seq',(stamp,)).fetchall()
        elif after_seq is not None:
            if after_seq<0:raise HTTPException(400,'after_seq must be >= 0')
            rows=conn.execute('SELECT snapshot_json FROM customer_changes WHERE change_seq > ? ORDER BY change_seq',(after_seq,)).fetchall()
        else:
            rows=conn.execute('SELECT * FROM customers ORDER BY customer_id').fetchall()
            return ''.join(json.dumps(serialize(row),separators=(',',':'))+'\n' for row in rows)
        return ''.join(r['snapshot_json']+'\n' for r in rows)
