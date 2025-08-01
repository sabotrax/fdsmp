#!/usr/bin/env python3

import os
import json
import logging
import sys
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

def extract_emails_to_files():
    """Extract latest emails and save each to individual files in data/ directory"""
    setup_logging()
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
                
                logging.info(f"Processing email {i}/{len(emails)}: {subject[:50]}...")
                
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
                
                # Save to file
                file_path = data_dir / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Write header with metadata
                    f.write("=" * 80 + "\n")
                    f.write(f"EMAIL EXTRACTION - {timestamp}\n")
                    f.write("=" * 80 + "\n")
                    f.write(f"Subject: {subject}\n")
                    f.write(f"From: {sender}\n")
                    f.write(f"To: {email_data.get('to', '')}\n")
                    f.write(f"Email ID: {email_id}\n")
                    f.write(f"Text Length: {len(email_text)} characters\n")
                    f.write("-" * 80 + "\n")
                    f.write("EXTRACTED TEXT FOR SPAM CLASSIFICATION:\n")
                    f.write("-" * 80 + "\n")
                    f.write(email_text)
                    f.write("\n" + "-" * 80 + "\n")
                    f.write("CLASSIFICATION: unknown (manually set to 'spam' or 'not spam')\n")
                    f.write("-" * 80 + "\n")
                    f.write("\nTo add to spam_examples.json:\n")
                    f.write("{\n")
                    # Remove Windows line endings and clean up text
                    clean_text = email_text.replace('\r\n', '\n').replace('\r', '\n')
                    escaped_text = clean_text.replace('"', '\\"').replace('\n', '\\n')
                    f.write(f'  "email": "{escaped_text}",\n')
                    f.write('  "classification": "spam_or_not_spam"\n')
                    f.write("}\n")
                
                logging.info(f"Saved: {filename}")
                
            except SystemExit:
                raise  # Re-raise SystemExit to allow proper shutdown
            except Exception as e:
                logging.error(f"FATAL: Failed to process email {i}: {e}")
                raise SystemExit(f"FATAL: Email extraction failed: {e}")
        
        logging.info(f"Email extraction completed. Files saved in {data_dir.absolute()}")
        logging.info("Manual steps:")
        logging.info("1. Review files in data/ directory")
        logging.info("2. For spam emails, copy the JSON snippet at the end of each file")
        logging.info("3. Add to spam_examples.json manually")
        
    except Exception as e:
        logging.error(f"Email extraction failed: {e}")
        return 1
        
    finally:
        email_client.disconnect()
    
    return 0

if __name__ == "__main__":
    exit_code = extract_emails_to_files()
    print(f"\nExtraction completed with exit code: {exit_code}")
    sys.exit(exit_code)