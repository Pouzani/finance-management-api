# Finance Management API

Base URL: `http://localhost:8000/api`

All responses are JSON. Paginated endpoints return the envelope below:

```json
{
  "count": 42,
  "next": "http://localhost:8000/api/transactions/?page=2",
  "previous": null,
  "results": [ ... ]
}
```

Page size is **20**. Pass `?page=<n>` to navigate.

---

## Accounts

<!-- AUTO-GENERATED: accounts -->

### `GET /api/accounts/`

List all accounts. Each account includes a computed `balance` (sum of all linked transaction amounts).

**Response**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "3f1e2b4c-...",
      "name": "CIH Principale",
      "balance": "3500.00",
      "created_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

---

### `POST /api/accounts/`

Create a new account.

**Request body**
```json
{
  "name": "CIH Principale"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Account display name |

**Response** — `201 Created`
```json
{
  "id": "3f1e2b4c-...",
  "name": "CIH Principale",
  "balance": "0",
  "created_at": "2024-01-01T10:00:00Z"
}
```

---

### `GET /api/accounts/{id}/`

Retrieve a single account by UUID.

---

### `PUT /api/accounts/{id}/`

Update an account name.

**Request body**
```json
{ "name": "CIH Épargne" }
```

---

### `DELETE /api/accounts/{id}/`

Delete an account. **Cascades to all linked transactions.**

**Response** — `204 No Content`

<!-- END AUTO-GENERATED: accounts -->

---

## Categories

<!-- AUTO-GENERATED: categories -->

### `GET /api/categories/`

List all categories.

**Response**
```json
{
  "count": 3,
  "results": [
    {
      "id": "a1b2c3d4-...",
      "name": "Logement",
      "color": "#ef4444",
      "type": "expense"
    },
    {
      "id": "e5f6a7b8-...",
      "name": "Salaire",
      "color": "#22c55e",
      "type": "income"
    }
  ]
}
```

---

### `POST /api/categories/`

Create a new category.

**Request body**
```json
{
  "name": "Transport",
  "color": "#eab308",
  "type": "expense"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Category display name |
| `color` | string | Yes | Hex color code, e.g. `#ef4444` |
| `type` | string | Yes | `"income"` or `"expense"` |

**Response** — `201 Created`

> Categories are read-only after creation (no PUT/DELETE endpoints). Update by recreating if needed.

<!-- END AUTO-GENERATED: categories -->

---

## Transactions

<!-- AUTO-GENERATED: transactions -->

### `GET /api/transactions/`

List transactions. Results are ordered by date descending by default.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `type` | string | `income` or `expense` |
| `start_date` | date | Transactions on or after `YYYY-MM-DD` |
| `end_date` | date | Transactions on or before `YYYY-MM-DD` |
| `account` | UUID | Filter by account ID |
| `category` | UUID | Filter by category ID |
| `search` | string | Full-text search on `label` |
| `ordering` | string | `date`, `-date`, `amount`, `-amount` |
| `page` | integer | Page number |

**Example requests**
```
GET /api/transactions/?type=expense&start_date=2024-01-01&end_date=2024-01-31
GET /api/transactions/?search=loyer&ordering=-amount
GET /api/transactions/?account=3f1e2b4c-...
```

**Response**
```json
{
  "count": 23,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "7c8d9e0f-...",
      "label": "Loyer Janvier",
      "amount": "-3200.00",
      "date": "2024-01-07",
      "type": "expense",
      "account": "3f1e2b4c-...",
      "account_name": "CIH Principale",
      "category": "a1b2c3d4-...",
      "category_detail": {
        "id": "a1b2c3d4-...",
        "name": "Logement",
        "color": "#ef4444",
        "type": "expense"
      },
      "created_at": "2024-01-07T08:30:00Z",
      "updated_at": "2024-01-07T08:30:00Z"
    }
  ]
}
```

---

### `POST /api/transactions/`

Create a new transaction.

**Request body**
```json
{
  "label": "Salaire Janvier",
  "amount": "8500.00",
  "date": "2024-01-05",
  "type": "income",
  "account": "3f1e2b4c-...",
  "category": "e5f6a7b8-..."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Transaction description |
| `amount` | decimal | Yes | Positive for income, **negative** for expense |
| `date` | date | Yes | `YYYY-MM-DD` |
| `type` | string | Yes | `"income"` or `"expense"` |
| `account` | UUID | Yes | Account ID |
| `category` | UUID | Yes | Category ID |

> **Validation rule:** `type` and `amount` sign must be consistent. An expense with a positive amount or an income with a negative amount will return `400 Bad Request`.

**Error response example**
```json
{
  "amount": ["Expense amount must be negative."]
}
```

**Response** — `201 Created` — same shape as list results above.

---

### `GET /api/transactions/{id}/`

Retrieve a single transaction by UUID.

---

### `PUT /api/transactions/{id}/`

Replace a transaction. All writable fields are required.

---

### `DELETE /api/transactions/{id}/`

Delete a transaction.

**Response** — `204 No Content`

<!-- END AUTO-GENERATED: transactions -->

---

## Goals

<!-- AUTO-GENERATED: goals -->

### `GET /api/goals/`

List all savings goals.

**Response**
```json
{
  "count": 2,
  "results": [
    {
      "id": "b1c2d3e4-...",
      "label": "Fonds d'urgence",
      "current": "3500.00",
      "target": "10000.00",
      "icon": "shield",
      "color": "#ef4444"
    }
  ]
}
```

---

### `POST /api/goals/`

Create a new goal.

**Request body**
```json
{
  "label": "Vacances Été 2025",
  "current": "1200.00",
  "target": "5000.00",
  "icon": "plane",
  "color": "#3b82f6"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Goal name |
| `current` | decimal | Yes | Amount saved so far |
| `target` | decimal | Yes | Target amount |
| `icon` | string | Yes | Icon identifier (e.g. `shield`, `plane`, `car`, `book`) |
| `color` | string | Yes | Hex color code |

---

### `PUT /api/goals/{id}/`

Update a goal (e.g. increment `current` as savings grow).

---

### `DELETE /api/goals/{id}/`

Delete a goal.

**Response** — `204 No Content`

<!-- END AUTO-GENERATED: goals -->

---

## Analytics

Analytics endpoints are not paginated — they always return a full list.

<!-- AUTO-GENERATED: analytics -->

### `GET /api/analytics/monthly-flow/`

Monthly income vs expenses summary across all transactions, ordered by month ascending.

**Response**
```json
[
  {
    "month": "2024-01",
    "income": "10500.00",
    "expenses": "4165.00"
  },
  {
    "month": "2024-02",
    "income": "9000.00",
    "expenses": "4330.00"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `month` | string | `YYYY-MM` format |
| `income` | decimal | Sum of all income transactions that month |
| `expenses` | decimal | Sum of absolute values of expense transactions that month (always positive) |

---

### `GET /api/analytics/category-split/`

Expense totals broken down by category. Only expense transactions are included. Ordered alphabetically by category name.

**Response**
```json
[
  {
    "name": "Alimentation",
    "value": "1950.00",
    "color": "#f97316"
  },
  {
    "name": "Logement",
    "value": "9600.00",
    "color": "#ef4444"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Category name |
| `value` | decimal | Total amount spent (always positive) |
| `color` | string | Category hex color for use in charts |

<!-- END AUTO-GENERATED: analytics -->

---

## Error Responses

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | Validation error — response body contains field-level errors |
| `404 Not Found` | Resource does not exist |
| `405 Method Not Allowed` | HTTP method not supported on this endpoint |

**Validation error shape**
```json
{
  "field_name": ["Error message."],
  "non_field_errors": ["Cross-field error message."]
}
```
