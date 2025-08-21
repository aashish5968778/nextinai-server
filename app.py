from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os
import time

# ------------------------------------------------------------------
# 1) Flask setup
# ------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # allow requests from your Flutter Web app

# ------------------------------------------------------------------
# 2) Load credentials (Render ▸ Environment ▸ Variables)
#    Key: GOOGLE_CREDS_JSON   Value: *entire service-account JSON (one line)*
# ------------------------------------------------------------------
creds_json_str = os.environ.get("GOOGLE_CREDS_JSON")
if not creds_json_str:
    raise RuntimeError(
        "❌ GOOGLE_CREDS_JSON environment variable is missing.\n"
        "   Add it in Render → Environment → Add Env Var."
    )
creds_dict = json.loads(creds_json_str)

# ------------------------------------------------------------------
# 3) Google Sheets client
# ------------------------------------------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the spreadsheet titled exactly "NextinAI News"
# - news_sheet = first worksheet (Sheet1 / sheet1)
# - tools_sheet = worksheet named "tools" (you create this tab)
SPREADSHEET_TITLE = "NextinAI News"
spreadsheet = client.open(SPREADSHEET_TITLE)
news_sheet = spreadsheet.sheet1
try:
    tools_sheet = spreadsheet.worksheet("tools")
except gspread.exceptions.WorksheetNotFound:
    tools_sheet = None  # Will raise a clear error when /tools is called

# ------------------------------------------------------------------
# 4) Small in-memory cache (per process). Reset on redeploy/sleep.
# ------------------------------------------------------------------
_cache: dict[str, tuple[float, dict]] = {}  # key -> (expires_epoch, payload)

def cache_get(key: str):
    rec = _cache.get(key)
    if not rec:
        return None
    expires_at, payload = rec
    if expires_at <= time.time():
        _cache.pop(key, None)
        return None
    return payload

def cache_put(key: str, payload: dict, ttl_sec: int = 300):
    _cache[key] = (time.time() + ttl_sec, payload)

def cache_response(payload: dict, max_age: int = 300):
    resp = make_response(jsonify(payload))
    resp.headers["Cache-Control"] = f"public, max-age={max_age}"
    return resp

def normalize_row(row: dict) -> dict:
    """Trim strings for consistent filtering."""
    def norm(v):
        return v.strip() if isinstance(v, str) else v
    return {k: norm(v) for k, v in row.items()}

# ------------------------------------------------------------------
# 5) Routes
# ------------------------------------------------------------------
@app.route("/")
def alive():
    return "✅ NextinAI API is live!"

@app.route("/news", methods=["GET"])
def get_news():
    """
    Returns all rows (as list of dicts) from your Google Sheet's first tab.
    Column names are taken from the first row.
    """
    rows = news_sheet.get_all_records()  # list[dict]
    return cache_response(rows, max_age=120)  # 2 min cache

@app.route("/tools", methods=["GET"])
def get_tools():
    """
    Returns AI Tools from the 'tools' worksheet in the same spreadsheet.
    Expected columns (header row):
      id | name | description | category | link | logoUrl | status
    Query params:
      ?category=Video
      ?search=chat
      ?page=1&limit=50
    Only rows where status is 'published' (case-insensitive) are returned.
    """
    if tools_sheet is None:
        return jsonify({
            "ok": False,
            "error": "Worksheet 'tools' not found. Create a tab named exactly 'tools'."
        }), 400

    # Query params
    category = (request.args.get("category") or "").strip()
    search = (request.args.get("search") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except Exception:
        page = 1
    try:
        limit = max(1, min(100, int(request.args.get("limit", 50))))
    except Exception:
        limit = 50

    # Cache key per query
    cache_key = f"tools|cat={category}|q={search}|p={page}|l={limit}"
    cached = cache_get(cache_key)
    if cached:
        return cache_response(cached, max_age=300)

    # Fetch and normalize rows
    rows = [normalize_row(r) for r in tools_sheet.get_all_records()]  # list[dict]

    # Keep only published
    items = [
        r for r in rows
        if (r.get("status", "").lower() in ("published", "publish", "live"))
    ]

    # Category filter (exact match ignoring case)
    if category:
        cat_lower = category.lower()
        items = [r for r in items if r.get("category", "").lower() == cat_lower]

    # Search (name/description/category)
    if search:
        s = search.lower()
        items = [
            r for r in items
            if s in r.get("name", "").lower()
            or s in r.get("description", "").lower()
            or s in r.get("category", "").lower()
        ]

    # Sort by name (alphabetical). Change here if you later add 'rank'.
    items.sort(key=lambda r: r.get("name", ""))

    # Pagination
    start = (page - 1) * limit
    slice_ = items[start:start + limit]

    payload = {
        "ok": True,
        "total": len(items),
        "page": page,
        "limit": limit,
        "items": slice_,
    }
    cache_put(cache_key, payload, ttl_sec=300)  # 5 min cache
    return cache_response(payload, max_age=300)

# ------------------------------------------------------------------
# 6) Run (local dev) or bind correctly on Render/Heroku/etc.
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' is critical for Render
    app.run(host="0.0.0.0", port=port, debug=True)  # set debug=False in prod
