# Appointment Search Implementation (TASK-001)

## Runtime status

This Python API is now a legacy compatibility runtime for local testing only.

- Single production backend runtime: .NET API at src/PropelIQ.Api
- Python runtime requires explicit opt-in via PROPELLQ_ENABLE_LEGACY_PYTHON=true

## Run locally

1. Start server:

```bash
python server.py
```

2. Open browser:

- http://127.0.0.1:8000

## API Endpoints

- `GET /api/appointments/search`
- `GET /api/appointments/specialties`
- `GET /api/providers/suggest?query=`
- `GET /api/providers/{id}`
- `POST /api/appointments/{id}/book`

## Supported search query params

- `dateFrom` (YYYY-MM-DD)
- `dateTo` (YYYY-MM-DD)
- `timeOfDay` (`morning` | `afternoon` | `evening`)
- `provider` (contains match)
- `specialty` (must match active specialty)
- `page` (>=1)
- `pageSize` (1..50)
- `sortBy` (`date` | `provider`)
- `sortDir` (`asc` | `desc`)

## Testing

```bash
python -m unittest tests/test_search.py -v
```

## DB

Schema and index definitions are in `db/schema.sql`.
