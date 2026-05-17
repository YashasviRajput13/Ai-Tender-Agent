"""
email_service.py — Enhanced Gmail SMTP notification service.
"""
import os
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_EMAIL    = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
NOTIF_LOG    = Path(PROJECT_ROOT) / "notifications.log"

logger = logging.getLogger(__name__)


def _log_notification(tender_id: str, title: str, score: int, sent: bool):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "SENT" if sent else "LOGGED"
    line = f"[{ts}] [{status}] Score={score}% | {tender_id} | {title[:80]}\n"
    with open(NOTIF_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def _build_html_email(tender_id, title, score, recommendation, risk, deadline, summary, organization) -> str:
    score_color = "#22c55e" if score >= 70 else ("#f59e0b" if score >= 50 else "#ef4444")
    risk_color  = "#ef4444" if risk == "High" else ("#f59e0b" if risk == "Medium" else "#22c55e")
    rec_icon    = "✅" if recommendation == "Go" else ("⚠️" if recommendation == "Review" else "❌")

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0a0a1a;font-family:'Segoe UI',Arial,sans-serif;">
<div style="max-width:600px;margin:30px auto;background:linear-gradient(135deg,#111128,#0f0f2e);border-radius:16px;overflow:hidden;border:1px solid #2a2a5a;">
  <div style="background:linear-gradient(135deg,#7c3aed,#4f46e5);padding:24px 30px;">
    <h1 style="margin:0;color:#fff;font-size:1.4rem;">🤖 AI Tender Intelligence Alert</h1>
    <p style="margin:6px 0 0;color:#c4b5fd;font-size:0.9rem;">High-Priority Opportunity Detected</p>
  </div>
  <div style="padding:28px 30px;">
    <div style="background:rgba(124,58,237,0.1);border:1px solid #4c1d95;border-radius:12px;padding:20px;margin-bottom:24px;">
      <h2 style="margin:0 0 8px;color:#e0e0f0;font-size:1.1rem;">{title}</h2>
      <p style="margin:0;color:#8888bb;font-size:0.85rem;">{organization}</p>
    </div>
    <table style="width:100%;border-collapse:collapse;">
      <tr>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#8888bb;width:140px;">Match Score</td>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:{score_color};font-weight:700;font-size:1.1rem;">{score}%</td>
      </tr>
      <tr>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#8888bb;">Recommendation</td>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#e0e0f0;font-weight:600;">{rec_icon} {recommendation}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#8888bb;">Risk Level</td>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:{risk_color};font-weight:600;">{risk}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#8888bb;">Tender ID</td>
        <td style="padding:10px 0;border-bottom:1px solid #1e1e4a;color:#a78bfa;">{tender_id}</td>
      </tr>
      <tr>
        <td style="padding:10px 0;color:#8888bb;">Deadline</td>
        <td style="padding:10px 0;color:#e0e0f0;">{deadline}</td>
      </tr>
    </table>
    {'<p style="margin:20px 0 0;color:#aaaacc;font-size:0.88rem;line-height:1.5;">' + summary + '</p>' if summary else ''}
    <div style="margin-top:24px;text-align:center;">
      <a href="https://eprocure.gov.in/cppp/" style="display:inline-block;background:linear-gradient(135deg,#7c3aed,#4f46e5);color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:600;">View on CPPP Portal →</a>
    </div>
  </div>
  <div style="padding:16px 30px;border-top:1px solid #1e1e4a;text-align:center;">
    <p style="margin:0;color:#444;font-size:0.75rem;">AI Tender Intelligence Platform — Powered by CrewAI & OpenRouter</p>
  </div>
</div>
</body>
</html>"""


def send_tender_alert(tender_id: str, title: str, score: int, recommendation: str,
                      risk: str, deadline: str, summary: str = "", organization: str = "") -> bool:
    """Send HTML email alert. Logs to notifications.log regardless of email config."""
    sent = False

    if SMTP_EMAIL and SMTP_PASSWORD and ALERT_RECIPIENT:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"]    = SMTP_EMAIL
            msg["To"]      = ALERT_RECIPIENT
            msg["Subject"] = f"🚀 [{score}% Match] {recommendation} — {tender_id}"

            html_body = _build_html_email(
                tender_id, title, score, recommendation, risk, deadline, summary, organization
            )
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_EMAIL, SMTP_PASSWORD)
                server.sendmail(SMTP_EMAIL, ALERT_RECIPIENT, msg.as_string())

            print(f"  [MAIL] ✓ Alert sent to {ALERT_RECIPIENT}")
            sent = True
        except Exception as e:
            print(f"  [MAIL] Failed: {e}")
    else:
        print("  [MAIL] SMTP not configured — logging only (set SMTP_EMAIL, SMTP_PASSWORD, ALERT_RECIPIENT in .env)")

    _log_notification(tender_id, title, score, sent)
    return sent
