"""
cppp_bulk_fetch.py — Standalone CPPP bulk ingestion script.

This script:
1. Scrapes live tenders from CPPP (requests + BeautifulSoup)
2. Sends each tender title to OpenRouter for AI analysis
3. Saves the structured result to the SQLite database

Run with:  uv run python cppp_bulk_fetch.py [keyword] [pages]
Example:   uv run python cppp_bulk_fetch.py "Road" 2
"""
import sys
import os
import json
from dotenv import load_dotenv

# Fix Windows cp1252 encoding issue — must be first before any print
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI
from scraper.cppp_scraper import scrape_cppp_listings
from database.db import init_db, get_db
from database.models import Tender
from database.vector_db import get_vector_db


# ── OpenRouter client ───────────────────────────────────────────────────────
client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1"
)


def analyse_tender_with_ai(tender: dict) -> dict:
    """Send tender title/description to AI and extract structured fields."""
    title = tender.get("title", "Unknown Tender")

    prompt = f"""You are a government tender analysis expert.

Analyse the following tender title and extract as much information as possible.
If a field cannot be determined from the title alone, make a reasonable inference
based on typical government tenders in this category. Never leave fields blank.

Tender Title: {title}

Return ONLY a valid JSON object with these exact keys:
{{
  "tender_type": "Category/type of work (e.g. Civil Works, IT Supply, Maintenance)",
  "budget": "Estimated budget range (e.g. 50 Lakh - 2 Crore, or Not Mentioned)",
  "deadline": "Typical closing period (e.g. 30 days from publication, or Not Mentioned)",
  "emd_amount": "Typical EMD for this type (e.g. 2% of project value, or Not Mentioned)",
  "required_experience": "Typical experience requirement for this type",
  "eligibility_criteria": "Typical eligibility for this category of tender",
  "risk_level": "Low / Medium / High based on complexity",
  "summary": "One sentence description of what this tender is about"
}}"""

    try:
        response = client.chat.completions.create(
            model="openai/gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        result = response.choices[0].message.content.strip()
        # Strip markdown code fences if present
        result = result.replace("```json", "").replace("```", "").strip()
        return json.loads(result)
    except Exception as e:
        print(f"  [WARN] AI analysis failed: {e}")
        return {
            "tender_type": "General",
            "budget": "Not Mentioned",
            "deadline": "Not Mentioned",
            "emd_amount": "Not Mentioned",
            "required_experience": "Not Mentioned",
            "eligibility_criteria": "Not Mentioned",
            "risk_level": "Medium",
            "summary": title,
        }


def load_company_profile() -> dict:
    path = os.path.join(os.path.dirname(__file__), "company_profile.json")
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {"name": "TechBuild Pvt Ltd", "experience_years": 8,
                "specialization": ["Road Construction", "IT Infrastructure"],
                "max_emd_capacity": "10 Lakh"}


def score_match(ai_data: dict, profile: dict) -> tuple[int, str, str]:
    """Simple rule-based scoring + AI recommendation."""
    score = 50  # base score
    notes = []

    risk = ai_data.get("risk_level", "Medium").lower()
    if risk == "low":
        score += 20
        notes.append("Low risk tender")
    elif risk == "high":
        score -= 20
        notes.append("High risk tender")

    specs = [s.lower() for s in profile.get("specialization", [])]
    title_lower = ai_data.get("summary", "").lower()
    tender_type_lower = ai_data.get("tender_type", "").lower()

    for spec in specs:
        if spec.lower() in title_lower or spec.lower() in tender_type_lower:
            score += 20
            notes.append(f"Matches specialization: {spec}")
            break

    score = max(0, min(100, score))
    recommendation = "Go" if score >= 50 else "No-Go"
    reason = "; ".join(notes) if notes else "Based on general profile match."
    return score, recommendation, reason


def save_to_db(tender: dict, ai_data: dict, score: int, recommendation: str, reason: str):
    """Save the processed tender to SQLite."""
    init_db()
    db = next(get_db())

    try:
        existing = db.query(Tender).filter(Tender.tender_id == tender["tender_id"]).first()
        if existing:
            print(f"  [SKIP] Already exists: {tender['tender_id']}")
            return False

        record = Tender(
            tender_id=tender["tender_id"],
            title=tender["title"],
            organization=tender.get("organization", "CPPP"),
            tender_type=ai_data.get("tender_type", ""),
            budget=ai_data.get("budget", ""),
            deadline=ai_data.get("deadline", ""),
            emd_amount=ai_data.get("emd_amount", ""),
            required_experience=ai_data.get("required_experience", ""),
            eligibility_criteria=ai_data.get("eligibility_criteria", ""),
            risk_level=ai_data.get("risk_level", ""),
            summary=ai_data.get("summary", ""),
            match_score=str(score),
            recommendation=recommendation,
            match_reason=reason,
            raw_data={**tender, **ai_data, "match_score": score, "recommendation": recommendation}
        )
        db.add(record)
        db.commit()
        
        # Index to Vector DB
        try:
            vdb = get_vector_db()
            text_for_embedding = f"{tender['title']} {ai_data.get('summary', '')} {ai_data.get('tender_type', '')}"
            vdb.add_tender(
                tender_id=tender["tender_id"],
                text=text_for_embedding,
                metadata={
                    "title": tender["title"],
                    "organization": tender.get("organization", "CPPP"),
                    "risk_level": ai_data.get("risk_level", ""),
                    "score": score
                }
            )
        except Exception as e:
            print(f"  [WARN] Failed to index to Vector DB: {e}")
            
        return True
    finally:
        db.close()


def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else ""
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    print(f"\n{'='*60}")
    print(f"  [CPPP] Bulk Fetch - keyword='{keyword}', pages={pages}")
    print(f"{'='*60}\n")

    # Scrape CPPP
    tenders = scrape_cppp_listings(pages=pages, keyword_filter=keyword)
    print(f"\n[OK] Scraped {len(tenders)} tenders from CPPP.\n")

    if not tenders:
        print("No tenders found. Try a different keyword or more pages.")
        return

    profile = load_company_profile()
    saved = 0
    skipped = 0

    for i, tender in enumerate(tenders, 1):
        print(f"[{i}/{len(tenders)}] Processing: {tender['title'][:70]}...")

        # AI Analysis
        ai_data = analyse_tender_with_ai(tender)
        print(f"  → Type: {ai_data['tender_type']} | Risk: {ai_data['risk_level']}")

        # Scoring
        score, recommendation, reason = score_match(ai_data, profile)
        print(f"  → Score: {score}% | Decision: {recommendation}")

        # Save
        if save_to_db(tender, ai_data, score, recommendation, reason):
            saved += 1
            print(f"  [SAVED] Saved to database.")
            
            # Send Email Alert if High Priority
            if score >= 70:
                try:
                    from src.utils.email_service import send_tender_alert
                    send_tender_alert(
                        tender_id=tender["tender_id"],
                        title=tender["title"],
                        score=score,
                        recommendation=recommendation,
                        risk=ai_data.get("risk_level", "Unknown"),
                        deadline=ai_data.get("deadline", "Unknown")
                    )
                except Exception as e:
                    print(f"  [WARN] Could not send email alert: {e}")
                    
        else:
            skipped += 1

        print()

    print(f"\n{'='*60}")
    print(f"  Done! Saved: {saved} | Skipped (duplicates): {skipped}")
    print(f"  Run 'uv run streamlit run dashboard.py' to view results.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
