"""
cppp_bulk_fetch.py — Enhanced AI Tender Ingestion Pipeline

Pipeline:
  1. Scrape live tenders from CPPP (with retry + fallback)
  2. Best-effort PDF download and text extraction
  3. AI analysis via OpenRouter (Gemini Flash) with retry + JSON validation
  4. Rule-based + AI-assisted match scoring
  5. Save to SQLite + index in ChromaDB vector store
  6. Gmail SMTP alerts for high-priority matches

Run:  uv run python cppp_bulk_fetch.py [keyword] [pages]
      uv run python cppp_bulk_fetch.py "Road" 2
"""
import sys
import os
import json
import re
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# ── Encoding fix (Windows) — must be before any print ─────────────────────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

load_dotenv()

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from openai import OpenAI
from scraper.cppp_scraper import scrape_cppp_listings
from scraper.pdf_downloader import download_and_extract_pdf
from db import init_db, get_db
from models import Tender
from vector_db import get_vector_db
from email_service import send_tender_alert

# ── OpenRouter Client ─────────────────────────────────────────────────────────
API_KEY = os.getenv("OPENROUTER_API_KEY", "")
if not API_KEY:
    print("[WARN] OPENROUTER_API_KEY not set — AI analysis will use mock data.")

client = OpenAI(
    api_key=API_KEY or "sk-dummy",
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://github.com/tender-intelligence",
        "X-Title": "AI Tender Intelligence Platform",
    },
)

# ── Model config ──────────────────────────────────────────────────────────────
AI_MODEL = os.getenv("AI_MODEL", "google/gemini-flash-1.5")
FALLBACK_MODELS = [
    "google/gemini-flash-1.5",
    "openai/gpt-3.5-turbo",
    "anthropic/claude-haiku",
    "mistralai/mistral-7b-instruct",
]
MAX_AI_RETRIES = 3
AI_RETRY_DELAY = 2


# ── AI Analysis ───────────────────────────────────────────────────────────────
ANALYSIS_PROMPT = """You are an expert Indian government tender analyst with 15 years of experience.

Analyse the following tender details and extract all structured fields.
You MUST provide a specific value for every field — never leave anything as "Not Mentioned".
Make confident, specific inferences based on the tender category and typical government practices.

Tender Details:
Title: {title}
Organization: {organization}
Department: {department}
PDF Content (if available): {pdf_excerpt}

Return ONLY a valid JSON object (no markdown, no explanation, just the JSON):
{{
  "tender_type": "Specific category (e.g. Road Construction, IT Software, Civil Works, Water Supply, Electrical, Maintenance, Supply)",
  "budget": "Specific estimated budget (e.g. Rs. 50 Lakh, Rs. 2-5 Crore, Rs. 15 Crore) — infer from project scope",
  "budget_numeric": <estimated value in Lakhs as a number, e.g. 500 for 5 Crore>,
  "deadline": "Typical closing period (e.g. 45 days from publication, or specific date if known)",
  "emd_amount": "Specific EMD amount (e.g. Rs. 1.5 Lakh — typically 2%% of bid value)",
  "emd_numeric": <estimated EMD in Lakhs as a number>,
  "required_experience": "Specific experience requirement (e.g. 5 years in road construction, Class-A contractor)",
  "eligibility_criteria": "Specific eligibility (e.g. Annual turnover >5 Cr, ISO certified, CPWD registered)",
  "risk_level": "Low / Medium / High — based on project size, complexity, and timeline",
  "summary": "One clear sentence describing exactly what work will be done and where",
  "key_concerns": "2-3 specific risks or challenges for this type of tender"
}}"""


def _clean_json_response(raw: str) -> str:
    """Strip markdown fences and extract JSON from AI response."""
    # Remove ```json ... ``` fences
    raw = re.sub(r"```(?:json)?\s*", "", raw)
    raw = re.sub(r"```\s*$", "", raw)
    # Find first { and last }
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        return raw[start:end]
    return raw.strip()


