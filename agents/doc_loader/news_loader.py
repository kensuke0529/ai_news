from langchain_community.document_loaders import TextLoader
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import json
from dotenv import load_dotenv
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import hashlib
import pytz
from dateutil import parser as date_parser

load_dotenv()
OPEN_AI_KEY = os.environ.get("OPENAI_API_KEY")

llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPEN_AI_KEY)
output_parser = StrOutputParser()
rss_url = "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"

def get_article_id(entry):
    unique_string = entry.get("link", "") + entry.get("title", "")
    return hashlib.md5(unique_string.encode("utf-8")).hexdigest()

def get_week_start_end(target_date=None):
    """Get the start (Monday) and end (Sunday) of current week or specified date's week"""
    if target_date is None:
        target_date = datetime.now()
    
    # Ensure we're working with a datetime object
    if isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
    
    # Convert to local timezone if it has timezone info
    if target_date.tzinfo is not None:
        target_date = target_date.replace(tzinfo=None)
    
    days_since_monday = target_date.weekday()
    start_of_week = target_date - timedelta(days=days_since_monday)
    end_of_week = start_of_week + timedelta(days=6)
    
    # Set time to beginning/end of day
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start_of_week, end_of_week

def get_week_tag(target_date=None):
    """Generate week tag in ISO format (e.g., 2025-W35)"""
    if target_date is None:
        target_date = datetime.now()
    
    # Ensure we're working with a datetime object
    if isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
    
    if target_date.tzinfo is not None:
        target_date = target_date.replace(tzinfo=None)
    
    year, week_num, _ = target_date.isocalendar()
    return f"{year}-W{week_num:02d}"

def parse_article_date(date_string):
    """Parse RSS date string to datetime object with better error handling"""
    if not date_string:
        return None
    
    try:
        # First try dateutil parser which handles most formats
        parsed_date = date_parser.parse(date_string)
        # Convert to naive datetime for consistent comparison
        if parsed_date.tzinfo is not None:
            parsed_date = parsed_date.replace(tzinfo=None)
        return parsed_date
    except Exception:
        pass
    
    # Fallback to manual parsing
    try:
        formats = [
            "%a, %d %b %Y %H:%M:%S %z",  # RFC 822
            "%a, %d %b %Y %H:%M:%S GMT", # GMT format
            "%a, %d %b %Y %H:%M:%S",     # No timezone
            "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601 with tz
            "%Y-%m-%dT%H:%M:%S",         # ISO 8601 no tz
            "%Y-%m-%d %H:%M:%S",         # Simple format
            "%Y-%m-%d",                  # Date only
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_string, fmt)
                # Remove timezone info if present
                if parsed_date.tzinfo is not None:
                    parsed_date = parsed_date.replace(tzinfo=None)
                return parsed_date
            except ValueError:
                continue
    except Exception:
        pass
    
    print(f"Warning: Could not parse date string: {date_string}")
    return None

def tag_weekly_articles():
    """Load existing JSON and tag articles with their respective weeks"""
    file_path = "../../data/mit_ai_news.json"
    
    if not os.path.exists(file_path):
        print("No existing articles file found.")
        return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        
        updated_count = 0
        
        for article in articles:
            date_string = article.get("date", "")
            if not date_string:
                continue
            
            # Parse the article date
            article_date = parse_article_date(date_string)
            
            if article_date:
                # Generate week tag for this article's date
                article_week_tag = get_week_tag(article_date)
                
                # Only update if week tag is missing or different
                if article.get("week") != article_week_tag:
                    article["week"] = article_week_tag
                    updated_count += 1
        
        # Save updated articles
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=4)
        
        print(f"Updated {updated_count} articles with week tags")
            
    except Exception as e:
        print(f"Error tagging weekly articles: {e}")

