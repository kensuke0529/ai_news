
from pathlib import Path
from datetime import datetime
import sys
import os
import json

# Add the agents directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_openai import ChatOpenAI
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from dotenv import load_dotenv


# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY not found in environment variables")
    sys.exit(1)

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

# Store for chat histories (in production, use a proper database)
store = {}

def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

# Build a single string with all articles
week_articles_text = ""
for article in data.get("articles", []):
    title = article.get("title", "")
    link = article.get("link", "")
    summary = article.get("summary", "")
    week_articles_text += f"Title: {title}\nLink: {link}\nSummary: {summary}\n\n"

# Enhanced system prompt with RAG context
system_prompt = f"""You are an AI news analyst. Answer questions about AI news articles from week {week_tag}.

You have access to a vector database of articles that you can search through to find relevant information. When answering questions:

1. Use the provided context from relevant articles when available
2. Be specific and cite sources when possible
3. If you don't have relevant information in the context, say so clearly
4. Provide accurate, helpful analysis based on the available articles

Context will be provided dynamically based on the user's question."""

# Modern LangChain setup with RAG context
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("system", "Here is the relevant context for the user's question:\n{context}"),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4o-mini", api_key=OPENAI_API_KEY)

# Create the base chain
chain = prompt | llm

# Add message history support
chain_with_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)

if __name__ == "__main__":
    session_id = "default_session"
    print("AI News Analyst Chatbot (type 'exit' to quit)")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        response = chain_with_history.invoke(
            {"input": user_input, "context": week_articles_text},
            {"configurable": {"session_id": session_id}}
        )
        print(f"AI: {response.content}")
