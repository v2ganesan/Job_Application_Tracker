# Google Sheets service module
from __future__ import print_function
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime

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
    """Main function to set up complete Google Sheets integration"""
    print("🚀 Starting Google Sheets setup for Job Application Tracker...")
    
    # Step 1: Authenticate
    service = authenticate_sheets()
    if not service:
        print("❌ Authentication failed. Make sure to run gmail_auth.py first.")
        return
    
    # Step 2: Create spreadsheet
    try:
        spreadsheet_id, spreadsheet_url = create_job_tracker_sheet(service)
    except Exception as e:
        print(f"❌ Failed to create spreadsheet: {e}")
        return
    
    # Step 3: Setup headers
    try:
        setup_sheet_headers(service, spreadsheet_id)
    except Exception as e:
        print(f"❌ Failed to setup headers: {e}")
        return
    
    # Step 4: Add test data
    try:
        add_test_data(service, spreadsheet_id)
    except Exception as e:
        print(f"❌ Failed to add test data: {e}")
        return
    
    # Step 5: Verify read access
    try:
        verify_read_access(service, spreadsheet_id)
    except Exception as e:
        print(f"❌ Failed to verify read access: {e}")
        return
    
    print("\n🎉 Google Sheets integration complete!")
    print(f"📋 Your Job Application Tracker: {spreadsheet_url}")
    print("\n✅ Story 2 Complete: The service can now create and manage spreadsheets!")

if __name__ == '__main__':
    main()
