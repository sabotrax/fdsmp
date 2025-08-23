#!/usr/bin/env python3

import os
import imaplib
from dotenv import load_dotenv

load_dotenv()


def test_imap_folders():
    """Test IMAP connection and list all available folders"""

    # Get IMAP settings from .env
    imap_server = os.getenv("IMAP_SERVER")
    imap_port = int(os.getenv("IMAP_PORT", 993))
    username = os.getenv("IMAP_USERNAME")
    password = os.getenv("IMAP_PASSWORD")
    spam_folder = os.getenv("SPAM_FOLDER", "SPAM")

    print(f"Testing IMAP connection to {imap_server}:{imap_port}")
    print(f"Username: {username}")
    print(f"Configured SPAM folder: {spam_folder}")
    print("-" * 50)

    try:
        # Connect to IMAP server
        connection = imaplib.IMAP4_SSL(imap_server, imap_port)
        connection.login(username, password)
        print("✓ IMAP connection successful")

        # List all folders
        print("\nAvailable folders:")
        folders = connection.list()

        if folders[0] == "OK":
            folder_list = []
            for folder_data in folders[1]:
                # Parse folder name from IMAP response
                folder_info = folder_data.decode("utf-8")
                print(f"  Raw: {folder_info}")

                # Extract folder name (last part after hierarchy delimiter)
                # Format: (flags) "delimiter" "folder_name" or (flags) "delimiter" folder_name
                parts = folder_info.split(' "/"')
                if len(parts) == 2:
                    # Extract folder name part
                    folder_part = parts[1].strip()
                    if folder_part.startswith('"') and folder_part.endswith('"'):
                        folder_name = folder_part[1:-1]  # Remove quotes
                    else:
                        folder_name = folder_part
                    folder_list.append(folder_name)
                    print(f"    -> Parsed: {folder_name}")
                else:
                    print("    -> Could not parse folder name")

            print(f"\nTotal folders found: {len(folder_list)}")

            # Check if configured SPAM folder exists
            if spam_folder in folder_list:
                print(f"✓ Configured SPAM folder '{spam_folder}' exists")

                # Try to select it
                try:
                    result = connection.select(spam_folder)
                    if result[0] == "OK":
                        print(f"✓ Can select SPAM folder '{spam_folder}'")
                        email_count = int(result[1][0])
                        print(f"  Emails in SPAM folder: {email_count}")
                    else:
                        print(f"✗ Cannot select SPAM folder '{spam_folder}': {result}")
                except Exception as e:
                    print(f"✗ Error selecting SPAM folder '{spam_folder}': {e}")
            else:
                print(f"✗ Configured SPAM folder '{spam_folder}' NOT FOUND")
                print("\nPossible SPAM folder names:")
                spam_candidates = [
                    f for f in folder_list if "spam" in f.lower() or "junk" in f.lower()
                ]
                if spam_candidates:
                    for candidate in spam_candidates:
                        print(f"  - {candidate}")
                else:
                    print("  No obvious SPAM folder candidates found")
        else:
            print(f"✗ Failed to list folders: {folders}")

        connection.logout()
        print("\n✓ IMAP connection closed")

    except Exception as e:
        print(f"✗ IMAP test failed: {e}")
        return False

    return True


if __name__ == "__main__":
    print("IMAP Folder Test")
    print("=" * 50)
    success = test_imap_folders()
    exit_code = 0 if success else 1
    print(f"\nTest completed with exit code: {exit_code}")
