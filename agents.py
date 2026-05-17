from crewai import Agent
import os
from src.tools.scraper_tool import PlaywrightScraperTool
from src.tools.pdf_tool import PDFExtractionTool
from src.tools.db_tool import DatabaseStorageTool
from src.tools.notification_tool import NotificationTool


def create_agents(llm):
    """Instantiate and return all 7 CrewAI agents."""

    scraper_agent = Agent(
        role='Tender Scraper',
        goal='Search and extract tender links and basic metadata from government procurement portals (e.g., CPPP).',
        backstory=(
            'You are an expert data extraction bot designed to navigate complex government portals, '
            'avoid bot detection, and find the most relevant business opportunities.'
        ),
        tools=[PlaywrightScraperTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    pdf_agent = Agent(
        role='PDF Processing Specialist',
        goal='Download tender PDFs and extract all text content accurately.',
        backstory=(
            'You specialize in parsing complex government PDF documents, ensuring no text, '
            'table, or requirement is missed during the extraction process.'
        ),
        tools=[PDFExtractionTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    analysis_agent = Agent(
        role='Tender AI Analyst',
        goal='Analyse raw tender text and extract structured key information (budget, EMD, deadlines, criteria).',
        backstory=(
            'You are a seasoned government contractor who can quickly skim a 100-page tender document '
            'and pinpoint the budget, deadlines, and eligibility requirements.'
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    matching_agent = Agent(
        role='Company Profile Matcher',
        goal='Compare the extracted tender requirements against the company profile to determine eligibility.',
        backstory=(
            'You are the Head of Business Development. You know the company's capabilities, past experience, '
            'and financial limits perfectly. You evaluate if a new tender is a good fit.'
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    ranking_agent = Agent(
        role='Opportunity Ranker',
        goal='Assign a risk level, a match score (0-100), and a final Go/No-Go recommendation for each tender.',
        backstory=(
            'You are the Chief Risk Officer. You analyse match data and assess financial and operational risk, '
            'ultimately producing a final numeric score and clear recommendation.'
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    db_agent = Agent(
        role='Database Manager',
        goal='Save the fully analysed and ranked tender into the database securely.',
        backstory=(
            'You are a meticulous Data Engineer who ensures all tender intelligence is perfectly '
            'formatted and stored without data loss.'
        ),
        tools=[DatabaseStorageTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    notification_agent = Agent(
        role='Smart Notification Dispatcher',
        goal='Evaluate the final ranked tender and dispatch priority alerts for high-match or urgent opportunities.',
        backstory=(
            'You are an intelligent alerting system. You review the final tender intelligence and send '
            'structured notifications so the business development team never misses a critical opportunity.'
        ),
        tools=[NotificationTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    return {
        "scraper": scraper_agent,
        "pdf": pdf_agent,
        "analyzer": analysis_agent,
        "matcher": matching_agent,
        "ranker": ranking_agent,
        "db": db_agent,
        "notification": notification_agent,
    }
