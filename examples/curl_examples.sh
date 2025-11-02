#!/bin/bash
# cURL Examples for Elastic RAG API
#
# This script demonstrates how to interact with the Elastic RAG API using cURL.
# Make sure the services are running before executing these commands.

BASE_URL="http://localhost:8000"

echo "==================================="
echo "Elastic RAG API - cURL Examples"
echo "==================================="

# 1. Check API Health
echo -e "\n1. Health Check (Liveness)"
curl -s "$BASE_URL/health/live" | jq '.'

echo -e "\n2. Health Check (Readiness)"
curl -s "$BASE_URL/health/ready" | jq '.'

# 3. Upload a Document
echo -e "\n3. Upload Document (replace 'test.txt' with your file)"
echo "curl -X POST \"$BASE_URL/documents/upload\" \\"
echo "     -H \"accept: application/json\" \\"
echo "     -H \"Content-Type: multipart/form-data\" \\"
echo "     -F \"file=@test.txt\""

# 4. List All Documents
echo -e "\n4. List All Documents"
curl -s "$BASE_URL/documents/" | jq '.'

# 5. Query the System
echo -e "\n5. Query Example"
curl -s -X POST "$BASE_URL/query/" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "What is machine learning?",
       "top_k": 5
     }' | jq '.'

# 6. Query with Custom Parameters
echo -e "\n6. Query with Custom Top K"
curl -s -X POST "$BASE_URL/query/" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Explain neural networks",
       "top_k": 3
     }' | jq '.'

# 7. Batch Query
echo -e "\n7. Batch Query Example"
curl -s -X POST "$BASE_URL/query/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "queries": [
         "What is deep learning?",
         "How does backpropagation work?",
         "What are convolutional neural networks?"
       ]
     }' | jq '.'

# 8. Async Upload
echo -e "\n8. Async Upload (returns task ID)"
echo "curl -X POST \"$BASE_URL/documents/upload/async\" \\"
echo "     -H \"accept: application/json\" \\"
echo "     -H \"Content-Type: multipart/form-data\" \\"
echo "     -F \"file=@large-document.pdf\""

# 9. Check Processing Status
echo -e "\n9. Check Processing Status (replace {task_id})"
echo "curl -s \"$BASE_URL/documents/status/{task_id}\" | jq '.'"

# 10. List All Processing Tasks
echo -e "\n10. List All Processing Tasks"
curl -s "$BASE_URL/documents/status" | jq '.'

# 11. Delete a Document
echo -e "\n11. Delete Document (replace {document_id})"
echo "curl -X DELETE \"$BASE_URL/documents/{document_id}\""

# 12. Batch Upload
echo -e "\n12. Batch Upload Example"
echo "curl -X POST \"$BASE_URL/documents/upload/batch\" \\"
echo "     -H \"accept: application/json\" \\"
echo "     -H \"Content-Type: multipart/form-data\" \\"
echo "     -F \"files=@doc1.pdf\" \\"
echo "     -F \"files=@doc2.txt\" \\"
echo "     -F \"files=@doc3.docx\""

echo -e "\n==================================="
echo "For more examples, see:"
echo "  - API Documentation: http://localhost:8000/docs"
echo "  - Python examples: examples/basic_*.py"
echo "==================================="
