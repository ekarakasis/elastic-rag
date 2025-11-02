#!/usr/bin/env python3
"""
Basic Document Upload Example

This example demonstrates how to upload a document to the Elastic RAG system.
"""

import sys
from pathlib import Path

import requests


def upload_document(file_path: str, base_url: str = "http://localhost:8000") -> dict:
    """
    Upload a document to the RAG system.

    Args:
        file_path: Path to the document file
        base_url: Base URL of the API (default: http://localhost:8000)

    Returns:
        dict: Response from the API
    """
    # Check if file exists
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Prepare file for upload
    with open(file_path, "rb") as f:
        files = {"file": (path.name, f, "application/octet-stream")}

        # Upload document
        print(f"Uploading {path.name}...")
        response = requests.post(f"{base_url}/documents/upload", files=files)

    # Check response
    if response.status_code == 200:
        result = response.json()
        print("✅ Success! Document uploaded.")
        print(f"   Status: {result.get('status')}")
        print(f"   Chunks created: {result.get('chunks_created')}")
        print(f"   Message: {result.get('message')}")
        return result
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
        response.raise_for_status()


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python basic_upload.py <file_path>")
        print("Example: python basic_upload.py document.pdf")
        sys.exit(1)

    file_path = sys.argv[1]

    try:
        result = upload_document(file_path)
        print("\n📊 Upload Summary:")
        print(f"   Status: {result.get('status')}")
        print(f"   Filename: {result.get('filename')}")
        print(f"   Chunks: {result.get('chunks_created', 0)}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
