# Invoice Tracker

A deliberately small invoice & billing tracker. Single user role — every
logged-in user only ever sees their own clients, invoices, line items and
payments. React + Vite + TypeScript frontend, Django REST Framework
backend, PostgreSQL database. No Celery/Redis — there is no background
work to run.

## Data model

- **User** — Django's `AbstractUser` with `email` as `USERNAME_FIELD`. No
  profile model; single role.
- **Client** — `user`, `name`, `email`, `phone` (optional), `notes`
  (optional).
- **Invoice** — `user`, `client`, `invoice_number` (unique per user),
  `issue_date`, `due_date`, `status`, `notes`.
- **InvoiceLineItem** — `invoice`, `description`, `quantity`, `unit_price`.
- **Payment** — `invoice`, `amount`, `paid_date`, `method` (free text).

### Status logic (see `apps/invoices/models.py::Invoice`)

Only `draft` and `sent` are ever *persisted* on `status`. An invoice starts
as `draft` and moves to `sent` exactly once, via `POST
/api/invoices/{id}/mark-sent/` — never implicitly.

The status shown to the API/frontend is **computed** on read
(`Invoice.computed_status`), layered on top of the persisted value:

1. `draft` — persisted status is still `draft`.
2. `paid` — persisted status is `sent` **and** `sum(payments) >= total`.
   Paid always wins once reached: a paid invoice whose due date has since
   passed is *not* overdue.
3. `overdue` — persisted status is `sent`, not fully paid, and `due_date`
   is in the past.
4. `sent` — persisted status is `sent`, not fully paid, due date not yet
   passed.

`total`, `amount_paid`, `amount_due` and `days_overdue` are likewise never
stored — they're always derived from the related line items/payments, both
as model properties and as read-only fields on `InvoiceSerializer`.

## REST API

- `POST /api/auth/register/`, `POST /api/auth/login/` (JWT),
  `POST /api/auth/refresh/`, `POST /api/auth/logout/`, `GET /api/auth/me/`
- `/api/clients/` — list/create/retrieve/update/delete
- `/api/invoices/` — list/create/retrieve/update/delete,
  `?status=draft|sent|paid|overdue`, `?client=<id>`
- `POST /api/invoices/{id}/mark-sent/` — draft → sent (400 if not currently
  draft)
- `/api/invoices/{id}/line-items/` — list/create;
  `/api/invoices/{id}/line-items/{item_id}/` — retrieve/update/delete
- `/api/invoices/{id}/payments/` — list/create;
  `/api/invoices/{id}/payments/{payment_id}/` — retrieve/update/delete
- `GET /api/dashboard/` — total outstanding (sum of `amount_due` across
  every `sent`/`overdue` invoice), total paid this calendar month, and the
  list of overdue invoices (`id`, `client_name`, `total`, `amount_due`,
  `days_overdue`)

Every ViewSet/view scopes its queryset to `request.user` (directly for
clients/invoices, via the parent invoice's `user` for line items/payments)
— there is no cross-user access even by guessing another user's object ID
(a mismatched ID returns `404`, not `403`).

## Demo data

`apps/invoices/migrations/0002_seed_demo_data.py` is a data migration
(`RunPython`) that seeds a fresh database with:

- one login: **demo@example.com** / **demo12345**
- 4 clients
- 5 invoices covering every status: draft, sent-unpaid, paid,
  overdue-unpaid, overdue-partially-paid
- a full payment on the paid invoice and a partial payment on one of the
  overdue invoices

It's idempotent — every row is looked up with `get_or_create` (or an
explicit existence check for line items/payments, which have no natural
unique key) before being created, so running `migrate` again never
duplicates rows.

## Running locally with Docker (Postgres)

```bash
cp .env.example .env
docker compose up --build
```

Backend on http://localhost:8000, frontend on http://localhost:5173.

## Running the backend without Docker (dev-only SQLite override)

No Postgres/Docker needed for this — same `USE_SQLITE` pattern used by the
sibling apps in this workspace. **Never set `USE_SQLITE=True` in
docker-compose or production.**

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash; use venv\Scripts\activate.bat on cmd

pip install -r requirements.txt

export USE_SQLITE=True
export DJANGO_SETTINGS_MODULE=config.settings.dev

python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py test
python manage.py runserver
```

## Running the frontend

```bash
cd frontend
npm install
npm run dev      # dev server on :5173
npm run build    # production build (tsc -b && vite build)
```

Set `VITE_API_BASE_URL` (see `frontend/.env.example`) if the backend isn't
at `http://localhost:8000/api`.

## Auth trade-off (dev-only)

The access token is kept in memory only; the refresh token is kept in
`localStorage` and the client refreshes on a 401. A real deployment would
instead issue the refresh token as an httpOnly cookie from the backend —
this simplified pattern (same as the sibling apps in this workspace) is a
deliberate trade-off for a small demo app, not a recommendation for
production.