def get_articles_for_week(week_tag=None):
    """Get all articles for a specific week"""
    if week_tag is None:
        week_tag = get_week_tag()
    
    file_path = "../../data/mit_ai_news.json"
    
    if not os.path.exists(file_path):
        print("No existing articles file found.")
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        
        # Filter articles by week tag
        weekly_articles = []
        for article in articles:
            if article.get("week") == week_tag:
                weekly_articles.append(article)
        
        # Sort by date (newest first)
        weekly_articles.sort(key=lambda x: parse_article_date(x.get("date", "")) or datetime.min, reverse=True)
        
        return weekly_articles
        
    except Exception as e:
        print(f"Error getting articles for week {week_tag}: {e}")
        return []

# ==================================================================== #
def process_specific_week(week_tag):
    """Process articles for a specific week - useful for reprocessing or testing"""
    print(f"Processing articles for week {week_tag}...")
    save_weekly_articles_with_summary(week_tag)

def list_available_weeks():
    """List all weeks that have articles"""
    file_path = "../../data/mit_ai_news.json"
    if not os.path.exists(file_path):
        print("No articles file found")
        return []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            articles = json.load(f)
        
        week_counts = {}
        for article in articles:
            week = article.get("week")
            if week:
                week_counts[week] = week_counts.get(week, 0) + 1
        
        print("Available weeks and article counts:")
        for week in sorted(week_counts.keys(), reverse=True):
            print(f"  {week}: {week_counts[week]} articles")
        
        return list(week_counts.keys())
        
    except Exception as e:
        print(f"Error listing weeks: {e}")
        return []

# ==================================================================== #
def test_week_calculation():
    """Test function to verify week calculation accuracy"""
    test_dates = [
        "Thu, 28 Aug 2025 11:50:00 -0400",  # Should be W35
        "Tue, 26 Aug 2025 09:00:00 -0400",  # Should be W35
        "Mon, 25 Aug 2025 17:00:00 -0400",  # Should be W35
        "Mon, 01 Sep 2025 12:00:00 -0400",  # Should be W36
    ]
    
    for date_str in test_dates:
        parsed_date = parse_article_date(date_str)
        week_tag = get_week_tag(parsed_date)
        start_week, end_week = get_week_start_end(parsed_date)
        
        print(f"Date: {date_str}")
        print(f"  Parsed: {parsed_date}")
        print(f"  Week: {week_tag}")
        print(f"  Week range: {start_week.strftime('%Y-%m-%d')} to {end_week.strftime('%Y-%m-%d')}")
        print()

# ==================================================================== #
def doc_loader(file_path):
    """Load and process text documents"""
    try:
        loader = TextLoader(file_path)
        documents = loader.load()
        
        data_list = []
        for doc in documents:
            data_list.append({
                "source": doc.metadata.get('source', ''), 
                "content": doc.page_content,
                "processed_at": datetime.now().isoformat()
            })
            
        os.makedirs("../../data", exist_ok=True)        
        
        with open("../../documents.json", "w", encoding="utf-8") as f:
            json.dump(data_list, f, ensure_ascii=False, indent=4)
        
        return {"news_text": documents[0].page_content if documents else ""}
        
    except Exception as e:
        print(f"Error loading document: {e}")
        return {"news_text": ""}

