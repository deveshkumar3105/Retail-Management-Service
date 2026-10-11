import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .config import LOG_LEVEL
from .database import init_db
from .routes.orders import router
from .services.orders import export_jsonl
logging.basicConfig(level=getattr(logging,LOG_LEVEL,logging.INFO),format='%(asctime)s %(levelname)s %(name)s %(message)s')
@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db()
    yield
app=FastAPI(title='Retail Order Service',version='1.0.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
app.include_router(router)
@app.get('/',include_in_schema=False)
def index(): return FileResponse(Path(__file__).parent/'static'/'index.html')
@app.get('/health')
def health(): return {'status':'ok','service':'order-service'}
@app.get('/exports/orders')
def export_orders(since:str|None=None):
    body=export_jsonl(since)
    return Response(body,media_type='application/x-ndjson',headers={'Content-Disposition':'attachment; filename="orders.jsonl"'})
