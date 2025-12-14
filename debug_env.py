from app.config import settings
from sqlalchemy import create_engine, text

print(f"DB URL: {settings.DATABASE_URL.replace(settings.DATABASE_URL.split(':')[2].split('@')[0], '***')}")
print(f"Redis URL: {settings.REDIS_URL.replace(settings.REDIS_URL.split(':')[2].split('@')[0], '***')}")

try:
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("DB Connection: SUCCESS")
except Exception as e:
    print(f"DB Connection FAILED: {e}")

import redis
try:
    r = redis.from_url(settings.REDIS_URL, ssl_cert_reqs=None)
    r.ping()
    print("Redis Connection: SUCCESS")
except Exception as e:
    print(f"Redis Connection FAILED: {e}")
