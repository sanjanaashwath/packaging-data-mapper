"""Tests for the mapping logic (no web server needed). Run: python -m pytest"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mapper.core import load_config, parse_weight_grams, process_csv_text  # noqa: E402

CFG = load_config("default")
HEADER = "Artikelnr;Product Name;Packaging Component;Material Type;Weight;Recyclable?;Country;Supplier\n"


class TestParsing(unittest.TestCase):
    def test_weights(self):
        self.assertEqual(parse_weight_grams("24 g"), 24.0)
        self.assertEqual(parse_weight_grams("3,5g"), 3.5)
        self.assertEqual(parse_weight_grams("0.032 kg"), 32.0)

    def test_invalid_weight(self):
        with self.assertRaises(ValueError):
            parse_weight_grams("abc")


class TestProcessing(unittest.TestCase):
    def test_sample_file(self):
        text = (ROOT / "sample_data" / "client_packaging_export.csv").read_text(encoding="utf-8")
        products, rejected = process_csv_text(text, CFG)
        self.assertEqual(len(products), 4)
        self.assertEqual(len(rejected), 5)
        reasons = {r["reason"] for r in rejected}
        self.assertIn("missing SKU", reasons)
        self.assertIn("duplicate row", reasons)

    def test_values_are_normalised(self):
        text = HEADER + " sku-1 ;Gel;Cap;pp;3,5g;Ja;deutschland;X\n"
        products, rejected = process_csv_text(text, CFG)
        self.assertEqual(rejected, [])
        p = products[0]
        self.assertEqual(p["sku"], "SKU-1")
        self.assertEqual(p["country"], "DE")
        self.assertEqual(p["components"][0]["material"], "PP")
        self.assertTrue(p["components"][0]["recyclable"])

    def test_unknown_client_config(self):
        with self.assertRaises(FileNotFoundError):
            load_config("does-not-exist")


if __name__ == "__main__":
    unittest.main()
