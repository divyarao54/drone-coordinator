import gspread
from google.oauth2.service_account import Credentials
import os

print("🔍 Checking Google Sheets access...")

# Load credentials
creds_file = 'skylarkdrones-487006-99dc39e2a5ff.json'
if not os.path.exists(creds_file):
    print(f"❌ Credentials file not found: {creds_file}")
    exit(1)

creds = Credentials.from_service_account_file(creds_file)
client = gspread.authorize(creds)

print("✅ Authenticated")

# Get service account email
service_account_email = creds.service_account_email
print(f"🔑 Service Account Email: {service_account_email}")

# Get sheet ID from .env
sheet_id = None
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if 'GOOGLE_SHEET_ID' in line and '=' in line:
                sheet_id = line.split('=')[1].strip()
                break

if not sheet_id:
    print("❌ GOOGLE_SHEET_ID not found in .env file")
    print("Add this to your .env: GOOGLE_SHEET_ID=your_sheet_id_here")
    exit(1)

print(f"📋 Sheet ID from .env: {sheet_id}")

# Try to list all sheets we have access to
print("\n📋 Sheets you have access to:")
try:
    sheets = client.openall()
    found = False
    for s in sheets:
        print(f"  • {s.title} (ID: {s.id})")
        if s.id == sheet_id:
            found = True
            print(f"    ⭐ FOUND! You have access to this sheet")
    
    if not found:
        print(f"\n❌ Sheet ID {sheet_id} NOT FOUND in your accessible sheets")
        print("\n🔧 Solution: Share your sheet with the service account:")
        print(f"1. Open your Google Sheet")
        print(f"2. Click 'Share' button")
        print(f"3. Add this email: {service_account_email}")
        print(f"4. Set permission to 'Editor'")
        print(f"5. Click 'Send'")
        
except Exception as e:
    print(f"❌ Error listing sheets: {e}")