# API документация (для frontend команды)

Базовый URL: `/api/v1`

---

**Формат**: для каждого эндпоинта указаны: метод, путь, схема запроса, схема ответа, статус-коды и краткое описание.

**Общие схемы**

- `RequestAllObject` / `PaginationSchema` — общая пагинация и фильтрация (см. `src/schemas/base.py`).
- `BaseResponseSchema` — базовые поля ответа (включает: `id`, `created_at`, `updated_at`, `created_by`, `archived`).

---

## Аутентификация (open)

- POST `/api/v1/auth/login`
  - request: `src/schemas/auth/login.py::LoginSchema` (login, password)
  - response: `src/schemas/auth/login.py::LoginResponseSchema`
  - status: 200
  - описание: возвращает cookie с `access_token` и `refresh_token` и информацию о пользователе.
  - `LoginResponseSchema` поля (помимо `BaseResponseSchema`): `login`, `employee`, `firstname`, `lastname`, `middlename`, `active`, `staff_type`, `tenant_name`.

- POST `/api/v1/auth/refresh` — status 204 (обновление токенов)
- POST `/api/v1/auth/logout` — status 204 (выход)
- POST `/api/v1/auth/change-password` — status 204 (смена пароля)
- PATCH `/api/v1/auth/reset-password` — status 200, response: `str`

---

## Protected endpoints (требуют аутентификацию)

Ниже перечислены роуты, префиксы берутся из `src/routes/__init__.py`.

### Appointments (/api/v1/appointments)

- POST `` (create)
  - request: `src/schemas/appointment/create.py::AppointmentCreateSchema`
  - response: `src/schemas/appointment/response.py::AppointmentResponseSchema`
  - status: 201
- PATCH `` (update)
  - request: `src/schemas/appointment/update.py::AppointmentUpdateSchema`
  - response: `AppointmentResponseSchema`
  - status: 200
- POST `/get-all`
  - request: `src/schemas/base.py::RequestAllObject`
  - response: `src/schemas/base.py::PaginatedResponseSchema[AppointmentResponseSchema]`
  - status: 200
- GET `/{id}` — получить посещение по ID (200)
- PATCH `/{id}/cancel` — отмена посещения (200)
- GET `/{id}/receipts` — чекы по посещению (200)

### Appointment Records (/api/v1/appointments-records)

- POST `` (create record)
  - request: `src/schemas/appointment/create.py::AppointmentRecordsCreateSchema`
  - response: `src/schemas/appointment/response.py::AppointmentResponseSchema`
  - status: 201
- DELETE `/{id}` — удалить запись (возвращает `AppointmentResponseSchema`, status 200)

### Appointment Services (/api/v1/appointments-services)

- POST `` (create service record)
  - request: `src/schemas/appointment/create.py::AppointmentServicesCreateSchema`
  - response: `src/schemas/appointment/response.py::AppointmentResponseSchema`
  - status: 201
- PATCH `` (update)
  - request: `src/schemas/appointment/update.py::AppointmentServiceUpdateSchema`
  - response: `AppointmentResponseSchema`
  - status: 200
- DELETE `/{id}` — удалить запись, status 200

### Employees (/api/v1/employees)

- POST `` (create)
  - request: `src/schemas/employee/create.py::EmployeeCreateSchema`
  - response: `src/schemas/employee/response.py::EmployeeResponseBase`
  - status: 201
- POST `/get-all` — пагинированный список (`RequestAllObject` -> `PaginatedResponseSchema[EmployeeResponseBase]`)
- GET `/{id}` — получить сотрудника (200)
- PATCH `` — обновить (200)
- GET `/{id}/work-schedules` — рабочие графики и отсутствия (200)
- GET `/{id}/payrolls` — зарплаты сотрудника (пагинация)
- GET `/{id}/appointments` — посещения сотрудника (пагинация)

### Specializations (/api/v1/specializations)

- POST `` — create (`SpecializationCreateSchema`) -> `SpecializationResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- DELETE `/{id}` — delete (204)

### Work schedules (/api/v1/work-schedules)

- POST `` — create (`src/schemas/work_schedule/create.py`) -> `WorkScheduleResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- DELETE `/{id}` — delete (204)