def analyse_tender_with_ai(tender: dict, pdf_text: str = "") -> dict:
    """
    Send tender data to AI with retry logic across multiple models.
    Falls back to intelligent rule-based analysis if all AI calls fail.
    """
    pdf_excerpt = pdf_text[:3000] if pdf_text else "Not available"

    prompt = ANALYSIS_PROMPT.format(
        title=tender.get("title", "Unknown Tender"),
        organization=tender.get("organization", "Government of India"),
        department=tender.get("department", ""),
        pdf_excerpt=pdf_excerpt,
    )

    # Try each model with retries
    models_to_try = [AI_MODEL] + [m for m in FALLBACK_MODELS if m != AI_MODEL]

    for model in models_to_try[:2]:  # Max 2 models per tender
        for attempt in range(MAX_AI_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a government tender analysis expert. Always respond with valid JSON only.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=800,
                    timeout=30,
                )

                raw = response.choices[0].message.content.strip()
                cleaned = _clean_json_response(raw)
                data = json.loads(cleaned)

                # Validate required fields
                required_fields = ["tender_type", "budget", "deadline", "emd_amount",
                                   "required_experience", "eligibility_criteria", "risk_level", "summary"]
                if all(data.get(f) for f in required_fields):
                    data["_model_used"] = model
                    return data

                print(f"  [AI] Incomplete response from {model}, attempt {attempt + 1}")

            except json.JSONDecodeError as e:
                print(f"  [AI] JSON parse error ({model}, attempt {attempt + 1}): {e}")
            except Exception as e:
                err_str = str(e)
                if "rate" in err_str.lower() or "429" in err_str:
                    wait = AI_RETRY_DELAY * (2 ** attempt) + random.uniform(1, 3)
                    print(f"  [AI] Rate limited — waiting {wait:.1f}s")
                    time.sleep(wait)
                else:
                    print(f"  [AI] Error ({model}, attempt {attempt + 1}): {err_str[:100]}")

            if attempt < MAX_AI_RETRIES - 1:
                time.sleep(AI_RETRY_DELAY * (attempt + 1))

    # ── Intelligent fallback (rule-based) ─────────────────────────────────────
    print(f"  [AI] All models failed — using intelligent rule-based analysis")
    return _rule_based_analysis(tender)


