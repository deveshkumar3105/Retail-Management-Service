#!/usr/bin/env python3
"""Generate deterministic fictional customer profiles in the isolated customer database."""
import argparse, random, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from services.customer_service.app.database import init_db, transaction
from services.customer_service.app.services.customers import record_change
FIRST=['Avery','Jordan','Morgan','Riley','Taylor','Casey','Quinn','Skyler','Reese','Parker','Rowan','Emerson']
LAST=['Miller','Rivera','Bennett','Hayes','Brooks','Foster','Perry','Reed','Bailey','Morgan','Cruz','Sullivan']
PLACES=[('Portland','Oregon'),('Austin','Texas'),('Madison','Wisconsin'),('Raleigh','North Carolina'),('Denver','Colorado'),('Salem','Oregon'),('Albany','New York'),('Tucson','Arizona')]
def generate(number:int,seed:int):
    rng=random.Random(seed+number*7919)
    first=FIRST[rng.randrange(len(FIRST))]; last=LAST[rng.randrange(len(LAST))]
    city,state=PLACES[rng.randrange(len(PLACES))]
    return {'first_name':first,'last_name':last,'email':f'customer-{number:05d}@example.invalid',
      'phone':f'+1-555-01{number%100:02d}','city':city,'state':state,'postal_code':f'{rng.randrange(10000,99999):05d}',
      'country':'US','customer_status':'INACTIVE' if rng.random()<0.06 else 'ACTIVE'}
def run(count:int,seed:int,start:int=1,database:Path|None=None):
    if count<0:raise ValueError('count must be >= 0')
    if start<1:raise ValueError('start must be >= 1')
    db=database or ROOT/'data'/'customers.db'; init_db(db); inserted=0
    with transaction(db) as conn:
        for number in range(start,start+count):
            customer_id=f'customer-{number:05d}'
            if conn.execute('SELECT 1 FROM customers WHERE customer_id=?',(customer_id,)).fetchone():continue
            fields=generate(number,seed)
            # Stable synthetic timestamps make a repeated fixture byte-for-byte reproducible.
            created=(datetime(2024,1,1,tzinfo=timezone.utc)+timedelta(days=(number*17+seed)%700,minutes=(number*29)%1440)).isoformat(timespec='microseconds').replace('+00:00','Z')
            conn.execute('INSERT INTO customers VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(customer_id,fields['first_name'],fields['last_name'],fields['email'],fields['phone'],fields['city'],fields['state'],fields['postal_code'],fields['country'],fields['customer_status'],created,created,1,1))
            record_change(conn,customer_id,'INSERT'); inserted+=1
    print(f'Inserted {inserted} synthetic customers (requested {count}) into {db}. Existing IDs were skipped.')
    return inserted
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count',type=int,default=500); parser.add_argument('--seed',type=int,default=42); parser.add_argument('--start',type=int,default=1,help='First customer number; use a later range to add more customers.')
    args=parser.parse_args()
    if args.count<0 or args.start<1:parser.error('--count must be >= 0 and --start must be >= 1')
    run(args.count,args.seed,args.start)
