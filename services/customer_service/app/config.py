import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
DATABASE_PATH = Path(os.getenv('CUSTOMER_DATABASE_PATH', str(ROOT / 'data' / 'customers.db')))
LOG_LEVEL = os.getenv('CUSTOMER_LOG_LEVEL', 'INFO').upper()
