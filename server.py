"""Shopify Store Ops MCP server.

Personal portfolio project, independent of any employer.

Two modes, always labelled in every tool result:
- SAMPLE (default): a small built-in demo store — handmade candles and
  home goods, 8 products, 6 orders. Clearly labelled SAMPLE in every
  response. Nothing here is a real store, a real customer, or real
  revenue. Use it to demo the tools and the Claude Desktop flow.
- LIVE: a real Shopify store, via the Shopify Admin REST API
  (api_version 2025-01), when BOTH env vars are set:
    SHOPIFY_STORE_DOMAIN = e.g. my-store.myshopify.com
    SHOPIFY_ADMIN_ACCESS_TOKEN = a custom-app Admin API access token
  with read_products, read_orders, read_inventory scopes.
  The token lives only in the local Claude Desktop config env (or a
  private file on the PC, like the Yelp key) — never in chat, never
  in the repo, never in a screenshot.

Honest limits, stated in every tool that needs them:
- This server is READ-ONLY. It never creates/updates products,
  never changes inventory, never creates discounts or orders.
  Writes need Shopify Admin (or a separate write tool, with the
  merchant's explicit approval each time).
- Sample-mode numbers are demo numbers. Do not quote them as a
  real store's sales.
- Live-mode product/order data is whatever Shopify returns at
  call time; prices are in the store's currency, inventory is
  per-variant, and an order's status is Shopify's status, not a
  carrier's delivery guarantee.
- No payment, checkout, or customer PII beyond what Shopify
  returns for an order (name/email are returned only in live
  mode, only for that order, and are not stored by this server).
"""
import os
from datetime import datetime, timezone

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("shopify-store-ops")

API_VERSION = "2025-01"
STORE_DOMAIN = os.environ.get("SHOPIFY_STORE_DOMAIN", "").strip()
ACCESS_TOKEN = os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "").strip()
LIVE = bool(STORE_DOMAIN and ACCESS_TOKEN)

# This VM's egress proxy does TLS interception with a CA that lives in
# the system bundle but not in certifi's. Use the system bundle, and
# pass the proxy explicitly: httpx chokes parsing this shell's
# no_proxy list. (Same pattern as the Transit + Restaurants servers.)
_SYSTEM_CA = "/etc/ssl/certs/ca-certificates.crt"


def _client() -> httpx.Client:
    headers = {"User-Agent": "ShopifyStoreOpsMCP/1.0 (portfolio project)"}
    if LIVE:
        headers["X-Shopify-Access-Token"] = ACCESS_TOKEN
    return httpx.Client(
        proxy=os.environ.get("https_proxy") or os.environ.get("HTTPS_PROXY"),
        trust_env=False,
        verify=_SYSTEM_CA if os.path.exists(_SYSTEM_CA) else True,
        headers=headers,
        timeout=20,
    )


def _live_get(path: str, params: dict | None = None) -> dict:
    url = f"https://{STORE_DOMAIN}/admin/api/{API_VERSION}/{path}"
    try:
        with _client() as client:
            r = client.get(url, params=params or {})
    except Exception as e:
        return {"error": f"Shopify request failed: {e}"}
    if r.status_code == 401:
        return {"error": "Shopify returned 401 — check SHOPIFY_ADMIN_ACCESS_TOKEN and its read scopes."}
    if r.status_code == 404:
        return {"error": f"Shopify returned 404 for {path} — check SHOPIFY_STORE_DOMAIN."}
    if r.status_code == 429:
        return {"error": "Shopify rate limit (HTTP 429). Wait a minute and retry."}
    if r.status_code != 200:
        return {"error": f"Shopify returned HTTP {r.status_code} for {path}"}
    try:
        return r.json()
    except Exception:
        return {"error": "Shopify returned a response that was not JSON."}