def _rule_based_analysis(tender: dict) -> dict:
    """
    Intelligent rule-based analysis when AI is unavailable.
    Infers fields from title keywords — much better than "Not Mentioned".
    """
    title = tender.get("title", "").lower()
    org = tender.get("organization", "").lower()

    # Determine tender type
    type_map = {
        "road": "Road Construction",
        "highway": "Highway Development",
        "bridge": "Bridge Construction",
        "water": "Water Supply & Sanitation",
        "pipeline": "Pipeline Works",
        "software": "Software Development",
        "it": "IT Infrastructure",
        "cctv": "Security & Surveillance",
        "cyber": "Cybersecurity Services",
        "electric": "Electrical Works",
        "solar": "Renewable Energy",
        "building": "Building Construction",
        "hospital": "Healthcare Infrastructure",
        "school": "Education Infrastructure",
        "maintenance": "Operation & Maintenance",
        "supply": "Goods Supply",
        "cable": "Telecom Infrastructure",
        "railway": "Railway Infrastructure",
        "drainage": "Drainage & Sanitation",
    }

    tender_type = "Civil Works"
    for kw, cat in type_map.items():
        if kw in title:
            tender_type = cat
            break

    # Budget inference by category
    budget_map = {
        "Road Construction": ("Rs. 10-50 Crore", 2500, 50),
        "Highway Development": ("Rs. 50-200 Crore", 12500, 250),
        "Bridge Construction": ("Rs. 20-100 Crore", 6000, 120),
        "Water Supply & Sanitation": ("Rs. 5-20 Crore", 1250, 25),
        "Software Development": ("Rs. 2-10 Crore", 600, 12),
        "IT Infrastructure": ("Rs. 3-15 Crore", 900, 18),
        "Electrical Works": ("Rs. 5-25 Crore", 1500, 30),
        "Building Construction": ("Rs. 10-50 Crore", 3000, 60),
        "Goods Supply": ("Rs. 1-5 Crore", 300, 6),
        "Operation & Maintenance": ("Rs. 50 Lakh - 5 Crore", 275, 5.5),
    }

    budget_str, budget_num, emd_num = budget_map.get(tender_type, ("Rs. 5-25 Crore", 1500, 30))
    emd_str = f"Rs. {emd_num:.1f} Lakh (approx. 2% of bid value)"

    # Risk based on budget
    if budget_num > 5000:
        risk = "High"
    elif budget_num > 1000:
        risk = "Medium"
    else:
        risk = "Low"

    return {
        "tender_type": tender_type,
        "budget": budget_str,
        "budget_numeric": budget_num,
        "deadline": "45–60 days from date of publication",
        "emd_amount": emd_str,
        "emd_numeric": emd_num,
        "required_experience": f"Minimum 5 years in {tender_type}, Class-I contractor registration",
        "eligibility_criteria": (
            f"Annual turnover ≥ Rs. {max(1, int(budget_num / 300))} Crore, "
            "valid GST registration, EPFO/ESIC compliance, no blacklisting"
        ),
        "risk_level": risk,
        "summary": f"{tender.get('title', 'Government tender')} — {tender_type} project by {tender.get('organization', 'Government')}",
        "key_concerns": f"Competitive bidding expected; ensure compliance with {tender_type} technical specs",
        "_model_used": "rule-based",
    }


# ── Match Scoring ─────────────────────────────────────────────────────────────

def load_company_profile() -> dict:
    path = os.path.join(PROJECT_ROOT, "company_profile.json")
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "company_name": "TechBuild Infrastructure Pvt Ltd",
            "experience_years": 8,
            "annual_turnover_crore": 25,
            "specialization": ["Road Construction", "IT Infrastructure", "Civil Works"],
            "max_emd_capacity_lakh": 50,
            "max_project_value_crore": 30,
        }


def score_match(ai_data: dict, tender: dict, profile: dict) -> tuple[int, str, str]:
    """
    Multi-factor scoring: specialization match + risk + budget feasibility + experience.
    Returns (score: int, recommendation: str, reason: str)
    """
    score = 40  # Base
    notes = []

    specs = [s.lower() for s in profile.get("specialization", [])]
    tender_type_lower = ai_data.get("tender_type", "").lower()
    title_lower = tender.get("title", "").lower()
    summary_lower = ai_data.get("summary", "").lower()

    # ── Specialization match (up to +30) ─────────────────────────────────────
    spec_matched = False
    for spec in specs:
        spec_words = spec.lower().split()
        if any(w in title_lower or w in tender_type_lower or w in summary_lower for w in spec_words):
            score += 30
            notes.append(f"Core specialization match: {spec}")
            spec_matched = True
            break

    if not spec_matched:
        # Partial keyword match
        for spec in specs:
            spec_words = spec.lower().split()
            if any(w in title_lower for w in spec_words):
                score += 15
                notes.append(f"Partial match: {spec}")
                break

    # ── Risk adjustment (±15) ─────────────────────────────────────────────────
    risk = ai_data.get("risk_level", "Medium").lower()
    if risk == "low":
        score += 15
        notes.append("Low risk project")
    elif risk == "medium":
        score += 5
    elif risk == "high":
        score -= 15
        notes.append("High risk — careful evaluation needed")

    # ── Budget feasibility (+10 or -10) ───────────────────────────────────────
    max_crore = profile.get("max_project_value_crore", 30)
    budget_num = ai_data.get("budget_numeric", 0)
    if budget_num > 0:
        budget_crore = budget_num / 100  # Convert Lakh to Crore
        if budget_crore <= max_crore:
            score += 10
            notes.append(f"Budget within capacity (≤{max_crore} Cr)")
        elif budget_crore <= max_crore * 2:
            score += 0
            notes.append("Slightly above normal capacity — consortium possible")
        else:
            score -= 10
            notes.append(f"Budget exceeds capacity ({budget_crore:.0f} Cr vs {max_crore} Cr limit)")

    # ── EMD feasibility (+5 or -10) ───────────────────────────────────────────
    max_emd = profile.get("max_emd_capacity_lakh", 50)
    emd_num = ai_data.get("emd_numeric", 0)
    if emd_num > 0:
        if emd_num <= max_emd:
            score += 5
        else:
            score -= 10
            notes.append(f"EMD exceeds capacity ({emd_num:.0f}L vs {max_emd}L limit)")

    # ── Experience check (+10) ────────────────────────────────────────────────
    exp_text = ai_data.get("required_experience", "").lower()
    exp_years = profile.get("experience_years", 0)
    exp_match = re.search(r"(\d+)\s*year", exp_text)
    if exp_match:
        required_years = int(exp_match.group(1))
        if exp_years >= required_years:
            score += 10
            notes.append(f"Experience sufficient ({exp_years}yr ≥ {required_years}yr required)")
        else:
            score -= 5
            notes.append(f"Experience gap ({exp_years}yr < {required_years}yr required)")

    score = max(0, min(100, score))

    # ── Recommendation ────────────────────────────────────────────────────────
    if score >= 70:
        recommendation = "Go"
    elif score >= 50:
        recommendation = "Review"
    else:
        recommendation = "No-Go"

    reason = "; ".join(notes) if notes else "General profile assessment"
    return score, recommendation, reason


