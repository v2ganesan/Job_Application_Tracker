# Gmail authentication module
from __future__ import print_function
import os
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

def main():
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
            credentials_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials', 'client_secret.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=8080)

        # Save the token for next time
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    # Build Gmail API service
    service = build('gmail', 'v1', credentials=creds)

    # Try to get ONLY Primary category messages
    results = service.users().messages().list(userId='me', maxResults=10, q='category:primary').execute()
    messages = results.get('messages', [])

    if not messages:
        print("No messages found in Primary category.")
        print("Your Gmail might not have tabbed inbox enabled, or no emails are categorized as Primary.")
        print("Try enabling Gmail's tabbed inbox in Gmail settings to see Primary/Promotions/Social tabs.")
    else:
        print("Recent emails from PRIMARY category only:")
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
            
            print(f"From: {sender}")
            print(f"Subject: {subject}")
            print("-----")

if __name__ == '__main__':
    main()
