#!/usr/bin/env python3
"""Create deterministic synthetic order rows. Re-running the same seed is a no-op."""
import argparse, random, sys, uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from services.order_service.app.database import transaction, init_db
from services.order_service.app.schemas import cents
STATUSES=['CREATED','CONFIRMED','SHIPPED','DELIVERED','CANCELLED']

def run(count:int, seed:int):
    db=ROOT/'data'/'orders.db'; init_db(db)
    rng=random.Random(seed)
    namespace=uuid.uuid5(uuid.NAMESPACE_URL,f'retail-order-seed:{seed}')
    with transaction(db) as conn:
        prefix=f'seed-{seed}-'
        existing=conn.execute('SELECT count(*) FROM orders WHERE order_id LIKE ?',(prefix+'%',)).fetchone()[0]
        if existing:
            # Existing fixture identifiers make this seed safe to rerun; never partially extend it.
            if existing == count:
                print(f'Seed {seed} already present ({existing} orders); no changes made.')
                return
            raise SystemExit(f'Seed {seed} already has {existing} orders; refusing to duplicate or partially alter it.')
        base=datetime(2024,1,1,tzinfo=timezone.utc)
        for n in range(count):
            oid=f'{prefix}{n:06d}'
            created=base+timedelta(days=rng.randint(0,640),seconds=rng.randint(0,86399))
            status=rng.choices(STATUSES,weights=[8,22,14,50,6])[0]
            stamp=created.isoformat(timespec='microseconds').replace('+00:00','Z')
            cid=f'customer-{rng.randint(1,2000):05d}'
            items=[]; total=0
            for j in range(rng.randint(1,5)):
                qty=rng.randint(1,4); price=cents(Decimal(rng.randint(500,25000))/100)
                discount= rng.choice([0,0,0,int(price*qty*.10)])
                line=price*qty-discount; total+=line
                iid=str(uuid.uuid5(namespace,f'{n}:{j}'))
                items.append((iid,oid,f'product-{rng.randint(1,500):04d}',qty,price,discount,line))
            conn.execute('INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?)',(oid,cid,status,stamp,'USD',total,stamp,stamp,1))
            conn.executemany('INSERT INTO order_items VALUES(?,?,?,?,?,?,?)',items)
    print(f'Created {count} synthetic orders in {db} with seed {seed}.')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--count',type=int,default=500); p.add_argument('--seed',type=int,default=42)
    a=p.parse_args()
    if a.count < 0: p.error('--count must be >= 0')
    run(a.count,a.seed)
