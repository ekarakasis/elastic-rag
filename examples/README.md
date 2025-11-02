# Examples Directory

This directory contains practical usage examples for the Elastic RAG system.

## Available Examples

### Basic Usage

- `basic_upload.py` - Simple document upload
- `basic_query.py` - Simple RAG query
- `batch_upload.py` - Batch document processing

### API Examples

- `api_client.py` - Python API client wrapper
- `curl_examples.sh` - cURL command examples

### Advanced Usage

- `custom_config.py` - Custom configuration examples
- `async_processing.py` - Asynchronous document processing

## Running Examples

### Prerequisites

1. Ensure services are running:

   ```bash
   task start
   ```

2. Verify health:

   ```bash
   task health
   ```

### Run an Example

```bash
# Basic upload
python examples/basic_upload.py path/to/document.pdf

# Basic query
python examples/basic_query.py "What is machine learning?"

# Batch upload
python examples/batch_upload.py path/to/documents/

# API client
python examples/api_client.py
```

## Example Structure

Each example includes:

- Clear comments explaining the code
- Error handling
- Expected output documentation
- Prerequisites and dependencies

## More Examples

See the `demos/` directory for comprehensive demonstrations of each phase:

- `demos/demo_phase3.py` - Document processing
- `demos/demo_phase4.py` - Elasticsearch integration
- `demos/demo_phase5.py` - Agent and LLM usage
- `demos/demo_phase6.py` - Circuit breaker and resilience
- `demos/demo_phase7.py` - Complete API usage

## Need Help?

- Check [API Documentation](../docs/API.md)
- See [README](../README.md) for general usage
- Read [TROUBLESHOOTING](../docs/TROUBLESHOOTING.md) for common issues
