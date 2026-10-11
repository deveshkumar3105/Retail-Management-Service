import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
import pytest
from fastapi.testclient import TestClient
from services.order_service.app import database
from services.order_service.app.main import app
@pytest.fixture
def client(tmp_path,monkeypatch):
    db=tmp_path/'test.db'; monkeypatch.setattr(database,'DATABASE_PATH',db)
    with TestClient(app) as c: yield c
