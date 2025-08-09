import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from bs4 import BeautifulSoup
import logging
import os
from dotenv import load_dotenv

load_dotenv()

class TextExtractor:
    @staticmethod
    def _clean_invisible_chars(text: str) -> str:
        """Remove invisible Unicode characters commonly used in email tracking"""
        invisible_chars = [
            '\u034F',  # Combining Grapheme Joiner
            '\u200C',  # Zero Width Non-Joiner  
            '\u200D',  # Zero Width Joiner
            '\u200B',  # Zero Width Space
            '\uFEFF',  # Zero Width No-Break Space
            '\u2060',  # Word Joiner
            '\u180E',  # Mongolian Vowel Separator
            '\u00AD',  # Soft Hyphen
        ]
        
        cleaned_text = text
        for char in invisible_chars:
            cleaned_text = cleaned_text.replace(char, '')
        
        # Remove excessive whitespace that may result from removed characters
        cleaned_text = ' '.join(cleaned_text.split())
        
        return cleaned_text
    
    @staticmethod
    def _remove_links_from_html(html_content: str) -> str:
        """Remove various types of links from HTML content before text extraction"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove link tags but keep text content
            for tag in soup.find_all('a'):
                tag.unwrap()
            
            # Remove images completely
            for tag in soup.find_all('img'):
                tag.decompose()
            
            # Remove CSS/Script references
            for tag in soup.find_all(['link', 'script', 'style']):
                tag.decompose()
            
            # Remove tracking pixels and other media
            for tag in soup.find_all(['video', 'audio', 'iframe', 'embed', 'object']):
                tag.decompose()
            
            # Remove meta tags with URLs
            for tag in soup.find_all('meta'):
                tag.decompose()
            
            # Remove base tags
            for tag in soup.find_all('base'):
                tag.decompose()
            
            return str(soup)
            
        except Exception as e:
            logging.warning(f"Failed to remove links from HTML: {e}")
            return html_content  # Return original if cleaning fails
    
    @staticmethod
    def extract_text_from_email(email_message: email.message.Message) -> str:
        try:
            text_content = ""
            
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition"))
                    
                    if content_type == "text/html" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_content = payload.decode('utf-8', errors='ignore')
                            cleaned_html = TextExtractor._remove_links_from_html(html_content)
                            soup = BeautifulSoup(cleaned_html, 'html.parser')
                            raw_text = soup.get_text(separator=' ', strip=True)
                            clean_text = TextExtractor._clean_invisible_chars(raw_text)
                            text_content += clean_text + "\n"
            else:
                content_type = email_message.get_content_type()
                payload = email_message.get_payload(decode=True)
                
                if payload:
                    if content_type == "text/html":
                        html_content = payload.decode('utf-8', errors='ignore')
                        cleaned_html = TextExtractor._remove_links_from_html(html_content)
                        soup = BeautifulSoup(cleaned_html, 'html.parser')
                        raw_text = soup.get_text(separator=' ', strip=True)
                        text_content = TextExtractor._clean_invisible_chars(raw_text)
            
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
        
        # Extract body text and truncate to configured length
        body_text = TextExtractor.extract_text_from_email(email_data['message'])
        body_length = int(os.getenv('MAIL_BODY_LENGTH', 200))
        
        if body_text:
            truncated_body = body_text[:body_length].strip()
            analysis_text = f"""Subject: {subject}
From: {sender}
Body: {truncated_body}""".strip()
        else:
            # Fallback if no body text extracted
            analysis_text = f"""Subject: {subject}
From: {sender}""".strip()
        
        return analysis_text