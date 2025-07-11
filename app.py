from flask import Flask, jsonify
from flask_cors import CORS  # ✅ Import CORS
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS

# Setup Google Sheets API credentials
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open your Google Sheet by name
sheet = client.open("NextinAI News").sheet1  # ✅ Make sure name matches Google Sheet title

@app.route('/')
def home():
    return "✅ NextinAI API is live!"

@app.route('/news', methods=['GET'])
def get_news():
    data = sheet.get_all_records()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
