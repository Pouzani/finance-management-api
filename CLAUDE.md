# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django 6.0.3 REST API backend for a personal finance management application targeting Moroccan users. Data is entered manually (no bank integrations). The frontend counterpart lives in `/home/pouzani/projects/finance-management` (Next.js).

**Database:** SQLite locally; Supabase PostgreSQL in production (configured via `.env`).

<!-- AUTO-GENERATED: commands -->
## Commands

```bash
# Run development server
python manage.py runserver

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Seed the database with initial data (idempotent — clears and reseeds)
python manage.py seed_data

# Run all tests
python manage.py test

# Run tests for a specific app
python manage.py test <app_name>

# Run a specific test class or method
python manage.py test <app_name>.tests.TestClassName.test_method_name

# Open Django shell
python manage.py shell

# Create superuser
python manage.py createsuperuser
```
<!-- END AUTO-GENERATED: commands -->

<!-- AUTO-GENERATED: env -->
## Environment Variables

Copy `.env.example` to `.env` and fill in values before running.

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `SECRET_KEY` | Yes | Django secret key | any long random string |
| `DEBUG` | No | Enable debug mode (default: `True`) | `True` / `False` |
| `ALLOWED_HOSTS` | No | Comma-separated allowed hosts (default: `localhost,127.0.0.1`) | `myapp.com,www.myapp.com` |
| `DB_HOST` | No | Supabase PostgreSQL host — if unset, SQLite is used | `db.xxxx.supabase.co` |
| `DB_ENGINE` | No | Database engine (default: `django.db.backends.postgresql`) | — |
| `DB_NAME` | No | Database name (default: `postgres`) | `postgres` |
| `DB_USER` | No | Database user (default: `postgres`) | `postgres` |
| `DB_PASSWORD` | No | Database password | — |
| `DB_PORT` | No | Database port (default: `5432`) | `5432` |
<!-- END AUTO-GENERATED: env -->

<!-- AUTO-GENERATED: api -->
## API Endpoints

Base path: `/api/`

All endpoints (except auth) require a JWT Bearer token: `Authorization: Bearer <access_token>`

### Authentication — `/api/auth/`
| Method | Path | Auth required | Description |
|--------|------|---------------|-------------|
| POST | `/api/auth/register/` | No | Register; returns `access` + `refresh` tokens |
| POST | `/api/auth/login/` | No | Login; returns `access` + `refresh` tokens |
| POST | `/api/auth/token/refresh/` | No | Exchange `refresh` for a new `access` token |
| GET | `/api/auth/me/` | Yes | Retrieve current user profile |
| PATCH | `/api/auth/me/` | Yes | Update current user profile |

### Accounts — `/api/accounts/`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/accounts/` | List all accounts (with computed balance) |
| POST | `/api/accounts/` | Create an account |
| GET | `/api/accounts/{id}/` | Retrieve an account |
| PUT | `/api/accounts/{id}/` | Update an account |
| DELETE | `/api/accounts/{id}/` | Delete an account |

### Categories — `/api/categories/`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/categories/` | List all categories |
| POST | `/api/categories/` | Create a category |

### Transactions — `/api/transactions/`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/transactions/` | List transactions (paginated, filterable) |
| POST | `/api/transactions/` | Create a transaction |
| GET | `/api/transactions/{id}/` | Retrieve a transaction |
| PUT | `/api/transactions/{id}/` | Update a transaction |
| DELETE | `/api/transactions/{id}/` | Delete a transaction |

**Transaction query parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | date | Filter transactions on or after this date (`YYYY-MM-DD`) |
| `end_date` | date | Filter transactions on or before this date |
| `category` | UUID | Filter by category ID |
| `account` | UUID | Filter by account ID |
| `type` | string | Filter by `income` or `expense` |
| `search` | string | Search within `label` field |
| `ordering` | string | Order by `date` or `amount` (prefix `-` for descending) |
| `page` | int | Page number (page size: 20) |

### Goals — `/api/goals/`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/goals/` | List all goals |
| POST | `/api/goals/` | Create a goal |
| GET | `/api/goals/{id}/` | Retrieve a goal |
| PUT | `/api/goals/{id}/` | Update a goal |
| DELETE | `/api/goals/{id}/` | Delete a goal |

### Analytics — `/api/analytics/`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analytics/monthly-flow/` | Monthly income vs expenses grouped by month |
| GET | `/api/analytics/category-split/` | Expense totals grouped by category |
<!-- END AUTO-GENERATED: api -->

## Architecture

### App Structure

```
finance_management_api/   ← Django config package (settings, urls, wsgi)
authentication/           ← JWT auth: register, login, token refresh, me
accounts/                 ← Account model, serializer, viewset, tests
categories/               ← Category model, serializer, viewset, tests
transactions/             ← Transaction model, serializer, viewset, filter, tests
  management/commands/
    seed_data.py          ← Seed command (python manage.py seed_data)
goals/                    ← Goal model, serializer, viewset, tests
analytics/                ← MonthlyFlowView, CategorySplitView, tests
```

### Business Rules
- `amount` is stored as `DecimalField` (not float)
- Expenses must have a **negative** amount; income must have a **positive** amount — enforced in `TransactionSerializer.validate()`
- `Account.balance` is computed dynamically via ORM annotation (`Sum('transactions__amount')`) — never stored
- All primary keys are UUIDs

### Key Conventions
- Register new apps in `INSTALLED_APPS` in `settings.py`
- Include new app URL configs via `include()` in `finance_management_api/urls.py`
- Keep app-level URL patterns in each app's own `urls.py`
- Use `DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'` (already set in settings)
