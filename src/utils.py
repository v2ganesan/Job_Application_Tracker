# Utility functions module
import re
import spacy
from typing import Optional


def extract_company_from_sender(sender: str) -> Optional[str]:
    """
    Extract company name from email sender using spaCy NLP
    
    Args:
        sender (str): Email sender in format "Name <email@domain.com>" or "email@domain.com"
    
    Returns:
        str: Extracted company name or None if not found
    """
    if not sender:
        return None
    
    try:
        # Load spaCy transformer model (more accurate)
        nlp = spacy.load("en_core_web_trf")
    except OSError:
        try:
            # Fallback to small model
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("❌ spaCy model not found. Install with: python -m spacy download en_core_web_trf")
            return None
    
    # Extract name part if sender has format "Name <email>"
    if '<' in sender:
        name_part = sender.split('<')[0].strip()
        if name_part and 'noreply' not in name_part.lower():
            # Special handling for patterns like "Atlassian @ icims"
            if ' @ ' in name_part:
                company_name = name_part.split(' @ ')[0].strip()
                if company_name and len(company_name) > 1:
                    return company_name.title()
            
            # Use spaCy to find organization entities
            doc = nlp(name_part)
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    return ent.text.title()
    
    # Fallback: Extract from email domain
    email_part = sender.split('<')[-1].replace('>', '') if '<' in sender else sender
    if '@' in email_part:
        domain = email_part.split('@')[1]
        
        # Special handling for workday domains - extract the prefix
        if 'myworkday.com' in domain:
            prefix = email_part.split('@')[0]
            # Remove common prefixes
            if prefix not in ['send-only.sec', 'system', 'notification']:
                return prefix.upper()
        
        # Remove common domain extensions and subdomains
        domain_parts = domain.replace('.com', '').replace('.org', '').replace('.io', '').replace('.xyz', '').split('.')
        if domain_parts and domain_parts[0] not in ['mail', 'noreply', 'jobs', 'careers', 'myworkday', 'us.greenhouse-mail', 'talent']:
            return domain_parts[0].title()
    
    return None


