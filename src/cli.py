import asyncio, uuid
from datetime import timedelta
import typer
from temporalio.client import Client, WorkflowExecutionStatus
from rich.console import Console
from rich.table import Table
from src.shared import ORDER_TASK_QUEUE
from src.workflows import OrderWorkflow

app = typer.Typer()
console = Console()

async def _get_client(): 
    return await Client.connect("localhost:7233")

@app.command()
def start_workflow(order_id: str = typer.Option(lambda: f"order-{uuid.uuid4().hex[:6]}")):
    async def _start():
        client = await _get_client()
        payment_id = f"payment-{uuid.uuid4().hex[:8]}"
        console.print(f"🚀 Starting workflow [bold cyan]{order_id}[/] with Payment ID [bold magenta]{payment_id}[/]")
        
        await client.start_workflow(
            OrderWorkflow.run, 
            args=[order_id, payment_id], 
            id=order_id, 
            task_queue=ORDER_TASK_QUEUE, 
            execution_timeout=timedelta(seconds=300)#15)
        )
    asyncio.run(_start())

@app.command()
def signal(order_id: str, signal_name: str = typer.Argument(..., help="approve, cancel")):
    async def _signal():
        handle = (await _get_client()).get_workflow_handle(order_id)

        if signal_name == "approve": 
            await handle.signal(OrderWorkflow.approve_order)
        elif signal_name == "cancel": 
            await handle.signal(OrderWorkflow.cancel_order)
        else: 
            console.print(f"[red]Error: Unknown signal '{signal_name}'.[/]"); 
            return

        console.print(f"✅ Signal '{signal_name}' sent to {order_id}.")
    asyncio.run(_signal())

@app.command()
def query(order_id: str):
    async def _query():
        handle = (await _get_client()).get_workflow_handle(order_id)

        try:
            status = await handle.query(OrderWorkflow.status); 
            desc = await handle.describe()

            table = Table(title=f"Status for Order [bold cyan]{order_id}[/]"); 
            table.add_column("Property", style="magenta"); 
            table.add_column("Value", style="green")
            table.add_row("Workflow Status", str(desc.status))

            for k, v in status.items(): 
                table.add_row(k.replace("_", " ").title(), str(v))
            console.print(table)

            if desc.status != WorkflowExecutionStatus.RUNNING: 
                console.print(f"\n[bold]Final Result:[/bold] {await handle.result()}")
        
        except Exception as e: 
            console.print(f"[red]Error querying '{order_id}':[/] {e}")
    asyncio.run(_query())

if __name__ == "__main__": 
    app()