# ---------------------------------------------------------------- sample store
# Demo data only. Prices in USD. Inventory is per-variant.
SAMPLE_PRODUCTS = [
    {"id": 101, "title": "Lavender Soy Candle — 8 oz", "vendor": "Willow & Wick",
     "product_type": "Candle", "status": "active", "price": 24.00, "currency": "USD",
     "inventory": 42, "sku": "WW-LAV-8", "tags": ["candle", "lavender", "soy"]},
    {"id": 102, "title": "Cedarwood Soy Candle — 8 oz", "vendor": "Willow & Wick",
     "product_type": "Candle", "status": "active", "price": 24.00, "currency": "USD",
     "inventory": 3, "sku": "WW-CED-8", "tags": ["candle", "cedarwood", "soy"]},
    {"id": 103, "title": "Vanilla Bean Soy Candle — 12 oz", "vendor": "Willow & Wick",
     "product_type": "Candle", "status": "active", "price": 32.00, "currency": "USD",
     "inventory": 18, "sku": "WW-VAN-12", "tags": ["candle", "vanilla", "soy"]},
    {"id": 104, "title": "Ceramic Pour-Over Coffee Set", "vendor": "Willow & Wick",
     "product_type": "Home goods", "status": "active", "price": 58.00, "currency": "USD",
     "inventory": 7, "sku": "WW-POUR-1", "tags": ["coffee", "ceramic", "kitchen"]},
    {"id": 105, "title": "Handmade Stoneware Mug — Speckled", "vendor": "Willow & Wick",
     "product_type": "Home goods", "status": "active", "price": 28.00, "currency": "USD",
     "inventory": 0, "sku": "WW-MUG-SP", "tags": ["mug", "stoneware", "ceramic"]},
    {"id": 106, "title": "Eucalyptus Shower Steamer — Pack of 6", "vendor": "Willow & Wick",
     "product_type": "Bath", "status": "active", "price": 18.00, "currency": "USD",
     "inventory": 56, "sku": "WW-EUC-6", "tags": ["bath", "eucalyptus", "steamer"]},
    {"id": 107, "title": "Linen Throw Blanket — Natural", "vendor": "Willow & Wick",
     "product_type": "Home goods", "status": "draft", "price": 89.00, "currency": "USD",
     "inventory": 12, "sku": "WW-LIN-NAT", "tags": ["linen", "blanket", "throw"]},
    {"id": 108, "title": "Citrus Grove Reed Diffuser", "vendor": "Willow & Wick",
     "product_type": "Home goods", "status": "active", "price": 26.00, "currency": "USD",
     "inventory": 2, "sku": "WW-CIT-DIF", "tags": ["diffuser", "citrus", "home"]},
]

# quantity_sold is demo history, used only for top_selling_products.
SAMPLE_SOLD = {101: 214, 103: 187, 106: 163, 104: 92, 108: 71, 102: 58, 105: 44, 107: 0}

SAMPLE_ORDERS = [
    {"id": 9001, "order_number": 1042, "name": "#1042", "created_at": "2026-11-14T10:24:00-08:00",
     "customer": "Sample Customer A", "financial_status": "paid", "fulfillment_status": "fulfilled",
     "total_price": 72.00, "currency": "USD",
     "line_items": [{"title": "Lavender Soy Candle — 8 oz", "quantity": 2, "price": 24.00},
                    {"title": "Vanilla Bean Soy Candle — 12 oz", "quantity": 1, "price": 32.00}]},
    {"id": 9002, "order_number": 1043, "name": "#1043", "created_at": "2026-11-14T15:41:00-08:00",
     "customer": "Sample Customer B", "financial_status": "paid", "fulfillment_status": "unfulfilled",
     "total_price": 58.00, "currency": "USD",
     "line_items": [{"title": "Ceramic Pour-Over Coffee Set", "quantity": 1, "price": 58.00}]},
    {"id": 9003, "order_number": 1044, "name": "#1044", "created_at": "2026-11-13T09:12:00-08:00",
     "customer": "Sample Customer C", "financial_status": "paid", "fulfillment_status": "fulfilled",
     "total_price": 48.00, "currency": "USD",
     "line_items": [{"title": "Lavender Soy Candle — 8 oz", "quantity": 2, "price": 24.00}]},
    {"id": 9004, "order_number": 1045, "name": "#1045", "created_at": "2026-11-13T18:03:00-08:00",
     "customer": "Sample Customer D", "financial_status": "pending", "fulfillment_status": "unfulfilled",
     "total_price": 26.00, "currency": "USD",
     "line_items": [{"title": "Citrus Grove Reed Diffuser", "quantity": 1, "price": 26.00}]},
    {"id": 9005, "order_number": 1046, "name": "#1046", "created_at": "2026-11-12T11:37:00-08:00",
     "customer": "Sample Customer E", "financial_status": "paid", "fulfillment_status": "fulfilled",
     "total_price": 54.00, "currency": "USD",
     "line_items": [{"title": "Eucalyptus Shower Steamer — Pack of 6", "quantity": 3, "price": 18.00}]},
    {"id": 9006, "order_number": 1047, "name": "#1047", "created_at": "2026-11-12T16:20:00-08:00",
     "customer": "Sample Customer F", "financial_status": "refunded", "fulfillment_status": "fulfilled",
     "total_price": 24.00, "currency": "USD",
     "line_items": [{"title": "Cedarwood Soy Candle — 8 oz", "quantity": 1, "price": 24.00}]},
]

