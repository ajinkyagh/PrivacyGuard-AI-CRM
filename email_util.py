import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Tuple, List, Optional
from datetime import datetime


def send_email(to_email: str, subject: str, body: str, attachments: Optional[List[Dict[str, bytes]]] = None, html_body: Optional[str] = None) -> Tuple[bool, Dict[str, str]]:
    """Send an email with optional attachments.

    attachments: list of {"filename": str, "content": bytes, "mime": "application/pdf"}
    html_body: Optional HTML version of the email body
    """
    user = os.getenv("GMAIL_USER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")
    if not user or not app_password:
        return False, {"error": "Missing GMAIL_USER or GMAIL_APP_PASSWORD env"}

    msg = MIMEMultipart('alternative')
    msg["From"] = f"Luxury Automotive <{user}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    
    # Add plain text version
    msg.attach(MIMEText(body, "plain"))
    
    # Add HTML version if provided
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    if attachments:
        for att in attachments:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(att.get("content", b""))
            encoders.encode_base64(part)
            filename = att.get("filename", "document.pdf")
            part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
            msg.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(user, app_password)
        server.send_message(msg)
        server.quit()
        return True, {"email_sent_at": datetime.utcnow().isoformat()}
    except Exception as e:
        return False, {"error": str(e)}
