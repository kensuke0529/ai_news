import os
import json
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from agents.chat_bot.chat import chain_with_history
from agents.reporter.report_bot import generate_weekly_summary
from agents.doc_loader.news_loader import get_week_tag
from rag.embedding import vector_store, distance_to_confidence, initialize_vector_store
import uuid
from pathlib import Path
import markdown

load_dotenv()

app = Flask(__name__)

# Initialize vector store on startup
try:
    initialize_vector_store()
    print("✅ Vector store initialized successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not initialize vector store: {e}")
    print("Search functionality may not work properly")

# ----------------------
# Load news data function
# ----------------------
def load_news_data(week_tag=None):
    """Load news data from JSON files and convert Markdown summaries to HTML."""
    try:
        data = None

        # Try weekly file
        if week_tag:
            weekly_file = f"data/week-{week_tag}.json"
            if os.path.exists(weekly_file):
                with open(weekly_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

        # Fallback to most recent week or general news
        if not data:
            current_week = get_week_tag()
            weekly_file = f"data/week-{current_week}.json"
            if os.path.exists(weekly_file):
                with open(weekly_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open('data/mit_ai_news.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)

        # Ensure data is a dict
        if isinstance(data, list):
            data = {"articles": data, "week": week_tag or "all"}
        else:
            data["week"] = data.get("week") or week_tag or "all"

        # Convert Markdown to HTML and add safe defaults
        for article in data.get("articles", []):
            summary_md = article.get("summary") or ""
            try:
                article["summary_html"] = markdown.markdown(summary_md)
            except Exception:
                article["summary_html"] = summary_md

            article["title"] = article.get("title") or "No Title"
            article["link"] = article.get("link") or "#"
            article["date"] = article.get("date") or ""

        return data

    except Exception as e:
        print(f"Error loading news data: {e}")
        return {"articles": [], "week": "Unknown"}

# ----------------------
# Available weeks
# ----------------------
def get_available_weeks():
    weeks = []
    data_dir = Path("data")

    # General news
    if (data_dir / "mit_ai_news.json").exists():
        weeks.append({"value": "all", "label": "All Articles"})

    # Weekly files
    for file_path in data_dir.glob("week-*.json"):
        week_name = file_path.stem.replace("week-", "")
        weeks.append({"value": week_name, "label": f"Week {week_name}"})

    weeks.sort(key=lambda x: x["value"], reverse=True)
    return weeks

# ----------------------
# Search articles
# ----------------------
def search_articles(query, week_filter=None, limit=10):
    try:
        if not vector_store:
            return []

        docs_scores = vector_store.similarity_search_with_score(query, k=limit*2)
        threshold = 0.01
        filtered_results = []

        unique_links = set()  # Track links we've already added

        for doc, score in docs_scores:
            confidence = distance_to_confidence(score)
            if confidence < threshold:
                continue

            try:
                parts = {}
                for item in doc.page_content.split(" | "):
                    if ": " in item:
                        key, value = item.split(": ", 1)
                        parts[key] = value

                link = parts.get("link", "#")

                # Skip duplicates
                if link in unique_links:
                    continue
                unique_links.add(link)

                # Filter by week
                if week_filter and week_filter != "all":
                    doc_week = doc.metadata.get("week", "")
                    if doc_week != week_filter:
                        continue

                filtered_results.append({
                    "title": parts.get("title", "Unknown"),
                    "summary": parts.get("summary", "Unknown"),
                    "link": link,
                    "confidence": round(confidence, 3)
                })

                # Stop early if we have enough results
                if len(filtered_results) >= limit:
                    break

            except Exception as e:
                print(f"Error parsing document: {e}")
                continue

        return filtered_results

    except Exception as e:
        print(f"Error searching articles: {e}")
        return []

# ----------------------
# Routes
# ----------------------
@app.route('/')
def index():
    news_data = load_news_data()
    available_weeks = get_available_weeks()
    return render_template('index.html', news_data=news_data, available_weeks=available_weeks)

@app.route('/api/news')
def api_news():
    week_tag = request.args.get('week', None)
    news_data = load_news_data(week_tag)
    return jsonify(news_data)

@app.route('/api/weeks')
def api_weeks():
    weeks = get_available_weeks()
    return jsonify(weeks)

@app.route('/api/search', methods=['POST'])
def api_search():
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        week_filter = data.get('week_filter', 'all')
        limit = data.get('limit', 10)

        if not query:
            return jsonify({"error": "Query is required", "success": False}), 400

        results = search_articles(query, week_filter, limit)

        return jsonify({
            "results": results,
            "query": query,
            "week_filter": week_filter,
            "total_results": len(results),
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/summary', methods=['GET'])
def api_summary():
    try:
        summary = generate_weekly_summary()
        return jsonify({"summary": summary, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))

        if not message:
            return jsonify({"error": "No message provided"}), 400

        # --- Step 1: Detect if user wants article info ---
        search_keywords = ["search", "find", "show articles", "get articles", "latest news"]
        wants_search = any(word in message.lower() for word in search_keywords)

        # --- Step 2: Load latest week's news JSON for context ---
        latest_week_tag = get_week_tag()
        news_data = load_news_data(week_tag=latest_week_tag)
        context_text = ""
        if news_data.get("articles"):
            context_text = f"Here are the AI news articles for week {latest_week_tag}:\n\n"
            for article in news_data["articles"]:
                context_text += f"Title: {article['title']}\nLink: {article['link']}\nSummary: {article.get('summary', '')}\n\n"

        # --- Step 3: If user explicitly wants search, filter by query ---
        if wants_search and vector_store:
            search_results = search_articles(query=message, week_filter=latest_week_tag, limit=5)
            if search_results:
                context_text = f"Based on the latest AI news (week {latest_week_tag}), here are some relevant articles:\n\n"
                for article in search_results:
                    context_text += f"Title: {article['title']}\nLink: {article['link']}\nSummary: {article['summary']}\n\n"
            else:
                context_text = f"I looked at the latest AI news (week {latest_week_tag}) but couldn't find any articles matching your query.\n\n"

        # --- Step 4: Include a note in general response ---
        if not wants_search:
            context_text += f"Note: The AI news articles referenced here are from the latest week ({latest_week_tag}).\n\n"

        # --- Step 5: Call the LLM chain ---
        llm_input = {
            "input": message,
            "context": context_text
        }

        response = chain_with_history.invoke(
            llm_input,
            {"configurable": {"session_id": session_id}}
        )

        # Safe handling
        if hasattr(response, "content"):
            reply_text = response.content
        else:
            reply_text = str(response)

        return jsonify({
            "response": reply_text,
            "session_id": session_id,
            "success": True
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e), "success": False}), 500

# ---------------------- 
# Run server
# ----------------------
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5111)
