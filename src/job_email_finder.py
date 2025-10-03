# Job application email finder - Story 3
from __future__ import print_function
import os
import pickle
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Import our extraction functions
from utils import extract_company, extract_position

# Load environment variables
load_dotenv()

# Job-related keywords - used for both subject line search AND body content analysis
JOB_KEYWORDS = {
    'application': [
        'application received',
        'thank you for applying',
        'we received your application',
        'application submitted',
        'application confirmation',
        'thank you for your interest',
        'thanks for applying',
        'your application has been received',
        'your application has been submitted',
        'your application has been confirmed',
        'thank you for your job application',
        'successfully applied',
        'thanks for completing your application',
        'thank you for your application',
        'you have successfully applied',
        "we've received your application",
        'you have successfully submitted'
    ],
    'interview': [
        'interview',
        'phone screen',
        'technical interview',
        'onsite interview',
        'video call',
        'interview invitation',
        'schedule an interview',
        'interview request'
    ],
    'assessment': [
        'coding assessment',
        'technical assessment',
        'coding challenge',
        'technical challenge',
        'hirevue',
        'virtual interview',
        'online assessment',
        'skills assessment',
        'programming challenge',
        'take home assignment',
        'coding test',
        'technical test',
        'assessment invitation',
        'complete your assessment',
        'pre-interview assessment',
        'next step: assessment',
        'hackerrank',
        'codility',
        'codesignal'
    ],
    'offers': [
        'job offer',
        'offer of employment',
        'employment offer',
        'we would like to extend',
        'we are pleased to offer you',
        'congratulations on your',
        'offer letter',
        'position offer',
        'we are excited to offer',
        'pleased to extend an offer',
        'pleased to offer',
        'excited to offer',
        'would like to extend an offer',
        'we are pleased to inform you'
    ],
    'rejections': [
        'unfortunately',
        'position has been filled',
        'we have decided to move forward',
        'we have decided not to move forward',
        'thank you for your time and interest',
        'we will not be moving forward',
        'after careful consideration',
        'we regret to inform',
        'we have chosen to proceed',
        'not selected for this position',
        'we have decided to pursue',
        'thank you for your interest, however',
        'we appreciate your interest, but',
        'we will be moving forward with other candidates',
        'we regret',
        'not selected',
        'decided to move forward with other candidates',
        'chosen to proceed with other applicants',
        'we have decided to pursue other candidates',
        'not be moving to the next round',
        'we will not be proceeding',
        'we have decided not to proceed',
        'we are unable to move forward',
        'we cannot move forward',
        'we have decided to go with',
        'we have selected another candidate',
        'we have chosen another candidate',
        'we will be proceeding with other candidates',
        'we have decided to pursue other applicants',
        'not moving forward with your application',
        'we will not be considering your application further',
        'your application was not selected',
        'we have decided to decline',
        'we must respectfully decline',
        'we are not able to offer you',
        'we will not be extending an offer',
        'you have not been selected to move forward',
        'not been selected to move forward',
        'have not been selected',
        'candidates whose experience and qualifications are more aligned',
        'more aligned with our needs',
        'selected candidates whose experience',
        'we have selected candidates',
        'move forward with other candidates'
        'with other candidates',
        'with other applicants',
        'pursue other candidates',
        'your application at',
        'more closely aligns with',
        'more closely match our requirements',
        'more closely match our needs',
        'more closely match our criteria',
        'more closely match our qualifications',
        'more closely match our experience',
        'more closely match our skills',
        'more closely match',
        'more closely match our abilities',
        'move forward with other applicants',
        'move forward with other candidates',
        'move forward with other applicants'
    ]
}

def get_gmail_service():
    """Get authenticated Gmail service using existing token"""
    token_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tokens', 'token.pickle')
    
    if not os.path.exists(token_path):
        print("❌ No authentication token found. Please run gmail_auth.py first.")
        return None
    
    try:
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
        
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"❌ Failed to get Gmail service: {e}")
        return None

def build_job_search_query():
    """Build Gmail search query for application emails only"""
    # Only use application keywords, not all job keywords
    all_keywords = JOB_KEYWORDS['application']
    
    # Build search queries for both subject and body content
    search_queries = []
    for keyword in all_keywords:
        # Search both subject and body content
        search_queries.append(f'(subject:("{keyword}") OR "{keyword}")')
    
    # Combine with OR and limit to primary category
    query = f"({' OR '.join(search_queries)}) AND category:primary"
    
    return query

