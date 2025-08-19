import os
import asyncpg
from typing import Optional

class DatabaseRepository:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self):
        if not self._pool: 
            self._pool = await asyncpg.create_pool(dsn=self._dsn)

    async def disconnect(self):
        if self._pool: 
            await self._pool.close()

    async def create_order(self, order_id: str, address: str):
        async with self._pool.acquire() as c: 
            await c.execute("INSERT INTO orders (id, state, shipping_address_json) VALUES ($1, 'CREATED', $2)", order_id, address)
    
    async def update_order_state(self, order_id: str, state: str):
        async with self._pool.acquire() as c: 
            await c.execute("UPDATE orders SET state = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2", state, order_id)
    
    async def upsert_payment(self, payment_id: str, order_id: str, amount: float) -> str:
        async with self._pool.acquire() as c:
            r = await c.execute("INSERT INTO payments (payment_id, order_id, status, amount) VALUES ($1, $2, 'PENDING', $3) ON CONFLICT (payment_id) DO NOTHING RETURNING payment_id", payment_id, order_id, amount)
            return "INSERTED" if r else "EXISTED"
    
    async def update_payment_status(self, payment_id: str, status: str):
        async with self._pool.acquire() as c: 
            await c.execute("UPDATE payments SET status = $1, updated_at = CURRENT_TIMESTAMP WHERE payment_id = $2", status, payment_id)

db_dsn = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}"
db_repo = DatabaseRepository(dsn=db_dsn)
