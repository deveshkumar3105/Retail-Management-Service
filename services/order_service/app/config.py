import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = Path(os.getenv("ORDER_DATABASE_PATH", str(ROOT / "data" / "orders.db")))
LOG_LEVEL = os.getenv("ORDER_LOG_LEVEL", "INFO").upper()
