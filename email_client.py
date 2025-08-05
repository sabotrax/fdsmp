import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv
import logging

load_dotenv()

class EmailClient:
    def __init__(self):
        self.server = os.getenv('IMAP_SERVER')
        self.port = int(os.getenv('IMAP_PORT', 993))
        self.username = os.getenv('IMAP_USERNAME')
        self.password = os.getenv('IMAP_PASSWORD')
        self.inbox_folder = os.getenv('INBOX_FOLDER', 'INBOX')
        self.spam_folder = os.getenv('SPAM_FOLDER', 'SPAM')
        self.max_emails = int(os.getenv('MAX_EMAILS_TO_PROCESS', 3))
        self.connection = None
        
    def connect(self) -> bool:
        try:
            self.connection = imaplib.IMAP4_SSL(self.server, self.port)
            self.connection.login(self.username, self.password)
            logging.info(f"Connected to {self.server}")
            return True
        except Exception as e:
            logging.error(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        if self.connection:
            try:
                # Only close if we have an active mailbox selected
                if hasattr(self.connection, 'state') and self.connection.state == 'SELECTED':
                    self.connection.close()
                self.connection.logout()
            except Exception as e:
                logging.debug(f"Error during IMAP disconnect: {e}")
            finally:
                self.connection = None
                logging.info("Disconnected from IMAP server")
    
    def fetch_latest_emails(self) -> List[Dict]:
        if not self.connection:
            raise Exception("Not connected to server")
        
        try:
            self.connection.select(self.inbox_folder)
            
            # Use UID SEARCH instead of regular search for persistent IDs
            status, messages = self.connection.uid('search', None, 'ALL')
            if status != 'OK':
                raise Exception("Failed to search emails")
            
            email_uids = messages[0].split()
            latest_uids = email_uids[-self.max_emails:] if len(email_uids) >= self.max_emails else email_uids
            
            emails = []
            for email_uid in latest_uids:
                # Use UID FETCH instead of regular fetch
                status, msg_data = self.connection.uid('fetch', email_uid, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    emails.append({
                        'id': email_uid.decode(),  # Now stores UID instead of sequence number
                        'subject': email_message.get('Subject', ''),
                        'from': email_message.get('From', ''),
                        'to': email_message.get('To', ''),
                        'message': email_message
                    })
            
            logging.info(f"Fetched {len(emails)} emails")
            return emails
            
        except Exception as e:
            logging.error(f"FATAL: Failed to fetch emails from IMAP server: {e}")
            raise SystemExit(f"FATAL: IMAP fetch failed: {e}")
    
    def move_to_spam(self, email_uid: str) -> bool:
        """Move email to spam folder using UID (persistent identifier)"""
        if not self.connection:
            raise Exception("Not connected to server")
        
        try:
            self.connection.select(self.inbox_folder)
            
            # Use UID COPY and UID STORE for persistent operations
            result = self.connection.uid('copy', email_uid, self.spam_folder)
            if result[0] != 'OK':
                raise Exception(f"UID COPY failed: {result}")
            
            result = self.connection.uid('store', email_uid, '+FLAGS', '\\Deleted')
            if result[0] != 'OK':
                raise Exception(f"UID STORE failed: {result}")
                
            self.connection.expunge()
            
            logging.info(f"Moved email UID {email_uid} to spam folder")
            return True
            
        except Exception as e:
            logging.error(f"FATAL: Failed to move email UID {email_uid} to spam folder: {e}")
            raise SystemExit(f"FATAL: Failed to move spam email: {e}")