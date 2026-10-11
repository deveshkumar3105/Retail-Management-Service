from decimal import Decimal

def payload(order_id='ord-1'):
    return {'order_id':order_id,'customer_id':'customer-1','order_timestamp':'2025-01-01T10:00:00Z','currency':'USD','items':[{'product_id':'product-1','quantity':2,'unit_price':'12.35','discount_amount':'1.00'}]}
def test_health(client):
    r=client.get('/health'); assert r.status_code==200 and r.json()['status']=='ok'
def test_ui_assets(client):
    r=client.get('/')
    assert r.status_code==200 and 'Order desk' in r.text
    assert client.get('/static/app.js').status_code==200
    assert client.get('/static/styles.css').status_code==200
def test_create_totals_and_duplicate(client):
    r=client.post('/orders',json=payload()); assert r.status_code==201
    assert r.json()['order_total']=='23.70' and r.json()['items'][0]['line_total']=='23.70'
    assert client.post('/orders',json=payload()).status_code==409
def test_invalid_payload(client):
    p=payload(); p['items'][0]['quantity']=0
    assert client.post('/orders',json=p).status_code==422
    p=payload('ord-2'); p['items'][0]['discount_amount']='99.00'
    assert client.post('/orders',json=p).status_code==422
def test_missing(client): assert client.get('/orders/nope').status_code==404
def test_pagination(client):
    client.post('/orders',json=payload('a')); client.post('/orders',json=payload('b'))
    assert len(client.get('/orders?limit=1&offset=0').json()['items'])==1
    assert len(client.get('/orders?limit=1&offset=1').json()['items'])==1
def test_transitions_and_incremental(client):
    client.post('/orders',json=payload())
    changed=client.patch('/orders/ord-1',json={'order_status':'CONFIRMED'}); assert changed.status_code==200
    assert changed.json()['source_version']==2
    assert client.patch('/orders/ord-1',json={'order_status':'DELIVERED'}).status_code==409
    since='2020-01-01T00:00:00Z'
    found=client.get('/orders/changes',params={'since':since}).json(); assert len(found)==1
    assert client.get('/orders/changes',params={'since':'invalid'}).status_code==400
def test_export_and_foreign_key(client):
    client.post('/orders',json=payload())
    r=client.get('/exports/orders'); assert r.status_code==200 and r.headers['content-type'].startswith('application/x-ndjson')
    assert '"order_id":"ord-1"' in r.text and '"source_version":1' in r.text
    from services.order_service.app.database import connect
    with connect() as db:
        try: db.execute("INSERT INTO order_items VALUES('x','missing','p',1,100,0,100)")
        except Exception: pass
        else: raise AssertionError('foreign key constraint was not enforced')
