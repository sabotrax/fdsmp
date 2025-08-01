#!/usr/bin/env python3

import argparse
import logging
import sys
from email_client import EmailClient
from text_extractor import TextExtractor
from spam_classifier import SpamClassifier

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('fdsmp.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    parser = argparse.ArgumentParser(description='fdsmp - automated spam filter')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Classify emails but do not move them to spam folder')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging for LLM classification')
    args = parser.parse_args()
    
    setup_logging()
    if args.dry_run:
        logging.info("Starting fdsmp - spam filter (DRY RUN MODE)")
    else:
        logging.info("Starting fdsmp - spam filter")
    
    email_client = EmailClient()
    text_extractor = TextExtractor()
    spam_classifier = SpamClassifier(debug=args.debug)
    
    try:
        if not email_client.connect():
            logging.error("Failed to connect to email server")
            return 1
        
        emails = email_client.fetch_latest_emails()
        if not emails:
            logging.info("No emails to process")
            return 0
        
        spam_count = 0
        for email_data in emails:
            try:
                logging.info(f"Processing email:")
                logging.info(f"  From: {email_data['from']}")
                logging.info(f"  Subject: {email_data['subject'][:50]}{'...' if len(email_data['subject']) > 50 else ''}")
                
                email_text = text_extractor.prepare_email_for_analysis(email_data)
                
                classification = spam_classifier.classify_email(email_text)
                
                if classification == "spam":
                    if args.dry_run:
                        logging.info(f"[DRY RUN] Would move spam email: {email_data['subject'][:50]}")
                        spam_count += 1
                    else:
                        if email_client.move_to_spam(email_data['id']):
                            spam_count += 1
                            logging.info(f"Moved spam email to spam folder: {email_data['subject'][:50]}")
                        else:
                            logging.error(f"Failed to move spam email: {email_data['subject'][:50]}")
                else:
                    logging.info(f"Email is not spam: {email_data['subject'][:50]}")
                    
            except SystemExit:
                raise  # Re-raise SystemExit to allow proper shutdown
            except Exception as e:
                logging.error(f"FATAL: Error processing email {email_data.get('subject', 'Unknown')}: {e}")
                raise SystemExit(f"FATAL: Email processing failed: {e}")
        
        if args.dry_run:
            logging.info(f"Processing complete. {spam_count} emails classified as spam (not moved).")
        else:
            logging.info(f"Processing complete. {spam_count} emails moved to spam folder.")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1
        
    finally:
        email_client.disconnect()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