def extract_company_from_email(subject: str) -> Optional[str]:
    """
    Extract company name from email subject line using spaCy NLP
    
    Args:
        subject (str): Email subject line
    
    Returns:
        str: Extracted company name or None if not found
    """
    if not subject:
        return None
    
    try:
        # Load spaCy transformer model (more accurate)
        nlp = spacy.load("en_core_web_trf")
    except OSError:
        try:
            # Fallback to small model
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("❌ spaCy model not found. Install with: python -m spacy download en_core_web_trf")
            return None
    
    subject = subject.strip()
    doc = nlp(subject)
    
    # Method 1: Look for patterns with prepositions (most reliable)
    # "Application at Google", "Interview at Microsoft", "Your application to Apple", "Summer 2026 at Plaid"
    for token in doc:
        if token.dep_ == 'pobj' and token.head.text.lower() in ['at', 'to']:
            if token.pos_ == 'PROPN':
                # Get the company name - check for compound dependencies first
                company_tokens = []
                
                # Look backward for compound modifiers (like "Lucid" in "Lucid Software")
                for child in token.children:
                    if child.dep_ == 'compound' and child.pos_ == 'PROPN':
                        company_tokens.append(child.text)
                
                # Add the main token
                company_tokens.append(token.text)
                
                # Look ahead for additional proper nouns but avoid job titles
                for i in range(token.i + 1, min(len(doc), token.i + 3)):
                    next_token = doc[i]
                    if (next_token.pos_ == 'PROPN' and 
                        next_token.text.lower() not in ['engineer', 'manager', 'developer', 'scientist', 'analyst', 'intern', 'internship']):
                        company_tokens.append(next_token.text)
                    else:
                        break
                
                if company_tokens:
                    company_name = ' '.join(company_tokens)
                    
                    # For compound names like "Lucid Software", "Scale AI" - return just the core name
                    if len(company_tokens) == 2:
                        first, second = company_tokens
                        if second.lower() in ['software', 'ai', 'technologies', 'systems', 'solutions', 'services']:
                            return first.title()
                    
                    # Filter out job titles that might be misidentified
                    if (len(company_name) > 1 and 
                        company_name.lower() not in ['software engineer', 'data scientist', 'product manager', 'software engineering', 'intern']):
                        return company_name.title()
    
    # Method 2: Look for company patterns with dashes/pipes
    # "Microsoft - Software Engineer", "Google | Product Manager"
    for i, token in enumerate(doc):
        if token.text in ['-', '|'] and i > 0:
            # Look at the token before the dash/pipe
            prev_token = doc[i-1]
            if prev_token.pos_ == 'PROPN':
                # Try to get multi-word company name before the dash
                company_tokens = [prev_token.text]
                
                # Look backward for more proper nouns
                for j in range(i-2, -1, -1):
                    if doc[j].pos_ == 'PROPN':
                        company_tokens.insert(0, doc[j].text)
                    else:
                        break
                
                company_name = ' '.join(company_tokens)
                if len(company_name) > 1:
                    return company_name.title()
    
    # Method 3: Look for ORGANIZATION entities (but be more selective)
    for ent in doc.ents:
        if ent.label_ == 'ORG':
            # Skip entities that are clearly job titles or generic terms
            entity_lower = ent.text.lower()
            if not any(word in entity_lower for word in [
                'team', 'department', 'group', 'division', 'platform', 
                'engineer', 'interview', 'application', 'position', 'role',
                'data scientist', 'product manager', 'software engineer',
                'intern', 'internship', 'software', 'engineering'
            ]):
                # For compound company names, be smarter about what to include
                entity_words = ent.text.split()
                
                # Special cases for common patterns
                if len(entity_words) == 2:
                    first, second = entity_words
                    # "Scale AI", "Lucid Software" - return just the company name part
                    if second.lower() in ['ai', 'software', 'technologies', 'systems', 'solutions', 'services']:
                        return first.title()
                    # "Software Engineering" - skip this entirely
                    elif first.lower() in ['software', 'data', 'product'] and second.lower() in ['engineering', 'science', 'management']:
                        continue
                
                # Clean the entity - take only the company part
                clean_words = []
                for word in entity_words:
                    if word.lower() in ['engineer', 'engineering', 'manager', 'developer', 'scientist', 'analyst', 'data', 'position', 'role', 'interview']:
                        break
                    # Special handling for "Technologies" - often part of company name
                    if word.lower() == 'technologies':
                        if len(clean_words) <= 2:
                            clean_words.append(word)
                        break
                    clean_words.append(word)
                
                if clean_words:
                    company_name = ' '.join(clean_words)
                    if len(company_name) > 1:
                        return company_name.title()
    
    # Method 4: Look for proper nouns at the beginning of subject
    # "Netflix Senior Engineer Position", "Amazon Web Services Interview"
    if doc[0].pos_ == 'PROPN':
        company_tokens = [doc[0].text]
        
        # Look ahead for more proper nouns but stop at job-related words
        for i in range(1, min(len(doc), 4)):
            if doc[i].pos_ == 'PROPN' and doc[i].text.lower() not in ['engineer', 'manager', 'developer', 'scientist', 'analyst']:
                # Special handling for "Cloud Platform" - likely part of job title, not company
                if doc[i].text.lower() in ['cloud', 'platform'] and i > 1:
                    break
                company_tokens.append(doc[i].text)
            else:
                break
        
        # Clean the company name
        clean_tokens = []
        for token in company_tokens:
            if token.lower() in ['cloud', 'platform', 'engineer', 'data', 'scientist']:
                break
            clean_tokens.append(token)
        
        # Only return if we have a reasonable company name
        if clean_tokens:
            company_name = ' '.join(clean_tokens)
            if len(company_name) > 1:
                return company_name.title()
    
    return None


