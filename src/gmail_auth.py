# Gmail authentication module
from __future__ import print_function
import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import user_exists, save_new_user, init_database

# Load environment variables
load_dotenv()

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def main():
    print("🚀 Job Application Tracker - Authentication & Setup")
    
    # Initialize database
    print("📋 Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database")
        return
    
    creds = None

    # If token already exists, load it
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)

    # If no valid creds, go through OAuth login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("🔐 Starting OAuth authentication...")
            # Create client config from environment variables
            client_config = {
                "installed": {
                    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                    "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"]
                }
            }
            
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the token for next time
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    print("✅ Authentication successful!")
    
    # Get user email and check if first-time user
    user_email = get_user_email(creds)
    print(f"👤 User: {user_email}")
    
    # Check if this is a first-time user
    if not user_exists(user_email):
        # First-time user - set up their workspace
        handle_first_time_user(creds, user_email)
    else:
        print("👋 Welcome back! Your Job Application Tracker is ready.")

    # Build Gmail API service for email demo
    print("\n📧 Testing Gmail access...")
    service = build('gmail', 'v1', credentials=creds)

    # Get recent messages from inbox
    results = service.users().messages().list(userId='me', maxResults=5, q='in:inbox').execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found in inbox.")
    else:
        print("Recent emails from inbox:")
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
            
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print("-----")
    
    print("\n🎉 Setup complete! Your Job Application Tracker is ready to use.")

def get_user_email(credentials):
    """Get user email from OAuth credentials"""
    oauth_service = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth_service.userinfo().get().execute()
    return user_info.get('email')

def create_job_tracker_sheet(credentials):
    """Create a new spreadsheet for job application tracking"""
    service = build('sheets', 'v4', credentials=credentials)
    
    spreadsheet = {
        'properties': {
            'title': 'Job Application Tracker'
        }
    }
    
    spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId,spreadsheetUrl').execute()
    spreadsheet_id = spreadsheet.get('spreadsheetId')
    spreadsheet_url = spreadsheet.get('spreadsheetUrl')
    
    print(f"✅ Created spreadsheet: 'Job Application Tracker'")
    print(f"📋 Spreadsheet URL: {spreadsheet_url}")
    
    return service, spreadsheet_id, spreadsheet_url

def setup_sheet_headers(service, spreadsheet_id):
    """Add headers to the job tracker spreadsheet"""
    headers = [
        'Company', 'Position', 'Date Applied', 'Status', 
        'Application Method', 'Contact Person', 'Notes', 
        'Interview Date', 'Follow-up Date'
    ]
    
    values = [headers]
    body = {'values': values}
    
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='A1:I1',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    # Format headers (bold)
    format_request = {
        'requests': [{
            'repeatCell': {
                'range': {
                    'sheetId': 0, 'startRowIndex': 0, 'endRowIndex': 1,
                    'startColumnIndex': 0, 'endColumnIndex': 9
                },
                'cell': {
                    'userEnteredFormat': {'textFormat': {'bold': True}}
                },
                'fields': 'userEnteredFormat.textFormat.bold'
            }
        }]
    }
    
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=format_request
    ).execute()
    
    print(f"✅ Added headers: {' | '.join(headers)}")

def handle_first_time_user(credentials, user_email):
    """Handle first-time user setup - create sheet and save to database"""
    print(f"🆕 First-time user detected: {user_email}")
    print("📋 Setting up your Job Application Tracker...")
    
    try:
        # Create sheet
        sheets_service, spreadsheet_id, spreadsheet_url = create_job_tracker_sheet(credentials)
        
        # Set up headers
        setup_sheet_headers(sheets_service, spreadsheet_id)
        
        # Save user to database
        if save_new_user(user_email, spreadsheet_id):
            print(f"✅ User setup complete!")
            print(f"📋 Your Job Application Tracker: {spreadsheet_url}")
            return True
        else:
            print("❌ Failed to save user to database")
            return False
            
    except Exception as e:
        print(f"❌ Failed to set up first-time user: {e}")
        return False

if __name__ == '__main__':
    main()
