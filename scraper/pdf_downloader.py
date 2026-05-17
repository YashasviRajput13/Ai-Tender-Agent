"""
scraper/pdf_downloader.py — Best-effort PDF download and extraction.

Downloads tender PDFs from CPPP detail pages and extracts structured text
using PyMuPDF. Gracefully handles auth-gated / unavailable PDFs.
"""
import os
import re
import tempfile
import time
import random
from typing import Optional, Dict

import requests


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/125.0",
]


def _extract_pdf_urls_from_page(detail_url: str) -> list:
    """Attempt to find PDF links on the tender detail page."""
    try:
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        resp = requests.get(detail_url, headers=headers, timeout=20, allow_redirects=True)
        if resp.status_code != 200:
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower() or "download" in href.lower():
                if href.startswith("http"):
                    pdf_links.append(href)
                elif href.startswith("/"):
                    pdf_links.append(f"https://eprocure.gov.in{href}")
        return pdf_links
    except Exception:
        return []


def download_and_extract_pdf(detail_url: str, pdf_url: Optional[str] = None) -> Dict:
    """
    Best-effort: download tender PDF and extract text content.

    Returns:
        {
          "success": bool,
          "pdf_url": str or None,
          "text": str,           # extracted text (empty string on failure)
          "budget": str,         # regex-extracted budget
          "emd": str,            # regex-extracted EMD
          "deadline": str,       # regex-extracted deadline
          "pages": int,
        }
    """
    result = {
        "success": False,
        "pdf_url": pdf_url,
        "text": "",
        "budget": "",
        "emd": "",
        "deadline": "",
        "pages": 0,
    }

    # ── Try to find PDF URL from detail page if not provided ─────────────────
    if not pdf_url and detail_url and detail_url.startswith("http"):
        pdf_urls = _extract_pdf_urls_from_page(detail_url)
        if pdf_urls:
            pdf_url = pdf_urls[0]
            result["pdf_url"] = pdf_url

    if not pdf_url:
        return result

    # ── Download PDF ──────────────────────────────────────────────────────────
    try:
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/pdf,*/*",
        }
        resp = requests.get(pdf_url, headers=headers, timeout=30, stream=True, allow_redirects=True)

        if resp.status_code != 200:
            return result

        content_type = resp.headers.get("content-type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            return result

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name

        # ── Extract with PyMuPDF ───────────────────────────────────────────
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(tmp_path)
            text_parts = []
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()
            full_text = "\n".join(text_parts)
            result["text"] = full_text[:20000]  # Cap at 20k chars
            result["pages"] = len(text_parts)
            result["success"] = True
        except ImportError:
            print("  [PDF] PyMuPDF not available — install pymupdf")
        except Exception as e:
            print(f"  [PDF] PyMuPDF extraction failed: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    except requests.exceptions.Timeout:
        print("  [PDF] Download timed out")
        return result
    except Exception as e:
        print(f"  [PDF] Download failed: {e}")
        return result

    # ── Regex extraction on PDF text ─────────────────────────────────────────
    if result["text"]:
        text = result["text"]

        # Budget / Estimated Cost
        budget_match = re.search(
            r"(?:estimated\s+cost|tender\s+value|total\s+value|project\s+cost|estimated\s+amount)[:\s]*"
            r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|crore|lacs|cr|l)?",
            text, re.IGNORECASE
        )
        if budget_match:
            result["budget"] = budget_match.group(0)[:100].strip()

        # EMD
        emd_match = re.search(
            r"(?:emd|earnest\s+money\s+deposit|bid\s+security)[:\s]*"
            r"(?:Rs\.?|INR|₹)?\s*([\d,]+(?:\.\d+)?)\s*(?:lakh|crore|lacs|cr|l)?",
            text, re.IGNORECASE
        )
        if emd_match:
            result["emd"] = emd_match.group(0)[:100].strip()

        # Deadline / Closing Date
        deadline_match = re.search(
            r"(?:last\s+date|closing\s+date|submission\s+date|bid\s+due\s+date)[:\s]*"
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})",
            text, re.IGNORECASE
        )
        if deadline_match:
            result["deadline"] = deadline_match.group(1).strip()

    return result
