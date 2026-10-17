# Packaging Data Mapper

A small Python tool that takes a **messy packaging export from a client system** and turns it into **clean, validated JSON** that a sustainability platform's API could accept.

Every client exports data differently: other column names, weights in g or kg, "Ja" instead of "yes", "Deutschland" instead of "DE", missing values and duplicates. This project shows how I handle that in a clear, configurable and traceable way.

## What it does

| Problem in the client file | How it is handled |
|---|---|
| Different column names (`Artikelnr`, `Material Type`) | Mapped to platform fields via `mapping.json`, with no code changes per client |
| Weights like `24 g`, `3,5g`, `0.032 kg` | Converted to grams (`weight_g`) |
| `yes`, `Y`, `Ja`, `true` | Converted to `true` / `false` |
| `DE`, `Germany`, `deutschland` | Converted to ISO country codes |
| `pp`, `Polypropylene` | Unified to one material code (`PP`) |
| Extra spaces, mixed case | Cleaned |
| Duplicate rows | Removed and reported |
| Missing or invalid values | **Not silently dropped**: written to `rejected_rows.json` with a reason |

The clean rows are grouped into one object per product, including the total packaging weight, like a typical API payload.

## How to run

Requires Python 3.8+ and no extra libraries.

```bash
python packaging_mapper.py sample_data/client_packaging_export.csv
```

Output:

```
Rows read:      12
Rows mapped:    7  ->  4 products in output/clean_packaging.json
Rows rejected:  5  ->  see output/rejected_rows.json
  line 8: missing weight
  line 9: recyclable value 'maybe' is not yes/no
  line 11: missing SKU
  line 12: duplicate row
  line 13: weight 'abc' is not a valid number
```

## Example

**Input (messy CSV):**
```
  SKU-1001 ;Shower Gel 250ml;Bottle;PET;24 g;yes;DE;Plastico GmbH
SKU-1001;Shower Gel 250ml;Cap;pp;3,5g;Y;Germany;Plastico GmbH
```

**Output (clean JSON):**
```json
{
  "sku": "SKU-1001",
  "product_name": "Shower Gel 250ml",
  "country": "DE",
  "components": [
    {"component": "bottle", "material": "PET", "weight_g": 24.0, "recyclable": true, "supplier": "Plastico GmbH"},
    {"component": "cap", "material": "PP", "weight_g": 3.5, "recyclable": true, "supplier": "Plastico GmbH"}
  ],
  "total_packaging_weight_g": 27.5
}
```

## Adding a new client

Copy `mapping.json`, change the column names and value lists to match the new client's export, and run the script. The rejected-rows report then shows exactly which records need clarification with the customer.

## Files

- `packaging_mapper.py`: the mapping and validation logic
- `mapping.json`: client-specific configuration
- `sample_data/client_packaging_export.csv`: example messy export (fictional data)
- `output/`: example results

Author: Sanjana Aswathaiah
