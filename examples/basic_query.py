#!/usr/bin/env python3
"""
Basic Query Example

This example demonstrates how to query the Elastic RAG system.
"""

import sys

import requests


def query_rag(query: str, base_url: str = "http://localhost:8000", top_k: int = 10) -> dict:
    """
    Query the RAG system.

    Args:
        query: The question to ask
        base_url: Base URL of the API (default: http://localhost:8000)
        top_k: Number of documents to retrieve (default: 5)

    Returns:
        dict: Response from the API including answer and sources
    """
    print(f"🔍 Querying: {query}")

    # Prepare request
    data = {"query": query, "top_k": top_k}

    # Send query
    response = requests.post(f"{base_url}/query/", json=data)

    # Check response
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Query successful!")
        return result
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(f"   {response.text}")
        response.raise_for_status()


def print_result(result: dict):
    """Pretty print the query result."""
    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(result.get("answer", "No answer provided"))

    sources = result.get("sources", [])
    if sources:
        print("\n" + "=" * 60)
        print(f"SOURCES ({len(sources)} documents):")
        print("=" * 60)
        for i, source in enumerate(sources, 1):
            print(f"\n{i}. {source.get('filename', 'Unknown')}")
            print(f"   Score: {source.get('score', 0):.4f}")
            content = source.get("content", "")
            if content:
                print(f"   Excerpt: {content[:200]}...")
    else:
        print("\nℹ️  No sources available (sources feature may not be fully implemented)")

    metadata = result.get("metadata", {})
    print("\n" + "=" * 60)
    print("METADATA:")
    print("=" * 60)
    print(f"Original query: {result.get('query', 'N/A')}")
    print(f"Top K: {metadata.get('top_k', 'N/A')}")


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print('Usage: python basic_query.py "<your question>"')
        print('Example: python basic_query.py "What is machine learning?"')
        sys.exit(1)

    query = " ".join(sys.argv[1:])

    try:
        result = query_rag(query)
        print_result(result)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