# ==================================================================== #
def fetch_mit_news(max_articles=5):
    """Fetch and process MIT AI news from RSS feed, avoiding duplicates"""
    try:
        print("Fetching RSS feed...")
        feed = feedparser.parse(rss_url)

        if not feed.entries:
            return {"news_text": "No news articles found", "link": "", "title": "", "date": ""}

        # Load existing articles if file exists
        existing_data = []
        existing_ids = set()
        file_path = "../../data/mit_ai_news.json"

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                existing_ids = {article.get("id") for article in existing_data if "id" in article}

        new_articles = []
        print(f"Processing {min(len(feed.entries), max_articles)} articles...")

        for entry in feed.entries[:max_articles]:
            article_id = get_article_id(entry)

            # Skip if already exists
            if article_id in existing_ids:
                print(f"Skipping existing article: {entry.get('title', 'Unknown')}")
                continue

            # Extract content with fallback
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].get("value", "")
            elif hasattr(entry, 'summary'):
                content = entry.summary
            else:
                content = entry.get("description", "")

            text_content = BeautifulSoup(content, "html.parser").get_text().strip()
            
            # Parse and validate date
            date_string = entry.get("published", "") or entry.get("updated", "")
            article_date = parse_article_date(date_string)
            week_tag = get_week_tag(article_date) if article_date else get_week_tag()

            new_article = {
                "id": article_id,
                "date": date_string,
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "description": entry.get("description", ""),
                "content": text_content,
                "week": week_tag,
                "processed_at": datetime.now().isoformat()
            }
            
            new_articles.append(new_article)
            print(f"New article added: {entry.get('title', 'Unknown')} (Week: {week_tag})")

        # Merge old and new
        all_articles = existing_data + new_articles

        # Save updated file
        os.makedirs("../../data", exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=4)

        print(f"Added {len(new_articles)} new articles")

        if not new_articles:
            # If no new articles, return the most recent existing article
            if existing_data:
                # Sort by parsed date
                sorted_articles = sorted(existing_data, 
                                       key=lambda x: parse_article_date(x.get("date", "")) or datetime.min, 
                                       reverse=True)
                latest_article = sorted_articles[0]
                return {
                    "title": latest_article.get("title", ""),
                    "news_text": latest_article.get("content", ""),
                    "link": latest_article.get("link", ""),
                    "date": latest_article.get("date", "")
                }
            else:
                return {"news_text": "", "link": "", "title": "", "date": ""}

        # Return the latest *new* article for summarization
        sorted_new = sorted(new_articles, 
                          key=lambda x: parse_article_date(x.get("date", "")) or datetime.min, 
                          reverse=True)
        latest_article = sorted_new[0]
        return {
            "title": latest_article.get("title", ""),
            "news_text": latest_article.get("content", ""),
            "link": latest_article.get("link", ""),
            "date": latest_article.get("date", "")
        }

    except Exception as e:
        print(f"Error fetching news: {e}")
        return {"news_text": f"Error fetching news: {e}", "link": "", "title": "", "date": ""}

# ==================================================================== #
def summarize_news(title, news_text, link, date, week_tag=None, save_to_file=True):
    """Generate AI news summary using LangChain"""
    if not news_text.strip():
        return {"title": title, "summary": "No content available for summarization", "link": link, "date": date}
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful summarizer of current AI trend news. Make a single-sentence summary of the provided news."),
        ("human", "{news_text}"),
    ])
    
    # Create chain with output parser
    chain = prompt | llm | output_parser
    
    try:
        response = chain.invoke({"news_text": news_text})
        
        # Use provided week_tag or calculate from date
        if week_tag is None:
            article_date = parse_article_date(date)
            week_tag = get_week_tag(article_date) if article_date else get_week_tag()
        
        summary = {"title": title, "summary": response, "link": link, "date": date, "week": week_tag}
    
        if save_to_file:
            os.makedirs("../../data", exist_ok=True)
            output_file = f"../../data/weekly_summary_{week_tag}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=4)
            
        return summary
    except Exception as e:
        # Use provided week_tag or calculate from date
        if week_tag is None:
            article_date = parse_article_date(date)
            week_tag = get_week_tag(article_date) if article_date else get_week_tag()
        return {"title": title, "summary": f"Error generating summary: {e}", "link": link, "date": date, "week": week_tag}

