from pathlib import Path
from datetime import datetime
import sys
import os
import json

# Add the agents directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from doc_loader.news_loader import get_week_tag

from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain_openai import ChatOpenAI

from dotenv import load_dotenv
load_dotenv()
OPEN_AI_KEY = os.environ.get("OPENAI_API_KEY")

def generate_weekly_summary():
    """
    Generate a weekly summary of AI news articles.
    
    Returns:
        str: The generated summary
    """
    # Get week tag and load JSON
    week_tag = "2025-W36"  
    project_root = Path(__file__).resolve().parent.parent.parent
    data_file = project_root / "data" / f"week-{week_tag}.json"

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return f"Data file not found: {data_file}"
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {e}"

    # Build a single string with all articles
    week_articles_text = ""
    for article in data.get("articles", []):
        title = article.get("title", "")
        link = article.get("link", "")
        summary = article.get("summary", "")
        week_articles_text += f"Title: {title}\nLink: {link}\nSummary: {summary}\n\n"

    # Enhanced system prompt
    system_prompt = """You are an AI news analyst. Create a comprehensive weekly summary of AI news articles. 
    Keep summaries concise but informative. Response 3 sentence."""

    # Simplified LangChain setup without deprecated memory
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPEN_AI_KEY)

    # Create chain using LCEL
    chain = prompt | llm

    # Invoke chain with our articles
    try:
        response = chain.invoke({"text": week_articles_text})
        return response.content
    except Exception as e:
        return f"Error generating summary: {e}"

# Keep existing main execution logic
if __name__ == "__main__":
    # Get week tag and load JSON
    week_tag = "2025-W36"  
    project_root = Path(__file__).resolve().parent.parent.parent
    data_file = project_root / "data" / f"week-{week_tag}.json"

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Data file not found: {data_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        sys.exit(1)

    # Build a single string with all articles
    week_articles_text = ""
    for article in data.get("articles", []):
        title = article.get("title", "")
        link = article.get("link", "")
        summary = article.get("summary", "")
        week_articles_text += f"Title: {title}\nLink: {link}\nSummary: {summary}\n\n"

    # Enhanced system prompt
    system_prompt = """You are an AI news analyst. Create a comprehensive weekly summary of AI news articles. 
    Keep summaries concise but informative. Response 3 sentence."""

    # Simplified LangChain setup without deprecated memory
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{text}")
    ])

    llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPEN_AI_KEY)

    # Create chain using LCEL
    chain = prompt | llm

    # Invoke chain with our articles
    try:
        response = chain.invoke({"text": week_articles_text})
        print(response.content)
    except Exception as e:
        print(f"Error generating summary: {e}")
        sys.exit(1)