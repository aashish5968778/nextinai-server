from flask import Flask, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

# ------------------------------------------------------------------
# 1. Flask setup
# ------------------------------------------------------------------
app = Flask(__name__)
CORS(app)  # allow requests from your Flutter Web app

# ------------------------------------------------------------------
# 2. Load credentials (stored in Render ▸ Environment ▸ Variables)
#    Key: GOOGLE_CREDS_JSON   Value: *entire JSON key as one line*
# ------------------------------------------------------------------
creds_json_str = os.environ.get("GOOGLE_CREDS_JSON")  # ← comes from Render env var
if not creds_json_str:
    raise RuntimeError(
        "❌  GOOGLE_CREDS_JSON environment variable is missing.\n"
        "    Add it in Render → Environment → Add Env Var."
    )

creds_dict = json.loads(creds_json_str)

# ------------------------------------------------------------------
# 3. Google Sheets client
# ------------------------------------------------------------------
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Open the first worksheet of the spreadsheet titled exactly "NextinAI News"
sheet = client.open("NextinAI News").sheet1  # check spelling/capitalisation!

# ------------------------------------------------------------------
# 4. Routes
# ------------------------------------------------------------------
@app.route("/")
def alive():
    return "✅ NextinAI API is live!"

@app.route("/news", methods=["GET"])
def get_news():
    """
    Returns all rows (as list of dicts) from your Google Sheet.
    Column names are taken from the first row.
    """
    rows = sheet.get_all_records()  # list[dict]
    return jsonify(rows)

# ------------------------------------------------------------------
# 5. Run (local dev) or bind correctly on Render/Heroku/etc.
# ------------------------------------------------------------------
if __name__ == "__main__":
    # If Render sets PORT (e.g. 10000-59999) use that, else default to 5000
    port = int(os.environ.get("PORT", 5000))

    # host='0.0.0.0' is critical for Render so that the container listens externally
    app.run(host="0.0.0.0", port=port, debug=True)  # ▸ set debug=False in prod
