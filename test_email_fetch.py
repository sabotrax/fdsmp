#!/usr/bin/env python3

import logging
import sys
import os
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

def test_email_fetch():
    """Test script to fetch and display emails without classification"""
    setup_logging()
    logging.info("Starting email fetch test")
    
    # Display configuration
    logging.info(f"IMAP Server: {os.getenv('IMAP_SERVER')}")
    logging.info(f"IMAP Port: {os.getenv('IMAP_PORT', 993)}")
    logging.info(f"IMAP Username: {os.getenv('IMAP_USERNAME')}")
    logging.info(f"Inbox Folder: {os.getenv('INBOX_FOLDER', 'INBOX')}")
    logging.info(f"Max Emails: {os.getenv('MAX_EMAILS_TO_PROCESS', 3)}")
    
    email_client = EmailClient()
    text_extractor = TextExtractor()
    
    try:
        # Test connection
        logging.info("Testing IMAP connection...")
        if not email_client.connect():
            logging.error("Failed to connect to email server")
            return 1
        
        logging.info("✓ IMAP connection successful")
        
        # Test email fetching
        logging.info("Fetching latest emails...")
        emails = email_client.fetch_latest_emails()
        
        if not emails:
            logging.info("No emails found in inbox")
            return 0
        
        logging.info(f"✓ Fetched {len(emails)} emails")
        
        # Display email details
        for i, email_data in enumerate(emails, 1):
            print(f"\n{'='*60}")
            print(f"EMAIL {i}/{len(emails)}")
            print(f"{'='*60}")
            print(f"Subject: {email_data['subject']}")
            print(f"From: {email_data['from']}")
            print(f"To: {email_data['to']}")
            print(f"ID: {email_data['id']}")
            
            # Extract and display text content
            try:
                email_text = text_extractor.prepare_email_for_analysis(email_data)
                print(f"\nExtracted Content (first 500 chars):")
                print("-" * 40)
                print(email_text[:500])
                if len(email_text) > 500:
                    print(f"\n... (truncated, total length: {len(email_text)} chars)")
                print("-" * 40)
                
            except Exception as e:
                logging.error(f"Failed to extract text from email: {e}")
        
        logging.info("✓ Email fetch and display test completed successfully")
        
    except Exception as e:
        logging.error(f"Test failed: {e}")
        return 1
        
    finally:
        email_client.disconnect()
    
    return 0

if __name__ == "__main__":
    exit_code = test_email_fetch()
    print(f"\nTest completed with exit code: {exit_code}")
    sys.exit(exit_code)