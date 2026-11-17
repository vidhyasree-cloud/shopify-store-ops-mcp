# Shopify Store Ops MCP Server

Personal portfolio project — independent, not affiliated with any employer.

A read-only MCP server for running a Shopify store from Claude Desktop:
search products, check low stock, see recent orders, check one order,
rank best sellers, and get a one-call store health summary.

## Tools (6)

| Tool | What it does |
| --- | --- |
| `search_products` | Search products by title / vendor / type / tag |
| `get_low_stock` | Products at or below inventory threshold (default 5), 0-stock first |
| `get_recent_orders` | Most recent orders, newest first, with payment + fulfilment status |
| `get_order_status` | One order by order number, e.g. 1042 |
| `top_selling_products` | Best sellers ranked by units sold |
| `store_summary` | Products, low stock, paid revenue in window, unfulfilled paid orders |

## Two modes — always labelled

**SAMPLE (default, no setup):** a built-in demo store, "Willow & Wick"
(handmade candles / home goods) — 8 products, 6 orders. Every tool
result says `mode: "sample"`. Nothing is a real store, customer, or sale.

**LIVE (real store):** set the store domain plus the app's client
credentials in the Claude Desktop config — this is the lasting live
mode, the server fetches a fresh access token itself and refreshes
it before it expires, so there is no 24-hour token to paste again:
```
SHOPIFY_STORE_DOMAIN = my-store.myshopify.com
SHOPIFY_CLIENT_ID = <Dev Dashboard app Client ID>
SHOPIFY_CLIENT_SECRET = <Dev Dashboard app Client Secret>
```
Scopes needed: `read_products`, `read_orders`, `read_inventory`.
Since 1 January 2026 new apps are made in the Shopify Dev Dashboard
— there is no "Reveal token once" in the admin for them. The client
credentials grant (`POST /admin/oauth/access_token`, grant_type
`client_credentials`) is how the token is obtained, and it lasts
about 24 hours (`expires_in: 86399`).

A static token also still works, for a day at a time:
```
SHOPIFY_ADMIN_ACCESS_TOKEN = <custom-app Admin API token>
```
Client credentials win over a static token when both are set.
Credentials live only in the local config / a private file on the PC —
never in chat, never in the repo, never in a screenshot. Rotate them if
they are ever pasted anywhere.

## Honest limits

- **Read-only.** This server never creates/updates products, never
  changes inventory, never creates discounts or orders.
- Sample numbers are demo numbers — do not quote them as real sales.
- Live `top_selling_products` ranks units in the 50 most recent
  orders (Shopify has no one-call lifetime units-sold), and says so.
- An order's fulfilment status is Shopify's status, not a carrier's
  delivery guarantee.

## Run locally

```powershell
cd C:\Users\Vidhya_Devaraju\shopify-store-ops-mcp
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.venv\Scripts\python.exe test_smoke.py
```

Expected: `ALL SMOKE TESTS PASSED` (sample mode).

## Claude Desktop

Add to the **Local** config file
(`%LOCALAPPDATA%\Claude-Data\claude_pzs8sxrjxfjjc\claude_desktop_config.json`
— the Local file, not Roaming; quit Claude fully first):

```json
"shopify-store-ops": {
  "command": "C:\\Users\\Vidhya_Devaraju\\shopify-store-ops-mcp\\.venv\\Scripts\\python.exe",
  "args": ["C:\\Users\\Vidhya_Devaraju\\shopify-store-ops-mcp\\server.py"],
  "env": {}
}
```

For live mode, add the two env vars inside `"env"`. Then test in a
**new chat** and force the tool by name, e.g.:
"Use the shopify-store-ops MCP tool store_summary" — a plain question
may get Claude's own answer instead of the tool.