def extract_position_from_body(body: str) -> Optional[str]:
    """
    Extract job position from full email body using spaCy NLP
    
    Args:
        body (str): Full email body text
    
    Returns:
        str: Extracted job position or None if not found
    """
    if not body:
        return None
    
    try:
        # Load spaCy transformer model (more accurate)
        nlp = spacy.load("en_core_web_trf")
    except OSError:
        try:
            # Fallback to small model
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("❌ spaCy model not found. Install with: python -m spacy download en_core_web_trf")
            return None
    
    body = body.strip()
    doc = nlp(body)
    
    # Job title patterns to look for
    job_title_keywords = [
        'engineer', 'developer', 'manager', 'analyst', 'scientist', 'designer',
        'coordinator', 'specialist', 'consultant', 'director', 'lead', 'senior',
        'junior', 'intern', 'associate', 'principal', 'staff', 'architect',
        'administrator', 'technician', 'supervisor', 'executive', 'officer',
        'representative', 'advisor', 'assistant', 'researcher'
    ]
    
    # Method 1: Look for patterns like "position of Software Engineer", "role as Data Scientist"
    for token in doc:
        if token.dep_ == 'pobj' and token.head.text.lower() in ['of', 'as', 'for']:
            # Check if the head suggests a job context
            head_context = token.head.head.text.lower() if token.head.head else ""
            if head_context in ['position', 'role', 'job', 'opening', 'opportunity']:
                if token.pos_ == 'PROPN' or any(keyword in token.text.lower() for keyword in job_title_keywords):
                    # Build the position title
                    position_tokens = [token.text]
                    
                    # Look ahead for additional tokens
                    for i in range(token.i + 1, min(len(doc), token.i + 4)):
                        next_token = doc[i]
                        if (next_token.pos_ in ['PROPN', 'NOUN', 'ADJ'] and 
                            any(keyword in next_token.text.lower() for keyword in job_title_keywords + ['senior', 'junior', 'lead', 'principal'])):
                            position_tokens.append(next_token.text)
                        else:
                            break
                    
                    position_name = ' '.join(position_tokens)
                    if len(position_name) > 2:
                        return position_name.title()
    
    # Method 2: Look for job titles in noun phrases
    for chunk in doc.noun_chunks:
        chunk_text = chunk.text.lower()
        # Check if chunk contains job-related keywords
        if any(keyword in chunk_text for keyword in job_title_keywords):
            # Filter out non-position chunks
            if not any(word in chunk_text for word in ['application', 'interview', 'team', 'company', 'process']):
                # Clean the position title
                cleaned_position = clean_position_title(chunk.text)
                if cleaned_position and is_valid_position_title(cleaned_position):
                    return cleaned_position
    
    # Method 3: Look for patterns with "Engineer", "Developer", etc. and context
    for token in doc:
        if any(keyword in token.text.lower() for keyword in job_title_keywords):
            # Look backward for modifiers (Senior, Lead, etc.)
            position_tokens = []
            
            # Check tokens before
            for i in range(max(0, token.i - 3), token.i):
                prev_token = doc[i]
                if prev_token.pos_ in ['ADJ', 'PROPN'] and prev_token.text.lower() in ['senior', 'junior', 'lead', 'principal', 'staff', 'associate']:
                    position_tokens.append(prev_token.text)
            
            # Add the main keyword
            position_tokens.append(token.text)
            
            # Look ahead for additional parts
            for i in range(token.i + 1, min(len(doc), token.i + 3)):
                next_token = doc[i]
                if (next_token.pos_ in ['PROPN', 'NOUN'] and 
                    any(keyword in next_token.text.lower() for keyword in job_title_keywords)):
                    position_tokens.append(next_token.text)
                else:
                    break
            
            if position_tokens:
                position_name = ' '.join(position_tokens)
                cleaned_position = clean_position_title(position_name)
                if cleaned_position and is_valid_position_title(cleaned_position):
                    return cleaned_position
    
    return None