# ── Database Operations ───────────────────────────────────────────────────────

def save_to_db(tender: dict, ai_data: dict, pdf_result: dict,
               score: int, recommendation: str, reason: str) -> bool:
    """Save processed tender to SQLite. Returns True if saved, False if duplicate."""
    init_db()
    db = next(get_db())

    try:
        existing = db.query(Tender).filter(Tender.tender_id == tender["tender_id"]).first()
        if existing:
            print(f"  [SKIP] Already in DB: {tender['tender_id']}")
            return False

        record = Tender(
            tender_id=tender["tender_id"],
            title=tender.get("title", ""),
            organization=tender.get("organization", "CPPP"),
            department=tender.get("department", ""),
            published_date=tender.get("published_date", ""),
            closing_date=tender.get("closing_date", ""),
            detail_url=tender.get("detail_url", ""),
            pdf_url=pdf_result.get("pdf_url", ""),
            status="active",
            tender_type=ai_data.get("tender_type", ""),
            budget=ai_data.get("budget", ""),
            budget_numeric=float(ai_data.get("budget_numeric", 0) or 0),
            deadline=ai_data.get("deadline", ""),
            emd_amount=ai_data.get("emd_amount", ""),
            emd_numeric=float(ai_data.get("emd_numeric", 0) or 0),
            required_experience=ai_data.get("required_experience", ""),
            eligibility_criteria=ai_data.get("eligibility_criteria", ""),
            risk_level=ai_data.get("risk_level", "Medium"),
            summary=ai_data.get("summary", ""),
            pdf_text=pdf_result.get("text", "")[:10000],
            match_score=str(score),
            match_score_num=float(score),
            recommendation=recommendation,
            match_reason=reason,
            raw_data={**tender, **ai_data, "match_score": score, "recommendation": recommendation},
        )
        db.add(record)
        db.commit()

        # ── Index to ChromaDB ─────────────────────────────────────────────────
        try:
            vdb = get_vector_db()
            text_for_embedding = (
                f"{tender['title']} {ai_data.get('summary', '')} "
                f"{ai_data.get('tender_type', '')} {tender.get('organization', '')}"
            )
            vdb.add_tender(
                tender_id=tender["tender_id"],
                text=text_for_embedding,
                metadata={
                    "title": tender["title"],
                    "organization": tender.get("organization", ""),
                    "risk_level": ai_data.get("risk_level", ""),
                    "score": score,
                    "recommendation": recommendation,
                },
            )
        except Exception as e:
            print(f"  [WARN] Vector DB indexing failed: {e}")

        return True
    finally:
        db.close()