def find_job_emails(max_results=20):
    """Find confirmed job application emails based on application keywords"""
    print("🔍 Searching for confirmed job application emails...")
    
    service = get_gmail_service()
    if not service:
        return []
    
    # Build search query
    query = build_job_search_query()
    print(f"📋 Search query: {query[:100]}...")  # Show first 100 chars
    
    try:
        # Search for matching emails
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print("📭 No job application emails found.")
            return []
        
        print(f"✅ Found {len(messages)} potential job emails")
        print(f"🔄 Processing emails and extracting company/position info...")
        
        # Get detailed info for each email with progress indicators
        job_emails = []
        for i, msg in enumerate(messages, 1):
            print(f"   Processing email {i}/{len(messages)}... ", end='', flush=True)
            
            email_details = get_email_details(service, msg['id'])
            if email_details:
                job_emails.append(email_details)
                # Show what we extracted
                company = email_details.get('company', 'None')
                position = email_details.get('position', 'None')
                print(f"✅ Company: {company}, Position: {position}")
            else:
                print("❌ Skipped (non-job email)")
        
        print(f"\n🎉 Completed processing {len(job_emails)} job emails!")
        return job_emails
        
    except Exception as e:
        print(f"❌ Error searching for job emails: {e}")
        return []

def get_email_details(service, message_id):
    """Extract relevant details from a job email"""
    try:
        msg_data = service.users().messages().get(
            userId='me', 
            id=message_id, 
            format='full'
        ).execute()
        
        headers = msg_data['payload']['headers']
        
        # Extract key information
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'No Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'No Date')
        
        # Filter out obvious non-job emails
        if is_non_job_email(subject, sender):
            return None
        
        # Extract email body for better classification
        body_text = extract_email_body(msg_data)
        
        # Extract company and position using our functions
        company = extract_company(sender=sender, subject=subject)
        position = extract_position(
            body=body_text,
            preview=body_text[:200] if body_text else None,
            subject=subject
        )
        
        return {
            'id': message_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body_snippet': body_text[:500] if body_text else '',  # First 500 chars for preview
            'category': classify_job_email_with_body(subject, body_text),
            'company': company,
            'position': position
        }
        
    except Exception as e:
        print(f"❌ Error getting email details: {e}")
        return None

def extract_email_body(msg_data):
    """Extract plain text from email body"""
    try:
        payload = msg_data['payload']
        body_text = ''
        
        # Handle different email structures
        if 'parts' in payload:
            # Multi-part email - check all parts
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    import base64
                    body_text += base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                elif part['mimeType'] == 'text/html' and 'data' in part['body'] and not body_text:
                    # Fall back to HTML if no plain text (we'll strip HTML tags)
                    import base64
                    html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    # Basic HTML tag removal
                    import re
                    body_text = re.sub('<[^<]+?>', '', html_content)
        elif payload['mimeType'] == 'text/plain' and 'data' in payload['body']:
            # Simple text email
            import base64
            body_text = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        elif payload['mimeType'] == 'text/html' and 'data' in payload['body']:
            # HTML email - strip tags
            import base64
            html_content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            import re
            body_text = re.sub('<[^<]+?>', '', html_content)
        
        # Clean up and return first 2000 characters for classification
        cleaned_text = body_text.replace('\n', ' ').replace('\r', ' ').strip()
        return cleaned_text[:2000].lower()
        
    except Exception as e:
        return ''

def classify_job_email_with_body(subject, body_text):
    """Classify job email type using both subject and body content"""
    subject_lower = subject.lower()
    body_lower = body_text.lower() if body_text else ''
    
    # Check each category in priority order (rejections and offers first since they're often hidden in body)
    for category, keywords in JOB_KEYWORDS.items():
        # Check body content first (especially important for rejections/offers)
        if category in ['rejections', 'offers']:
            for keyword in keywords:
                if keyword.lower() in body_lower:
                    return category
        
        # Then check subject line
        for keyword in keywords:
            if keyword.lower() in subject_lower:
                return category
    
    return 'unknown'

