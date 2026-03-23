# src/mail.py
import os
import base64
from email.mime.text import MIMEText

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def get_gmail_service(credentials_path="credentials.json", token_path="token.json"):
    """Authenticate with Gmail API and return a service object.

    Returns the service object, or raises an exception on failure.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                "credentials.json nicht gefunden. "
                "Bitte erstelle ein Google Cloud Projekt mit Gmail API "
                "und lade die OAuth2 Client-ID herunter."
            )
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

    with open(token_path, "w") as f:
        f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(service, to, subject, html_body):
    """Send an HTML email via Gmail API.

    Returns the sent message id, or raises an exception on failure.
    """
    message = MIMEText(html_body, "html")
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent["id"]
