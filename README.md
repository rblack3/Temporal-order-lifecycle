# Temporal Order Workflow Assessment

This project implements a durable Order Lifecycle orchestration using the Temporal Python SDK, demonstrating core concepts like parent/child workflows, signals, timers, retries, and task-queue isolation.

## Core Concepts Demonstrated

-   **Parent/Child Workflows**: `OrderWorkflow` orchestrates the main process and invokes a `ShippingWorkflow`.
-   **Task Queues**: `ShippingWorkflow` runs on a dedicated `shipping-tq` to simulate service isolation.
-   **Signals & Timers**: A `workflow.wait_for` acts as a timer for a manual approval step, which is triggered by an `approve_order` signal.
-   **Retries & Timeouts**: Activities have tight timeouts (5s) and retry policies to handle simulated failures. The entire workflow is constrained to a 15-second execution timeout.
-   **Persistence & Idempotency**: State changes are written to a PostgreSQL database. The payment activity uses an idempotency key and `INSERT ... ON CONFLICT` to prevent double charges.
-   **Observability**: A CLI is provided to start, signal, and query the live state of any order workflow.

## How to Run

### 1. Setup

- Clone the repository.
- Create a `.env` file from `.env.example`: `cp .env.example .env`
- Start local services: `docker-compose up -d`
- Install dependencies: `pip install -r requirements.txt`

### 2. Run the Application

1.  **Start the Workers** (in one terminal):
    ```bash
    python src/run_workers.py
    ```

2.  **Use the CLI** (in another terminal):
    -   **Start a workflow:** `python src/cli.py start-workflow` (copy the order-id)
    -   **Query status:** `python src/cli.py query --order-id <your-order-id>`
    -   **Approve the order:** `python src/cli.py signal --order-id <your-order-id> approve`
    -   **Query again to see completion.**