### Absences (/api/v1/absences)

- POST `` — create (`AbsenceCreateSchema`) -> `AbsenceResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- DELETE `/{id}` — delete (204)

### Transactions (/api/v1/transactions)

- POST `` — create (`src/schemas/transaction/create.py`) -> `TransactionResponseSchema` (201)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- POST `/{id}/cancel` — cancel transaction (200)

### Receipts (/api/v1/receipts)

- POST `` — create (`src/schemas/payment/create.py::ReceiptCreateSchema`) -> `ReceiptResponseSchema` (201)
- POST `/get-all` — paginated (200)
- POST `/cancel` — cancel receipt (200)

### Payments (/api/v1/payments)

- POST `` — create (`src/schemas/payment/create.py::PaymentCreateSchema`) -> `src/schemas/payment/response.py::ReceiptResponseSchema` (201)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)

### Payrolls (/api/v1/payrolls)

- POST `` — create (`src/schemas/payroll/create.py`) -> `PayrollResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- DELETE `/{id}` — delete (204)
- POST `/cancel` — cancel payroll (200)

### Payouts (/api/v1/payouts)

- POST `` — create (`src/schemas/payout/create.py`) -> `PayoutResponseSchema` (201)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)

### Clients (/api/v1/clients)

- POST `` — create (`src/schemas/client/create.py`) -> `ClientResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- POST `/update-deposit` — обновить депозит (`ClientDepositUpdateSchema`) -> `ClientResponseSchema` (200)
- GET `/{id}/appointments` — appointments for client (paginated)

### Materials (/api/v1/materials)

- POST `` — create (`src/schemas/material/create.py`) -> `MaterialResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- POST `/update-quantity` — update quantity (`MaterialQuantityUpdateSchema`) -> `MaterialResponseSchema` (200)

### Services (/api/v1/services)

- POST `` — create (`src/schemas/service.py::ServiceCreateSchema`) -> `ServiceResponseSchema` (201)
- PATCH `` — update (200)
- POST `/get-all` — paginated (200)
- GET `/{id}` — get (200)
- POST `/import` — импорт из Excel (file upload)

### Service categories (/api/v1/service-categories)

- (аналогично) CRUD + get-all (см. `src/routes/serviceCategory_router.py`)

### Notifications (/api/v1/notifications)

- POST `` — create (`src/schemas/notification/create.py`) -> `NotificationResponseSchema` (201)
- POST `/get-all` — paginated (200)
- GET `/stream` — Server-Sent Events (SSE) stream для текущего staff (подключение к Redis pubsub)
- GET `/{id}` — get (200)
- DELETE `/{id}` — archive (200)
- DELETE `/{id}` — delete (204)

### Audit logs (/api/v1/audit-logs)

- GET `` — paginated audit logs (200)

---

### Tenant Branches / Филиалы (/api/v1/tenant-branches)

**Как это работает.** Любая организация (tenant) может стать «головной» и завести собственные дочерние организации — «филиалы» (branches). Технически это те же самостоятельные tenant'ы (у каждого свой набор сотрудников, клиентов, услуг, чеков и т.д. — данные между филиалами и головной организацией не шарятся автоматически и полностью изолированы друг от друга, как у любых двух независимых организаций), но связанные полем `parent_id`.

Ключевые правила:

- Заводить филиалы и управлять ими может **только сама головная организация** — сотрудник, чья организация не имеет родителя (`parent_id == null`). Если под эти эндпоинты попадает сотрудник филиала (у которого `parent_id` уже указывает на головную организацию), сервер вернёт `403 ONLY_FOR_PARENT_TENANT`.
- Иерархия ограничена **двумя уровнями** — у филиала не может быть своих филиалов.
- У головной организации нет «постраничного списка» данных филиалов (записей клиентов, чеков и т.п.) — только агрегированные **отчёты** (`GET /report`, `GET /report/{id}`): количество сотрудников/сотрудников-исполнителей/клиентов/записей/услуг/товаров и суммы доходов/расходов по каждому филиалу и по организации в целом.
- Первый админ филиала создаётся либо сразу вместе с филиалом (`POST /api/v1/tenant-branches`), либо отдельно позже (`POST /create-branch-admin`, можно создать нескольких админов).
- Логин сотрудника уникален **глобально** (не в рамках одной организации) — при совпадении логина вернётся `409 STAFF_LOGIN_DUPLICATE`.
- Изменения `active`/`staff_type` админа филиала и `active` самого филиала применяются **сразу** (на следующий же запрос), а не после истечения токена — так что деактивированный админ/филиал мгновенно теряет доступ.