SAMPLE_NOTE = ("SAMPLE MODE — demo store 'Willow & Wick' (handmade candles / "
               "home goods). Not a real store, customer, or sale. Set "
               "SHOPIFY_STORE_DOMAIN + SHOPIFY_ADMIN_ACCESS_TOKEN to use a "
               "real Shopify store instead.")
LIVE_NOTE = "LIVE MODE — data from the connected Shopify store, as returned by Shopify at call time."


def _mode() -> dict:
    return {"mode": "live" if LIVE else "sample",
            "store": STORE_DOMAIN if LIVE else "Willow & Wick (sample)",
            "note": LIVE_NOTE if LIVE else SAMPLE_NOTE}


def _live_products() -> list:
    data = _live_get("products.json", {"limit": 250})
    if "error" in data:
        return data
    out = []
    for p in data.get("products") or []:
        variants = p.get("variants") or []
        out.append({
            "id": p.get("id"), "title": p.get("title"), "vendor": p.get("vendor"),
            "product_type": p.get("product_type"), "status": p.get("status"),
            "price": float(variants[0].get("price")) if variants and variants[0].get("price") else None,
            "currency": None,
            "inventory": sum(int(v.get("inventory_quantity") or 0) for v in variants),
            "sku": variants[0].get("sku") if variants else None,
            "tags": (p.get("tags") or "").split(", ") if p.get("tags") else [],
        })
    return out


def _live_orders(limit: int = 10) -> list:
    data = _live_get("orders.json", {"status": "any", "limit": max(1, min(limit, 50))})
    if "error" in data:
        return data
    out = []
    for o in data.get("orders") or []:
        out.append({
            "id": o.get("id"), "order_number": o.get("order_number"), "name": o.get("name"),
            "created_at": o.get("created_at"),
            "customer": ((o.get("customer") or {}).get("first_name") or "") + " " + ((o.get("customer") or {}).get("last_name") or ""),
            "financial_status": o.get("financial_status"),
            "fulfillment_status": o.get("fulfillment_status"),
            "total_price": float(o.get("total_price")) if o.get("total_price") else None,
            "currency": o.get("currency"),
            "line_items": [{"title": li.get("title"), "quantity": li.get("quantity"),
                            "price": float(li.get("price")) if li.get("price") else None}
                           for li in o.get("line_items") or []],
        })
    return out


def _products() -> list | dict:
    return _live_products() if LIVE else list(SAMPLE_PRODUCTS)


def _orders(limit: int = 10) -> list | dict:
    return _live_orders(limit) if LIVE else sorted(
        SAMPLE_ORDERS, key=lambda o: o["created_at"], reverse=True)[:limit]


@mcp.tool()
def search_products(query: str = "", limit: int = 10) -> dict:
    """Search products by title / vendor / type / tag.

    Sample mode: searches the demo store. Live mode: searches the
    connected Shopify store (title, vendor, type, tags).
    Returns id, title, vendor, type, status, price, inventory, sku.
    """
    products = _products()
    if isinstance(products, dict) and "error" in products:
        return products
    q = (query or "").strip().lower()
    if q:
        products = [p for p in products
                    if q in (p.get("title") or "").lower()
                    or q in (p.get("vendor") or "").lower()
                    or q in (p.get("product_type") or "").lower()
                    or any(q in (t or "").lower() for t in p.get("tags") or [])]
    result = {**_mode(), "query": query, "count": len(products[:limit]),
              "products": products[:max(1, min(limit, 50))]}
    return result


@mcp.tool()
def get_low_stock(threshold: int = 5) -> dict:
    """Products at or below the inventory threshold (default 5).

    The stock alert a store owner checks every morning. Sample mode:
    demo inventory. Live mode: summed variant inventory from Shopify.
    Out-of-stock (0) is listed first, then lowest inventory first.
    """
    products = _products()
    if isinstance(products, dict) and "error" in products:
        return products
    low = [p for p in products
           if p.get("inventory") is not None and p["inventory"] <= threshold]
    low.sort(key=lambda p: p["inventory"])
    return {**_mode(), "threshold": threshold, "count": len(low),
            "low_stock": low,
            "note2": "Reorder the 0-stock items first; the rest are at/below threshold."}


