import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ChildWorkflowError
from src import activities
from src.shared import ORDER_TASK_QUEUE, SHIPPING_TASK_QUEUE

@workflow.defn(name="ShippingWorkflow")
class ShippingWorkflow:
    @workflow.run
    async def run(self, order: dict):
        try:
            await workflow.execute_activity(activities.prepare_package, order, start_to_close_timeout=timedelta(seconds=5), retry_policy=RetryPolicy(maximum_attempts=3))
            await workflow.execute_activity(activities.dispatch_carrier, order, start_to_close_timeout=timedelta(seconds=5), retry_policy=RetryPolicy(maximum_attempts=3))
        except ActivityError as e:
            await workflow.get_parent_workflow().signal("dispatch_failed", str(e)) 
            raise

@workflow.defn(name="OrderWorkflow")
class OrderWorkflow:
    def __init__(self):
        self._status: str = "CREATED" 
        self._is_cancelled: bool = False 
        self._is_approved: bool = False
        self._dispatch_failed: bool = False 
        self._dispatch_failure_reason: str = ""

    @workflow.run
    async def run(self, order_id: str, payment_id: str):
        start_opts = {
            "start_to_close_timeout": timedelta(seconds=5),
            "retry_policy": RetryPolicy(
                maximum_attempts=3,
                non_retryable_error_types=["ValueError"],
            ),
        }        
        try:
            self._status = "RECEIVING_ORDER"
            
            order_details = await workflow.execute_activity(activities.receive_order, args=[order_id, "123 Temporal Lane"], **start_opts)
            
            if self._is_cancelled: 
                return await self._handle_cancellation("Cancelled before validation")
            
            self._status = "VALIDATING_ORDER"
            
            await workflow.execute_activity(activities.validate_order, args=[order_details], **start_opts)
            
            self._status = "PENDING_MANUAL_APPROVAL"
            
            try: 
                await workflow.wait_condition(lambda: self._is_approved, timeout=timedelta(seconds=10))
            except asyncio.TimeoutError: 
                return await self._handle_cancellation("Approval timed out")
            
            if self._is_cancelled: 
                return await self._handle_cancellation("Cancelled after approval")
            
            self._status = "CHARGING_PAYMENT"
            
            await workflow.execute_activity(activities.charge_payment, args=[order_details, payment_id], **start_opts)
            
            if self._is_cancelled: 
                return await self._handle_cancellation("Cancelled after payment")
            
            self._status = "SHIPPING_STARTED"
            
            try: 
                await workflow.execute_child_workflow(ShippingWorkflow, args=[order_details], id=f"shipping-{order_id}", task_queue=SHIPPING_TASK_QUEUE)
            except ChildWorkflowError:
                return await self._handle_cancellation(f"Shipping Failed: {self._dispatch_failure_reason}" if self._dispatch_failed else "Shipping failed unexpectedly.")
            
            self._status = "COMPLETED" 
            
            return f"Order {order_id} completed."
        
        except ActivityError as e: 
            return await self._handle_cancellation(f"Activity Failed: {str(e)}")

    async def _handle_cancellation(self, reason: str):
        self._status = f"CANCELLING: {reason}"
        
        await workflow.execute_activity(activities.process_cancellation, args=[workflow.info().workflow_id, reason], start_to_close_timeout=timedelta(seconds=10))
        
        self._status = "CANCELLED"
        
        return f"Order cancelled: {reason}"
    
    @workflow.query
    def status(self): 
        return {"status": self._status, "cancelled": self._is_cancelled, "approved": self._is_approved}
    
    @workflow.signal
    def cancel_order(self): 
        self._is_cancelled = True
    
    @workflow.signal
    def approve_order(self):
        if self._status == "PENDING_MANUAL_APPROVAL": 
            self._is_approved = True
    
    @workflow.signal
    def dispatch_failed(self, reason: str):
        self._dispatch_failed = True 
        self._dispatch_failure_reason = reason