---

- POST `` — создать филиал (и его первого админа)
  - request: `src/schemas/tenant/create.py::TenantBranchCreateSchema`
    ```json
    {
      "company_name": "Z-company",
      "company_tin": "3342421123",
      "admin_login": "aleksandr",
      "admin_firstname": "makedonian",
      "admin_password": "theGreat"
    }
    ```
    `company_tin` и `admin_password` необязательны — если `admin_password` не передан, сервер сгенерирует случайный и вернёт его в ответе.
  - response: `TenantBranchCreateResponseSchema`, status 201
    ```json
    {
      "tenant": {
        "id": 8,
        "name": "Z-company",
        "TIN": "3342421123",
        "parent_id": 1,
        "active": true,
        "created_at": "2026-08-20T10:00:00Z"
      },
      "login": "aleksandr",
      "password": "theGreat"
    }
    ```

- POST `/create-branch-admin` — создать ещё одного админа для уже существующего филиала
  - request: `src/schemas/tenant/create.py::BranchAdminCreateSchema`
    ```json
    {
      "branch_id": 8,
      "admin_login": "aleksandr2",
      "admin_firstname": "Alexander",
      "admin_password": null
    }
    ```
  - response: `BranchCreateAdminResponse`, status 201
    ```json
    {
      "login": "aleksandr2",
      "password": "kJ8$mQ2pXzW1vT9r"
    }
    ```
    (пароль сгенерирован автоматически, т.к. `admin_password` не был передан)

- GET `` — список филиалов текущей (головной) организации
  - response: `list[TenantBranchResponseSchema]`, status 200
    ```json
    [
      {
        "id": 8,
        "name": "Z-company",
        "TIN": "3342421123",
        "parent_id": 1,
        "active": true,
        "created_at": "2026-08-20T10:00:00Z"
      }
    ]
    ```

- POST `/reset-admin-password` — сбросить/задать пароль админа филиала
  - request: `src/schemas/tenant/update.py::UpdateBranchAdminPassword`
    ```json
    {
      "branch_id": 8,
      "admin_id": 5,
      "password": null
    }
    ```
  - response: `str | null`, status 200
    - `password` не передан → в ответе новый сгенерированный пароль (строка);
    - `password` передан → ответ пустой (`null`), т.к. пароль уже известен вызывающему.

- GET `/report` — агрегированный отчёт по всем филиалам + итог
  - response: `TenantBranchReportSchema`, status 200
    ```json
    {
      "branches": [
        {
          "tenant_id": 8,
          "tenant_name": "Z-company",
          "staffs": 3,
          "employees": 5,
          "clients": 120,
          "appointments": 340,
          "services": 12,
          "materials": 8,
          "income": 15000000,
          "expense": 2000000
        }
      ],
      "total": {
        "staffs": 3,
        "employees": 5,
        "clients": 120,
        "appointments": 340,
        "services": 12,
        "materials": 8,
        "income": 15000000,
        "expense": 2000000
      }
    }
    ```
    `income`/`expense` считаются по неотменённым и незаархивированным транзакциям; остальные поля — количество незаархивированных записей.

- GET `/report/{id}` — отчёт по одному конкретному филиалу (без `total`)
  - response: `TenantBranchReportItemSchema`, status 200
    ```json
    {
      "tenant_id": 8,
      "tenant_name": "Z-company",
      "staffs": 3,
      "employees": 5,
      "clients": 120,
      "appointments": 340,
      "services": 12,
      "materials": 8,
      "income": 15000000,
      "expense": 2000000
    }
    ```

