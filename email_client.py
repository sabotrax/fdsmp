import imaplib
import email
import os
from typing import List, Dict
from dotenv import load_dotenv
import logging

load_dotenv()


class EmailClient:
    def __init__(self, debug=False):
        self.server = os.getenv("IMAP_SERVER")
        self.port = int(os.getenv("IMAP_PORT", 993))
        self.username = os.getenv("IMAP_USERNAME")
        self.password = os.getenv("IMAP_PASSWORD")
        self.inbox_folder = os.getenv("INBOX_FOLDER", "INBOX")
        self.spam_folder = os.getenv("SPAM_FOLDER", "SPAM")
        self.max_emails = int(os.getenv("MAX_EMAILS_TO_PROCESS", 3))
        self.debug = debug
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
                if (
                    hasattr(self.connection, "state")
                    and self.connection.state == "SELECTED"
                ):
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
            status, messages = self.connection.uid("search", None, "ALL")
            if status != "OK":
                raise Exception("Failed to search emails")

            email_uids = messages[0].split()
            latest_uids = (
                email_uids[-self.max_emails :]
                if len(email_uids) >= self.max_emails
                else email_uids
            )

            emails = []
            for email_uid in latest_uids:
                # Use UID FETCH instead of regular fetch
                status, msg_data = self.connection.uid("fetch", email_uid, "(RFC822)")
                if status == "OK":
                    raw_email = msg_data[0][1]
                    email_message = email.message_from_bytes(raw_email)

                    emails.append(
                        {
                            "id": email_uid.decode(),  # Now stores UID instead of sequence number
                            "subject": email_message.get("Subject", ""),
                            "from": email_message.get("From", ""),
                            "to": email_message.get("To", ""),
                            "message": email_message,
                        }
                    )

            logging.info(f"Fetched {len(emails)} emails")
            return emails

        except Exception as e:
            logging.error(f"FATAL: Failed to fetch emails from IMAP server: {e}")
            raise SystemExit(f"FATAL: IMAP fetch failed: {e}")

    def move_to_spam(self, email_uid: str) -> tuple[bool, str]:
        """
        Move email to spam folder using UID (persistent identifier)

        Returns:
            tuple[bool, str]: (success, error_message)
            - (True, "") if successful
            - (False, error_description) if failed
        """
        if not self.connection:
            return False, "Not connected to server"

        try:
            # First check if email still exists in inbox
            select_result = self.connection.select(self.inbox_folder)
            if select_result[0] != "OK":
                return False, f"Cannot select inbox folder: {select_result[1]}"

            # Check if UID still exists
            search_result = self.connection.uid("search", None, f"UID {email_uid}")
            if search_result[0] != "OK" or not search_result[1][0]:
                return (
                    False,
                    f"Email UID {email_uid} not found (may have been moved/deleted by user)",
                )

            # Use UID COPY and UID STORE for persistent operations
            copy_result = self.connection.uid("copy", email_uid, self.spam_folder)
            if copy_result[0] != "OK":
                error_msg = (
                    copy_result[1][0].decode() if copy_result[1] else "Unknown error"
                )
                return False, f"UID COPY failed: {error_msg}"

            store_result = self.connection.uid(
                "store", email_uid, "+FLAGS", "\\Deleted"
            )
            if store_result[0] != "OK":
                error_msg = (
                    store_result[1][0].decode() if store_result[1] else "Unknown error"
                )
                return False, f"UID STORE failed: {error_msg}"

            self.connection.expunge()

            if self.debug:
                logging.info(f"Moved email UID {email_uid} to spam folder")
            return True, ""

        except Exception as e:
            return False, f"IMAP operation failed: {str(e)}"
