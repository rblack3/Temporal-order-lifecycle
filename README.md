# Temporal Order Workflow Assessment

This project implements a durable Order Lifecycle orchestration using the Temporal Python SDK, demonstrating core concepts like parent/child workflows, signals, timers, retries, and task-queue isolation.

## Core Concepts Demonstrated

-   **Parent/Child Workflows**: `OrderWorkflow` orchestrates the main process and invokes a `ShippingWorkflow` for isolated shipping tasks.
-   **Task Queues**: `ShippingWorkflow` runs on a dedicated `shipping-tq` to simulate service/team isolation.
-   **Signals & Timers**: A `workflow.wait_condition` acts as a timer for a simulated manual approval step, which is triggered by an `approve_order` signal.
-   **Retries & Timeouts**: Activities have tight timeouts (5s) and retry policies to handle the simulated failures from the `flaky_call` function. The overall workflow timeout is configurable in `src/cli.py` (originally 15 seconds, relaxed to 5 minutes for easier manual testing).
-   **Persistence & Idempotency**: State changes are written to a PostgreSQL database. The payment activity uses a unique `payment_id` and an `INSERT ... ON CONFLICT` statement to ensure payments are idempotent and safe to retry.
-   **Observability**: A CLI is provided to start, signal, and query the live state of any order workflow. The Temporal Web UI provides a complete event history for auditing and debugging.

## How to Run

### 1. Setup

**Prerequisites:**
- Docker & Docker Compose
- Python 3.8+

1.  **Clone the repository** and navigate into the project directory.

2.  **Ensure Docker Desktop is running.**

3.  **Create the environment file** for Docker Compose:
    ```bash
    cp .env.example .env
    ```

4.  **Start local services** (Temporal & PostgreSQL) in the background:
    ```bash
    docker-compose up -d
    ```

5.  **Install Python dependencies.** Using `python3 -m pip` ensures packages are installed for the correct Python interpreter.
    ```bash
    python3 -m pip install -r requirements.txt
    ```

### 2. Run and Test the Application

You will need two separate terminal windows open.

**Terminal 1: Start the Workers**
The workers are the background processes that execute your code. They will run indefinitely, waiting for tasks.

   ```bash
   python3 -m src.run_workers
   ```

**Terminal 2: Use the CLI to Interact with Workflows**
Use this terminal to start, query, and send signals to your workflows.

#### **A Full Manual Test Plan**

**1. The Happy Path:**

* **Start a workflow:**
    ```bash
    python3 -m src.cli start-workflow
    ```
    (This will print a new `order-id`. Copy it for the next steps.)

* **Query its status:** The workflow will likely be paused, waiting for your input.
    ```bash
    python3 -m src.cli query <your-order-id>
    ```
    (The `Status` should be `PENDING_MANUAL_APPROVAL`.)

* **Approve the order:**
    ```bash
    python3 -m src.cli signal <your-order-id> approve
    ```

* **Observe completion:** Query the status again every few seconds. You will see the status change until the `Workflow Status` is `COMPLETED`. Your worker terminal will show logs of the activities being processed.

**2. Test Cancellation:**

* Start a new workflow.
* Before the approval step, send a `cancel` signal instead:
    ```bash
    python3 -m src.cli signal <another-order-id> cancel
    ```
* Query the workflow to see that its final status is `CANCELLED`.

**3. Using the Temporal Web UI:**

* Open your browser to `http://localhost:8233`.
* Click on any of your workflow IDs.
* Explore the "Event History" to see a complete audit trail of every activity attempt, retry, timeout, and signal.

### Database & Persistence Rationale

-   **`orders` table**: Stores the high-level state of the order (`CREATED`, `VALIDATED`, `SHIPPED`, etc.).
-   **`payments` table**: Contains payment information. The `payment_id` is the `PRIMARY KEY`.
    -   **Idempotency**: The `charge_payment` activity first attempts an `INSERT ... ON CONFLICT DO NOTHING`. If the `payment_id` already exists, the database does nothing. This prevents double charges, even if the activity is retried multiple times due to timeouts or failures.
-   **`workflow_events` table**: An audit log that captures a detailed history of significant events throughout the workflow's execution. For debugging purposes.

### Automated Tests

The project includes a basic structure for automated integration tests using `pytest` and Temporal's testing framework.

**1. Setup for Testing:**
```bash
python3 -m pip install pytest pytest-asyncio
```

**2. Run the Tests:**
```bash
pytest
```
Pytest will automatically discover and run the test files in the tests/ directory. You can add more tests there to cover all scenarios.