- PATCH `/update-admin` — изменить `active` и/или `staff_type` админа филиала
  - request: `src/schemas/tenant/update.py::UpdateBranchAdminSchema`
    ```json
    {
      "branch_id": 8,
      "admin_id": 5,
      "active": false
    }
    ```
    Нужно указать хотя бы одно из полей `active`/`staff_type`.
  - response: `BranchAdminResponseSchema`, status 200
    ```json
    {
      "id": 5,
      "login": "aleksandr2",
      "firstname": "Alexander",
      "staff_type": "administrator",
      "active": false
    }
    ```

- PATCH `/update` — изменить данные самого филиала (`name` / `TIN` / `active`)
  - request: `src/schemas/tenant/update.py::UpdateBranchSchema`
    ```json
    {
      "branch_id": 8,
      "name": "Z-company Tashkent"
    }
    ```
    Нужно указать хотя бы одно из полей `name`/`TIN`/`active`. При смене `name` сервер проверяет, что оно не занято другой организацией (`409 TENANT_NAME_TAKEN`).
  - response: `TenantBranchResponseSchema`, status 200
    ```json
    {
      "id": 8,
      "name": "Z-company Tashkent",
      "TIN": "3342421123",
      "parent_id": 1,
      "active": true,
      "created_at": "2026-08-20T10:00:00Z"
    }
    ```

**Специфичные для этого домена ошибки** (полный список и описания — `documentation-exceptions.md`):

| errorCode                          | statusCode | Когда возникает                                                                 |
| ----------------------------------- | ---------- | -------------------------------------------------------------------------------- |
| `ONLY_FOR_PARENT_TENANT`            | 403        | Запрос сделан от имени филиала, а не головной организации.                       |
| `BRANCH_DOES_NOT_BELONG_TO_TENANT`  | 409        | Указанный `branch_id` — не филиал текущей организации.                          |
| `TENANT_NAME_TAKEN`                 | 409        | Новое `name` уже занято другой организацией.                                    |
| `STAFF_TENANT_CONFLICT`             | 409        | Указанный `admin_id` не относится к указанному `branch_id`.                     |
| `STAFF_LOGIN_DUPLICATE`             | 409        | Такой `admin_login` уже используется (логины уникальны глобально).              |
| `TENANT_NOT_FOUND`                  | 404        | Головная организация или филиал с указанным id не найдены.                      |
| `STAFF_NOT_FOUND`                   | 404        | Админ с указанным `admin_id` не найден.                                         |


---

## Возможные ошибки (генерируются на уровне сервисов)

Ниже перечислены ключевые ошибки, которые возникают в сервисах (код ответа и сообщение), собраны из `src/services`:

- `appointment_service`:
  - 409 — "Appointment slot already taken by this client"
  - 404 — "Посещение с ID {id} не найден"
  - 400/409 — разные проверки целостности (архивированные сущности, некорректные операции)

- `appointmentRecords_service` / `appointmentServices_service`:
  - 400 — "Необходимо сначало отменить активный чек для этого посещения"
  - 404 — _entity_ not found (material/service/appointmentRecord)
  - 409 — попытка использовать архивированные объекты

- `auth_service`:
  - 404 — "Некорректный логин или пароль"
  - 401 — "Пользователь неактивен" / "Невалидный токен"

- `client_service`:
  - 4xx/409 — валидационные ошибки и конфликты (например дубликаты)

- `employee_service`:
  - 404 — связанные объекты не найдены
  - 409 — попытка привязать архивированную услугу/специализацию

- `material_service`, `receipt_service`, `service_service`:
  - 400 — валидация (пустые поля, некорректные операции)
  - 404 — сущность не найдена
  - 409 — использование архивированных сущностей

- `payout_service`, `payroll_service`, `transaction_service`:
  - 404 — не найдено
  - 400/409 — логика бизнес-ограничений (например, нельзя отменять автоматически сгенерированные транзакции/выплаты)

Обратите внимание: сообщения ошибок могут содержать русские тексты с контекстом (см. соответствующие файлы в `src/services/*_service.py`).

---

## Полезные файлы и схемы

