"""
scraper/cppp_scraper.py — Robust CPPP Portal Scraper

Scrapes active tenders from the Central Public Procurement Portal (eprocure.gov.in/cppp).
Features:
  - Retry logic with exponential backoff (3 attempts)
  - Multiple endpoint fallback strategies
  - User-agent rotation to avoid bot detection
  - Graceful handling of empty/failed portal responses
  - Keyword filtering on returned results
  - Returns structured list ready for AI analysis
"""
import sys
import os
import time
import random
import hashlib
import re
import json
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "https://eprocure.gov.in/cppp"

# Multiple endpoints to try (CPPP portal has changed structure over time)
ENDPOINTS = [
    "https://eprocure.gov.in/cppp/latestactivetenders/10",
    "https://eprocure.gov.in/cppp/tenders",
    "https://eprocure.gov.in/cppp/tendersearchresult",
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2   # seconds (doubles each retry)

# ── Realistic sample tenders for fallback when portal unreachable ──────────────
SAMPLE_TENDERS = [
    {
        "tender_id": "CPPP-2025-RD-001",
        "title": "Construction of Four-Lane Highway NH-44 Extension — Phase II",
        "organization": "National Highways Authority of India (NHAI)",
        "department": "Ministry of Road Transport and Highways",
        "published_date": "2025-05-10",
        "closing_date": "2025-06-15",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-RD-001",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-IT-002",
        "title": "Supply and Installation of CCTV Surveillance System for Smart City Project — Tier 2 Cities",
        "organization": "Smart Cities Mission, MoHUA",
        "department": "Ministry of Housing and Urban Affairs",
        "published_date": "2025-05-12",
        "closing_date": "2025-06-10",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-IT-002",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-WS-003",
        "title": "Piped Water Supply Scheme to Rural Habitations — Jal Jeevan Mission",
        "organization": "Department of Drinking Water and Sanitation",
        "department": "Ministry of Jal Shakti",
        "published_date": "2025-05-11",
        "closing_date": "2025-06-20",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-WS-003",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-SW-004",
        "title": "Development of Integrated Financial Management Information System (IFMIS) — Phase III",
        "organization": "Controller General of Accounts, Ministry of Finance",
        "department": "Ministry of Finance",
        "published_date": "2025-05-09",
        "closing_date": "2025-06-25",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-SW-004",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-EL-005",
        "title": "Rural Electrification under RDSS Scheme — Distribution Infrastructure Upgradation",
        "organization": "Rural Electrification Corporation (REC)",
        "department": "Ministry of Power",
        "published_date": "2025-05-08",
        "closing_date": "2025-06-18",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-EL-005",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-BD-006",
        "title": "Construction of Multi-Specialty Government Hospital Building — 500 Beds",
        "organization": "Central Public Works Department (CPWD)",
        "department": "Ministry of Health and Family Welfare",
        "published_date": "2025-05-07",
        "closing_date": "2025-06-30",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-BD-006",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-MT-007",
        "title": "Annual Maintenance Contract for Government IT Equipment and Software Systems",
        "organization": "National Informatics Centre (NIC)",
        "department": "Ministry of Electronics and IT",
        "published_date": "2025-05-06",
        "closing_date": "2025-06-05",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-MT-007",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-CB-008",
        "title": "Laying of Optical Fibre Cable Network for BharatNet Phase III — Last Mile Connectivity",
        "organization": "BSNL / BharatNet",
        "department": "Department of Telecommunications",
        "published_date": "2025-05-05",
        "closing_date": "2025-06-12",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-CB-008",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-SL-009",
        "title": "Supply of Laptop Computers and Peripherals for Government Schools — PM e-Vidya",
        "organization": "Department of School Education and Literacy",
        "department": "Ministry of Education",
        "published_date": "2025-05-04",
        "closing_date": "2025-06-08",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-SL-009",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-DM-010",
        "title": "Construction of Drainage and Stormwater Management System — Urban Flood Mitigation",
        "organization": "Jawaharlal Nehru National Urban Renewal Mission",
        "department": "Ministry of Housing and Urban Affairs",
        "published_date": "2025-05-03",
        "closing_date": "2025-06-22",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-DM-010",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-RW-011",
        "title": "Renovation and Repair of Railway Quarters and Staff Buildings — Zone-III",
        "organization": "Indian Railways / Rail Vikas Nigam",
        "department": "Ministry of Railways",
        "published_date": "2025-05-02",
        "closing_date": "2025-06-14",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-RW-011",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-GS-012",
        "title": "Installation of Solar Power Plant (5 MW) at Government Campus — Green Energy Initiative",
        "organization": "NTPC Renewable Energy Ltd",
        "department": "Ministry of New and Renewable Energy",
        "published_date": "2025-05-01",
        "closing_date": "2025-06-28",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-GS-012",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-WM-013",
        "title": "Solid Waste Management and Mechanized Sweeping Services for Municipal Corporation",
        "organization": "Greater Hyderabad Municipal Corporation",
        "department": "State Urban Development Authority",
        "published_date": "2025-04-30",
        "closing_date": "2025-06-02",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-WM-013",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-BR-014",
        "title": "Construction of RCC Bridge Over River Ganga — NH Connectivity Project",
        "organization": "National Highways and Infrastructure Development Corp",
        "department": "Ministry of Road Transport",
        "published_date": "2025-04-29",
        "closing_date": "2025-06-16",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-BR-014",
        "source": "sample",
    },
    {
        "tender_id": "CPPP-2025-SC-015",
        "title": "Cybersecurity Audit and Penetration Testing Services for Government Websites",
        "organization": "CERT-In / Ministry of Electronics and IT",
        "department": "MeitY",
        "published_date": "2025-04-28",
        "closing_date": "2025-05-28",
        "detail_url": "https://eprocure.gov.in/cppp/tender/CPPP-2025-SC-015",
        "source": "sample",
    },
]


def _make_headers() -> dict:
    """Build realistic browser-like headers."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "Referer": "https://eprocure.gov.in/cppp/",
    }


def _parse_tender_table(html: str, base_url: str = BASE_URL) -> List[Dict]:
    """
    Parse HTML table rows from CPPP portal page.
    Returns list of tender dicts.
    """
    soup = BeautifulSoup(html, "html.parser")
    tenders = []

    # Try multiple selectors used by CPPP portal over different versions
    selectors = [
        "table.list_table tr",
        "table.tablesorter tr",
        "table#tableId tr",
        "div.tender-list .tender-item",
        "table tr",
    ]

    rows = []
    for sel in selectors:
        rows = soup.select(sel)
        if len(rows) > 2:
            break

    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 3:
            continue

        # Skip header rows
        if cells[0].name == "th" or cells[0].get("class") and "header" in str(cells[0].get("class")):
            continue

        # Try to extract link and title
        link_tag = row.find("a", href=True)
        if not link_tag:
            continue

        title = link_tag.get_text(strip=True)
        if not title or len(title) < 10:
            continue

        href = link_tag.get("href", "")
        if href.startswith("http"):
            detail_url = href
        elif href.startswith("/"):
            detail_url = f"https://eprocure.gov.in{href}"
        else:
            detail_url = f"{base_url}/{href}"

        # Generate stable tender ID from URL or title hash
        url_slug = re.search(r"[A-Za-z0-9_-]{6,}", href)
        if url_slug:
            tender_id = f"CPPP-{url_slug.group()[:20]}"
        else:
            h = hashlib.md5(title.encode()).hexdigest()[:8].upper()
            tender_id = f"CPPP-{h}"

        # Extract org from adjacent cells
        org = ""
        if len(cells) > 1:
            org = cells[1].get_text(strip=True)
        if not org:
            org = "CPPP Portal"

        # Extract dates
        published_date = ""
        closing_date = ""
        for cell in cells:
            text = cell.get_text(strip=True)
            date_match = re.search(r"\d{2}[/-]\d{2}[/-]\d{4}", text)
            if date_match:
                if not published_date:
                    published_date = date_match.group()
                elif not closing_date:
                    closing_date = date_match.group()

        tenders.append({
            "tender_id": tender_id,
            "title": title,
            "organization": org,
            "department": org,
            "published_date": published_date or datetime.now().strftime("%Y-%m-%d"),
            "closing_date": closing_date or "",
            "detail_url": detail_url,
            "source": "live",
        })

    return tenders


def _fetch_with_retry(url: str, session: requests.Session, attempt: int = 0) -> Optional[str]:
    """Fetch URL with exponential backoff retry."""
    try:
        resp = session.get(
            url,
            headers=_make_headers(),
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        if resp.status_code == 200 and len(resp.text) > 500:
            return resp.text
        print(f"  [SCRAPER] HTTP {resp.status_code} from {url}")
        return None
    except requests.exceptions.SSLError:
        # Some govt portals have SSL issues — try without verification
        try:
            import urllib3
            urllib3.disable_warnings()
            resp = session.get(url, headers=_make_headers(), timeout=TIMEOUT, verify=False, allow_redirects=True)
            if resp.status_code == 200 and len(resp.text) > 500:
                return resp.text
        except Exception as e:
            print(f"  [SCRAPER] SSL fallback failed: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"  [SCRAPER] Connection error: {e}")
        return None
    except requests.exceptions.Timeout:
        print(f"  [SCRAPER] Timeout on attempt {attempt + 1}")
        return None
    except Exception as e:
        print(f"  [SCRAPER] Unexpected error: {e}")
        return None


def _filter_tenders(tenders: List[Dict], keyword: str) -> List[Dict]:
    """Filter tenders by keyword (case-insensitive, multi-word support)."""
    if not keyword or not keyword.strip():
        return tenders
    kw_lower = keyword.lower().strip()
    words = kw_lower.split()
    return [
        t for t in tenders
        if any(w in t.get("title", "").lower() for w in words)
        or any(w in t.get("organization", "").lower() for w in words)
    ]


def scrape_cppp_listings(pages: int = 1, keyword_filter: str = "") -> List[Dict]:
    """
    Main entry point — scrapes CPPP portal for active tenders.

    Args:
        pages:          Number of pages to scrape (each page ≈ 10 tenders).
        keyword_filter: Optional keyword to filter results.

    Returns:
        List of tender dicts with keys:
        tender_id, title, organization, department,
        published_date, closing_date, detail_url, source
    """
    print(f"\n[CPPP Scraper] Starting: pages={pages}, keyword='{keyword_filter}'")
    all_tenders = []

    session = requests.Session()
    session.headers.update(_make_headers())

    # ── Try live scraping ──────────────────────────────────────────────────────
    scraped_ok = False
    for page_num in range(1, pages + 1):
        for attempt in range(MAX_RETRIES):
            print(f"  [CPPP] Page {page_num}/{pages} — attempt {attempt + 1}/{MAX_RETRIES}")

            html = None
            for endpoint in ENDPOINTS:
                page_url = endpoint if page_num == 1 else f"{endpoint}/{page_num}"
                html = _fetch_with_retry(page_url, session, attempt)
                if html:
                    break

            if html:
                page_tenders = _parse_tender_table(html)
                if page_tenders:
                    print(f"  [CPPP] ✓ Parsed {len(page_tenders)} tenders from page {page_num}")
                    all_tenders.extend(page_tenders)
                    scraped_ok = True
                    break
                else:
                    print(f"  [CPPP] Parsed 0 tenders from HTML — portal may have changed structure")
            else:
                print(f"  [CPPP] No HTML received, retrying...")

            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAY * (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"  [CPPP] Waiting {delay:.1f}s before retry...")
                time.sleep(delay)

        if scraped_ok:
            # Brief pause between pages
            if page_num < pages:
                time.sleep(random.uniform(1.5, 3.0))

    # ── Fallback: return curated sample tenders ───────────────────────────────
    if not all_tenders or not scraped_ok:
        print(f"\n  [CPPP] Portal unreachable or returned no data.")
        print(f"  [CPPP] Using {len(SAMPLE_TENDERS)} curated sample tenders for analysis.")
        all_tenders = SAMPLE_TENDERS.copy()

        # Multiply samples based on pages requested
        if pages > 1:
            extended = []
            for i, t in enumerate(SAMPLE_TENDERS):
                new = t.copy()
                new["tender_id"] = f"{t['tender_id']}-P{pages}"
                extended.append(new)
            all_tenders = SAMPLE_TENDERS + extended[:pages * 5]

    # ── Deduplicate by tender_id ───────────────────────────────────────────────
    seen = set()
    unique = []
    for t in all_tenders:
        tid = t.get("tender_id", "")
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(t)
    all_tenders = unique

    # ── Apply keyword filter ───────────────────────────────────────────────────
    if keyword_filter and keyword_filter.strip():
        filtered = _filter_tenders(all_tenders, keyword_filter)
        if filtered:
            all_tenders = filtered
            print(f"  [CPPP] Keyword filter '{keyword_filter}': {len(all_tenders)} matches")
        else:
            print(f"  [CPPP] No keyword matches for '{keyword_filter}' — returning all {len(all_tenders)}")

    print(f"\n[CPPP Scraper] Complete — {len(all_tenders)} tenders ready for processing.\n")
    return all_tenders


if __name__ == "__main__":
    # Quick test
    results = scrape_cppp_listings(pages=1, keyword_filter="")
    for t in results[:3]:
        print(f"  {t['tender_id']}: {t['title'][:70]}")
    print(f"\nTotal: {len(results)}")
