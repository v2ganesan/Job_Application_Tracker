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
from src.database import user_exists, save_new_user, init_database, get_user_sheet_id, update_user_sheet_id
from src.utils import extract_company, extract_position
from src.job_email_finder import find_job_emails

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


def create_job_tracker_sheet(credentials):
    """Create a new spreadsheet for job application tracking"""
    # Build Sheets service
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
        'Company', 'Position', 'Date Applied', 'Status', 'Follow-up Date'
    ]
    
    values = [headers]
    body = {
        'values': values
    }
    
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range='A1:E1',
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
                    'endColumnIndex': 5
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

# Scenario 2: Email-to-Sheet (single email processing)
def add_job_from_email(service, spreadsheet_id, email_data):
    """Add a job application from email data to the sheet"""
    # Extract company name using parent function (tries both sender and subject)
    company = extract_company(
        sender=email_data.get('sender'),
        subject=email_data.get('subject')
    )
    position = 'Unknown Position'  # Default since position extraction was removed
    date_applied = datetime.now().strftime('%Y-%m-%d')  # Use current date
    status = 'Applied'  # Default status
    follow_up = ''  # Empty by default
    
    # Get next available row - simple implementation
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A:A'
        ).execute()
        values = result.get('values', [])
        next_row = len(values) + 1
    except:
        next_row = 2  # Default to row 2
    
    row_data = [company, position, date_applied, status, follow_up]
    
    values = [row_data]
    body = {'values': values}
    
    result = service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'A{next_row}:E{next_row}',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    print(f"✅ Added job application: {company} - {position} ({status})")
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
        range='A1:E10'  # Read headers plus some data
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

def add_application_emails_to_sheet(service, spreadsheet_id, max_emails=20):
    """
    Find application emails and add them to the Google Sheet
    
    Args:
        service: Google Sheets service object
        spreadsheet_id: ID of the spreadsheet to update
        max_emails: Maximum number of emails to process
    
    Returns:
        dict: Summary of results
    """
    print("🔍 Finding job application emails...")
    
    # Get job emails using our finder
    job_emails = find_job_emails(max_results=max_emails)
    
    if not job_emails:
        print("❌ No job emails found.")
        return {'total': 0, 'applications': 0, 'added': 0}
    
    # Filter for application emails only, but also show what categories other emails got
    application_emails = []
    other_emails = []
    
    for email in job_emails:
        if email.get('category') == 'application':
            application_emails.append(email)
        elif email.get('company') and email.get('company') != 'Unknown Company':
            other_emails.append(email)
    
    # Show what we found
    if other_emails:
        print(f"📋 Found {len(other_emails)} other job emails with valid companies:")
        for email in other_emails[:5]:  # Show first 5
            print(f"   • {email.get('company')} - Category: {email.get('category')} - Subject: {email.get('subject')[:50]}...")
    
    if not application_emails:
        print("❌ No application emails found.")
        return {'total': len(job_emails), 'applications': 0, 'added': 0}
    
    print(f"✅ Found {len(application_emails)} application emails to add to sheet")
    
    # Get the next available row
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range='A:A'
        ).execute()
        values = result.get('values', [])
        next_row = len(values) + 1
    except:
        next_row = 2  # Default to row 2 if error
    
    # Prepare data for batch insert
    rows_to_add = []
    added_count = 0
    
    for email in application_emails:
        company = email.get('company', 'Unknown Company')
        position = email.get('position', 'Unknown Position')
        
        # Parse date (basic formatting)
        try:
            date_applied = datetime.now().strftime('%Y-%m-%d')  # Use today's date as fallback
        except:
            date_applied = 'Unknown Date'
        
        status = 'Applied'  # Default status for application emails
        follow_up = ''  # Empty by default
        
        # Only add if we have at least a company name
        if company and company != 'Unknown Company':
            row_data = [company, position, date_applied, status, follow_up]
            rows_to_add.append(row_data)
            added_count += 1
            
            print(f"   ✅ Adding: {company} - {position}")
        else:
            print(f"   ❌ Skipping: No company found for email from {email.get('sender', 'Unknown')}")
    
    if not rows_to_add:
        print("❌ No valid applications to add (no companies extracted)")
        return {'total': len(job_emails), 'applications': len(application_emails), 'added': 0}
    
    # Batch insert all rows
    try:
        range_name = f'A{next_row}:E{next_row + len(rows_to_add) - 1}'
        body = {'values': rows_to_add}
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        print(f"✅ Successfully added {added_count} job applications to the sheet!")
        
        return {
            'total': len(job_emails),
            'applications': len(application_emails),
            'added': added_count
        }
        
    except Exception as e:
        print(f"❌ Error adding to sheet: {e}")
        return {'total': len(job_emails), 'applications': len(application_emails), 'added': 0}


def get_user_email_from_credentials():
    """Get user email from stored credentials"""
    try:
        token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                if creds and creds.valid:
                    # Build Gmail service to get user email
                    gmail_service = build('gmail', 'v1', credentials=creds)
                    profile = gmail_service.users().getProfile(userId='me').execute()
                    return profile.get('emailAddress')
    except Exception as e:
        print(f"❌ Error getting user email: {e}")
    return None

def main():
    """Main function to demonstrate adding application emails to sheet"""
    print("📊 Job Application Email to Sheet Processor")
    print("=" * 50)
    
    # Authenticate with Google Sheets
    service = authenticate_sheets()
    if not service:
        print("❌ Failed to authenticate with Google Sheets")
        return
    
    # Get user email from credentials
    user_email = get_user_email_from_credentials()
    if not user_email:
        print("❌ Could not determine user email from credentials")
        return
    
    print(f"📧 User: {user_email}")
    
    # Check if user exists and get their sheet ID
    if user_exists(user_email):
        spreadsheet_id = get_user_sheet_id(user_email)
        if spreadsheet_id:
            print(f"✅ Found existing sheet ID: {spreadsheet_id}")
        else:
            print("⚠️  User exists but no sheet ID found. Creating new sheet...")
            # Create a new sheet for the user - need to get credentials first
            token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            
            service_new, spreadsheet_id, spreadsheet_url = create_job_tracker_sheet(creds)
            if spreadsheet_id:
                # Update the database with the new sheet ID
                if update_user_sheet_id(user_email, spreadsheet_id):
                    print(f"✅ Created new sheet and updated database: {spreadsheet_id}")
                else:
                    print("⚠️  Sheet created but failed to update database")
            else:
                print("❌ Failed to create new sheet")
                return
    else:
        print("❌ User not found in database. Please run gmail_auth.py first to set up your account.")
        return
    
    if not spreadsheet_id:
        print("❌ No spreadsheet ID available")
        return
    
    # Process emails and add to sheet
    results = add_application_emails_to_sheet(service, spreadsheet_id, max_emails=20)
    
    # Display summary
    print(f"\n📊 PROCESSING SUMMARY:")
    print(f"   📧 Total emails found: {results['total']}")
    print(f"   📝 Application emails: {results['applications']}")
    print(f"   ✅ Added to sheet: {results['added']}")
    
    if results['added'] > 0:
        print(f"\n🎉 Successfully processed job applications!")
    else:
        print(f"\n⚠️  No applications were added to the sheet.")


if __name__ == '__main__':
    main()
