import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import sys
from dateutil import parser as date_parser

load_dotenv()
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def parse_rss_date(date_string):
    """Parse RSS date string to datetime object"""
    if not date_string:
        return None
    
    try:
        # Use dateutil parser which handles most formats
        parsed_date = date_parser.parse(date_string)
        return parsed_date
    except Exception as e:
        print(f"Error parsing date '{date_string}': {e}")
        return None

def add_article_to_notion(article):
    """Add a single article to Notion database"""
    try:
        # Parse the date more robustly
        date_obj = parse_rss_date(article.get("date", ""))
        if date_obj:
            iso_date = date_obj.isoformat()
        else:
            print(f"Skipping article due to invalid date: {article.get('title', 'Unknown')}")
            return False

        data = {
            "parent": {"database_id": DATABASE_ID},
            "properties": {
                "Title": {"title": [{"text": {"content": article.get("title", "No Title")}}]},
                "Summary": {"rich_text": [{"text": {"content": article.get("summary", "")}}]},
                "Link": {"rich_text": [{"text": {"content": article.get("link", ""), "link": {"url": article.get("link", "")}}}]},
                "Date": {"date": {"start": iso_date}},
                "Week": {"rich_text": [{"text": {"content": article.get("week", "")}}]}
            }
        }

        response = requests.post("https://api.notion.com/v1/pages", headers=headers, data=json.dumps(data))

        if response.status_code in (200, 201):
            print(f"✅ Added: {article.get('title', 'No Title')}")
            return True
        else:
            print(f"❌ Failed to add '{article.get('title', 'No Title')}': {response.status_code}")
            print(f"   Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error adding article '{article.get('title', 'Unknown')}': {e}")
        return False

def check_notion_connection():
    """Test if Notion API connection is working"""
    if not NOTION_TOKEN or not DATABASE_ID:
        print("❌ Missing NOTION_TOKEN or DATABASE_ID in environment variables")
        return False
    
    try:
        # Try to query the database
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        response = requests.post(url, headers=headers, data=json.dumps({"page_size": 1}))
        
        if response.status_code == 200:
            print("✅ Notion connection successful")
            return True
        else:
            print(f"❌ Notion connection failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing Notion connection: {e}")
        return False

def get_existing_articles_from_notion():
    """Get all existing articles from Notion database to check for duplicates"""
    existing_articles = {}
    
    try:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        
        # Query all pages in the database
        response = requests.post(url, headers=headers, data=json.dumps({
            "page_size": 100,
            "sorts": [{"property": "Date", "direction": "descending"}]
        }))
        
        if response.status_code != 200:
            print(f"❌ Failed to query Notion database: {response.status_code}")
            return existing_articles
        
        data = response.json()
        
        # Process all pages
        while True:
            for page in data.get("results", []):
                properties = page.get("properties", {})
                
                # Extract article ID (using link as unique identifier)
                link_prop = properties.get("Link", {})
                if link_prop.get("rich_text"):
                    link = link_prop["rich_text"][0].get("text", {}).get("content", "")
                    if link:
                        existing_articles[link] = {
                            "id": page.get("id"),
                            "title": properties.get("Title", {}).get("title", [{}])[0].get("text", {}).get("content", ""),
                            "link": link,
                            "date": properties.get("Date", {}).get("date", {}).get("start", "")
                        }
            
            # Check if there are more pages
            if data.get("has_more") and data.get("next_cursor"):
                response = requests.post(url, headers=headers, data=json.dumps({
                    "page_size": 100,
                    "start_cursor": data["next_cursor"]
                }))
                if response.status_code == 200:
                    data = response.json()
                else:
                    break
            else:
                break
        
        print(f"📊 Found {len(existing_articles)} existing articles in Notion database")
        return existing_articles
        
    except Exception as e:
        print(f"❌ Error getting existing articles from Notion: {e}")
        return existing_articles

def load_weekly_articles(week_tag):
    """Load articles from weekly JSON file"""
    file_path = f"../../data/week-{week_tag}.json"
    
    if not os.path.exists(file_path):
        print(f"❌ Weekly file not found: {file_path}")
        return None
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        articles = data.get("articles", [])
        print(f"📄 Loaded {len(articles)} articles for week {week_tag}")
        return data
    
    except Exception as e:
        print(f"❌ Error loading weekly file: {e}")
        return None

