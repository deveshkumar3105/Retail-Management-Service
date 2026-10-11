from pathlib import Path
from services.customer_service.app import database as customer_db
from services.order_service.app import database as order_db

def payload(customer_id='customer-00001',email='customer-00001@example.invalid'):
    return {'customer_id':customer_id,'first_name':'Avery','last_name':'Rivera','email':email,'phone':'+1-555-0101','city':'Portland','state':'Oregon','postal_code':'97201','country':'US'}
def test_health(client):
    r=client.get('/health');assert r.status_code==200 and r.json()['service']=='customer-service'
def test_ui_assets(client):
    assert client.get('/').status_code==200 and 'Customer directory' in client.get('/').text
    assert client.get('/static/app.js').status_code==200
    assert client.get('/static/styles.css').status_code==200
def test_create_and_get(client):
    r=client.post('/customers',json=payload());assert r.status_code==201
    assert r.json()['source_version']==1 and r.json()['change_seq']==1
    assert client.get('/customers/customer-00001').json()['email']=='customer-00001@example.invalid'
def test_invalid_and_duplicate_email(client):
    p=payload(email='person@gmail.com');assert client.post('/customers',json=p).status_code==422
    client.post('/customers',json=payload())
    assert client.post('/customers',json=payload('customer-00002','CUSTOMER-00001@example.invalid')).status_code==409
    p=payload('customer-00003');p['country']='USA';assert client.post('/customers',json=p).status_code==422
    p=payload('customer-00004');p['phone']='555-1234';assert client.post('/customers',json=p).status_code==422
    p=payload('customer-00005');p['customer_status']='PENDING';assert client.post('/customers',json=p).status_code==422
def test_missing_and_pagination(client):
    assert client.get('/customers/nope').status_code==404
    for n in range(1,4):client.post('/customers',json=payload(f'c-{n}',f'c{n}@example.invalid'))
    page=client.get('/customers?limit=2&offset=1').json()
    assert len(page['items'])==2 and page['offset']==1 and page['items'][0]['customer_id']=='c-2'
def test_patch_version_deactivation_and_unique_email(client):
    client.post('/customers',json=payload())
    updated=client.patch('/customers/customer-00001',json={'city':'Austin','customer_status':'INACTIVE'})
    assert updated.status_code==200 and updated.json()['source_version']==2 and updated.json()['customer_status']=='INACTIVE'
    assert client.patch('/customers/customer-00001',json={'city':'Austin'}).json()['source_version']==2
    assert client.patch('/customers/customer-00001',json={'email':'bad@gmail.com'}).status_code==422
    assert client.patch('/customers/customer-00001',json={}).status_code==422
    assert client.patch('/customers/customer-00001',json={'first_name':None}).status_code==422
def test_incremental_sequence_and_timestamp(client):
    created=client.post('/customers',json=payload()).json()
    changed=client.patch('/customers/customer-00001',json={'city':'Salem'}).json()
    page=client.get('/customers/changes?after_seq=1').json()
    assert page['items'][0]['source_version']==2 and page['next_after_seq']==2
    own=client.get('/customers/changes?after_seq=0&customer_id=customer-00001').json()['items']
    assert [item['source_version'] for item in own]==[1,2]
    assert client.get('/customers/changes?after_seq=2').json()['items']==[]
    assert len(client.get('/customers/changes?since=2020-01-01T00:00:00Z').json()['items'])==2
    boundary=client.get('/customers/changes',params={'since':created['created_at']}).json()['items']
    assert len(boundary)==1 and boundary[0]['source_version']==2
    assert client.get('/customers/changes',params={'since':changed['updated_at']}).json()['items']==[]
    assert client.get('/customers/changes').status_code==400
    assert client.get('/customers/changes?since=not-a-date').status_code==400
def test_export_jsonl(client):
    client.post('/customers',json=payload())
    text=client.get('/exports/customers').text
    assert text.endswith('\n') and '"customer_id":"customer-00001"' in text
    incremental=client.get('/exports/customers?after_seq=1').text
    assert incremental==''
    assert client.get('/exports/customers?since=2020-01-01T00:00:00Z').text.count('\n')==1
def test_seed_repeatable_incremental_and_isolated(tmp_path):
    from services.customer_service.scripts.seed_customers import run
    first=tmp_path/'first.db'; second=tmp_path/'second.db'
    assert run(3,42,database=first)==3; assert run(3,42,database=first)==0
    assert run(3,42,database=second)==3
    with customer_db.connect(first) as a, customer_db.connect(second) as b:
        rows_a=[tuple(r) for r in a.execute('select customer_id,email,created_at from customers order by customer_id')]
        rows_b=[tuple(r) for r in b.execute('select customer_id,email,created_at from customers order by customer_id')]
        assert rows_a==rows_b
    assert run(2,42,start=4,database=first)==2
    order_path=tmp_path/'orders.db'; order_db.init_db(order_path)
    with order_db.connect(order_path) as conn:assert conn.execute('select count(*) from orders').fetchone()[0]==0
    assert first != order_path