def is_non_job_email(subject, sender):
    """Filter out obvious non-job emails (credit cards, promotions, etc.)"""
    subject_lower = subject.lower()
    sender_lower = sender.lower()
    
    # Credit card and financial offer filters
    financial_keywords = [
        'credit card', 'cash back', 'rewards', 'bonus offer', 
        'investment', 'cd rate', 'cash rewards', '$', '%',
        'credit', 'savings', 'checking', 'loan'
    ]
    
    # Bank/financial sender filters (but allow job-related emails)
    bank_senders = [
        'bankofamerica', 'chase', 'wells fargo', 'citi', 'discover',
        'american express', 'capital one', 'usbank'
    ]
    
    # News/media/newsletter filters
    news_senders = [
        'linkedin.com', 'glassdoor.com', 'tldrnewsletter.com', 
        'news', 'newsletter', 'editors-noreply', 'community',
        'quora', 'digest', 'beehiiv', 'motley fool', 'talentinsightsweekly'
    ]
    
    # Check for financial offers
    for keyword in financial_keywords:
        if keyword in subject_lower:
            return True
    
    # Check for bank senders (but allow job-related emails)
    for bank in bank_senders:
        if (bank in sender_lower and 
            'thank you for applying' not in subject_lower and
            'interview' not in subject_lower and
            'talent acquisition' not in sender_lower and
            'careers' not in sender_lower and
            'recruiting' not in sender_lower and
            'hr' not in sender_lower and
            'application' not in subject_lower):
            return True
    
    # Check for news/media/newsletters
    for sender_keyword in news_senders:
        if sender_keyword in sender_lower:
            return True
    

    
    # Only filter out very generic "interest" emails that are clearly not job applications
    if ('thank you for your interest' in subject_lower and 
        'applying' not in subject_lower and
        'application' not in subject_lower and
        'position' not in subject_lower and
        'job' not in subject_lower and
        'career' not in subject_lower):
        return True
    
    return False

def classify_job_email(subject):
    """Classify job email type based on subject line"""
    subject_lower = subject.lower()
    
    # Check each category
    for category, keywords in JOB_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in subject_lower:
                return category
    
    return 'unknown'

def display_job_emails(job_emails):
    """Display found job emails in a nice format"""
    if not job_emails:
        print("📭 No job emails to display.")
        return
    
    print(f"\n📧 Found {len(job_emails)} job-related emails:")
    print("=" * 80)
    
    # Group by category
    categories = {'application': [], 'assessment': [], 'interview': [], 'offers': [], 'rejections': [], 'unknown': []}
    
    for email in job_emails:
        categories[email['category']].append(email)
    
    # Display each category
    for category, emails in categories.items():
        if emails:
            print(f"\n🏷️  {category.upper().replace('_', ' ')} ({len(emails)} emails):")
            print("-" * 40)
            
            for email in emails:
                print(f"From: {email['sender']}")
                print(f"Subject: {email['subject']}")
                print(f"Date: {email['date']}")
                print()

def main():
    """Main function to find and display emails from each job category"""
    print("🔍 Job Application Email Finder")
    print("=" * 60)
    
    # Find job emails (increased limit to get more emails for categorization)
    job_emails = find_job_emails(max_results=20)
    
    if not job_emails:
        print("No job application emails found.")
        return
    
    # Organize emails by category
    categorized_emails = {
        'application': [],
        'interview': [],
        'assessment': [],
        'offers': [],
        'rejections': [],
        'unknown': []
    }
    
    # Categorize all emails
    for email in job_emails:
        category = email['category']
        categorized_emails[category].append(email)
    
    # Display summary
    print(f"\n📊 Found {len(job_emails)} job-related emails total")
    print("=" * 60)
    
    # Display 5 emails from each category
    for category, emails in categorized_emails.items():
        if emails:  # Only show categories that have emails
            emoji_map = {
                'application': '📝',
                'interview': '🎤', 
                'assessment': '💻',
                'offers': '🎉',
                'rejections': '❌',
                'unknown': '❓'
            }
            
            print(f"\n{emoji_map[category]} {category.upper()} EMAILS ({len(emails)} total)")
            print("-" * 40)
            
            # Show ALL emails from each category with extracted info
            for i, email in enumerate(emails):
                print(f"{i+1}. From: {email['sender']}")
                print(f"   Subject: {email['subject']}")
                print(f"   Date: {email['date']}")
                
                # Display extracted company and position
                company_status = "✅" if email.get('company') else "❌"
                position_status = "✅" if email.get('position') else "❌"
                
                print(f"   {company_status} Company: {email.get('company', 'Not found')}")
                print(f"   {position_status} Position: {email.get('position', 'Not found')}")
                print()
    
    # Calculate extraction statistics
    total_emails = len(job_emails)
    successful_companies = sum(1 for email in job_emails if email.get('company'))
    successful_positions = sum(1 for email in job_emails if email.get('position'))
    
    print(f"\n📊 EXTRACTION SUMMARY:")
    print("=" * 40)
    print(f"Total emails processed: {total_emails}")
    print(f"✅ Company extraction: {successful_companies}/{total_emails} ({successful_companies/total_emails*100:.1f}%)")
    print(f"✅ Position extraction: {successful_positions}/{total_emails} ({successful_positions/total_emails*100:.1f}%)")
    
    print(f"\n✅ Email categorization and extraction complete!")

if __name__ == '__main__':
    main()
