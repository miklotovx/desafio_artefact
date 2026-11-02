# Provides controlled product, order and policy queries for the customer-service agent.
"""Tools return source facts and explicit price calculations as JSON-compatible data."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from data_access import StoreData


HUMAN_ASSISTANCE = (
    "Não foi possível processar sua solicitação com as informações disponíveis. "
    "Você deseja receber atendimento humano?"
)


def _normalize(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text.casefold())
        if not unicodedata.combining(c)
    )


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _unavailable() -> dict:
    return {"status": "unavailable", "message": HUMAN_ASSISTANCE}


class StoreTools:
    """Read-only queries over a validated source snapshot."""

    def __init__(self, data: StoreData):
        self.data = data
        self.products = {p["product_id"]: p for p in data.tables["products"]}
        self.categories = {c["category_id"]: c["name"] for c in data.tables["categories"]}

    def _product(self, product: dict) -> dict:
        price = product["price_brl"]
        promotions = [
            p for p in self.data.tables["promotions"]
            if p["product_id"] == product["product_id"] and p["is_active"]
        ]
        # Multiple active discounts have no explicit precedence in the sources.
        ambiguous = len(promotions) > 1
        discount = promotions[0]["discount_percent"] if len(promotions) == 1 else Decimal(0)
        final_price = price * (1 - discount / 100)
        return {
            "product_id": product["product_id"], "name": product["name"],
            "category": self.categories[product["category_id"]],
            "description": product["description"], "specs": product["specs"].copy(),
            "stock_quantity": product["stock_quantity"], "catalog_status": product["status"],
            "available": product["status"] == "active" and product["stock_quantity"] > 0,
            "original_price_brl": _money(price),
            "current_price_brl": None if ambiguous else _money(final_price),
            "pix_price_brl": None if ambiguous else _money(
                final_price if promotions else price * Decimal("0.95")
            ),
            "active_promotions": [
                {"description": p["description"], "discount_percent": str(p["discount_percent"])}
                for p in promotions
            ],
            "price_status": "ambiguous" if ambiguous else "ok",
            "price_rule": "Promoções não acumulam entre si nem com os 5% de PIX (manual, 6.2).",
        }

    def search_products(
        self, query: str = "", category: str = "", max_price_brl: str = "",
        available_only: bool = True,
    ) -> dict:
        """Search products using name/model words and exact category name.

        Categories include Violões, Ukuleles, Guitarras, Baixos, Baterias e Percussão,
        Teclados e Pianos. max_price_brl uses decimal notation such as '1000.00'.
        The price ceiling uses the current promotional price, without a PIX assumption.
        Set available_only=False when checking a named product even if unavailable.
        """
        ceiling = None
        if max_price_brl:
            try:
                ceiling = Decimal(max_price_brl)
            except InvalidOperation:
                return _unavailable()
            if not ceiling.is_finite() or ceiling < 0:
                return _unavailable()
        words = _normalize(query).split()
        matches = []
        for product in self.products.values():
            if not all(word in _normalize(product["name"]) for word in words):
                continue
            if category and _normalize(category) != _normalize(self.categories[product["category_id"]]):
                continue
            item = self._product(product)
            if available_only and not item["available"]:
                continue
            if ceiling is not None:
                if item["current_price_brl"] is None:
                    return _unavailable()
                if Decimal(item["current_price_brl"]) > ceiling:
                    continue
            matches.append(item)
        matches.sort(key=lambda p: (Decimal(p["original_price_brl"] if p["current_price_brl"] is None else p["current_price_brl"]), p["product_id"]))
        return {
            "status": "ok" if matches else "not_found", "count": len(matches),
            "products": matches, "source": "products.csv, categories.csv, promotions.csv",
            "message": None if matches else HUMAN_ASSISTANCE,
        }

    def get_product(self, product_id: int) -> dict:
        """Return source details, stock and calculated prices for an exact product ID."""
        product = self.products.get(product_id)
        if product is None:
            return _unavailable()
        return {"status": "ok", "product": self._product(product),
                "source": "products.csv, categories.csv, promotions.csv; manual 3 and 6"}

    def get_order(self, order_id: int, customer_email: str) -> dict:
        """Consult an exact order ID after matching the customer's supplied email.

        Ask the customer for both fields; never infer them. This is a prototype
        ownership check, not authentication. Do not reveal customer contact data.
        """
        order = next((o for o in self.data.tables["orders"] if o["order_id"] == order_id), None)
        if order is None:
            return _unavailable()
        customer = next(c for c in self.data.tables["customers"] if c["customer_id"] == order["customer_id"])
        if not customer_email.strip() or customer["email"].strip().casefold() != customer_email.strip().casefold():
            return _unavailable()
        return {
            "status": "ok", "order_id": order_id, "order_status": order["status"],
            "order_date": order["order_date"].isoformat(), "total_brl": _money(order["total_brl"]),
            "payment_method": order["payment_method"], "tracking_code": order["tracking_code"],
            "estimated_delivery": order["estimated_delivery"].isoformat() if order["estimated_delivery"] else None,
            "notes": order["notes"],
            "items": [
                {"product_id": i["product_id"], "name": self.products[i["product_id"]]["name"], "quantity": i["quantity"]}
                for i in self.data.tables["order_items"] if i["order_id"] == order_id
            ],
            "limitations": "Não há data efetiva de entrega, canal da compra ou preços históricos dos itens. Previsão não comprova entrega. Rastreamento é o registro do CSV, sem consulta externa.",
            "source": "orders.csv, order_items.csv, products.csv; customers.csv for email matching",
        }

    def get_tracking(self, order_id: int, customer_email: str) -> dict:
        """Get an order's recorded tracking code using its ID and supplied email.

        Use this tool whenever the customer asks for tracking. A missing code
        returns unavailable; order confirmation is not evidence of shipment.
        """
        order = self.get_order(order_id, customer_email)
        if order["status"] != "ok" or not order["tracking_code"]:
            return _unavailable()
        return {
            "status": "ok", "order_id": order_id,
            "tracking_code": order["tracking_code"],
            "order_status": order["order_status"], "source": "orders.csv",
        }

    def get_policies(self, topic: str = "todas") -> dict:
        """Return complete manual sections, including exceptions, without semantic search.

        Topics: loja, horarios, pagamento, parcelamento, devolucao, troca, frete,
        entrega, promocao, desconto, atendimento, garantia, privacidade, todas.
        """
        topics = {
            "loja": {1, 7}, "horarios": {2}, "pagamento": {3, 6},
            "parcelamento": {3}, "devolucao": {4, 8}, "troca": {4, 8},
            "frete": {5}, "entrega": {5}, "promocao": {3, 6}, "desconto": {3, 6},
            "atendimento": {7}, "garantia": {4, 8}, "privacidade": {9},
            "todas": set(range(1, 11)),
        }
        selected = topics.get(_normalize(topic))
        if selected is None:
            return _unavailable()
        sections = [
            match.group(0).strip()
            for match in re.finditer(r"^## (\d+)\..*?(?=^## \d+\.|\Z)", self.data.policies, re.M | re.S)
            if int(match.group(1)) in selected
        ]
        if not sections:
            return _unavailable()
        return {"status": "ok", "text": "\n\n".join(sections),
                "source": "políticas_da_loja.md (manual version 2.1)",
                "instruction": "Não resolver lacunas ou contradições por suposição. Quando impedirem a resposta, oferecer atendimento humano."}
