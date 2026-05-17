"""
agents.py — CrewAI Agent definitions for the Tender Intelligence Platform.
All tool imports now use flat root-level paths.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crewai import Agent
from tools.pdf_tool import PDFExtractionTool
from tools.notification_tool import NotificationTool
from scraper_tool import PlaywrightScraperTool
from db_tool import DatabaseStorageTool


def create_agents(llm):
    """Instantiate and return all CrewAI agents."""

    scraper_agent = Agent(
        role="Tender Scraper",
        goal="Search and extract active tender listings from the CPPP government procurement portal.",
        backstory=(
            "You are an expert data extraction bot designed to navigate government portals, "
            "handle bot detection, and return structured tender data for downstream analysis."
        ),
        tools=[PlaywrightScraperTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    pdf_agent = Agent(
        role="PDF Processing Specialist",
        goal="Download tender documents and extract all structured content: budget, EMD, deadlines, eligibility.",
        backstory=(
            "You specialize in parsing complex government PDF documents. "
            "You never miss a budget figure, EMD requirement, or eligibility clause."
        ),
        tools=[PDFExtractionTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    analysis_agent = Agent(
        role="Tender AI Analyst",
        goal="Analyse tender text and extract structured intelligence: budget, EMD, deadlines, type, and risk level.",
        backstory=(
            "A seasoned government contractor who reads 100-page tender documents in minutes, "
            "extracting every critical figure, requirement, and risk factor."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    matching_agent = Agent(
        role="Company Profile Matcher",
        goal="Compare tender requirements against the company profile to compute an eligibility and match score.",
        backstory=(
            "Head of Business Development. Knows the company's capabilities, past experience, "
            "and financial limits perfectly. Evaluates every new tender with precision."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    ranking_agent = Agent(
        role="Opportunity Ranker",
        goal="Assign risk level (Low/Medium/High), match score (0-100), and Go/No-Go/Review recommendation.",
        backstory=(
            "Chief Risk Officer. Analyses match data and financial risk, "
            "producing a final numeric score and a clear, actionable recommendation."
        ),
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    db_agent = Agent(
        role="Database Manager",
        goal="Save fully analysed and ranked tender data to the database and vector index.",
        backstory=(
            "A meticulous Data Engineer ensuring all tender intelligence is "
            "perfectly formatted and persisted without data loss."
        ),
        tools=[DatabaseStorageTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )

    notification_agent = Agent(
        role="Smart Notification Dispatcher",
        goal="Dispatch priority alerts for high-match or urgent opportunities via email and log.",
        backstory=(
            "An intelligent alerting system that reviews final tender intelligence and sends "
            "structured notifications so the BD team never misses a critical opportunity."
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
