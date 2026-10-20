# Packaging Data Mapper API

**A small FastAPI service that takes in messy packaging exports from partner systems and returns clean, validated product data, plus a clear list of every row it could not accept and why.**

Every partner exports data differently: other column names, weights in g or kg, "Ja" instead of "yes", "Deutschland" instead of "DE", missing values and duplicates. This service makes getting that data into a platform easy and traceable.

## Endpoints

| Method | Path | What it does |
|---|---|---|
| `POST` | `/ingest?client=default` | Upload a CSV export → clean products (JSON) + rejected rows with reasons |
| `GET` | `/health` | Liveness check for monitoring |
| `GET` | `/docs` | Auto-generated Swagger/OpenAPI documentation |

Example response (shortened):

```json
{
  "client": "default",
  "rows_received": 12,
  "products": [
    {"sku": "SKU-1001", "product_name": "Shower Gel 250ml", "country": "DE",
     "components": [
       {"component": "bottle", "material": "PET", "weight_g": 24.0, "recyclable": true, "supplier": "Plastico GmbH"},
       {"component": "cap", "material": "PP", "weight_g": 3.5, "recyclable": true, "supplier": "Plastico GmbH"}],
     "total_packaging_weight_g": 27.5}
  ],
  "rejected": [
    {"line": 9, "reason": "recyclable value 'maybe' is not yes/no", "raw": {"...": "..."}}
  ]
}
```

## What it handles

| Problem in the partner file | How it is handled |
|---|---|
| Different column names per partner | Mapped via `configs/<client>.json`, so a new partner needs no code changes |
| `24 g`, `3,5g`, `0.032 kg` | Converted to grams |
| `yes`, `Y`, `Ja`, `true` | Converted to `true` / `false` |
| `DE`, `Germany`, `deutschland` | Converted to ISO country codes |
| `;` or `,` as separator | Detected automatically |
| Duplicates, missing or invalid values | **Never silently dropped**: returned in `rejected` with the line number and reason |

The response is validated with **pydantic** models (`mapper/models.py`), so the API never returns malformed data. Every request is logged with client, row counts and processing time, for monitoring.

## Run it

```bash
pip install -r requirements.txt
uvicorn app:app --reload          # then open http://localhost:8000/docs
python -m pytest -v               # core + API tests
```

With Docker:

```bash
docker build -t packaging-mapper .
docker run -p 8000:8000 packaging-mapper
```

Command-line version (no server):

```bash
python packaging_mapper.py sample_data/client_packaging_export.csv
```

## Project structure

```
app.py                 FastAPI app (endpoints, error handling, logging)
mapper/core.py         mapping and validation logic
mapper/models.py       pydantic response schemas
configs/default.json   partner-specific mapping (copy it for a new partner)
tests/                 pytest tests for the core logic and the API
Dockerfile             container image with health check
.github/workflows/     CI: runs all tests on every push
```

## Next ideas
- Store accepted records in PostgreSQL
- Accept JSON and Excel uploads as well as CSV
- Alert when a partner's error rate suddenly rises (an upstream format change)

*All sample data is fictional.* · Author: Sanjana Aswathaiah
