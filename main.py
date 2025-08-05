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
    parser.add_argument('--debug-prompt', action='store_true',
                       help='Show full prompt sent to LLM (implies --debug)')
    parser.add_argument('--emails', type=int, metavar='N',
                       help='Number of emails to process (overrides .env MAX_EMAILS_TO_PROCESS)')
    args = parser.parse_args()
    
    # --debug-prompt implies --debug
    if args.debug_prompt:
        args.debug = True
    
    # Override MAX_EMAILS_TO_PROCESS if --emails is specified
    if args.emails:
        import os
        os.environ['MAX_EMAILS_TO_PROCESS'] = str(args.emails)
    
    setup_logging()
    if args.dry_run:
        logging.info("Starting fdsmp - spam filter (DRY RUN MODE)")
    else:
        logging.info("Starting fdsmp - spam filter")
    
    email_client = EmailClient()
    text_extractor = TextExtractor()
    spam_classifier = SpamClassifier(debug=args.debug, debug_prompt=args.debug_prompt)
    
    try:
        if not email_client.connect():
            logging.error("Failed to connect to email server")
            return 1
        
        # PHASE 1: FETCH - Get emails and disconnect IMAP
        logging.info("=== PHASE 1: FETCHING EMAILS ===")
        emails = email_client.fetch_latest_emails()
        if not emails:
            logging.info("No emails to process")
            return 0
        
        # Disconnect IMAP to avoid timeouts during LLM processing
        email_client.disconnect()
        logging.info("Disconnected from IMAP server for offline processing")
        
        # PHASE 2: CLASSIFY - Offline LLM processing (no IMAP timeouts)
        logging.info("=== PHASE 2: CLASSIFYING EMAILS (OFFLINE) ===")
        spam_email_uids = []
        processed_count = 0
        
        for email_data in emails:
            try:
                from email.header import decode_header
                
                # Decode subject for display
                subject = email_data['subject']
                try:
                    decoded_parts = decode_header(subject)
                    decoded_subject = ""
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            decoded_subject += part
                    subject = decoded_subject.strip()
                except:
                    pass
                
                # Decode sender for display  
                sender = email_data['from']
                try:
                    decoded_parts = decode_header(sender)
                    decoded_sender = ""
                    for part, encoding in decoded_parts:
                        if isinstance(part, bytes):
                            decoded_sender += part.decode(encoding or 'utf-8', errors='ignore')
                        else:
                            decoded_sender += part
                    sender = decoded_sender.strip()
                except:
                    pass
                
                processed_count += 1
                logging.info(f"Processing email {processed_count}/{len(emails)}:")
                logging.info(f"  From: {sender}")
                logging.info(f"  Subject: {subject[:50]}{'...' if len(subject) > 50 else ''}")
                
                email_text = text_extractor.prepare_email_for_analysis(email_data)
                
                classification = spam_classifier.classify_email(email_text)
                
                if classification == "spam":
                    # Collect spam email UID for later batch move operation
                    spam_email_uids.append({
                        'uid': email_data['id'],
                        'subject': subject[:50] + ('...' if len(subject) > 50 else ''),
                        'sender': sender
                    })
                    logging.info(f"Marked as spam (will move later): {subject[:50]}{'...' if len(subject) > 50 else ''}")
                else:
                    logging.info(f"Email is not spam: {subject[:50]}{'...' if len(subject) > 50 else ''}")
                    
            except SystemExit:
                raise  # Re-raise SystemExit to allow proper shutdown
            except Exception as e:
                logging.error(f"FATAL: Error processing email {email_data.get('subject', 'Unknown')}: {e}")
                raise SystemExit(f"FATAL: Email processing failed: {e}")
        
        # PHASE 3: MOVE - Reconnect and batch move spam emails
        spam_count = len(spam_email_uids)
        if spam_count > 0:
            logging.info(f"=== PHASE 3: MOVING {spam_count} SPAM EMAILS ===")
            
            if args.dry_run:
                logging.info("[DRY RUN] Would move the following spam emails:")
                for spam_email in spam_email_uids:
                    logging.info(f"  - {spam_email['subject']} (from {spam_email['sender']})")
                logging.info(f"Processing complete. {spam_count} emails classified as spam (not moved).")
            else:
                # Reconnect to IMAP for batch move operation
                if not email_client.connect():
                    logging.error("Failed to reconnect to email server for spam move operation")
                    return 1
                
                moved_count = 0
                for spam_email in spam_email_uids:
                    try:
                        if email_client.move_to_spam(spam_email['uid']):
                            moved_count += 1
                            logging.info(f"Moved spam email: {spam_email['subject']}")
                        else:
                            logging.error(f"Failed to move spam email: {spam_email['subject']}")
                    except Exception as e:
                        logging.error(f"Error moving spam email UID {spam_email['uid']}: {e}")
                
                logging.info(f"Processing complete. {moved_count}/{spam_count} emails moved to spam folder.")
        else:
            logging.info("=== PHASE 3: NO SPAM EMAILS TO MOVE ===")
            logging.info("Processing complete. No spam emails found.")
        
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        return 1
        
    finally:
        # Only disconnect if we have an active connection
        if email_client.connection:
            email_client.disconnect()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
