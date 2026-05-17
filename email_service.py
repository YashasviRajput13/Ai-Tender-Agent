import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "")

def send_tender_alert(tender_id: str, title: str, score: int, recommendation: str, risk: str, deadline: str):
    """Sends an email alert for a high priority tender."""
    if not SMTP_EMAIL or not SMTP_PASSWORD or not ALERT_RECIPIENT:
        print("  [MAIL] SMTP credentials or recipient not configured in .env. Skipping email.")
        return False

    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = ALERT_RECIPIENT
    msg['Subject'] = f"🚀 HIGH PRIORITY TENDER: {score}% Match - {tender_id}"

    body = f"""
    <h2>Tender Intelligence Alert</h2>
    <p>A new high-priority tender has been identified that strongly matches your company profile.</p>
    
    <table border="1" cellpadding="8" style="border-collapse: collapse; width: 100%;">
        <tr><th style="text-align: left; background-color: #f2f2f2;">Tender ID</th><td>{tender_id}</td></tr>
        <tr><th style="text-align: left; background-color: #f2f2f2;">Title</th><td>{title}</td></tr>
        <tr><th style="text-align: left; background-color: #f2f2f2;">Match Score</th><td style="color: green; font-weight: bold;">{score}%</td></tr>
        <tr><th style="text-align: left; background-color: #f2f2f2;">Recommendation</th><td>{recommendation}</td></tr>
        <tr><th style="text-align: left; background-color: #f2f2f2;">Risk Level</th><td>{risk}</td></tr>
        <tr><th style="text-align: left; background-color: #f2f2f2;">Deadline</th><td>{deadline}</td></tr>
    </table>
    <br>
    <p>Log in to your Tender AI Dashboard to view full details and analysis.</p>
    """
    
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(SMTP_EMAIL, ALERT_RECIPIENT, text)
        server.quit()
        print(f"  [MAIL] Successfully sent alert email to {ALERT_RECIPIENT}")
        return True
    except Exception as e:
        print(f"  [MAIL] Failed to send email: {e}")
        return False
