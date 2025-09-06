#!/usr/bin/env python3
"""
Script to initialize the vector store with all available articles.
Run this script to set up the RAG search functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rag.embedding import initialize_vector_store

def main():
    print("🚀 Initializing AI News Vector Store...")
    print("=" * 50)
    
    try:
        initialize_vector_store()
        print("✅ Vector store initialization completed successfully!")
        print("\nYou can now run the Flask app with: python app.py")
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure you have the required dependencies installed:")
        print("   pip install -r requirements.txt")
        print("2. Check that your data files exist in the data/ directory")
        print("3. Ensure you have an OpenAI API key in your .env file")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

