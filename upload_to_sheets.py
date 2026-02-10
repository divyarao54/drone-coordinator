import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import os

# Setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('skylarkdrones-487006-99dc39e2a5ff.json', scopes=SCOPES)
client = gspread.authorize(creds)

# Open or create sheet
sheet_id = os.getenv('GOOGLE_SHEET_ID')
sheet = client.open_by_key(sheet_id)

# Upload pilots
df_pilots = pd.read_csv('data/pilot_roster.csv')
worksheet = sheet.worksheet('pilot_roster')
worksheet.clear()
worksheet.update([df_pilots.columns.values.tolist()] + df_pilots.values.tolist())
print("✓ Uploaded pilots")

# Upload drones
df_drones = pd.read_csv('data/drone_fleet.csv')
worksheet = sheet.worksheet('drone_fleet')
worksheet.clear()
worksheet.update([df_drones.columns.values.tolist()] + df_drones.values.tolist())
print("✓ Uploaded drones")

# Upload missions
df_missions = pd.read_csv('data/missions.csv')
worksheet = sheet.worksheet('missions')
worksheet.clear()
worksheet.update([df_missions.columns.values.tolist()] + df_missions.values.tolist())
print("✓ Uploaded missions")

print("✅ All data uploaded to Google Sheets!")