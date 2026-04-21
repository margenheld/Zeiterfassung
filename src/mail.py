# src/mail.py
import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.header import Header

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class TokenAuthError(Exception):
    """Refresh-Token ist ungültig — User muss sich neu anmelden."""


class TokenNetworkError(Exception):
    """Refresh fehlgeschlagen wegen Netzwerkproblem."""


def _refresh_and_persist(creds, token_path):
    """Refresh credentials and write them back. Translates Google exceptions."""
    from google.auth.exceptions import RefreshError, TransportError
    from google.auth.transport.requests import Request

    try:
        creds.refresh(Request())
    except RefreshError as e:
        raise TokenAuthError(str(e)) from e
    except TransportError as e:
        raise TokenNetworkError(str(e)) from e

    with open(token_path, "w") as f:
        f.write(creds.to_json())


def refresh_token_if_needed(token_path="token.json"):
    """Proactively refresh the Gmail token when it is expired.

    Returns one of:
        "no_token"  — no token file present (first use)
        "valid"     — token is still valid, no refresh needed
        "refreshed" — refresh succeeded and file was updated

    Raises:
        TokenAuthError    — refresh_token is invalid, user must re-authenticate
        TokenNetworkError — network issue prevented the refresh attempt
    """
    from google.oauth2.credentials import Credentials

    if not os.path.exists(token_path):
        return "no_token"

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds.valid:
        return "valid"

    if not creds.expired or not creds.refresh_token:
        raise TokenAuthError(
            "Token ist ungültig und enthält kein Refresh-Token."
        )

    _refresh_and_persist(creds, token_path)
    return "refreshed"


def get_gmail_service(credentials_path="credentials.json", token_path="token.json"):
    """Authenticate with Gmail API and return a service object.

    Returns the service object, or raises an exception on failure.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            _refresh_and_persist(creds, token_path)
        except TokenAuthError:
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


def send_email(service, to, subject, html_body, pdf_bytes=None, pdf_filename=None):
    """Send an HTML email via Gmail API, optionally with a PDF attachment.

    Returns the sent message id, or raises an exception on failure.
    """
    if pdf_bytes:
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = Header(subject, "utf-8")
        message.attach(MIMEText(html_body, "html", _charset="utf-8"))

        attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        attachment.add_header(
            "Content-Disposition", "attachment",
            filename=pdf_filename or "Zeiterfassung.pdf"
        )
        message.attach(attachment)
    else:
        message = MIMEText(html_body, "html", _charset="utf-8")
        message["to"] = to
        message["subject"] = Header(subject, "utf-8")

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    body = {"raw": raw}

    sent = service.users().messages().send(userId="me", body=body).execute()
    return sent["id"]
