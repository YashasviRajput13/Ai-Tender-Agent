"""
tools/notification_tool.py — CrewAI Notification Tool
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from email_service import send_tender_alert


class NotificationInput(BaseModel):
    tender_data: str = Field(description="JSON string with tender_id, title, score, recommendation, risk, deadline, summary, organization.")


class NotificationTool(BaseTool):
    name: str = "Smart Notification Tool"
    description: str = "Sends email alerts for high-priority tenders and logs to notifications.log."
    args_schema: Type[BaseModel] = NotificationInput

    def _run(self, tender_data: str) -> str:
        try:
            data = json.loads(tender_data)
            score = int(data.get("score", data.get("match_score", 0)))
            sent = send_tender_alert(
                tender_id=data.get("tender_id", "UNKNOWN"),
                title=data.get("title", "Unknown Tender"),
                score=score,
                recommendation=data.get("recommendation", "Review"),
                risk=data.get("risk", data.get("risk_level", "Medium")),
                deadline=data.get("deadline", "Not specified"),
                summary=data.get("summary", ""),
                organization=data.get("organization", ""),
            )
            return f"Notification {'sent' if sent else 'logged (email not configured)'} for {data.get('tender_id')}"
        except Exception as e:
            return f"Notification error: {e}"