- Общие схемы: `src/schemas/base.py`
- Аутентификация: `src/schemas/auth/login.py`
- Модели сущностей и поля ответов находятся в `src/schemas/*/response.py` и запросов в `src/schemas/*/create.py` / `update.py`.

---

## Рекомендации для frontend команды

- Для всех `get-all` endpoints используйте `RequestAllObject` (`filters`, `page`, `pageSize`).
- SSE: подключение к `/api/v1/notifications/stream` требует авторизации (cookie) и поддерживает события `connected` и `notification`.
- Для операций, которые изменяют состояние (create/update/delete), следите за статус-кодами 201/200/204 и обрабатывайте 4xx ошибки, где тело ошибки содержит `detail`.
- Для операций, которые изменяют состояние (create/update/delete), следите за статус-кодами 201/200/204 и обрабатывайте 4xx ошибки, где тело ошибки содержит `detail`.

---

## Доступные фильтры для `get-all` (поля)

Вы можете получить схему доступных фильтров программно через endpoint:
`GET /api/v1/docs/filters/{table}` — где `{table}` берётся из enum `FilterTables` (например: `appointments`, `clients`, `employees` и т.д.).

Ниже перечислены поля, которые можно указывать в `filters` у `RequestAllObject` для основных таблиц (в формате `field: type`):

- `appointments`:
  - `client_id`: number
  - `start_time_est`: datetime
  - `end_time_est`: datetime
  - `status`: enum (awaiting, cancelled, started, finished)
  - `paid`: boolean
  - `archived`: boolean

- `clients`:
  - `firstname`: string
  - `lastname`: string
  - `middlename`: string
  - `phone`: string
  - `birth_date`: date
  - `sex`: enum (male, female)
  - `archived`: boolean

- `employees`:
  - `firstname`: string
  - `lastname`: string
  - `middlename`: string
  - `phone`: string
  - `active`: boolean
  - `specialization_id`: number
  - `archived`: boolean

- `services`:
  - `name`: string
  - `price`: number
  - `category_id`: number
  - `archived`: boolean

- `service-categories`:
  - `name`: string
  - `archived`: boolean

- `materials`:
  - `article`: string
  - `name`: string
  - `measurement_unit`: enum (piece, pack, box, bottle, milliliter, liter, gramm, kilogram)
  - `quantity`: number
  - `volume`: number
  - `sell_price`: number
  - `archived`: boolean

- `notifications`:
  - `client_id`: number
  - `type`: enum (reminder, other)
  - `delivered_at`: datetime
  - `archived`: boolean

- `receipts`:
  - `total_amount`: number
  - `receipt_type`: enum (appointment, direct sale)
  - `status`: enum (pending, paid, cancelled)
  - `archived`: boolean

- `payments`:
  - `amount`: number
  - `receipt_id`: number
  - `method`: enum (cash, card, deposit)
  - `archived`: boolean

- `transactions`:
  - `amount`: number
  - `type`: enum (income, expense)
  - `method`: enum (card, cash, bank transfer, deposit)
  - `category`: enum (receipt, employee payment, utility, internet, telephone, other)
  - `cancelled`: boolean
  - `auto_generated`: boolean
  - `archived`: boolean

- `employee_work_schedules`:
  - `day`: date
  - `start_time`: string (time)
  - `end_time`: string (time)
  - `archived`: boolean

- `employee_absences`:
  - `employee_id`: number
  - `start_date`: date
  - `end_date`: date
  - `absence_type`: enum (sick, vacation, day off, weekend, other)
  - `archived`: boolean

---

## Схемы запросов (какие поля можно отправлять и правила валидации)

Ниже — краткая сводка основных Pydantic-схем запросов из `src/schemas` с перечислением полей и важными правилами валидации.

- `AppointmentCreateSchema` (`src/schemas/appointment/create.py`)
  - client_id: int (>=1)
  - start_time_est, end_time_est: datetime (микросекунды обрезаются); требуется `start_time_est < end_time_est`.
  - records: опциональный список `AppointmentRecordsCreateOptionalSchema`.
  - notes: str | None

