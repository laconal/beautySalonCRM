# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Multi-tenant SaaS backend for beauty salon / spa management ("Salon Platform"): appointments/bookings, clients with deposit balances, employees and their schedules, services & materials inventory, receipts/payments, payroll & payouts, promotions, gift cards, and staff notifications. FastAPI + SQLAlchemy (async) + PostgreSQL + Redis + Celery. Python 3.14, managed with `uv`.

Three existing docs are the source of truth for domain detail — don't re-derive this from code, read them:
- `documentation-api.md` — endpoint-by-endpoint catalog (method, path, request/response schema, status code) for the frontend team.
- `documentation-exceptions.md` — every `errorCode` / `statusCode` / meaning, grouped by domain.
- `docs-business-logic.md` — cross-cutting business rules (e.g. what blocks cancelling an appointment, when payroll auto-generates, deposit rules). Written in Russian.

## Commands

```bash
# Run the API locally (requires Postgres + Redis reachable per .env, and RSA keypairs — see Auth below)
uv run uvicorn src.app:app --reload

# Migrations (Alembic, async engine)
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head

# Tests — run against a REAL disposable Postgres DB, not mocks/sqlite.
# This drops+recreates `salon_test`, migrates it, seeds 2 tenants + admin staff, runs pytest, then drops the DB again.
uv run python src/tests/run_tests.py            # equivalent to: ... run_tests.py -v
uv run python src/tests/run_tests.py -k test_name   # args after the script pass straight to pytest

# Running pytest directly assumes the schema/seed data above already exists in DATABASE_URL:
uv run pytest src/tests/test_appointment.py -v
uv run pytest src/tests/test_appointment.py::test_create_conflict -v

# Celery (notification polling/delivery — see Background jobs below)
uv run celery -A src.core.celery.celeryApp.celery_app worker --loglevel=info
uv run celery -A src.core.celery.celeryApp.celery_app beat --loglevel=info

# Docker (see README.md for the full first-run checklist, incl. CRLF->LF fix for entrypoint.sh on Windows)
docker compose build
docker compose up -d
docker exec -it salonBackend uv run migrate_docker.py   # first run only: migrate + seed fake data
```

Local (non-docker) auth needs two RSA keypairs on disk before the app can start — paths are set via `.env` (`PRIVATE_KEY_PATH`/`PUBLIC_KEY_PATH` for staff tokens, `ADMIN_PRIVATE_KEY_PATH`/`ADMIN_PUBLIC_KEY_PATH` for the `/admin` panel). Generate with the `openssl genpkey`/`openssl rsa` commands in `README.md`. In Docker, `entrypoint.sh` generates both pairs automatically on first boot if missing.

`migrate_docker.py` (Docker-only helper, run manually) and `manage_tenants.py` (`--company_name`, `--admin-login`, ... CLI) both provision tenants — `manage_tenants.py` calls the same `provision_tenant` service used by the sqladmin panel; `migrate_docker.py` additionally seeds bulk fake data (Faker) for local exploration.

## Architecture

### Layering

Every domain (appointment, client, employee, material, service, receipt, payroll, payout, transaction, staff, role, tenant, promotion, giftCard, notification, ...) follows the same vertical slice, each in its own file per layer:

```
src/routes/<area>/<domain>_router.py       FastAPI router: declares endpoints, wires Depends(require_permission(...)), delegates 1:1 to a service method
src/services/<area>/<domain>_service.py    Business rules/orchestration. Takes a UnitOfWork in __init__, raises domain exceptions
src/repository/<domain>/<domain>_repository.py   SQLAlchemy queries for one model, extends BaseRepository[Model]
src/repository/<domain>/<domain>_model.py  SQLAlchemy ORM model (extends BaseFields or Base)
src/schemas/<domain>/{create,update,response}.py  Pydantic request/response schemas
src/exceptions/<domain>_exceptions.py      BaseAppException subclasses for this domain
```

`src/routes/__init__.py` assembles every router into two top-level routers mounted in `src/app.py`: `open_router` (just `/auth/*`) and `protected_router` (everything else, gated by `Depends(get_current_staff)` at the router level).

### Unit of Work / repositories

`src/core/dependencies/uow.py::UnitOfWork` is a flat namespace of every repository (`uow.appointments`, `uow.clients`, `uow.receipts`, ...), constructed once per request by the `get_request_uow` dependency, which opens one `transaction_scope()` (commit on success / rollback on exception) shared by every dependency in that request — including permission checks, so a permission-cache miss and the endpoint's own work run inside the exact same DB transaction.

`BaseRepository[T]` (`src/database/base.py`) auto-binds its generic type param (`__init_subclass__` reads `__orig_bases__`) and provides `get`/`update`/`archive`/`delete`; domain repositories add query methods (filters, joins, overlap checks, etc.) on top. Repositories don't hold a session themselves — `self.db` resolves the current `AsyncSession` from a `ContextVar` (`src/database/session.py::db_session_ctx`), set for the duration of `transaction_scope()`.