# ── Main Pipeline ─────────────────────────────────────────────────────────────

def main():
    keyword = sys.argv[1] if len(sys.argv) > 1 else ""
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    enable_pdf = os.getenv("ENABLE_PDF_DOWNLOAD", "false").lower() == "true"

    print(f"\n{'='*60}")
    print(f"  AI TENDER INTELLIGENCE PIPELINE")
    print(f"  Keyword: '{keyword}' | Pages: {pages} | PDF: {enable_pdf}")
    print(f"  Model: {AI_MODEL}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Step 1: Scrape
    tenders = scrape_cppp_listings(pages=pages, keyword_filter=keyword)
    if not tenders:
        print("[ERROR] No tenders returned. Exiting.")
        sys.exit(1)

    # Step 2: Load company profile
    profile = load_company_profile()
    print(f"[OK] Company: {profile.get('company_name')} | Specializations: {len(profile.get('specialization', []))}\n")

    saved = 0
    skipped = 0
    errors = 0

    for i, tender in enumerate(tenders, 1):
        title_short = tender["title"][:65]
        print(f"[{i:02d}/{len(tenders)}] {title_short}...")

        # Step 3: Best-effort PDF extraction
        pdf_result = {"success": False, "text": "", "pdf_url": ""}
        if enable_pdf and tender.get("detail_url", "").startswith("http"):
            print(f"  [PDF] Attempting download...")
            pdf_result = download_and_extract_pdf(
                detail_url=tender.get("detail_url", ""),
                pdf_url=tender.get("pdf_url", ""),
            )
            if pdf_result["success"]:
                print(f"  [PDF] ✓ Extracted {pdf_result['pages']} pages")

        # Step 4: AI Analysis
        ai_data = analyse_tender_with_ai(tender, pdf_result.get("text", ""))
        model_used = ai_data.get("_model_used", "unknown")
        print(f"  → Type: {ai_data['tender_type']} | Risk: {ai_data['risk_level']} | Model: {model_used}")

        # Step 5: Scoring
        score, recommendation, reason = score_match(ai_data, tender, profile)
        score_icon = "✅" if recommendation == "Go" else ("⚠️" if recommendation == "Review" else "❌")
        print(f"  → Score: {score}% | {score_icon} {recommendation} | {reason[:60]}")

        # Step 6: Save
        try:
            saved_ok = save_to_db(tender, ai_data, pdf_result, score, recommendation, reason)
            if saved_ok:
                saved += 1
                print(f"  [SAVED] ✓ Database + Vector index updated")

                # Step 7: Email alert for high-priority
                min_score = profile.get("min_match_score_for_alert", 65)
                if score >= min_score:
                    send_tender_alert(
                        tender_id=tender["tender_id"],
                        title=tender["title"],
                        score=score,
                        recommendation=recommendation,
                        risk=ai_data.get("risk_level", "Unknown"),
                        deadline=ai_data.get("deadline", "Unknown"),
                        summary=ai_data.get("summary", ""),
                        organization=tender.get("organization", ""),
                    )
            else:
                skipped += 1
        except Exception as e:
            print(f"  [ERROR] Failed to save: {e}")
            errors += 1

        print()

        # Rate limit protection — brief pause between tenders
        if i < len(tenders):
            time.sleep(random.uniform(0.5, 1.5))

    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  Saved: {saved} | Skipped (duplicates): {skipped} | Errors: {errors}")
    print(f"  Total processed: {len(tenders)}")
    print(f"  Run 'uv run streamlit run dashboard.py' to view results")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
