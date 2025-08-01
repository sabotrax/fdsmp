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
            self.connection.close()
            self.connection.logout()
            logging.info("Disconnected from IMAP server")
    
    def fetch_latest_emails(self) -> List[Dict]:
        if not self.connection:
            raise Exception("Not connected to server")
        
        try:
            self.connection.select(self.inbox_folder)
            
            status, messages = self.connection.search(None, 'ALL')
            if status != 'OK':
                raise Exception("Failed to search emails")
            
            email_ids = messages[0].split()
            latest_ids = email_ids[-self.max_emails:] if len(email_ids) >= self.max_emails else email_ids
            
            emails = []
            for email_id in latest_ids:
                status, msg_data = self.connection.fetch(email_id, '(RFC822)')
                if status == 'OK':
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)
                    
                    emails.append({
                        'id': email_id.decode(),
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
    
    def move_to_spam(self, email_id: str) -> bool:
        if not self.connection:
            raise Exception("Not connected to server")
        
        try:
            self.connection.select(self.inbox_folder)
            
            self.connection.copy(email_id, self.spam_folder)
            self.connection.store(email_id, '+FLAGS', '\\Deleted')
            self.connection.expunge()
            
            logging.info(f"Moved email {email_id} to spam folder")
            return True
            
        except Exception as e:
            logging.error(f"FATAL: Failed to move email {email_id} to spam folder: {e}")
            raise SystemExit(f"FATAL: Failed to move spam email: {e}")