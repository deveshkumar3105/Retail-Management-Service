import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .config import LOG_LEVEL
from .database import init_db
from .routes.customers import router
from .services.customers import export_jsonl
logging.basicConfig(level=getattr(logging,LOG_LEVEL,logging.INFO),format='%(asctime)s %(levelname)s %(name)s %(message)s')
@asynccontextmanager
async def lifespan(app:FastAPI):
    init_db()
    yield
app=FastAPI(title='Retail Lakehouse Platform — Customer Service',version='1.0.0',lifespan=lifespan)
app.mount('/static',StaticFiles(directory=Path(__file__).parent/'static'),name='static')
app.include_router(router)
@app.get('/',include_in_schema=False)
def index():return FileResponse(Path(__file__).parent/'static'/'index.html')
@app.get('/health')
def health():return {'status':'ok','service':'customer-service'}
@app.get('/exports/customers')
def export_customers(since:str|None=None,after_seq:int|None=None):
    body=export_jsonl(since,after_seq)
    return Response(body,media_type='application/x-ndjson',headers={'Content-Disposition':'attachment; filename="customers.jsonl"'})
