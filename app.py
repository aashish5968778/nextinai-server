from flask import Flask, jsonify
from flask_cors import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import os

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests (for Flutter web)

# Step 1: Read credentials from env variable
creds_json_str = os.environ.get("GOOGLE_CREDS_JSON")
if not creds_json_str:
    raise Exception("GOOGLE_CREDS_JSON not found in environment variables")

creds_dict = json.loads(creds_json_str)

# Step 2: Authenticate with Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# Step 3: Open your sheet
sheet = client.open("NextinAI News").sheet1

# Step 4: Create your endpoint
@app.route('/news', methods=['GET'])
def get_news():
    data = sheet.get_all_records()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
