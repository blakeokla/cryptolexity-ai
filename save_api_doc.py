api_doc = """# Protocol RAG API Documentation

## Ask a Question
Query information about blockchain protocols using natural language.

### Endpoint
POST /ask

### Request Body
{
    "text": string,      // Required: The question to ask
    "sources": boolean   // Optional: Whether to include source documents (default: false)
}

### Response

1. Success Response (without sources):
{
    "trace_id": "123e4567-e89b-12d3-a456-426614174000",
    "answer": "AAVE V3 is a lending protocol..."
}

2. Success Response (with sources):
{
    "trace_id": "123e4567-e89b-12d3-a456-426614174000",
    "answer": "AAVE V3 is a lending protocol...",
    "sources": [
        "Protocol Overview: AAVE V3 (AAVE) is a Lending protocol...",
        "Technical Details: Oracle Integration: Chainlink..."
    ]
}

3. Error Response:
{
    "detail": "Request timed out"  // or other error message
}

### Example Usage

Without sources:
curl -X POST "http://localhost:8000/ask" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "What is AAVE V3?"}'

With sources:
curl -X POST "http://localhost:8000/ask" \\
  -H "Content-Type: application/json" \\
  -d '{"text": "What is AAVE V3?", "sources": true}'

### Notes
- Timeout: 60 seconds
- Rate Limit: None
- Authentication: None
- Response time: Typically 5-15 seconds
"""

with open('api_documentation.txt', 'w') as f:
    f.write(api_doc) 