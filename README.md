# W4111 Web Application Project

This repository is the **starter template** for the course web application assignment. You will fork or clone it and implement a complete, production-style data-backed service on top of the skeleton provided here.

## Project goal

Design and implement a **REST API** backed by **MySQL** that exposes **customer**, **order**, and **order-detail** data from the **`classicmodels`** database (**Tasks 1–6**). The API must support **querying, creating, updating, and deleting** records while preserving a **clean separation** between HTTP handling, application/resource logic, and persistence. Your instructor may require additional domains or endpoints beyond this core scope.

The starter demonstrates one possible domain (**Harry Potter characters**) with **JSON file** storage. Your job is to implement **`MySQLDataService`**, **`CustomerResource`**, **`OrderResource`**, and **`OrderDetailsResource`** against the **`classicmodels`** MySQL database (see Tasks 1–4), wire the required HTTP routes in **`main.py`** (Task 5), provide a **Jupyter Notebook** that exercises your code (Task 6), then satisfy the remaining deliverables below.

## Assignment tasks

**Task 1 — `MySQLDataService`.** Extend `AbstractBaseDataService` and implement a concrete **`MySQLDataService`** that reads and writes data in **MySQL**. Use **`JSONFileDataService`** (`app/services/JSONFileDataService.py`) as your example: mirror how each abstract method maps to storage operations (`retrieveByPrimaryKey`, `retrieveByTemplate`, `create`, `updateByPrimaryKey`, `deleteByPrimaryKey`). Database connection settings (host, port, user, password, database name, etc.) must come from **environment variables** or another approved configuration mechanism—never hard-code credentials.

**Task 2 — `CustomerResource`.** Extend `AbstractBaseResource` and implement **`CustomerResource`** for customer records. Use **`HarryPotterResource`** (`app/resources/HarryPotterResource.py`) as your example for how a resource wires Pydantic models to a data service and implements `get`, `get_by_id`, `post`, `put`, and `delete`. **`CustomerResource` must use `MySQLDataService`** (Task 1) configured to access the **`classicmodels`** database—i.e., persistence for customers goes through MySQL and that schema, not the JSON file.

**Task 3 — `OrderResource`.** Extend `AbstractBaseResource` and implement **`OrderResource`** for order records, following the same pattern as Task 2. Use **`HarryPotterResource`** as your example. **`OrderResource` must use `MySQLDataService`** (Task 1) against **`classicmodels`**—persistence for orders goes through MySQL and that schema, not the JSON file.

**Task 4 — `OrderDetailsResource`.** Extend `AbstractBaseResource` and implement **`OrderDetailsResource`** for order-line / order-detail records, following the same pattern as Tasks 2–3. Use **`HarryPotterResource`** as your example. **`OrderDetailsResource` must use `MySQLDataService`** (Task 1) against **`classicmodels`**—persistence goes through MySQL and the **`orderdetails`** table (and its keys), not the JSON file.

**Task 5 — HTTP routes in `main.py`.** Register the routes below on the FastAPI app in **`app/main.py`**. Use the existing **Harry Potter** routes as examples: **`GET /harry-potter`** (optional query parameters as an equality template), **`POST /harry-potter`**, and **`GET`**, **`PUT`**, and **`DELETE`** on **`/harry-potter/{character_id}`** for path parameters and delegation to your resource layer. Path segments in `{curly braces}` are **path parameters** (`customerNumber`, `orderNumber`, etc.).

**Collection endpoints** — Implement **`GET`** and **`POST`** on each of these paths:

| Resource | Path | Methods |
|----------|------|---------|
| Customers | `/customers` | GET, POST |
| Orders | `/orders` | GET, POST |
| OrderDetails | `/orderdetails` | GET, POST |

**`GET`** on a collection should support listing / searching (e.g., optional query parameters matching your resource’s template semantics, following the Harry Potter **`GET /harry-potter`** pattern). **`POST`** should create a new row via the corresponding resource’s **`post`** method (following **`POST /harry-potter`**).

**Single-resource endpoints** — Implement **`GET`**, **`PUT`**, and **`DELETE`** on each path below. **`GET`** uses **`get_by_id`** (or equivalent); **`PUT`** replaces or updates the row via **`put`**; **`DELETE`** removes it via **`delete`**. Follow the Harry Potter **`PUT`** / **`DELETE`** patterns on **`/harry-potter/{character_id}`**. Return appropriate status codes (e.g., **`404`** when the row does not exist, **`400`** when the update is invalid).

| Resource | Path | Methods |
|----------|------|---------|
| Customers | `/customers/{customerNumber}` | GET, PUT, DELETE |
| Orders | `/orders/{orderNumber}` | GET, PUT, DELETE |
| OrderDetails | `/orders/{orderNumber}/orderdetails` | GET, PUT, DELETE |

Each handler should call the appropriate **`CustomerResource`**, **`OrderResource`**, or **`OrderDetailsResource`** method(s) from Tasks 2–4 and return suitable response models and HTTP status codes. If **`orderdetails`** rows are identified by a **composite primary key** in **`classicmodels`**, your **`PUT`** / **`DELETE`** (and **`GET`**) routes must identify a single row unambiguously—e.g., extra path segments such as **`/orders/{orderNumber}/orderdetails/{productCode}`**—per instructor guidance.