@mcp.tool()
def get_recent_orders(limit: int = 10) -> dict:
    """Most recent orders, newest first.

    Returns order number, date, customer, payment status,
    fulfilment status, total and line items. Sample mode: demo
    orders. Live mode: Shopify orders (status=any).
    """
    orders = _orders(limit)
    if isinstance(orders, dict) and "error" in orders:
        return orders
    return {**_mode(), "count": len(orders), "orders": orders}


@mcp.tool()
def get_order_status(order_number: int) -> dict:
    """Status of one order by its order number (e.g. 1042, not #1042).

    Returns payment status, fulfilment status, total and line items.
    Use get_recent_orders first if you only have a name/date.
    A Shopify fulfilment status is not a carrier delivery guarantee.
    """
    orders = _orders(50)
    if isinstance(orders, dict) and "error" in orders:
        return orders
    for o in orders:
        if o.get("order_number") == int(order_number):
            return {**_mode(), "order": o}
    return {**_mode(), "order_number": int(order_number),
            "error": f"No order #{order_number} found in the {'live' if LIVE else 'sample'} store."}


@mcp.tool()
def top_selling_products(limit: int = 5) -> dict:
    """Best sellers, ranked by units sold.

    Sample mode: demo sales history for the demo store. Live mode:
    Shopify does not expose lifetime units-sold in one call, so this
    ranks products by units in the 50 most recent orders — labelled
    as such, not as lifetime sales.
    """
    if LIVE:
        orders = _orders(50)
        if isinstance(orders, dict) and "error" in orders:
            return orders
        sold: dict[str, dict] = {}
        for o in orders:
            for li in o.get("line_items") or []:
                t = li.get("title") or "Unknown"
                sold.setdefault(t, {"title": t, "units_sold_recent_50_orders": 0})
                sold[t]["units_sold_recent_50_orders"] += int(li.get("quantity") or 0)
        ranked = sorted(sold.values(), key=lambda x: x["units_sold_recent_50_orders"], reverse=True)
        return {**_mode(), "count": len(ranked[:limit]), "top_selling": ranked[:max(1, min(limit, 20))],
                "note2": "Live ranking is units in the 50 most recent orders, not lifetime sales."}
    products = _products()
    ranked = sorted(products, key=lambda p: SAMPLE_SOLD.get(p["id"], 0), reverse=True)
    out = [{**p, "units_sold": SAMPLE_SOLD.get(p["id"], 0)} for p in ranked]
    return {**_mode(), "count": len(out[:limit]), "top_selling": out[:max(1, min(limit, 20))],
            "note2": "Sample ranking is demo sales history for the demo store."}


@mcp.tool()
def store_summary() -> dict:
    """One-call store health summary: products, low stock, recent orders.

    Counts active products, lists low-stock (<=5) items, totals the
    paid revenue in the recent orders window, and flags unfulfilled
    paid orders that need attention. Read-only; nothing is changed.
    """
    products = _products()
    if isinstance(products, dict) and "error" in products:
        return products
    orders = _orders(10)
    if isinstance(orders, dict) and "error" in orders:
        return orders
    active = [p for p in products if p.get("status") == "active"]
    low = [p for p in products if p.get("inventory") is not None and p["inventory"] <= 5]
    paid = [o for o in orders if o.get("financial_status") == "paid"]
    unfulfilled_paid = [o for o in paid if o.get("fulfillment_status") in ("unfulfilled", None)]
    revenue = round(sum(float(o.get("total_price") or 0) for o in paid), 2)
    return {
        **_mode(),
        "total_products": len(products),
        "active_products": len(active),
        "low_stock_count": len(low),
        "low_stock": sorted(low, key=lambda p: p["inventory"]),
        "recent_orders_checked": len(orders),
        "paid_orders_in_window": len(paid),
        "paid_revenue_in_window": revenue,
        "currency": orders[0].get("currency") if orders else "USD",
        "unfulfilled_paid_orders": unfulfilled_paid,
        "attention": (f"{len(unfulfilled_paid)} paid order(s) still unfulfilled — fulfil those first."
                      if unfulfilled_paid else "No paid-but-unfulfilled orders in the recent window."),
    }


if __name__ == "__main__":
    mcp.run()
