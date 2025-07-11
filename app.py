from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

# Public JSON feed from your Google Sheet
GOOGLE_SHEET_URL = "https://gsx2json.com/api?id=1FMl9eyC0XvEBMFr-feFxNMGC2Gxxy6xGIGlK-GMUXks&sheet=Sheet1"

@app.route('/')
def home():
    return "✅ NextinAI API is live!"

@app.route('/news', methods=['GET'])
def get_news():
    try:
        response = requests.get(GOOGLE_SHEET_URL)
        response.raise_for_status()
        data = response.json()
        return jsonify(data['rows'])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