- `AppointmentRecordsCreateSchema` / `AppointmentServicesCreateSchema`
  - AppointmentRecordsCreate: `appointment_id` (>=1), `employee_id` (>=1), `services` — список сервисов.
  - AppointmentServicesCreate: `appointment_record_id` (>=1, опционально для вложённых форм), `service_id` или `material_id` (обязательно один из двух, нельзя оба), `quantity` (>=1, по умолчанию 1), `price` (>=1, опционально), `price_changed_reason` (min_length=5 при изменении цены), `notes`.

- `AppointmentUpdateSchema` / `AppointmentServiceUpdateSchema` / `AppointmentCancelSchema` (`src/schemas/appointment/update.py`)
  - `id` (>=1) и остальные поля в `BaseUpdateSchema` (по крайней мере одно поле должно быть указано).
  - `status` ограничен набором {AWAITING, STARTED, FINISHED} при обновлении.
  - При обновлении услуги/товара нельзя одновременно указывать `service_id` и `material_id`.
  - `AppointmentCancelSchema` содержит `reason` (enum) и `id`.

- `ReceiptCreateSchema` / `PaymentCreateSchema` (`src/schemas/payment/create.py`)
  - `ReceiptCreateSchema`:
    - `receipt_type`: enum (APPOINTMENT или DIRECT_SALE)
    - Для `APPOINTMENT` требуется `appointment_id` (и нельзя указывать `client_id` или `receipt_items`)
    - Для прямой продажи (`DIRECT_SALE`) требуется `receipt_items` — список `material_id`+`quantity`; нельзя одновременно указать `appointment_id` и `receipt_items`.
  - `PaymentCreateSchema`:
    - `receipt_id` (>=1), `amount` (>=1), `method` (enum `PaymentMethodsEnum`), `add_change_to_deposit` (bool).
    - При `method == DEPOSIT` сервер дополнительно проверяет баланс клиента и может вернуть 400 при недостатке.

- `TransactionCreateSchema` (`src/schemas/transaction/create.py`)
  - `type`, `category`, `method` (enums), `amount` (>=1), `notes`.
  - Есть запрет на ручное создание транзакций для категорий `RECEIPT` и `EMPLOYEE_PAYMENT` (валидатор выбросит ошибку).

- `PayrollCreateSchema` / `PayrollUpdateSchema` (`src/schemas/payroll/*`)
  - `employee_id` (>=1), `amount` (>=1), `type` (enum), `notes`, `appointment_id` (опционально).
  - При обновлении `id` обязателен; на уровне сервисов есть дополнительные ограничения для `auto_generated` и `payout_id`.

- `PayoutCreateSchema` (`src/schemas/payout/create.py`)
  - `employee_id` (>=1), `type` (enum), `amount` (опционально), `method` (enum), `payrolls` (список id) или `start_date`/`end_date` для формирования по периоду.
  - Валидатор запрещает передавать одновременно `payrolls` и период; при `type` == SALARY/ADVANCE нельзя передавать `payrolls` или период.

- `ClientCreateSchema` / `ClientUpdateSchema` (`src/schemas/client/*`)
  - Create: `firstname`, `lastname`?, `middlename`?, `phone`?, `birth_date`?, `sex` (enum), `deposit` (int, default 0), `notes`.
  - Update: `id` обязателен; поля опциональны; `ClientDepositUpdateSchema` использует `operation` (1 или -1) и `amount` (>=1). Сервер запрещает отрицательный депозит.

- `EmployeeCreateSchema` / `EmployeeUpdateSchema` (`src/schemas/employee/*`)
  - Create: `firstname`, `lastname`?, `phone`?, `birth_date`, `active` (bool), `specialization_id`?, `services_ids` (list[int]), `salary_fixed`, `percent_from_services`, `percent_from_sales`.
  - Update: `id` обязателен; `services` — список id (>=1); при привязке проверяется, что услуги существуют и не архивированы.

- `MaterialCreateSchema` / `MaterialUpdateSchema` (`src/schemas/material/*`)
  - Create: `article`, `name`, `description`?, `quantity` (>=0), `measurement_unit` (enum), `volume` (>=0), `sell_price` (>=0).
  - Update: `id` обязателен; `MaterialQuantityUpdateSchema` использует `operation` (1 или -1) и `quantity` (>=1); нельзя получить отрицательный остаток.

