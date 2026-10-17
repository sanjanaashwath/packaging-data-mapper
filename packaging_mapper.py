"""
Packaging Data Mapper
---------------------
Takes a messy packaging export from a client system (CSV) and maps it into
clean, validated JSON that a sustainability platform API could accept.

What it handles:
- different column names per client (configured in mapping.json)
- extra spaces, mixed upper/lower case
- weights in g or kg, with comma or dot decimals ("3,5g", "0.032 kg")
- many ways to write yes/no ("Ja", "Y", "true") and country names
- duplicate rows
- invalid rows: they are not silently dropped, but reported with a reason

Usage:
    python packaging_mapper.py sample_data/client_packaging_export.csv
"""

import csv
import json
import re
import sys
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name("mapping.json").read_text(encoding="utf-8"))


def clean_text(value):
    return (value or "").strip()


def parse_weight_grams(raw):
    """'24 g' -> 24.0, '3,5g' -> 3.5, '0.032 kg' -> 32.0"""
    text = clean_text(raw).lower().replace(",", ".")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(g|kg)?", text)
    if not match:
        raise ValueError(f"weight '{raw}' is not a valid number")
    number, unit = float(match.group(1)), match.group(2) or "g"
    return round(number * 1000 if unit == "kg" else number, 2)


def parse_bool(raw):
    text = clean_text(raw).lower()
    if text in CONFIG["boolean_true"]:
        return True
    if text in CONFIG["boolean_false"]:
        return False
    raise ValueError(f"recyclable value '{raw}' is not yes/no")


def map_lookup(raw, table, field):
    key = clean_text(raw).lower()
    if key not in table:
        raise ValueError(f"unknown {field} '{raw}'")
    return table[key]


def map_row(row):
    """Rename columns and convert every value into the platform format."""
    r = {target: clean_text(row.get(source)) for source, target in CONFIG["columns"].items()}
    if not r["sku"]:
        raise ValueError("missing SKU")
    if not r["weight"]:
        raise ValueError("missing weight")
    return {
        "sku": r["sku"].upper(),
        "product_name": r["product_name"],
        "component": r["component"].lower(),
        "material": map_lookup(r["material"], CONFIG["materials"], "material"),
        "weight_g": parse_weight_grams(r["weight"]),
        "recyclable": parse_bool(r["recyclable"]),
        "country": map_lookup(r["country"], CONFIG["countries"], "country"),
        "supplier": r["supplier"] or None,
    }


def group_by_product(records):
    """Turn flat component rows into one object per product, like an API payload."""
    products = {}
    for rec in records:
        p = products.setdefault(rec["sku"], {
            "sku": rec["sku"],
            "product_name": rec["product_name"],
            "country": rec["country"],
            "components": [],
        })
        p["components"].append({k: rec[k] for k in ("component", "material", "weight_g", "recyclable", "supplier")})
    for p in products.values():
        p["total_packaging_weight_g"] = round(sum(c["weight_g"] for c in p["components"]), 2)
    return list(products.values())


def run(csv_path, out_dir="output"):
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    clean, rejected, seen = [], [], set()

    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        for line_no, row in enumerate(csv.DictReader(f, dialect=dialect), start=2):
            try:
                rec = map_row(row)
            except ValueError as err:
                rejected.append({"line": line_no, "reason": str(err), "raw": row})
                continue
            key = (rec["sku"], rec["component"], rec["material"])
            if key in seen:
                rejected.append({"line": line_no, "reason": "duplicate row", "raw": row})
                continue
            seen.add(key)
            clean.append(rec)

    products = group_by_product(clean)
    (out / "clean_packaging.json").write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "rejected_rows.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Rows read:      {len(clean) + len(rejected)}")
    print(f"Rows mapped:    {len(clean)}  ->  {len(products)} products in {out / 'clean_packaging.json'}")
    print(f"Rows rejected:  {len(rejected)}  ->  see {out / 'rejected_rows.json'}")
    for r in rejected:
        print(f"  line {r['line']}: {r['reason']}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sample_data/client_packaging_export.csv")
