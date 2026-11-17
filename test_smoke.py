"""Smoke tests — call the tool functions directly (no MCP client needed).

Default mode is SAMPLE (no Shopify store connected), so these tests
run without any credentials and assert on the demo store.
Run: .venv/bin/python test_smoke.py
"""
import server


def main():
    p = server.search_products("candle")
    assert "error" not in p, p
    assert p["mode"] == "sample", p
    assert p["products"], p
    print("search_products OK:", [(x["title"], x["inventory"]) for x in p["products"]])

    all_p = server.search_products("")
    assert all_p["count"] == 8, all_p
    print("search_products (all) OK: 8 products")

    low = server.get_low_stock(5)
    assert "error" not in low, low
    assert low["low_stock"][0]["inventory"] == 0, low
    print("get_low_stock OK:", [(x["title"], x["inventory"]) for x in low["low_stock"]])

    orders = server.get_recent_orders(3)
    assert "error" not in orders, orders
    assert len(orders["orders"]) == 3, orders
    assert orders["orders"][0]["order_number"] == 1043, orders
    print("get_recent_orders OK:", [(o["name"], o["financial_status"], o["fulfillment_status"]) for o in orders["orders"]])

    one = server.get_order_status(1042)
    assert "error" not in one, one
    assert one["order"]["total_price"] == 72.00, one
    print("get_order_status OK: #1042 paid, fulfilled, $72.00")

    missing = server.get_order_status(9999)
    assert "error" in missing, missing
    print("get_order_status (missing) OK: error returned, not invented")

    top = server.top_selling_products(3)
    assert "error" not in top, top
    assert top["top_selling"][0]["title"].startswith("Lavender"), top
    print("top_selling_products OK:", [(x["title"], x["units_sold"]) for x in top["top_selling"]])

    s = server.store_summary()
    assert "error" not in s, s
    assert s["total_products"] == 8 and s["active_products"] == 7, s
    assert s["low_stock_count"] == 3, s  # 0, 2, 3 — pour-over at 7 is above threshold
    assert len(s["unfulfilled_paid_orders"]) == 1, s
    print("store_summary OK:", s["total_products"], "products,",
          s["low_stock_count"], "low-stock,",
          "$" + str(s["paid_revenue_in_window"]), "paid in window,",
          s["attention"])

    print("ALL SMOKE TESTS PASSED")


if __name__ == "__main__":
    main()