def list_available_weekly_files():
    """List all available weekly JSON files with summaries"""
    data_dir = "../../data"
    
    if not os.path.exists(data_dir):
        print("❌ Data directory not found")
        return
    
    weekly_files = []
    for filename in os.listdir(data_dir):
        if filename.startswith("week-") and filename.endswith(".json"):
            week_tag = filename.replace("week-", "").replace(".json", "")
            file_path = os.path.join(data_dir, filename)
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    article_count = len(data.get("articles", []))
                    weekly_files.append((week_tag, article_count, file_path))
            except Exception as e:
                print(f"❌ Error reading {filename}: {e}")
    
    if not weekly_files:
        print("❌ No weekly files found")
        return
    
    print(f"\n📊 Available weekly files:")
    for week_tag, article_count, file_path in sorted(weekly_files, reverse=True):
        print(f"   {week_tag}: {article_count} articles")
        print(f"      File: {file_path}")
        print()

def upload_articles_to_notion(articles, existing_articles=None):
    """Upload multiple articles to Notion, skipping existing ones"""
    if not articles:
        print("No articles to upload")
        return
    
    if existing_articles is None:
        existing_articles = {}
    
    # Filter out articles that already exist in Notion
    new_articles = []
    skipped_count = 0
    
    for article in articles:
        article_link = article.get("link", "")
        if article_link in existing_articles:
            print(f"⏭️  Skipping existing article: {article.get('title', 'Unknown')[:50]}...")
            skipped_count += 1
        else:
            new_articles.append(article)
    
    if not new_articles:
        print(f"✅ All {len(articles)} articles already exist in Notion database")
        return
    
    success_count = 0
    total_count = len(new_articles)
    
    print(f"\n🚀 Starting upload of {total_count} new articles to Notion...")
    print(f"⏭️  Skipped {skipped_count} existing articles")
    
    for i, article in enumerate(new_articles, 1):
        print(f"\n[{i}/{total_count}] Processing: {article.get('title', 'Unknown')[:50]}...")
        
        if add_article_to_notion(article):
            success_count += 1
    
    print(f"\n📊 Upload Summary:")
    print(f"   ✅ Successfully uploaded: {success_count}")
    print(f"   ❌ Failed: {total_count - success_count}")
    print(f"   ⏭️  Skipped (already exist): {skipped_count}")
    print(f"   📈 Success rate: {(success_count/total_count)*100:.1f}%")

def main():
    print("🔗 MIT AI News -> Notion Uploader")
    print("=" * 40)
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 notion_loader.py week <week-tag>     - Upload specific week (e.g., 2025-W35)")
        print("  python3 notion_loader.py test                - Test Notion connection")
        print("  python3 notion_loader.py list                - List available weekly files")
        return
    
    command = sys.argv[1].lower()
    
    # Test connection first for most commands
    if command != "list":
        if not check_notion_connection():
            return
    
    if command == "test":
        print("✅ Notion connection test completed")
        return
    
    elif command == "week":
        if len(sys.argv) < 3:
            print("❌ Please specify week tag (e.g., 2025-W35)")
            return
        
        week_tag = sys.argv[2]
        weekly_data = load_weekly_articles(week_tag)
        
        if weekly_data:
            articles = weekly_data.get("articles", [])
            if articles:
                print(f"\n📅 Week {week_tag} Summary:")
                print(f"   Articles: {len(articles)}")
                print(f"   Date range: {weekly_data.get('start_of_week', 'Unknown')} to {weekly_data.get('end_of_week', 'Unknown')}")
                
                # Get existing articles from Notion to check for duplicates
                print("\n🔍 Checking for existing articles in Notion database...")
                existing_articles = get_existing_articles_from_notion()
                
                # Count how many are new vs existing
                new_count = 0
                existing_count = 0
                for article in articles:
                    if article.get("link", "") in existing_articles:
                        existing_count += 1
                    else:
                        new_count += 1
                
                print(f"📊 Article Status:")
                print(f"   🆕 New articles: {new_count}")
                print(f"   ⏭️  Already exist: {existing_count}")
                
                if new_count == 0:
                    print("✅ All articles from this week already exist in Notion!")
                    return
                
                confirm = input(f"\n❓ Upload {new_count} new articles to Notion? (y/N): ")
                if confirm.lower() == 'y':
                    upload_articles_to_notion(articles, existing_articles)
                else:
                    print("Upload cancelled")
            else:
                print(f"❌ No articles found in week {week_tag}")
    
    elif command == "list":
        list_available_weekly_files()
        
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    main()