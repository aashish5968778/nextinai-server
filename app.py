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
# 2) Load credentials
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
SPREADSHEET_TITLE = "NextinAI News"
spreadsheet = client.open(SPREADSHEET_TITLE)

news_sheet = spreadsheet.sheet1

try:
    tools_sheet = spreadsheet.worksheet("tools")
except gspread.exceptions.WorksheetNotFound:
    tools_sheet = None

try:
    courses_sheet = spreadsheet.worksheet("courses")
except gspread.exceptions.WorksheetNotFound:
    courses_sheet = None

try:
    lessons_sheet = spreadsheet.worksheet("lessons")
except gspread.exceptions.WorksheetNotFound:
    lessons_sheet = None

# ------------------------------------------------------------------
# 4) Small in-memory cache
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
    rows = news_sheet.get_all_records()
    return cache_response(rows, max_age=120)

@app.route("/tools", methods=["GET"])
def get_tools():
    if tools_sheet is None:
        return jsonify({
            "ok": False,
            "error": "Worksheet 'tools' not found. Create a tab named exactly 'tools'."
        }), 400

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

    cache_key = f"tools|cat={category}|q={search}|p={page}|l={limit}"
    cached = cache_get(cache_key)
    if cached:
        return cache_response(cached, max_age=300)

    rows = [normalize_row(r) for r in tools_sheet.get_all_records()]

    items = [
        r for r in rows
        if (r.get("status", "").lower() in ("published", "publish", "live"))
    ]

    if category:
        cat_lower = category.lower()
        items = [r for r in items if r.get("category", "").lower() == cat_lower]

    if search:
        s = search.lower()
        items = [
            r for r in items
            if s in r.get("name", "").lower()
            or s in r.get("description", "").lower()
            or s in r.get("category", "").lower()
        ]

    items.sort(key=lambda r: r.get("name", ""))

    start = (page - 1) * limit
    slice_ = items[start:start + limit]

    payload = {
        "ok": True,
        "total": len(items),
        "page": page,
        "limit": limit,
        "items": slice_,
    }
    cache_put(cache_key, payload, ttl_sec=300)
    return cache_response(payload, max_age=300)

@app.route("/courses", methods=["GET"])
def get_courses():
    if courses_sheet is None:
        return jsonify({
            "ok": False,
            "error": "Worksheet 'courses' not found. Create a tab named exactly 'courses'."
        }), 400

    search = (request.args.get("search") or "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except Exception:
        page = 1
    try:
        limit = max(1, min(100, int(request.args.get("limit", 50))))
    except Exception:
        limit = 50

    cache_key = f"courses|q={search}|p={page}|l={limit}"
    cached = cache_get(cache_key)
    if cached:
        return cache_response(cached, max_age=300)

    rows = [normalize_row(r) for r in courses_sheet.get_all_records()]

    if search:
        s = search.lower()
        rows = [
            r for r in rows
            if s in r.get("title", "").lower()
            or s in r.get("subtitle", "").lower()
            or s in r.get("tags", "").lower()
        ]

    rows.sort(key=lambda r: r.get("title", ""))

    start = (page - 1) * limit
    slice_ = rows[start:start + limit]

    payload = {
        "ok": True,
        "total": len(rows),
        "page": page,
        "limit": limit,
        "items": slice_,
    }
    cache_put(cache_key, payload, ttl_sec=300)
    return cache_response(payload, max_age=300)

@app.route("/lessons/<courseId>", methods=["GET"])
def get_lessons(courseId):
    if lessons_sheet is None:
        return jsonify({
            "ok": False,
            "error": "Worksheet 'lessons' not found. Create a tab named exactly 'lessons'."
        }), 400

    rows = [normalize_row(r) for r in lessons_sheet.get_all_records()]
    lessons = [r for r in rows if r.get("courseid") == courseId]
    lessons.sort(key=lambda r: int(r.get("order", 0)))

    payload = {
        "ok": True,
        "total": len(lessons),
        "items": lessons,
    }
    return cache_response(payload, max_age=120)

# ------------------------------------------------------------------
# 6) Run
# ------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)  # set debug=False in prod
