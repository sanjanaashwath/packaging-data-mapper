"""Core mapping logic: turns messy partner rows into clean, validated product records."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"


def load_config(client: str = "default") -> dict:
    """Each partner has its own mapping file in configs/<client>.json - no code changes needed."""
    path = CONFIG_DIR / f"{client}.json"
    if not path.exists():
        raise FileNotFoundError(f"No mapping config for client '{client}'")
    return json.loads(path.read_text(encoding="utf-8"))


def clean_text(value) -> str:
    return (value or "").strip()


def parse_weight_grams(raw) -> float:
    """'24 g' -> 24.0, '3,5g' -> 3.5, '0.032 kg' -> 32.0"""
    text = clean_text(raw).lower().replace(",", ".")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(g|kg)?", text)
    if not match:
        raise ValueError(f"weight '{raw}' is not a valid number")
    number, unit = float(match.group(1)), match.group(2) or "g"
    return round(number * 1000 if unit == "kg" else number, 2)


def parse_bool(raw, config: dict) -> bool:
    text = clean_text(raw).lower()
    if text in config["boolean_true"]:
        return True
    if text in config["boolean_false"]:
        return False
    raise ValueError(f"recyclable value '{raw}' is not yes/no")


def map_lookup(raw, table: dict, field: str) -> str:
    key = clean_text(raw).lower()
    if key not in table:
        raise ValueError(f"unknown {field} '{raw}'")
    return table[key]


def map_row(row: dict, config: dict) -> dict:
    """Rename columns and convert every value into the platform format."""
    r = {target: clean_text(row.get(source)) for source, target in config["columns"].items()}
    if not r["sku"]:
        raise ValueError("missing SKU")
    if not r["weight"]:
        raise ValueError("missing weight")
    return {
        "sku": r["sku"].upper(),
        "product_name": r["product_name"],
        "component": r["component"].lower(),
        "material": map_lookup(r["material"], config["materials"], "material"),
        "weight_g": parse_weight_grams(r["weight"]),
        "recyclable": parse_bool(r["recyclable"], config),
        "country": map_lookup(r["country"], config["countries"], "country"),
        "supplier": r["supplier"] or None,
    }


def group_by_product(records: list[dict]) -> list[dict]:
    """Turn flat component rows into one object per product, like an API payload."""
    products: dict[str, dict] = {}
    for rec in records:
        p = products.setdefault(rec["sku"], {"sku": rec["sku"], "product_name": rec["product_name"],
                                             "country": rec["country"], "components": []})
        p["components"].append({k: rec[k] for k in ("component", "material", "weight_g", "recyclable", "supplier")})
    for p in products.values():
        p["total_packaging_weight_g"] = round(sum(c["weight_g"] for c in p["components"]), 2)
    return list(products.values())


def process_csv_text(text: str, config: dict) -> tuple[list[dict], list[dict]]:
    """Map a whole CSV export. Returns (products, rejected_rows). Bad rows are never silently dropped."""
    sample = text[:2048]
    dialect = csv.Sniffer().sniff(sample, delimiters=";,")
    clean, rejected, seen = [], [], set()
    for line_no, row in enumerate(csv.DictReader(io.StringIO(text), dialect=dialect), start=2):
        try:
            rec = map_row(row, config)
        except ValueError as err:
            rejected.append({"line": line_no, "reason": str(err), "raw": row})
            continue
        key = (rec["sku"], rec["component"], rec["material"])
        if key in seen:
            rejected.append({"line": line_no, "reason": "duplicate row", "raw": row})
            continue
        seen.add(key)
        clean.append(rec)
    return group_by_product(clean), rejected
