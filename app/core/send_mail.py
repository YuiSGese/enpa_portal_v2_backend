from jinja2 import Template
import smtplib
from email.message import EmailMessage
from app.core.config import SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER

def send_html_email(to_email: str, subject: str, body: str):
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body, subtype="html")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls() 
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def render_template(template_path: str, context: dict) -> str:
    with open(template_path, mode="r", encoding="utf-8") as f:
        template_str = f.read()
    template = Template(template_str)
    return template.render(**context)