#!/usr/bin/env python3

import os
import json
import logging
import sys
import argparse
from datetime import datetime
from pathlib import Path
from email.header import decode_header
from dotenv import load_dotenv
from email_client import EmailClient
from text_extractor import TextExtractor

load_dotenv()

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def decode_email_subject(subject):
    """Decode email subject from encoded format"""
    if not subject:
        return "No_Subject"
    
    try:
        decoded_parts = decode_header(subject)
        decoded_subject = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_subject += part
        return decoded_subject.strip()
    except:
        return subject

def sanitize_filename(text, max_length=30):
    """Sanitize text for use as filename"""
    # First decode if it's an encoded email subject
    text = decode_email_subject(text)
    
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*äöüßÄÖÜ'
    for char in invalid_chars:
        text = text.replace(char, '_')
    
    # Replace special characters
    text = text.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
    text = text.replace('Ä', 'Ae').replace('Ö', 'Oe').replace('Ü', 'Ue')
    text = text.replace('ß', 'ss')
    
    # Remove excessive whitespace and truncate
    text = ' '.join(text.split()).replace(' ', '_')
    if len(text) > max_length:
        text = text[:max_length]
    
    return text or "email"

def extract_emails_to_files(max_emails=None):
    """Extract latest emails and save each to individual files in data/ directory"""
    setup_logging()
    if max_emails:
        logging.info(f"Starting email extraction to data/ directory (limit: {max_emails} emails)")
    else:
        logging.info("Starting email extraction to data/ directory")
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    logging.info(f"Using data directory: {data_dir.absolute()}")
    
    email_client = EmailClient()
    text_extractor = TextExtractor()
    
    try:
        # Connect to email server
        if not email_client.connect():
            logging.error("Failed to connect to email server")
            return 1
        
        logging.info("Connected to email server")
        
        # Fetch emails
        emails = email_client.fetch_latest_emails()
        if not emails:
            logging.info("No emails found")
            return 0
        
        logging.info(f"Fetched {len(emails)} emails")
        
        # Process each email
        for i, email_data in enumerate(emails, 1):
            try:
                subject = email_data.get('subject', 'No Subject')
                sender = email_data.get('from', 'Unknown Sender')
                email_id = email_data.get('id', str(i))
                
                # Decode subject for display
                decoded_subject = decode_email_subject(subject)
                
                logging.info(f"Processing email {i}/{len(emails)}: {decoded_subject[:50]}...")
                
                # Extract text content
                email_text = text_extractor.prepare_email_for_analysis(email_data)
                
                # Create filename from email ID
                filename = f"email_{email_id}.txt"
                
                # Create timestamp for metadata
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                # Create email data structure
                email_info = {
                    "id": email_id,
                    "subject": subject,
                    "from": sender,
                    "to": email_data.get('to', ''),
                    "timestamp": timestamp,
                    "extracted_text": email_text,
                    "text_length": len(email_text),
                    "classification": "unknown"
                }
                
                # Save to file as pure JSON
                file_path = data_dir / filename
                
                # Create JSON object
                clean_text = email_text.replace('\r\n', '\n').replace('\r', '\n')
                email_json = {
                    "email": clean_text,
                    "classification": "typ_1_or_typ_2"
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(email_json, f, indent=2, ensure_ascii=False)
                
                logging.info(f"Saved: {filename}")
                
            except SystemExit:
                raise  # Re-raise SystemExit to allow proper shutdown
            except Exception as e:
                logging.error(f"FATAL: Failed to process email {i}: {e}")
                raise SystemExit(f"FATAL: Email extraction failed: {e}")
        
        logging.info(f"Email extraction completed. Files saved in {data_dir.absolute()}")
        logging.info("Manual steps:")
        logging.info("1. Review files in data/ directory")
        logging.info("2. For spam/ham emails, copy the JSON snippet at the end of each file")
        spam_examples_file = os.getenv('SPAM_EXAMPLES_FILE', 'spam_examples.json')
        logging.info(f"3. Add to {spam_examples_file} manually (typ 1 = not spam, typ 2 = spam)")
        
    except Exception as e:
        logging.error(f"Email extraction failed: {e}")
        return 1
        
    finally:
        email_client.disconnect()
    
    return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract emails to data/ directory for analysis')
    parser.add_argument('--emails', type=int, metavar='N',
                       help='Number of emails to extract (overrides .env MAX_EMAILS_TO_PROCESS)')
    args = parser.parse_args()
    
    # Override MAX_EMAILS_TO_PROCESS if --emails is specified
    if args.emails:
        os.environ['MAX_EMAILS_TO_PROCESS'] = str(args.emails)
    
    exit_code = extract_emails_to_files(max_emails=args.emails)
    print(f"\nExtraction completed with exit code: {exit_code}")
    sys.exit(exit_code)