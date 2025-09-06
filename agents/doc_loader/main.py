import os
import json
from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from news_loader import *
from notion_loader import *
from pathlib import Path

load_dotenv()
OPEN_AI_KEY = os.environ.get("OPENAI_API_KEY")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("DATABASE_ID")

llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPEN_AI_KEY)
output_parser = StrOutputParser()
rss_url = "https://news.mit.edu/topic/mitartificial-intelligence2-rss.xml"

def main():
    """Main function to run the news processing pipeline"""
    try:
        # Get current week tag
        current_week = get_week_tag()
        print(f"🕐 Current week: {current_week}")
        print("=" * 50)
        
        # Step 1: Fetch and process news
        print("📰 Step 1: Fetching MIT AI news...")
        news_data = fetch_mit_news(max_articles=5)

        if news_data.get("news_text") and news_data.get("title"):
            print(f"✅ Processing article: {news_data['title']}")
            summary_data = summarize_news(news_data["title"], news_data["news_text"], news_data["link"], news_data["date"], save_to_file=False)
            print("✅ Summary generated successfully")
        else:
            print("⚠️  No valid news data to process")

        # Step 2: Tag articles with week information
        print("\n🏷️  Step 2: Tagging articles with week information...")
        tag_weekly_articles()
        print("✅ Weekly tagging completed")

        # Step 3: Generate weekly JSON with summaries
        print(f"\n📅 Step 3: Generating weekly summary for {current_week}...")
        save_weekly_articles_with_summary(current_week)
        print("✅ Weekly JSON with summaries completed")

        # Step 4: Upload to Notion if credentials are available
        if NOTION_TOKEN and DATABASE_ID:
            print(f"\n📤 Step 4: Uploading {current_week} articles to Notion...")
            upload_current_week_to_notion(current_week)
        else:
            print("❌ Notion credentials not found, skipping Notion integration")

        print(f"\n🎉 Pipeline completed successfully for week {current_week}!")

    except Exception as e:
        print(f"❌ Error in main function: {e}")
        import traceback
        traceback.print_exc()

def upload_current_week_to_notion(week_tag):
    """Upload current week's articles to Notion using the enhanced notion loader"""
    try:
        # Check if the weekly file exists
        data_file = f"../../data/week-{week_tag}.json"
        
        if not os.path.exists(data_file):
            print(f"❌ Weekly data file not found: {data_file}")
            print("💡 Make sure to run the news processing steps first")
            return
        
        # Load the weekly data
        with open(data_file, "r", encoding="utf-8") as f:
            weekly_data = json.load(f)
        
        articles = weekly_data.get("articles", [])
        if not articles:
            print(f"❌ No articles found in weekly file for {week_tag}")
            return
        
        print(f"📊 Found {len(articles)} articles in weekly file")
        
        # Check Notion connection first
        if not check_notion_connection():
            print("❌ Failed to connect to Notion")
            return
        
        # Get existing articles from Notion to check for duplicates
        print("🔍 Checking for existing articles in Notion database...")
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
        
        # Upload new articles to Notion
        print(f"🚀 Uploading {new_count} new articles to Notion...")
        upload_articles_to_notion(articles, existing_articles)
        
        print(f"✅ Notion upload completed for week {week_tag}")
        
    except Exception as e:
        print(f"❌ Error uploading to Notion: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "auto":
            # Run the full automated pipeline
            main()
        elif command == "news":
            # Only run news processing (steps 1-3)
            print("🕐 Running news processing only...")
            current_week = get_week_tag()
            print(f"Current week: {current_week}")
            
            # Step 1: Fetch and process news
            print("📰 Step 1: Fetching MIT AI news...")
            news_data = fetch_mit_news(max_articles=5)
            
            if news_data.get("news_text") and news_data.get("title"):
                print(f"✅ Processing article: {news_data['title']}")
                summary_data = summarize_news(news_data["title"], news_data["news_text"], news_data["link"], news_data["date"], save_to_file=False)
                print("✅ Summary generated successfully")
            else:
                print("⚠️  No valid news data to process")
            
            # Step 2: Tag articles with week information
            print("\n🏷️  Step 2: Tagging articles with week information...")
            tag_weekly_articles()
            print("✅ Weekly tagging completed")
            
            # Step 3: Generate weekly JSON with summaries
            print(f"\n📅 Step 3: Generating weekly summary for {current_week}...")
            save_weekly_articles_with_summary(current_week)
            print("✅ Weekly JSON with summaries completed")
            
        elif command == "notion":
            # Only run Notion upload (step 4)
            if not NOTION_TOKEN or not DATABASE_ID:
                print("❌ Notion credentials not found")
                sys.exit(1)
            
            current_week = get_week_tag()
            print(f"📤 Uploading {current_week} articles to Notion...")
            upload_current_week_to_notion(current_week)
            
        elif command == "week":
            # Process a specific week
            if len(sys.argv) < 3:
                print("❌ Please specify week tag (e.g., 2025-W35)")
                print("Usage:")
                print("  python3 main.py week <week-tag>")
                sys.exit(1)
            
            week_tag = sys.argv[2]
            print(f"🕐 Processing specific week: {week_tag}")
            
            # Generate weekly summary for specified week
            print(f"📅 Generating weekly summary for {week_tag}...")
            save_weekly_articles_with_summary(week_tag)
            print("✅ Weekly summary generated")
            
            # Upload to Notion if credentials available
            if NOTION_TOKEN and DATABASE_ID:
                print(f"📤 Uploading {week_tag} articles to Notion...")
                upload_current_week_to_notion(week_tag)
            else:
                print("❌ Notion credentials not found, skipping upload")
                
        else:
            print("Usage:")
            print("  python3 main.py auto          - Run full automated pipeline")
            print("  python3 main.py news          - Run news processing only (steps 1-3)")
            print("  python3 main.py notion        - Run Notion upload only (step 4)")
            print("  python3 main.py week <week>   - Process specific week (e.g., 2025-W35)")
            sys.exit(1)
    else:
        # Default: run full automated pipeline
        main()