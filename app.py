"""
Packaging Data Mapper API
-------------------------
POST /ingest   upload a partner CSV export -> clean, validated JSON + list of rejected rows
GET  /health   liveness check for monitoring
Docs:          http://localhost:8000/docs  (auto-generated Swagger/OpenAPI)

Run:  uvicorn app:app --reload
"""
import logging
import time

from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from mapper.core import load_config, process_csv_text
from mapper.models import IngestResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("packaging-mapper")

app = FastAPI(title="Packaging Data Mapper", version="2.0",
              description="Turns messy partner packaging exports into clean, validated product data.")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...), client: str = Query("default", description="partner mapping config")):
    started = time.perf_counter()
    try:
        config = load_config(client)
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err))

    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded CSV")
    if not text.strip():
        raise HTTPException(status_code=400, detail="File is empty")

    products, rejected = process_csv_text(text, config)
    rows = sum(len(p["components"]) for p in products) + len(rejected)
    log.info("client=%s file=%s rows=%d products=%d rejected=%d took=%.0fms",
             client, file.filename, rows, len(products), len(rejected), (time.perf_counter() - started) * 1000)
    return {"client": client, "rows_received": rows, "products": products, "rejected": rejected}
