# Google Sheets service module
from __future__ import print_function
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
from dotenv import load_dotenv
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.database import user_exists, save_new_user, init_database

# Load environment variables
load_dotenv()

def authenticate_sheets():
    """Authenticate and return Google Sheets service using existing token"""
    creds = None
    
    # Load existing token from gmail_auth
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        print("No valid credentials found. Please run gmail_auth.py first.")
        return None
    
    # Build and return Sheets API service
    service = build('sheets', 'v4', credentials=creds)
    print("✅ Authenticated with Google Sheets")
    return service

def get_user_email(credentials):
    """Get user email from OAuth credentials"""
    from googleapiclient.discovery import build
    
    # Build OAuth2 service to get user info
    oauth_service = build('oauth2', 'v2', credentials=credentials)
    user_info = oauth_service.userinfo().get().execute()
    
    return user_info.get('email')

def create_job_tracker_sheet(service):
    """Create a new spreadsheet for job application tracking"""
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
    
    return spreadsheet_id, spreadsheet_url

def setup_sheet_headers(service, spreadsheet_id):
    """Add headers to the job tracker spreadsheet"""
    headers = [
        'Company',
        'Position', 
        'Date Applied',
        'Status',
        'Application Method',
        'Contact Person',
        'Notes',
        'Interview Date',
        'Follow-up Date'
    ]
    
    values = [headers]
    body = {
        'values': values
    }
    
    result = service.spreadsheets().values().update(
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
                    'sheetId': 0,
                    'startRowIndex': 0,
                    'endRowIndex': 1,
                    'startColumnIndex': 0,
                    'endColumnIndex': 9
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {
                            'bold': True
                        }
                    }
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
    return result

def add_test_data(service, spreadsheet_id):
    """Add a test row to verify write permissions"""
    test_data = [
        'Google',
        'Software Engineer',
        datetime.now().strftime('%Y-%m-%d'),
        'Applied',
        'Online Portal',
        'Jane Smith',
        'Submitted through careers page',
        '',
        ''
    ]
    
    values = [test_data]
    body = {
        'values': values
    }
    
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='A2:I2',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print("✅ Added test data successfully")
    return result

def verify_read_access(service, spreadsheet_id):
    """Read data back to verify read permissions"""
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='A1:I2'
    ).execute()
    
    values = result.get('values', [])
    
    if not values:
        print("❌ No data found - read access failed")
        return False
    else:
        print("✅ Verified read access")
        print(f"   Headers: {values[0]}")
        if len(values) > 1:
            print(f"   Test data: {values[1]}")
        return True

def main():
    """Story 2.1: Create Google Sheet for new user with database tracking"""
    print("🚀 Story 2.1: Checking user status and managing sheets...")
    
    # Initialize database
    print("📋 Initializing database...")
    if not init_database():
        print("❌ Failed to initialize database")
        return
    
    # Step 1: Authenticate and get credentials
    service = authenticate_sheets()
    if not service:
        print("❌ Authentication failed. Make sure to run gmail_auth.py first.")
        return
    
    # Load credentials for user info
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
    with open(token_path, 'rb') as token:
        credentials = pickle.load(token)
    
    # Step 2: Get user email and check if they exist
    user_email = get_user_email(credentials)
    print(f"👤 User: {user_email}")
    
    # Step 3: Check if user exists in database (Story 2.1 core logic)
    if user_exists(user_email):
        print("📋 Returning user - user already exists in database")
        print("✅ Story 2.1 Complete: Existing user detected!")
    else:
        print("🆕 First-time user - creating new sheet and saving to database")
        
        try:
            # Create new sheet for first-time user
            spreadsheet_id, spreadsheet_url = create_job_tracker_sheet(service)
            
            # Set up headers
            setup_sheet_headers(service, spreadsheet_id)
            
            # Add test data for new user
            add_test_data(service, spreadsheet_id)
            
            # Save user to database
            if save_new_user(user_email, spreadsheet_id):
                print(f"✅ Saved new user to database: {user_email}")
                print(f"📋 Sheet URL: {spreadsheet_url}")
                print("\n✅ Story 2.1 Complete: Created new sheet for first-time user!")
            else:
                print("❌ Failed to save user to database")
                
        except Exception as e:
            print(f"❌ Failed to create sheet for new user: {e}")
            return

if __name__ == '__main__':
    main()