`@require_exists("clients", target_param="client_id")` (`src/core/decorators/requireID.py`) is a service-method decorator that 404s up front if a referenced FK id doesn't resolve via `self.uow.<repo_attr>.get(id)` — used to keep existence checks out of service bodies.

### Multi-tenancy (row-level, not schema-per-tenant)

Single shared schema; every tenant-scoped table has a `tenant_id` FK (via `TenantMixin`, `src/database/mixins.py`). Isolation is enforced at the SQLAlchemy session level, not by adding `WHERE tenant_id = ...` in every query:

- `src/core/dependencies/context.py` holds the active `tenant_id`/`staff_id`/`actor_id` in `ContextVar`s, set once per request by `get_current_staff` after decoding the JWT cookie.
- `src/core/dependencies/tenantFilter.py::register_tenant_filter(session)` attaches two SQLAlchemy event listeners to each session: `do_orm_execute` injects a `tenant_id == current_tenant` loader criteria into every SELECT/UPDATE/DELETE touching a `TenantMixin` entity; `before_flush` stamps `tenant_id` on new rows and raises `PermissionError` if code tries to read/write/delete a row belonging to a different tenant, or mutate `tenant_id` on an existing row. If there is no tenant in context, writes are blocked outright ("secure by default") but plain reads pass through unfiltered — this is what lets `/auth/login` look up `Staff` by globally-unique `login` before any tenant is known.
- Cross-tenant relationships that still need referential integrity (e.g. `Actor`, FKs on `BaseFields.created_by_actor_id`) use composite FKs/joins pinned to `(id, tenant_id)` rather than `id` alone (see `ForeignKeyConstraint` usage in `staff_model.py`, `tenant_model.py`).

### Tenant branches (parent/child hierarchy)

