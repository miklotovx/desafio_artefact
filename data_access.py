# Loads and validates the supplied CSV tables and store policy text for the agent.
"""Source access only; customer queries and business calculations belong in tools.py."""

import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_PREFIX = "desafio_tecnico_ai_eng - "

# Types are explicit so identifiers, money and dates never depend on inference.
SCHEMAS = {
    "categories": {"category_id": int, "name": str, "description": str},
    "customers": {
        "customer_id": int, "name": str, "phone": str, "email": str, "city": str,
    },
    "products": {
        "product_id": int, "price_brl": Decimal, "name": str, "category_id": int,
        "description": str, "stock_quantity": int, "status": str,
        "specs": json.loads, "created_at": date.fromisoformat,
    },
    "orders": {
        "order_id": int, "customer_id": int, "order_date": date.fromisoformat,
        "status": str, "total_brl": Decimal, "payment_method": str,
        "tracking_code": str, "estimated_delivery": date.fromisoformat, "notes": str,
    },
    "order_items": {"order_id": int, "quantity": int, "product_id": int},
    "promotions": {
        "promotion_id": int, "product_id": int, "discount_percent": Decimal,
        "description": str, "is_active": str,
    },
}
OPTIONAL_FIELDS = {"orders": {"tracking_code", "estimated_delivery", "notes"}}
PRIMARY_KEYS = {
    "categories": "category_id", "customers": "customer_id",
    "products": "product_id", "orders": "order_id", "promotions": "promotion_id",
}
RELATIONS = (
    ("products", "category_id", "categories"),
    ("orders", "customer_id", "customers"),
    ("order_items", "order_id", "orders"),
    ("order_items", "product_id", "products"),
    ("promotions", "product_id", "products"),
)


class DataValidationError(ValueError):
    """A supplied source is missing, malformed or structurally inconsistent."""


@dataclass
class StoreData:
    tables: dict[str, list[dict]]
    policies: str


def _read_table(data_dir: Path, name: str) -> list[dict]:
    path = data_dir / f"{CSV_PREFIX}{name}.csv"
    schema = SCHEMAS[name]
    rows = []
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source, strict=True)
            if reader.fieldnames != list(schema):
                raise DataValidationError(f"{path.name}: unexpected CSV columns.")
            for line, raw in enumerate(reader, start=2):
                if None in raw or any(value is None for value in raw.values()):
                    raise DataValidationError(f"{path.name}, row {line}: invalid column count.")
                row = {}
                for field, convert in schema.items():
                    value = raw[field]
                    if not value.strip():
                        if field in OPTIONAL_FIELDS.get(name, set()):
                            row[field] = None
                            continue
                        raise DataValidationError(f"{path.name}, row {line}: empty {field}.")
                    try:
                        row[field] = convert(value)
                    except (ValueError, ArithmeticError) as exc:
                        raise DataValidationError(
                            f"{path.name}, row {line}: invalid {field}."
                        ) from exc
                _validate_record(name, row, line)
                rows.append(row)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataValidationError(f"Could not read {path.name}.") from exc
    if not rows:
        raise DataValidationError(f"{path.name}: no records.")
    return rows


def _validate_record(name: str, row: dict, line: int) -> None:
    def fail(field: str) -> None:
        raise DataValidationError(f"{name}, row {line}: invalid {field}.")

    for field, value in row.items():
        if field.endswith("_id") and value <= 0:
            fail(field)
        if isinstance(value, Decimal) and (not value.is_finite() or value < 0):
            fail(field)
    if name == "products":
        if row["stock_quantity"] < 0:
            fail("stock_quantity")
        if not isinstance(row["specs"], dict):
            fail("specs")
        if row["status"] not in {"active", "discontinued", "coming_soon"}:
            fail("status")
    if name == "orders" and row["status"] not in {
        "pending", "confirmed", "shipped", "delivered", "cancelled",
    }:
        fail("status")
    if name == "order_items" and row["quantity"] <= 0:
        fail("quantity")
    if name == "promotions":
        if row["discount_percent"] > 100:
            fail("discount_percent")
        if row["is_active"] not in {"0", "1"}:
            fail("is_active")
        row["is_active"] = row["is_active"] == "1"


def load_data(data_dir: Path = DATA_DIR) -> StoreData:
    """Load a source snapshot without altering files or resolving business ambiguities."""
    data_dir = Path(data_dir)
    tables = {name: _read_table(data_dir, name) for name in SCHEMAS}
    identifiers = {}
    for name, key in PRIMARY_KEYS.items():
        identifiers[name] = {row[key] for row in tables[name]}
        if len(identifiers[name]) != len(tables[name]):
            raise DataValidationError(f"{name}: duplicate {key}.")
    for table, field, target in RELATIONS:
        if any(row[field] not in identifiers[target] for row in tables[table]):
            raise DataValidationError(f"{table}: {field} references a missing {target} record.")
    try:
        policies = (data_dir / "políticas_da_loja.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise DataValidationError("Could not read políticas_da_loja.md.") from exc
    if not policies.strip():
        raise DataValidationError("The policy manual is empty.")
    return StoreData(tables=tables, policies=policies)
