import asyncio, structlog, logging
import structlog.stdlib
import structlog.contextvars
from dotenv import load_dotenv

load_dotenv()

from temporalio.client import Client
from temporalio.worker import Worker
from src import activities
from src.database import db_repo
from src.shared import ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE
from src.workflows import OrderWorkflow, ShippingWorkflow


async def main():
    await db_repo.connect()
    client = await Client.connect("localhost:7233")
    order_worker = Worker(
        client, 
        task_queue=ORDER_TASK_QUEUE, 
        workflows=[OrderWorkflow], 
        activities=[activities.receive_order, activities.validate_order, activities.charge_payment, activities.process_cancellation]
    )
    shipping_worker = Worker(
        client, 
        task_queue=SHIPPING_TASK_QUEUE, 
        workflows=[ShippingWorkflow], 
        activities=[activities.prepare_package, activities.dispatch_carrier]
    )
    
    print("Starting workers...")
    await asyncio.gather(order_worker.run(), shipping_worker.run())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level, 
            structlog.processors.TimeStamper(fmt="iso"), 
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ], 
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    try: 
        asyncio.run(main())
    except KeyboardInterrupt: 
        print("\nWorkers shut down.")
