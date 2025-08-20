import asyncio, random, logging #, structlog
from typing import Dict, Any
from temporalio import activity
from src.database import db_repo
#log = structlog.get_logger(__name__)
log = logging.getLogger(__name__)
async def flaky_call():
    r = random.random()
    
    if r < 0.33: 
        raise RuntimeError("Forced failure for testing")
    if r < 0.67: 
        await asyncio.sleep(300)

async def sim_order_received(order_id: str, address: str):
    await flaky_call()
    await db_repo.create_order(order_id, address)
    log.info(f"DB: Wrote initial order record order_id={order_id}")
    return {"order_id": order_id, "items": [{"sku": "ABC", "qty": 1}], "address": address}

async def sim_order_validated(order: Dict[str, Any]):
    await flaky_call()
    await db_repo.update_order_state(order["order_id"], "VALIDATED")

    if not order.get("items"): 
        raise ValueError("No items to validate")
    log.info(f"DB: Order Validated order_id={order['order_id']}")
    return True

async def sim_payment_charged(order: Dict[str, Any], payment_id: str):
    amount = float(sum(i.get("qty", 1) for i in order.get("items", [])))
    
    if await db_repo.upsert_payment(payment_id, order["order_id"], amount) == "EXISTED": 
        return
        
    await flaky_call()
    await db_repo.update_payment_status(payment_id, "CHARGED")
    await db_repo.update_order_state(order["order_id"], "PAID")
    log.info(f"DB: Successfully charged order order_id={order['order_id']}")
    return {"status": "charged", "amount": amount}

async def sim_order_shipped(order: Dict[str, Any]):
    await flaky_call()
    await db_repo.update_order_state(order["order_id"], "SHIPPED")
    log.info(f"DB: Updated order to SHIPPED order_id={order['order_id']}")
    return "Shipped"

async def sim_package_prepared(order: Dict[str, Any]):
    await flaky_call()
    await db_repo.update_order_state(order["order_id"], "PACKAGE_PREPARED")
    log.info(f"DB: Updated order to PACKAGE_PREPARED order_id={order['order_id']}")
    return "Package Ready"

async def sim_carrier_dispatched(order: Dict[str, Any]):
    await flaky_call()
    await db_repo.update_order_state(order["order_id"], "DISPATCHED")
    log.info(f"DB: Updated order to DISPATCHED order_id={order['order_id']}")
    return "Out for Delivery"

@activity.defn
async def receive_order(order_id: str, address: str): 
    return await sim_order_received(order_id, address)

@activity.defn
async def validate_order(order: Dict[str, Any]): 
    return await sim_order_validated(order)

@activity.defn
async def charge_payment(order: Dict[str, Any], payment_id: str): 
    return await sim_payment_charged(order, payment_id)

@activity.defn
async def ship_order(order: Dict[str, Any]):
    return await sim_order_shipped(order)

@activity.defn
async def prepare_package(order: Dict[str, Any]): 
    return await sim_package_prepared(order)

@activity.defn
async def dispatch_carrier(order: Dict[str, Any]): 
    return await sim_carrier_dispatched(order)

@activity.defn
async def process_cancellation(order_id: str, reason: str):
    await db_repo.update_order_state(order_id, f"CANCELLED: {reason}")
