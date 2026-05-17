"""
tools/pdf_tool.py — CrewAI PDF Extraction Tool
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from scraper.pdf_downloader import download_and_extract_pdf


class PDFToolInput(BaseModel):
    detail_url: str = Field(description="Tender detail page URL.")
    pdf_url: str = Field(default="", description="Direct PDF URL if known.")


class PDFExtractionTool(BaseTool):
    name: str = "Tender PDF Extraction Tool"
    description: str = "Downloads tender PDFs and extracts text. Returns budget, EMD, deadline, and full text excerpt."
    args_schema: Type[BaseModel] = PDFToolInput

    def _run(self, detail_url: str, pdf_url: str = "") -> str:
        try:
            result = download_and_extract_pdf(detail_url=detail_url, pdf_url=pdf_url or None)
            return json.dumps({
                "success": result["success"],
                "pages": result.get("pages", 0),
                "budget_found": result.get("budget", ""),
                "emd_found": result.get("emd", ""),
                "deadline_found": result.get("deadline", ""),
                "text_excerpt": result.get("text", "")[:2000],
            })
        except Exception as e:
            return json.dumps({"success": False, "error": str(e), "text_excerpt": ""})