def extract_position_from_preview(preview: str) -> Optional[str]:
    """
    Extract job position from email body preview/snippet using spaCy NLP
    
    Args:
        preview (str): Email body preview/snippet
    
    Returns:
        str: Extracted job position or None if not found
    """
    if not preview:
        return None
    
    try:
        # Load spaCy transformer model (more accurate)
        nlp = spacy.load("en_core_web_trf")
    except OSError:
        try:
            # Fallback to small model
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("❌ spaCy model not found. Install with: python -m spacy download en_core_web_trf")
            return None
    
    preview = preview.strip()
    doc = nlp(preview)
    
    # For previews, use simpler patterns since text is shorter
    job_title_keywords = [
        'engineer', 'developer', 'manager', 'analyst', 'scientist', 'designer',
        'coordinator', 'specialist', 'consultant', 'director', 'lead', 'senior',
        'junior', 'intern', 'associate', 'principal', 'staff', 'architect'
    ]
    
    # Method 1: Look for job titles in the preview
    for token in doc:
        if any(keyword in token.text.lower() for keyword in job_title_keywords):
            # Build position from surrounding context
            position_tokens = []
            
            # Look backward for modifiers
            start_idx = max(0, token.i - 2)
            for i in range(start_idx, token.i):
                if doc[i].pos_ in ['ADJ', 'PROPN'] and doc[i].text.lower() in ['senior', 'junior', 'lead', 'principal', 'staff']:
                    position_tokens.append(doc[i].text)
            
            # Add main token
            position_tokens.append(token.text)
            
            # Look ahead
            for i in range(token.i + 1, min(len(doc), token.i + 3)):
                next_token = doc[i]
                if (next_token.pos_ in ['PROPN', 'NOUN'] and 
                    any(keyword in next_token.text.lower() for keyword in job_title_keywords)):
                    position_tokens.append(next_token.text)
                else:
                    break
            
            if position_tokens:
                position_name = ' '.join(position_tokens)
                cleaned_position = clean_position_title(position_name)
                if cleaned_position and is_valid_position_title(cleaned_position):
                    return cleaned_position
    
    return None


def clean_position_title(position: str) -> str:
    """Clean and normalize position title"""
    if not position:
        return ""
    
    # Remove common prefixes/suffixes
    position = re.sub(r'^(the\s+|a\s+|an\s+)', '', position, flags=re.IGNORECASE)
    position = re.sub(r'\s+(position|role|job|opening|opportunity)$', '', position, flags=re.IGNORECASE)
    
    # Remove extra whitespace and normalize
    position = ' '.join(position.split())
    
    # Title case
    return position.title() if position else ""


def is_valid_position_title(position: str) -> bool:
    """Check if extracted position looks valid"""
    if not position or len(position) < 3:
        return False
    
    # Filter out common false positives
    invalid_positions = [
        'application', 'interview', 'thank you', 'your', 'next steps', 
        'update', 'status', 'confirmation', 'receipt', 'notification',
        'team', 'company', 'organization', 'department', 'office',
        'process', 'system', 'platform'
    ]
    
    return position.lower() not in invalid_positions


def extract_position_from_subject(subject: str) -> Optional[str]:
    """
    Extract job position from email subject line using spaCy NLP
    
    Args:
        subject (str): Email subject line
    
    Returns:
        str: Extracted job position or None if not found
    """
    if not subject:
        return None
    
    try:
        # Load spaCy transformer model (more accurate)
        nlp = spacy.load("en_core_web_trf")
    except OSError:
        try:
            # Fallback to small model
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("❌ spaCy model not found. Install with: python -m spacy download en_core_web_trf")
            return None
    
    subject = subject.strip()
    doc = nlp(subject)
    
    # Job title keywords
    job_title_keywords = [
        'engineer', 'developer', 'manager', 'analyst', 'scientist', 'designer',
        'coordinator', 'specialist', 'consultant', 'director', 'lead', 'senior',
        'junior', 'intern', 'associate', 'principal', 'staff', 'architect',
        'administrator', 'technician', 'supervisor', 'executive', 'officer'
    ]
    
    # Method 1: Look for patterns in subject like "SOFTWARE ENGINEER", "Data Scientist Intern"
    # Extract job titles that appear in the subject
    for token in doc:
        if any(keyword in token.text.lower() for keyword in job_title_keywords):
            # Build position from surrounding context
            position_tokens = []
            
            # Look backward for modifiers (Senior, Lead, etc.)
            start_idx = max(0, token.i - 3)
            for i in range(start_idx, token.i):
                if (doc[i].pos_ in ['ADJ', 'PROPN', 'NOUN'] and 
                    doc[i].text.lower() in ['senior', 'junior', 'lead', 'principal', 'staff', 'associate', 'software', 'data', 'product', 'technical', 'full', 'stack', 'frontend', 'backend']):
                    position_tokens.append(doc[i].text)
            
            # Add main token
            position_tokens.append(token.text)
            
            # Look ahead for additional parts
            for i in range(token.i + 1, min(len(doc), token.i + 4)):
                next_token = doc[i]
                if (next_token.pos_ in ['PROPN', 'NOUN'] and 
                    any(keyword in next_token.text.lower() for keyword in job_title_keywords + ['intern', 'internship'])):
                    position_tokens.append(next_token.text)
                else:
                    break
            
            if position_tokens:
                position_name = ' '.join(position_tokens)
                cleaned_position = clean_position_title(position_name)
                if cleaned_position and is_valid_position_title(cleaned_position):
                    return cleaned_position
    
    # Method 2: Look for job titles in parentheses or after dashes
    # "Thank you for applying – SOFTWARE ENGINEER (R_1444250)"
    for i, token in enumerate(doc):
        if token.text in ['–', '-', '('] and i < len(doc) - 1:
            # Look for job titles after the delimiter
            for j in range(i + 1, min(len(doc), i + 5)):
                if any(keyword in doc[j].text.lower() for keyword in job_title_keywords):
                    # Extract the job title sequence
                    position_tokens = []
                    for k in range(j, min(len(doc), j + 4)):
                        if (doc[k].pos_ in ['PROPN', 'NOUN', 'ADJ'] and
                            not doc[k].text in ['(', ')', 'R_', 'ID']):
                            if any(keyword in doc[k].text.lower() for keyword in job_title_keywords + ['summer', '2026', 'analyst']):
                                position_tokens.append(doc[k].text)
                            elif doc[k].text.lower() in ['summer', '2026', 'analyst']:
                                position_tokens.append(doc[k].text)
                            else:
                                break
                        else:
                            break
                    
                    if position_tokens:
                        position_name = ' '.join(position_tokens)
                        cleaned_position = clean_position_title(position_name)
                        if cleaned_position and is_valid_position_title(cleaned_position):
                            return cleaned_position
                    break
    
    return None


