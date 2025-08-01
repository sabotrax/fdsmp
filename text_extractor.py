import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import logging

class TextExtractor:
    @staticmethod
    def extract_text_from_email(email_message: email.message.Message) -> str:
        try:
            text_content = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            text_content += payload.decode('utf-8', errors='ignore') + "\n"
                    
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            soup = BeautifulSoup(html_content, 'html.parser')
                            text_content += soup.get_text(separator=' ', strip=True) + "\n"
            else:
                content_type = email_message.get_content_type()
                payload = email_message.get_payload(decode=True)
                
                if payload:
                    if content_type == "text/plain":
                        text_content = payload.decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        html_content = payload.decode('utf-8', errors='ignore')
                        soup = BeautifulSoup(html_content, 'html.parser')
                        text_content = soup.get_text(separator=' ', strip=True)
            
            text_content = text_content.strip()
            logging.debug(f"Extracted text length: {len(text_content)} characters")
            return text_content
            
        except Exception as e:
            logging.error(f"FATAL: Failed to extract text from email: {e}")
            raise SystemExit(f"FATAL: Text extraction failed: {e}")
    
    @staticmethod
    def prepare_email_for_analysis(email_data: dict) -> str:
        from email.header import decode_header
        
        # Decode subject and sender
        subject = email_data.get('subject', '')
        sender = email_data.get('from', '')
        
        # Decode subject
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
            pass  # Keep original if decode fails
        
        # Decode sender
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
            pass  # Keep original if decode fails
        
        # Only use Subject and From for classification (no content)
        analysis_text = f"""Subject: {subject}
From: {sender}""".strip()
        
        return analysis_text