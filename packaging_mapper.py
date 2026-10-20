"""Command-line version: python packaging_mapper.py sample_data/client_packaging_export.csv [client]"""
import json
import sys
from pathlib import Path

from mapper.core import load_config, process_csv_text


def run(csv_path: str, client: str = "default", out_dir: str = "output"):
    out = Path(out_dir)
    out.mkdir(exist_ok=True)
    text = Path(csv_path).read_text(encoding="utf-8-sig")
    products, rejected = process_csv_text(text, load_config(client))
    (out / "clean_packaging.json").write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "rejected_rows.json").write_text(json.dumps(rejected, indent=2, ensure_ascii=False), encoding="utf-8")
    n_clean = sum(len(p["components"]) for p in products)
    print(f"Rows read:      {n_clean + len(rejected)}")
    print(f"Rows mapped:    {n_clean}  ->  {len(products)} products in {out / 'clean_packaging.json'}")
    print(f"Rows rejected:  {len(rejected)}  ->  see {out / 'rejected_rows.json'}")
    for r in rejected:
        print(f"  line {r['line']}: {r['reason']}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "sample_data/client_packaging_export.csv",
        sys.argv[2] if len(sys.argv) > 2 else "default")