A tenant can have child tenants ("branches") via `Tenant.parent_id` (self-referential FK, capped at two levels — a branch can't have branches of its own; enforced in code by `require_parent_tenant`, `src/core/dependencies/permissions.py`, not the DB). `Tenant` itself is `Base`, not `TenantMixin` — it isn't tenant-scoped, the row filter above doesn't apply to it, and `name` uniqueness is enforced at the service layer (`TenantBranchesService`), not a DB constraint.

Everything under `src/services/system/tenantBranches_service.py` / `src/routes/system/tenantBranches_router.py` deliberately operates across the row-level tenant boundary described above, using three techniques worth knowing before writing similar cross-tenant code elsewhere:
- **Cross-tenant reads** use `.execution_options(skip_tenant_filter=True)` on the request's own session — the one escape hatch `do_orm_execute` respects.
- **Cross-tenant writes** need a standalone `SessionLocal()` with no `register_tenant_filter` attached (that listener is wired to one specific session instance inside `transaction_scope()`, never the class) — the `before_flush` guard has no equivalent per-statement bypass. Same technique `provision_tenant`/sqladmin's tenant creation already used.
- **Actor attribution** needs `cleared_actor_context()` (`src/core/dependencies/context.py`) wrapped around the write — see Auditing below for why.

Parent-only report data (`GET /report`, `/report/{id}`) is aggregate-only (`GROUP BY tenant_id` counts/sums with `skip_tenant_filter`), not a raw cross-tenant list endpoint — deliberately, to keep the isolation guarantee intact for every other domain. Full endpoint/error catalog: `documentation-api.md`, `documentation-exceptions.md`, `docs-business-logic.md`.

### Auth & permissions

- Two independent JWT stacks, both RS256: staff tokens (`access_token`/`refresh_token` cookies, `src/core/auth/security.py`) and a separate admin keypair for the `/admin` sqladmin panel (`src/core/admin/auth_backend.py`).
- Permissions are a flat `IntEnum` catalog (`src/core/permissions.py::PermissionCode`, grouped by domain in blocks of 1000, e.g. `2xxx` = appointments). A staff has `permissions: list[int]` (direct overrides) plus zero or more `Role`s, each with its own `permissions: list[int]`; `compute_effective_permissions` unions them. Every domain has a `*_MANAGE` code; `PERMISSION_DOMAIN_MANAGE` (built once, matched by longest common name prefix) lets holding `APPOINTMENT_RECORDS_MANAGE` satisfy a check for `APPOINTMENT_RECORDS_CREATE` without also granting the broader `APPOINTMENT_MANAGE`.
- `require_permission([PermissionCode....], condition="all"|"or")` (`src/core/dependencies/permissions.py`) is the route-level dependency; `StaffType.ADMIN` staff bypass all checks. Effective permissions are cached in Redis per staff (`src/core/cache/permission_cache.py`, TTL = refresh-token lifetime, invalidated on logout/permission change) with a DB fallback if Redis is unreachable — Redis is treated as optional everywhere in this codebase (every cache module catches `RedisError` and logs+degrades rather than failing the request). That same cache entry also carries `active`, checked by `get_current_staff` on *every* request (`src/core/dependencies/auth.py::is_staff_active`, same cache-first/DB-fallback pattern as `is_tenant_active` below) — deactivating a staff member takes effect on their next request rather than only once their (long-lived) access token expires.
- `is_tenant_active` similarly cache-fronts a per-tenant active flag so a deactivated tenant's staff get `TenantIsInactive` without hitting Postgres on every request.
- `require_parent_tenant` (same file) is orthogonal to `require_permission` — it checks tenant hierarchy (`Tenant.parent_id is None`), not staff permissions, so `StaffType.ADMIN`'s bypass above doesn't accidentally grant a branch's own admin access to parent-only routes. See Tenant branches below.

### Auditing

`BaseFields` (base class for nearly every tenant-scoped model) carries `created_at`/`updated_at`/`archived`/`created_by_actor_id`, plus SQLAlchemy `@validates` that make `created_by_actor_id` and `created_at` immutable after the row exists. `Actor` (`src/database/base.py`) is an indirection layer over "who did this" — a `Staff`, or a system/api/telegram/instagram actor — so `created_by` can be rendered without assuming a human staff member exists.

`register_audit_listener()` (`src/database/audit_listener.py`, wired in `app.py`'s lifespan) hooks `before_flush` globally: it stamps `created_by_actor_id` on new `BaseFields` rows from the current actor context, and diffs every dirty column on every dirty `BaseFields` instance into `AuditLogs` rows (old/new value, per field, per flush) — this is automatic and requires no per-service opt-in. Unlike the tenant filter above, this listener is registered on the SQLAlchemy `Session` **class** itself, not one instance — it fires on every session in the process for the app's whole lifetime, including ad-hoc `SessionLocal()` instances outside the request's own `transaction_scope()`. Code that opens such a session to write rows for a *different* tenant (see Tenant branches above) must wrap the write in `cleared_actor_context()`, or this listener stamps the caller's own actor onto the new row — which then fails the `(actor_id, tenant_id)` composite FK since that actor belongs to a different tenant.

### Errors

All domain errors subclass `BaseAppException` (`src/exceptions/base.py`: `detail`, `errorCode`, `statusCode`, arbitrary `**metadata`) and are organized one file per domain under `src/exceptions/`. Two global handlers in `src/app.py`/`src/core/exceptions.py` turn these into a consistent JSON shape (`error_code`, `detail`, `metadata`) for `BaseAppException`, Pydantic `RequestValidationError` (422), and Postgres `IntegrityError` (mapped from `pgcode` — unique violation → 409, FK violation → 404, not-null/check → 409). Full catalog with meaning of every code: `documentation-exceptions.md`.

### Dynamic filtering

Domain models opt into the generic list/filter UI by declaring `ALLOWED_FILTERS: set[str]` (e.g. `staff_model.py`). `GET /api/v1/docs/filters/{table}` (`src/routes/__init__.py`) introspects a model's columns (via `MODEL_REGISTRY`, `src/repository/registry.py`) to hand the frontend field name + type (+ enum options) per filterable column, and `src/core/utils/model_filter.py::apply_dynamic_filters` turns a `{field: value}` / `{field: {op: value}}` filter dict from `RequestAllObject.filters` into SQLAlchemy predicates (`eq`/`ne`/`gt`/`gte`/`lt`/`lte`), coercing strings to the column's Python type.

### Background jobs & realtime

- Celery (`src/core/celery/celeryApp.py`) with a beat schedule that polls for due `Notification`s every 60s (`poll_and_deliver_notification`) and pushes them over Redis pub/sub to whichever process holds that staff member's live SSE connection (`src/core/utils/sse_publisher.py` publishes, `SSEManager` + `GET /notifications/stream` subscribes). The Celery task builds its own engine/session rather than reusing the app's, since it runs in a separate worker process.
- SSE is per-staff (keyed by staff id), so delivery only succeeds if that staff has an open `/notifications/stream` connection; failed/unsubscribed notification ids get reverted so the next beat tick retries them.

### Admin panel

`sqladmin` mounted at `/admin` (`src/core/admin/setup.py`), separate RSA-signed session auth (`auth_backend.py`) from the regular staff JWT flow. Currently exposes tenant management (`TenantAdmin`, `TenantCreateView` in `views.py`) — creating a tenant here goes through the same `provision_tenant` service as `manage_tenants.py`.

## Conventions worth knowing before touching code

- Schema files per domain are always split `create.py` / `update.py` / `response.py`; update schemas extend `BaseUpdateSchema` (`src/schemas/base.py`), which rejects a request with every optional field left `None` via a `model_validator`.
- List endpoints are `POST /<resource>/get-all` (not `GET`, since filters are a body payload), taking `RequestAllObject` (page/pageSize/filters) and returning `PaginatedResponseSchema[T]`.
- Money-affecting domains (receipts, payments, payroll, payouts, transactions, deposits) have significant cross-entity invariants enforced in the service layer (e.g. can't edit a `payroll` once `auto_generated` or attached to a `payout_id`; cancelling a receipt reverses deposit/materials/payroll/transactions together) — read `docs-business-logic.md` before changing anything in these areas, the rules are not obvious from a single file.
- `archived` is a soft-delete flag on `BaseFields`, not a real delete; most domains block operations on archived rows (409) rather than filtering them out implicitly — `RequestAllObject.filters` defaults to `{"archived": False}` for listing.
