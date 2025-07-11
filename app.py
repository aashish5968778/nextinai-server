from flask import Flask, jsonify
import requests
import os

app = Flask(__name__)

# Replace this URL with your gsx2json link
GOOGLE_SHEET_URL = "https://gsx2json.com/api?id=1FMl9eyC0XvEBMFr-feFxNMGC2Gxxy6xGIGlK-GMUXks&sheet=Sheet1"

@app.route('/news', methods=['GET'])
def get_news():
    response = requests.get(GOOGLE_SHEET_URL)
    data = response.json()
    return jsonify(data['rows'])

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # Render sets PORT automatically
    app.run(host='0.0.0.0', port=port, debug=True)
