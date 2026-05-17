"""
scraper_tool.py — CrewAI Scraper Tool (fixed imports).
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from scraper.cppp_scraper import scrape_cppp_listings


class ScraperToolInput(BaseModel):
    query: str = Field(description="Keyword to search for within CPPP tender titles.")


class PlaywrightScraperTool(BaseTool):
    name: str = "CPPP Tender Scraper Tool"
    description: str = (
        "Scrapes the CPPP government portal for active tenders. "
        "Accepts an optional keyword query. Returns a JSON list of matching tenders."
    )
    args_schema: Type[BaseModel] = ScraperToolInput

    def _run(self, query: str) -> str:
        print(f"\n[CPPP Scraper] Scraping for keyword: '{query}'")
        try:
            tenders = scrape_cppp_listings(pages=2, keyword_filter=query)
            if not tenders:
                tenders = scrape_cppp_listings(pages=1, keyword_filter="")[:5]
            tenders = tenders[:5]
            print(f"[CPPP Scraper] Returning {len(tenders)} tenders")
            return json.dumps(tenders, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Scraper error: {e}"
