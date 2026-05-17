"""
Updated Scraper Tool for CrewAI — uses the real CPPP scraper via requests.
No Playwright / captcha required for the listing pages.
"""
import sys
import os

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from scraper.cppp_scraper import scrape_cppp_listings
import json


class ScraperToolInput(BaseModel):
    query: str = Field(
        description="Keyword to search for within CPPP tender titles (e.g. 'Road Construction', 'IT', 'Water Supply')."
    )


class PlaywrightScraperTool(BaseTool):
    name: str = "CPPP Tender Scraper Tool"
    description: str = (
        "Scrapes the CPPP government portal (eprocure.gov.in) for active tenders. "
        "Accepts a keyword query to filter by title. Returns a JSON list of matching tenders "
        "with their title, tender_id, detail_url, and organization."
    )
    args_schema: Type[BaseModel] = ScraperToolInput

    def _run(self, query: str) -> str:
        print(f"\n[CPPP Scraper] Starting real scrape for keyword: '{query}'")
        try:
            # Fetch 2 pages (≈20 tenders) and filter by keyword
            tenders = scrape_cppp_listings(pages=2, keyword_filter=query)

            if not tenders:
                # If no keyword match, return top 5 from first page without filter
                print(f"[CPPP Scraper] No exact matches for '{query}', returning latest 5 tenders.")
                tenders = scrape_cppp_listings(pages=1, keyword_filter="")[:5]

            # Limit to top 5 to keep context manageable for LLM
            tenders = tenders[:5]

            print(f"[CPPP Scraper] Returning {len(tenders)} tenders to agent.")
            return json.dumps(tenders, indent=2, ensure_ascii=False)

        except Exception as e:
            error_msg = f"Error scraping CPPP portal: {str(e)}"
            print(f"[CPPP Scraper] {error_msg}")
            return error_msg