# ==================================================================== #
def save_weekly_articles_with_summary(week_tag=None):
    """Create a separate JSON for specified week's articles including AI summaries"""
    if week_tag is None:
        week_tag = get_week_tag()
    
    print(f"Processing articles for week {week_tag}...")
    
    # Get articles for the specified week
    weekly_articles_data = get_articles_for_week(week_tag)
    
    if not weekly_articles_data:
        print(f"No articles found for week {week_tag}")
        return

    weekly_articles = []
    
    for article in weekly_articles_data:
        print(f"Generating summary for: {article.get('title', 'Unknown')}")
        
        # Generate AI summary for the article, preserving existing week tag
        summary_obj = summarize_news(
            article.get("title", ""),
            article.get("content", ""),
            article.get("link", ""),
            article.get("date", ""),
            article.get("week"),  # Pass existing week tag
            save_to_file=False
        )

        weekly_articles.append({
            "id": article.get("id"),
            "title": article.get("title"),
            "link": article.get("link"),
            "date": article.get("date"),
            "content": article.get("content"),
            "summary": summary_obj.get("summary"),
            "week": week_tag
        })

    # Calculate week boundaries based on the actual week being processed
    # Use the first article's date to determine the correct week boundaries
    if weekly_articles_data:
        first_article_date = parse_article_date(weekly_articles_data[0].get("date", ""))
        if first_article_date:
            start_of_week, end_of_week = get_week_start_end(first_article_date)
        else:
            # Fallback to current date if parsing fails
            start_of_week, end_of_week = get_week_start_end()
    else:
        start_of_week, end_of_week = get_week_start_end()

    # Unique file per week
    output_file = f"../../data/week-{week_tag}.json"

    weekly_output = {
        "week": week_tag,
        "start_of_week": start_of_week.isoformat(),
        "end_of_week": end_of_week.isoformat(),
        "article_count": len(weekly_articles),
        "articles": weekly_articles
    }

    os.makedirs("../../data", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(weekly_output, f, ensure_ascii=False, indent=4)

    print(f"Weekly JSON with {len(weekly_articles)} articles and summaries saved to {output_file}")

# ==================================================================== #
# ==================================================================== #
def main():    
    import sys
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            print("Listing available weeks:")
            list_available_weeks()
            return
        elif command == "process" and len(sys.argv) > 2:
            week_tag = sys.argv[2]
            print(f"Processing specific week: {week_tag}")
            process_specific_week(week_tag)
            return
        elif command == "test":
            print("Testing week calculation:")
            test_week_calculation()
            return
        else:
            print("Usage:")
            print("  python3 news_loader.py          - Full processing")
            print("  python3 news_loader.py list     - List available weeks")
            print("  python3 news_loader.py process <week>  - Process specific week (e.g., 2025-W35)")
            print("  python3 news_loader.py test     - Test week calculation")
            return
    
    print("Starting MIT AI News processing...")
    
    # Test week calculation
    print("Testing week calculation:")
    test_week_calculation()
    
    # Fetch new articles
    news_data = fetch_mit_news(max_articles=5)

    # Check if we have valid news data before proceeding
    if news_data.get("news_text") and news_data.get("news_text").strip():
        # Ensure all required keys exist with default values
        title = news_data.get("title", "")
        news_text = news_data.get("news_text", "")
        link = news_data.get("link", "")
        date = news_data.get("date", "")
        
        print("\nGenerating summary for latest article...")
        summary_data = summarize_news(title, news_text, link, date, save_to_file=False)
        print("Summary generated:")
        print(f"Title: {summary_data.get('title', 'N/A')}")
        print(f"Summary: {summary_data.get('summary', 'N/A')}")
        print(f"Week: {summary_data.get('week', 'N/A')}")
    else:
        print("No valid news content found for summarization")

    # Tag all articles with their respective weeks
    print("\nTagging articles with week information...")
    tag_weekly_articles()

    # Save weekly JSON with summaries for the most recent week that has articles
    print("\nCreating weekly summary file...")
    
    # Find the most recent week with articles
    file_path = "../../data/mit_ai_news.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
            
            # Get all unique week tags and find the most recent one
            week_tags = set()
            for article in articles:
                if article.get("week"):
                    week_tags.add(article.get("week"))
            
            if week_tags:
                # Sort week tags to find the most recent
                sorted_weeks = sorted(week_tags, reverse=True)
                latest_week = sorted_weeks[0]
                print(f"Processing articles for most recent week with data: {latest_week}")
                save_weekly_articles_with_summary(latest_week)
            else:
                print("No week tags found in articles")
                
        except Exception as e:
            print(f"Error finding recent week: {e}")
    else:
        print("No articles file found")
    
    print("\nProcessing completed!")

# ==================================================================== #
if __name__ == "__main__":
    main()