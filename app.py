import os
import json
import gspread
from google.oauth2.service_account import Credentials

# Read the secret from environment
creds_dict = json.loads(os.environ["GOOGLE_CREDS_JSON"])
creds = Credentials.from_service_account_info(creds_dict)

client = gspread.authorize(creds)
sheet = client.open("NextinAI News").sheet1
