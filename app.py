from flask import Flask, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# Setup the credentials and open the sheet
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
client = gspread.authorize(creds)

# Open your Google Sheet by name
sheet = client.open("NextinAI News").sheet1  # Make sure the name matches exactly

@app.route('/news', methods=['GET'])
def get_news():
    data = sheet.get_all_records()
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
