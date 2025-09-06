from pathlib import Path
import os
import json
from dotenv import load_dotenv
from langchain.schema import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

from pathlib import Path
import shutil

load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
# Initialize embeddings
model_name = "sentence-transformers/all-mpnet-base-v2"  
embeddings = HuggingFaceEmbeddings(model_name=model_name)

# Create or load vector store
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

def news_embedding(data_file):
    if not data_file.exists():
        raise FileNotFoundError(f"Data file not found: {data_file}")

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Get all existing links in the vector store
    # Use metadata 'link' to detect duplicates
    existing_links = set()
    try:
        # Chroma stores metadata in _collection internally
        existing_metadatas = vector_store._collection.get()["metadatas"]
        for meta in existing_metadatas:
            if meta and meta.get("link"):  # Added None check
                existing_links.add(meta["link"])
    except Exception:
        pass  # First run, nothing exists yet

    docs_to_add = []
    for item in data.get("articles", []):
        content = f"title: {item['title']} | summary: {item['summary']} | link: {item['link']}"
        if item['link'] in existing_links:
            print(f"Already exists: {item['title']}")
        else:
            print(f"New: {item['title']}")
            docs_to_add.append(Document(
                page_content=content,
                metadata={
                    "link": item['link'],
                    "week": week_tag,
                    "title": item['title']
                }
            ))

    if docs_to_add:
        vector_store.add_documents(docs_to_add)
        print(f"Added {len(docs_to_add)} new documents to vector store.")
    else:
        print("No new documents to add.")

    print(f"Vector store saved to: {os.path.abspath('./chroma_langchain_db')}")

def get_week_tag():
    """Get current week tag"""
    from datetime import datetime
    year, week, _ = datetime.now().isocalendar()
    return f"{year}-W{week:02d}"

def load_all_articles():
    """Load all available articles from data directory"""
    # Get the project root directory
    project_root = Path(__file__).parent.parent
    data_dir = project_root / "data"
    all_articles = []
    
    print(f"Looking for data files in: {data_dir}")
    
    # Load general news file
    general_file = data_dir / "mit_ai_news.json"
    if general_file.exists():
        print(f"Loading general news from: {general_file}")
        with open(general_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle both list format and object with articles key
            if isinstance(data, list):
                articles = data
            else:
                articles = data.get("articles", [])
            
            for article in articles:
                article["week"] = "all"
                all_articles.append(article)
        print(f"Loaded {len(articles)} articles from general news")
    
    # Load weekly files
    weekly_files = list(data_dir.glob("week-*.json"))
    print(f"Found {len(weekly_files)} weekly files")
    
    for file_path in weekly_files:
        week_name = file_path.stem.replace("week-", "")
        print(f"Loading week {week_name} from: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Handle both list format and object with articles key
            if isinstance(data, list):
                articles = data
            else:
                articles = data.get("articles", [])
            
            for article in articles:
                article["week"] = week_name
                all_articles.append(article)
        print(f"Loaded {len(articles)} articles from week {week_name}")
    
    print(f"Total articles loaded: {len(all_articles)}")
    return all_articles

def initialize_vector_store():
    """Initialize vector store with all available articles"""
    try:
        all_articles = load_all_articles()
        if not all_articles:
            print("No articles found to embed")
            return
        
        # Get existing links
        existing_links = set()
        try:
            existing_metadatas = vector_store._collection.get()["metadatas"]
            for meta in existing_metadatas:
                if meta and meta.get("link"):
                    existing_links.add(meta["link"])
        except Exception:
            pass
        
        docs_to_add = []
        for article in all_articles:
            # Get summary or description, fallback to content if neither exists
            summary = article.get('summary') or article.get('description') or article.get('content', '')[:500] + "..."
            content = f"title: {article['title']} | summary: {summary} | link: {article['link']}"
            if article['link'] not in existing_links:
                docs_to_add.append(Document(
                    page_content=content,
                    metadata={
                        "link": article['link'],
                        "week": article['week'],
                        "title": article['title']
                    }
                ))
        
        if docs_to_add:
            vector_store.add_documents(docs_to_add)
            print(f"Added {len(docs_to_add)} new documents to vector store.")
        else:
            print("No new documents to add.")
            
    except Exception as e:
        print(f"Error initializing vector store: {e}")

# Only run if this script is executed directly
if __name__ == "__main__":
    # Specify which week to process
    week_tag = "2025-W36"  # Change week here
    data_file = Path(f"../data/week-{week_tag}.json")
    news_embedding(data_file)


# FIXED: Proper confidence calculation for cosine distance
def distance_to_confidence(distance):
    # Convert cosine distance to cosine similarity
    # Cosine distance: 0 = identical, 2 = completely opposite
    cosine_similarity = 1 - distance
    # Ensure confidence is between 0 and 1
    return max(0, min(1, cosine_similarity))


# Example query
query = "VaxSeer flu vaccine AI"  
docs_scores = vector_store.similarity_search_with_score(query, k=2)

threshold = 0.25 

# Filter results
filtered_results = [
    (doc, distance_to_confidence(score)) 
    for doc, score in docs_scores
    if distance_to_confidence(score) >= threshold
]

# Handle the "no results" case
if not filtered_results:
    print("No results found")
else:
    for i, (doc, confidence) in enumerate(filtered_results, start=1):
        # FIXED: More robust parsing with error handling
        try:
            parts = {}
            for item in doc.page_content.split(" | "):
                if ": " in item:
                    key, value = item.split(": ", 1)
                    parts[key] = value
        except Exception:
            parts = {"title": "Parse Error", "summary": "Parse Error", "link": "Parse Error"}
        
        print(f"\nResult {i}:")
        print("Title:", parts.get("title", "Unknown"))
        print("Summary:", parts.get("summary", "Unknown"))
        print("Link:", parts.get("link", "Unknown"))
        print("Confidence:", round(confidence, 3))