import imaplib
import email
from email.header import decode_header
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
import chardet

# Load environment variables from .env file
load_dotenv()

# Email credentials from environment variables
EMAIL = os.getenv('EMAIL')
PASSWORD = os.getenv('EMAIL_PASSWORD')
IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
NOTIFICATION_EMAIL = os.getenv('NOTIFICATION_EMAIL')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))

# Limit number of emails to process
MAX_EMAILS = 10

# Keywords in German
NEGATIVE_KEYWORDS = ["leider", "abgelehnt", "nicht möglich", "bedauern"]
POSITIVE_KEYWORDS = ["herzlichen glückwunsch", "zusage", "erfolgreich", "willkommen"]

def decode_content(content):
    """Decode content using chardet if utf-8 fails."""
    if content is None:
        return ""
    
    # First try utf-8
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            # Use chardet to detect encoding
            detected = chardet.detect(content)
            if detected['encoding']:
                return content.decode(detected['encoding'])
        except Exception:
            pass
        
        # If all else fails, try common encodings
        for encoding in ['latin-1', 'iso-8859-1', 'cp1252', 'windows-1252']:
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
    
    return ""

def send_notification(subject, message):
    """Send a notification email."""
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL
        msg["To"] = NOTIFICATION_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL, PASSWORD)
            server.sendmail(EMAIL, NOTIFICATION_EMAIL, msg.as_string())
        print(f"Notification sent: {subject}")
    except Exception as e:
        print(f"Error sending notification: {str(e)}")

def check_email():
    """Check emails for positive or negative keywords."""
    try:
        print("Connecting to email server...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")

        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            print("No new emails.")
            return

        email_ids = messages[0].split()
        # Get the last MAX_EMAILS emails
        email_ids = email_ids[-MAX_EMAILS:]
        
        print(f"Processing last {len(email_ids)} unread emails...")

        for mail_id in email_ids:
            try:
                print(f"\nChecking email ID: {mail_id.decode()}")
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Decode subject
                        subject_parts = decode_header(msg["Subject"])[0]
                        subject = subject_parts[0]
                        if isinstance(subject, bytes):
                            subject = decode_content(subject)
                        elif not isinstance(subject, str):
                            subject = str(subject)
                            
                        print(f"Processing email: {subject}")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        content = part.get_payload(decode=True)
                                        if content:
                                            decoded_content = decode_content(content)
                                            if decoded_content:
                                                body = decoded_content
                                                break
                                    except Exception as e:
                                        print(f"Error processing email part: {str(e)}")
                                        continue
                        else:
                            try:
                                content = msg.get_payload(decode=True)
                                if content:
                                    body = decode_content(content)
                            except Exception as e:
                                print(f"Error processing email body: {str(e)}")

                        if body:
                            body_lower = body.lower()

                            # Check for keywords
                            if any(keyword in body_lower for keyword in NEGATIVE_KEYWORDS):
                                print(f"Negative email detected: {subject}")
                                send_notification(
                                    "Negative Email Detected",
                                    f"Subject: {subject}\n\nExcerpt: {body[:500]}..."
                                )

                            if any(keyword in body_lower for keyword in POSITIVE_KEYWORDS):
                                print(f"Positive email detected: {subject}")
                                send_notification(
                                    "Positive Email Detected",
                                    f"Subject: {subject}\n\nExcerpt: {body[:500]}..."
                                )

            except Exception as e:
                print(f"Error processing email {mail_id}: {str(e)}")
                continue

    except Exception as e:
        print(f"Error connecting to email server: {str(e)}")
    finally:
        try:
            mail.close()
            mail.logout()
            print("\nEmail check completed. Connection closed.")
        except:
            pass

if __name__ == "__main__":
    if not all([EMAIL, PASSWORD, NOTIFICATION_EMAIL]):
        print("Please set up your environment variables first!")
    else:
        check_email()