- `ServiceCreateSchema` / `ServiceUpdateSchema` / `ServiceCategoryCreateSchema` (`src/schemas/service*`)
  - Service: `name`, `price` (>=0), `category_id` (opt). При архивировании услуги связи с сотрудниками очищаются.
  - ServiceCategory: `name`.

- `SpecializationCreateSchema` / `SpecializationUpdateSchema` — `name` (строка, max_length 255).

- `NotificationCreateSchema` (`src/schemas/notification/create.py`)
  - `client_id`?, `title` (max 50)?, `body` (строка), `type` (enum), `scheduled_at` (datetime).

- `SegmentationCreateSchema` (`src/schemas/segmentation/create.py`)
  - `name`, `description`, `criteria` (правила), `client_ids` (список id) — результат сохраняется в БД.

---

### Примеры `RequestAllObject` для `/get-all`

Ниже компактные JSON-примеры тела запроса `RequestAllObject` (поле `filters` — словарь фильтров, `page`/`pageSize` — пагинация, `sort` — опционально `field:direction`).

- `appointments/get-all` — ожидающие, неоплаченные посещения клиента `client_id=12`:

```json
{
  "filters": { "client_id": 12, "status": "awaiting", "paid": false },
  "page": 1,
  "pageSize": 20,
  "sort": "start_time_est:asc"
}
```

- `clients/get-all` — поиск по имени/телефону:

```json
{
  "filters": { "firstname": "Анна", "phone": "+79991234567" },
  "page": 1,
  "pageSize": 50
}
```

- `receipts/get-all` — оплаченные чеки прямых продаж:

```json
{
  "filters": { "receipt_type": "direct sale", "status": "paid" },
  "page": 1,
  "pageSize": 30,
  "sort": "total_amount:desc"
}
```

- `transactions/get-all` — приходные транзакции по карте:

```json
{
  "filters": { "type": "income", "method": "card" },
  "page": 1,
  "pageSize": 25
}
```

- `employees/get-all` — активные сотрудники с заданной специализацией:

```json
{
  "filters": { "active": true, "specialization_id": 3 },
  "page": 1,
  "pageSize": 20,
  "sort": "lastname:asc"
}
```

- `services/get-all` — услуги из категории `5` с ценой >= (серверная фильтрация по диапазону реализуется на клиенте через два запроса или дополнительный фильтр):

```json
{
  "filters": { "category_id": 5 },
  "page": 1,
  "pageSize": 50
}
```

- `service-categories/get-all` — категории по имени:

```json
{
  "filters": { "name": "Брови" },
  "page": 1,
  "pageSize": 25
}
```

- `materials/get-all` — материалы с определённой единицей измерения и минимальным количеством:

```json
{
  "filters": { "measurement_unit": "bottle", "quantity": 5 },
  "page": 1,
  "pageSize": 30
}
```

- `notifications/get-all` — непрочитанные напоминания для клиента `7`:

```json
{
  "filters": { "client_id": 7, "type": "reminder" },
  "page": 1,
  "pageSize": 20,
  "sort": "scheduled_at:asc"
}
```

- `payments/get-all` — платежи по конкретному чеку:

```json
{
  "filters": { "receipt_id": 42 },
  "page": 1,
  "pageSize": 20
}
```

- `payouts/get-all` — выплаты сотруднику `15`, только не отменённые:

```json
{
  "filters": { "employee_id": 15, "cancelled": false },
  "page": 1,
  "pageSize": 10
}
```

- `employee_work_schedules/get-all` — графики на определённый день:

```json
{
  "filters": { "day": "2026-07-06" },
  "page": 1,
  "pageSize": 50
}
```

- `employee_absences/get-all` — отсутствия сотрудника `9` в периоде (по start_date/end_date):

```json
{
  "filters": {
    "employee_id": 9,
    "start_date": "2026-07-01",
    "end_date": "2026-07-31"
  },
  "page": 1,
  "pageSize": 20
}
```
