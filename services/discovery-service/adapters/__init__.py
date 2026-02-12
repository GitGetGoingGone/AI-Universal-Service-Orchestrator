"""Legacy and format adapters for Module 2 (Legacy Adapter Layer)."""

from .legacy_adapter import (
    parse_csv_to_products,
    parse_json_to_products,
    parse_excel_to_products,
    normalize_legacy_product,
    DEFAULT_COLUMN_MAP,
)

__all__ = [
    "parse_csv_to_products",
    "parse_json_to_products",
    "parse_excel_to_products",
    "normalize_legacy_product",
    "DEFAULT_COLUMN_MAP",
]