**Task 6 — Jupyter Notebook.** Submit a **Jupyter Notebook** whose **cells** test and demonstrate your work: invoke your **resource** and/or **data service** methods directly and/or call your **HTTP API** (e.g., with **`httpx`** or **`requests`** while the FastAPI app is running). Cells should be **runnable in order** and clearly show inputs and outputs for the behaviors you implemented.

## What you must deliver

1. **Task 1 (`MySQLDataService`)** — Completed as described above; your implementation must satisfy the `AbstractBaseDataService` contract.
2. **Task 2 (`CustomerResource`)** — Completed as described above; customers are served from **`classicmodels`** via **`MySQLDataService`**.
3. **Task 3 (`OrderResource`)** — Completed as described above; orders are served from **`classicmodels`** via **`MySQLDataService`**.
4. **Task 4 (`OrderDetailsResource`)** — Completed as described above; order details are served from **`classicmodels`** (e.g., **`orderdetails`** via **`MySQLDataService`**).
5. **Task 5 (routes in `main.py`)** — **`GET`** and **`POST`** on **`/customers`**, **`/orders`**, and **`/orderdetails`** (collection endpoints), plus **`GET`**, **`PUT`**, and **`DELETE`** on each single-resource path under Task 5; all are implemented and wired to your resources.
6. **Working HTTP API** — Endpoints are stable, return appropriate status codes and JSON bodies, and behave correctly for success and common failure cases (e.g., missing resources return `404`, invalid input returns `400`).
7. **Layered implementation** — Keep the pattern used in the template:
   - **Resource** layer: Pydantic models and orchestration (`AbstractBaseResource` subclasses), including **`CustomerResource`** (Task 2), **`OrderResource`** (Task 3), and **`OrderDetailsResource`** (Task 4).
   - **Data service** layer: CRUD and queries (`AbstractBaseDataService` subclasses), using **`MySQLDataService`** against **`classicmodels`** where persistence is required.
   - **Application entrypoint** (`app/main.py`): route definitions only (including Task 5); minimal business logic in route handlers.
8. **Task 6 (Jupyter Notebook)** — Completed as described above; notebook cells test or demonstrate your methods and/or endpoints.
9. **Configuration** — Use environment variables (see `.env.example`) for anything environment-specific: app name, host/port, **MySQL connection parameters** (including database name **`classicmodels`** for this assignment), file paths, etc. Do not commit secrets.

## Starter vs your work

| Provided in the template | You implement |
|---------------------------|----------------|
| FastAPI app, `/health`, `/`, `/echo`; Harry Potter routes as examples | **Task 5**: **`GET`**/**`POST`** **`/customers`**, **`/orders`**, **`/orderdetails`**; **`GET`**/**`PUT`**/**`DELETE`** **`/customers/{customerNumber}`**, **`/orders/{orderNumber}`**, **`/orders/{orderNumber}/orderdetails`** (or composite-key paths per Task 5) |
| `HarryPotterResource` + sample JSON data (reference only) | **`CustomerResource`** (Task 2), **`OrderResource`** (Task 3), and **`OrderDetailsResource`** (Task 4), all backed by **`MySQLDataService`** |
| `JSONFileDataService` (reference only) | **`MySQLDataService`** (Task 1) targeting **`classicmodels`** |
| Abstract base classes for resource and data service | Concrete classes matching your API contract |
| *(no Jupyter Notebook in the starter)* | **Task 6** — Jupyter Notebook (`.ipynb`) whose cells test your methods and/or API |

## Functional expectations (illustrated by the sample)

The Harry Potter sample shows the kind of surface your own API should provide:

- **List / search** — `GET` with optional query parameters acting as an equality template over fields.
- **Read one** — `GET` by primary key; `404` when missing.
- **Create** — `POST` with a body; server assigns an identifier when omitted.
- **Update** — `PUT` by primary key; reflect conflicts or missing rows per your spec.
- **Delete** — `DELETE` by primary key; response indicates whether a row was removed.

**Task 5** requires **`GET`** and **`POST`** on **`/customers`**, **`/orders`**, and **`/orderdetails`**, plus **`GET`**, **`PUT`**, and **`DELETE`** on each single-resource route in the Task 5 section (customers and orders by id, and order-scoped order details—or composite-key paths as specified in Task 5).

Apply the same expectations to your **customer** endpoints (**`CustomerResource`**, **`customers`** table), **order** endpoints (**`OrderResource`**, **`orders`** table), and **order-detail** endpoints (**`OrderDetailsResource`**, **`orderdetails`** table) in **`classicmodels`**. If a table uses a **composite primary key**, your routes and resource models must reflect that (e.g., multiple path or query parameters), per instructor guidance.

Your domain may require additional operations (pagination, joins, aggregates); document them in your API and notebook.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Run the server (defaults in code: host `0.0.0.0`, port `8000`):

```bash
python -m app.main
```

Open your Jupyter Notebook (install Jupyter in your environment if needed: `pip install notebook` or `pip install jupyterlab`), run the server in another terminal if your cells call HTTP endpoints, then execute the notebook cells top to bottom.

Interactive docs: open `/docs` once the server is running.

## Academic integrity

Follow your instructor’s collaboration and citation rules. The abstract interfaces and layout of this template are provided as scaffolding; **your domain logic, schema, notebook, and written materials must be your own** unless the assignment permits otherwise.