def extract_position(body: str = None, preview: str = None, subject: str = None) -> Optional[str]:
    """
    Parent function to extract job position from email subject, then body/preview as fallback
    
    Args:
        body (str, optional): Full email body
        preview (str, optional): Email body preview/snippet
        subject (str, optional): Email subject line
    
    Returns:
        str: Extracted job position or None if not found
    """
    # Try subject extraction FIRST (most likely to contain position title)
    if subject:
        subject_position = extract_position_from_subject(subject)
        if subject_position:
            return subject_position
    
    # Fallback to body extraction if subject didn't work
    if body:
        body_position = extract_position_from_body(body)
        if body_position:
            return body_position
    
    # Final fallback to preview extraction
    if preview:
        preview_position = extract_position_from_preview(preview)
        if preview_position:
            return preview_position
    
    return None


def extract_company(sender: str = None, subject: str = None) -> Optional[str]:
    """
    Parent function to extract company name from email sender or subject line
    
    Args:
        sender (str, optional): Email sender
        subject (str, optional): Email subject line
    
    Returns:
        str: Extracted company name or None if not found
    """
    sender_company = None
    subject_company = None
    
    # Try both extraction methods
    if sender:
        sender_company = extract_company_from_sender(sender)
    
    if subject:
        subject_company = extract_company_from_email(subject)
    
    # Define generic/unreliable company names to deprioritize
    generic_companies = [
        'greenhouse', 'workday', 'myworkday', 'lever', 'bamboohr', 'smartrecruiters',
        'icims', 'jobvite', 'taleo', 'cornerstone', 'successfactors', 'talent',
        'ashbyhq', 'ripplematch', 'mail', 'noreply', 'jobs', 'careers', 'hiring', 'hr',
        'software', 'intern', 'engineering', 'engineer', 'developer', 'manager',
        'us', 'no', 'system', 'notification', 'notifications'
    ]
    
    # If we have both results, choose the better one
    if sender_company and subject_company:
        # Prefer subject company if sender company is generic
        if sender_company.lower() in generic_companies:
            return subject_company
        # Prefer sender company if subject company is generic
        elif subject_company.lower() in generic_companies:
            return sender_company
        # If both are good, prefer subject (more specific to the job)
        else:
            return subject_company
    
    # If only one result, check if it's not too generic
    if subject_company:
        return subject_company
    
    if sender_company and sender_company.lower() not in generic_companies:
        return sender_company
    
    return None
