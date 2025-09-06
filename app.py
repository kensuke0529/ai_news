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

load_dotenv()

app = Flask(__name__)

# Initialize vector store on startup
try:
    initialize_vector_store()
    print("✅ Vector store initialized successfully")
except Exception as e:
    print(f"⚠️  Warning: Could not initialize vector store: {e}")
    print("Search functionality may not work properly")

# Load news data
def load_news_data(week_tag=None):
    """Load news data from JSON files"""
    try:
        if week_tag:
            weekly_file = f"data/week-{week_tag}.json"
            if os.path.exists(weekly_file):
                with open(weekly_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        # Try to load the most recent weekly data first
        current_week = get_week_tag()
        weekly_file = f"data/week-{current_week}.json"
        
        if os.path.exists(weekly_file):
            with open(weekly_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list format and object with articles key
                if isinstance(data, list):
                    return {"articles": data, "week": week_tag}
                else:
                    return data
        else:
            # Fallback to the general news file
            with open('data/mit_ai_news.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle both list format and object with articles key
                if isinstance(data, list):
                    return {"articles": data, "week": "all"}
                else:
                    return data
    except Exception as e:
        print(f"Error loading news data: {e}")
        return {"articles": [], "week": "Unknown"}

def get_available_weeks():
    """Get list of available weeks from data directory"""
    weeks = []
    data_dir = Path("data")
    
    # Add general news file
    if (data_dir / "mit_ai_news.json").exists():
        weeks.append({"value": "all", "label": "All Articles"})
    
    # Add weekly files
    for file_path in data_dir.glob("week-*.json"):
        week_name = file_path.stem.replace("week-", "")
        weeks.append({"value": week_name, "label": f"Week {week_name}"})
    
    # Sort by week name (newest first)
    weeks.sort(key=lambda x: x["value"], reverse=True)
    return weeks

def search_articles(query, week_filter=None, limit=10):
    """Search articles using RAG with optional week filtering"""
    try:
        # Check if vector store is available
        if not vector_store:
            return []
            
        # Perform similarity search
        docs_scores = vector_store.similarity_search_with_score(query, k=limit * 2)
        
        # Convert to confidence scores and filter
        threshold = 0.25
        filtered_results = []
        
        for doc, score in docs_scores:
            confidence = distance_to_confidence(score)
            if confidence >= threshold:
                # Parse document content
                try:
                    parts = {}
                    for item in doc.page_content.split(" | "):
                        if ": " in item:
                            key, value = item.split(": ", 1)
                            parts[key] = value
                    
                    # Apply week filter if specified
                    if week_filter and week_filter != "all":
                        # Check if this article belongs to the specified week
                        doc_week = doc.metadata.get("week", "")
                        if doc_week != week_filter:
                            continue
                    
                    filtered_results.append({
                        "title": parts.get("title", "Unknown"),
                        "summary": parts.get("summary", "Unknown"),
                        "link": parts.get("link", "Unknown"),
                        "confidence": round(confidence, 3)
                    })
                except Exception as e:
                    print(f"Error parsing document: {e}")
                    continue
        
        return filtered_results[:limit]
    except Exception as e:
        print(f"Error searching articles: {e}")
        return []

@app.route('/')
def index():
    """Main application interface"""
    news_data = load_news_data()
    available_weeks = get_available_weeks()
    return render_template('index.html', news_data=news_data, available_weeks=available_weeks)

@app.route('/api/news')
def api_news():
    """API endpoint to get news data"""
    week_tag = request.args.get('week', None)
    news_data = load_news_data(week_tag)
    return jsonify(news_data)

@app.route('/api/weeks')
def api_weeks():
    """API endpoint to get available weeks"""
    weeks = get_available_weeks()
    return jsonify(weeks)

@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for RAG search"""
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
    """API endpoint to generate weekly AI summary"""
    try:
        summary = generate_weekly_summary()
        return jsonify({"summary": summary, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for chat functionality"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        session_id = data.get('session_id', str(uuid.uuid4()))
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Get news context for RAG
        news_data = load_news_data()
        week_articles_text = ""
        for article in news_data.get("articles", []):
            title = article.get("title", "")
            link = article.get("link", "")
            summary = article.get("summary", "")
            week_articles_text += f"Title: {title}\nLink: {link}\nSummary: {summary}\n\n"
        
        # Get response from the chat chain
        response = chain_with_history.invoke(
            {"input": message, "context": week_articles_text},
            {"configurable": {"session_id": session_id}}
        )
        
        return jsonify({
            "response": response.content,
            "session_id": session_id,
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5111)
