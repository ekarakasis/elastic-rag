# Elastic RAG - Gradio Web UI

A user-friendly web interface for the Elastic RAG system, built with [Gradio](https://gradio.app).

## 🎯 Features

### Document Management

- **📤 Upload Documents** - Drag & drop or browse to upload documents
  - Supports: PDF, DOCX, PPTX, HTML, TXT, MD, AsciiDoc
  - File validation and size limits
  - Progress tracking for uploads

- **📚 Document Library** - View and manage indexed documents
  - Paginated table view (20 per page)
  - Document metadata (filename, type, chunk count, upload date)
  - Delete documents with confirmation
  - Refresh to see latest changes

### Chat Interface

- **💬 Interactive Chat** - Ask questions about your documents
  - Natural language queries
  - AI-powered answers with source citations
  - Chat history (max 50 messages per session)
  - Clear chat functionality

- **📖 Source Citations** - View the source documents used
  - Expandable accordion with source details
  - Document excerpts with relevance scores
  - Chunk-level traceability

- **⚙️ Query Settings**
  - Adjustable Top-K slider (1-20 documents)
  - Real-time configuration

### System Status

- **🔍 Health Monitoring**
  - API connection status
  - Real-time health checks
  - Clear error messages

## 🚀 Quick Start

### Prerequisites

1. **Elastic RAG API** must be running:

   ```bash
   task start    # Start all services (Elasticsearch + API)
   ```

2. **Dependencies** installed:

   ```bash
   uv sync --all-extras
   ```

### Launch UI

**Option 1: Development Mode**

```bash
task ui:dev
```

- UI available at: `http://localhost:7860`
- Hot reload enabled
- Debug logging

**Option 2: Production Mode**

```bash
task ui:start
```

- Accessible on all network interfaces
- Optimized settings

**Option 3: Custom Configuration**

```bash
uv run python demos/launch_ui.py --help
```

#### Available Options

```bash
--api-url TEXT       URL of FastAPI backend (default: http://localhost:8000)
--host TEXT          Host to bind to (default: 0.0.0.0)
--port INTEGER       Port to bind to (default: 7860)
--share              Enable Gradio public URL sharing
--debug              Enable debug logging
```

#### Examples

```bash
# Custom API URL
python demos/launch_ui.py --api-url http://192.168.1.100:8000

# Custom port
python demos/launch_ui.py --port 8080

# Enable public sharing (creates temporary public URL)
python demos/launch_ui.py --share

# Debug mode
python demos/launch_ui.py --debug
```

## 📖 Usage Guide

### 1. Upload Documents

1. Navigate to **"📁 Document Management"** tab
2. Click **"Select File(s)"** or drag & drop files
3. Click **"Upload"** button
4. Wait for processing to complete
5. Documents appear in the library table

**Supported Formats:**

- PDF (`.pdf`)
- Microsoft Word (`.docx`)
- PowerPoint (`.pptx`)
- HTML (`.html`, `.htm`)
- Text (`.txt`)
- Markdown (`.md`)
- AsciiDoc (`.adoc`)

**File Size Limit:** 50 MB per file

### 2. Ask Questions

1. Navigate to **"💬 Chat"** tab
2. Ensure documents are uploaded (check warning message)
3. Type your question in the input box
4. Click **"Send"** or press Enter
5. View AI response with source citations
6. Expand **"📚 Sources"** accordion to see source documents

**Tips:**

- Be specific in your questions
- Adjust Top-K slider for more/fewer sources
- Clear chat to start fresh conversation

### 3. Manage Documents

**View Documents:**

- All documents shown in paginated table
- Use **"◀ Previous"** and **"Next ▶"** buttons to navigate

**Delete Documents:**

1. Copy Document ID from table
2. Paste in **"Document ID to Delete"** field
3. Click **"🗑️ Delete"** button
4. Confirm deletion

**Refresh List:**

- Click **"🔄 Refresh"** to reload document library

## 🏗️ Architecture

```
┌─────────────────┐
│  Gradio UI      │ (Port 7860)
│  (Python App)   │
└────────┬────────┘
         │ HTTP Requests (httpx)
         ▼
┌─────────────────┐
│  FastAPI        │ (Port 8000)
│  Backend        │
└─────────────────┘
```

**Key Components:**

- **`src/ui/gradio_app.py`** - Main application entry point
- **`src/ui/api_client.py`** - HTTP client for API communication
- **`src/ui/components/document_manager.py`** - Document management UI
- **`src/ui/components/chat_interface.py`** - Chat interface UI
- **`src/ui/components/utils.py`** - Utility functions
- **`demos/launch_ui.py`** - Standalone launcher script

## 🔒 Security

### File Upload Security

- ✅ File extension validation
- ✅ File size limits enforced
- ✅ Filename sanitization
- ✅ No arbitrary code execution

### Input Validation

- ✅ Query length limits (1-500 chars)
- ✅ Input sanitization
- ✅ XSS prevention in markdown rendering

### Connection Security

- ⚠️ **No authentication** (matches API)
- ⚠️ API must be accessible on network
- ℹ️ Use reverse proxy (nginx) for production
- ℹ️ Enable HTTPS in production deployments

## ⚙️ Configuration

### Environment Variables

Create or update `.env` file:

```bash
# UI Configuration
UI__HOST=0.0.0.0
UI__PORT=7860
UI__SHARE=false
UI__API_URL=http://localhost:8000

# API Configuration (for FastAPI backend)
# ... other API settings ...
```

### CORS Configuration

The FastAPI backend must allow UI origin. Check `src/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production:** Restrict `allow_origins` to specific UI domain:

```python
allow_origins=["http://your-ui-domain.com"],
```

## 🧪 Testing

### Unit Tests

```bash
uv run pytest tests/ui/ -v
```

### Integration Testing

1. Start API: `task start`
2. Launch UI: `task ui:dev`
3. Test workflows manually:
   - Upload documents
   - Query documents
   - Delete documents

### Browser Compatibility

- ✅ Chrome/Chromium
- ✅ Firefox
- ✅ Safari
- ✅ Edge

## 🐛 Troubleshooting

### UI won't start

**Error:** `Failed to connect to API`

**Solution:**

1. Ensure API is running: `curl http://localhost:8000/health/live`
2. Check API URL in launcher args or `.env`
3. Verify CORS configuration

### Upload fails

**Error:** `Unsupported file type`

**Solution:** Only use supported formats (PDF, DOCX, PPTX, HTML, TXT, MD, ADOC)

**Error:** `File too large`

**Solution:** Check file size limit (default: 50 MB)

### Query returns no results

**Solution:**

1. Verify documents are uploaded (Document Management tab)
2. Check Elasticsearch is running: `curl http://localhost:9200/_cluster/health`
3. Refresh document list

### Chat shows "No documents indexed"

**Solution:** Upload documents in Document Management tab first

### Port already in use

**Error:** `Address already in use: 7860`

**Solution:**

```bash
# Use different port
python demos/launch_ui.py --port 8080
```

## 🚀 Deployment

### Development

```bash
task ui:dev
```

### Production

**Option 1: Direct Launch**

```bash
python demos/launch_ui.py --host 0.0.0.0
```

**Option 2: Systemd Service**

Create `/etc/systemd/system/elastic-rag-ui.service`:

```ini
[Unit]
Description=Elastic RAG Gradio UI
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/elastic_rag
ExecStart=/path/to/uv run python demos/launch_ui.py --host 0.0.0.0
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable elastic-rag-ui
sudo systemctl start elastic-rag-ui
```

**Option 3: Docker (Future)**

- Docker support planned for v1.1.0
- Will integrate with existing `docker-compose.yml`

### Reverse Proxy (Nginx)

Example configuration:

```nginx
server {
    listen 80;
    server_name rag-ui.example.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📊 Performance

### Optimization Tips

1. **File Uploads**
   - Upload smaller batches (5-10 files at a time)
   - Use async upload for large files

2. **Chat Performance**
   - Adjust Top-K (lower = faster)
   - Clear chat history periodically (max 50 messages)

3. **Document Library**
   - Pagination set to 20 per page (optimal)
   - Use refresh sparingly

## 🔄 Updates & Maintenance

### Update UI

```bash
git pull
uv sync
task ui:start
```

### Check Logs

```bash
# UI logs (stdout)
python demos/launch_ui.py --debug

# API logs
task logs-app
```

## 📚 Related Documentation

- [Main README](../README.md) - Project overview
- [API Documentation](../docs/API.md) - REST API reference
- [Implementation Plan](../docs/GRADIO_UI_PLAN.md) - Technical design
- [Architecture](../docs/ARCHITECTURE.md) - System architecture

## 🤝 Contributing

See main [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - See [LICENSE](../LICENSE) for details.

---

**Built with ❤️ using [Gradio](https://gradio.app)**
