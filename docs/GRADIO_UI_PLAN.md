# Gradio UI Implementation Plan for Elastic RAG

**Version:** 1.0.0
**Date:** October 25, 2025
**Status:** Planning
**Phase:** 10

---

## 📋 Project Understanding Summary

**Current State:**

- ✅ Production-ready RAG system (v1.0.0)
- ✅ FastAPI backend with RESTful endpoints
- ✅ 299 tests passing, 83% coverage
- ✅ Supports: PDF, DOCX, PPTX, HTML, TXT, MD, AsciiDoc
- ✅ Elasticsearch + Google ADK + LiteLLM integration
- ✅ Circuit breaker and health monitoring
- ✅ Async document processing with progress tracking
- ✅ Stateless RAG agent with source citations

**Current Workflow:**

1. Upload documents via API (`/documents/upload` or `/documents/upload/async`)
2. Query via API (`/query/`)
3. Manage documents via API (`/documents/` for listing, delete)

---

## 🎯 Proposed Solution: Gradio Web Interface

### Phase 10: Gradio UI Implementation

**Goal:** Add an intuitive web interface for non-technical users to interact with the RAG system without using curl or API tools.

**Estimated Duration:** 5-6 days

---

## 📐 UI Design & Features

### 10.1 Interface Layout

**Two-Tab Design:**

#### **Tab 1: Document Management** 📁

- **Upload Section:**
  - File upload widget (drag & drop or browse)
  - Support for multiple files at once
  - Display of supported formats: `.pdf, .docx, .pptx, .html, .htm, .txt, .md, .adoc`
  - Max file size indicator (from settings)
  - Upload progress bar
  - Success/error messages

- **Document Library:**
  - Table showing indexed documents:
    - Filename
    - Upload date
    - Chunk count
    - File type
    - Processing status indicator
    - Actions (delete button)
  - Pagination (20 documents per page)
  - Refresh button
  - Total document count
  - Search/filter functionality

#### **Tab 2: Chat Interface** 💬

- **Chat Window:**
  - Clean chat interface with message history (max 50 messages)
  - User messages (right-aligned, blue)
  - AI responses (left-aligned, gray)
  - Source citations displayed as expandable Accordion components
  - Timestamp for each message
  - Auto-scroll to latest message

- **Input Section:**
  - Text input box for questions
  - Send button
  - Clear chat button
  - Top-K slider (1-20, default: 5) for result count

- **Settings Sidebar:**
  - Top-K documents selector
  - Model status indicator
  - Elasticsearch connection status
  - Document count badge

---

## 🏗️ Technical Architecture

### 10.2 Integration Approach

**Option A: Standalone Gradio App (RECOMMENDED)**

```
┌─────────────────┐
│  Gradio UI      │ (Port 7860)
│  (Python App)   │
└────────┬────────┘
         │ HTTP Requests
         ▼
┌─────────────────┐
│  FastAPI        │ (Port 8000)
│  Backend        │
└─────────────────┘
```

**Benefits:**

- ✅ No modification to existing production code
- ✅ Easy to enable/disable UI independently
- ✅ Can run on different server if needed
- ✅ Maintains separation of concerns

**Option B: Integrated into FastAPI**

- Mount Gradio app within FastAPI
- Single port deployment
- More complex but unified deployment

**Recommendation:** Use **Option A** for better modularity and easier maintenance.

---

## 📁 Proposed File Structure

```
elastic_rag/
├── src/
│   └── ui/
│       ├── __init__.py
│       ├── gradio_app.py          # Main Gradio application
│       ├── components/
│       │   ├── __init__.py
│       │   ├── document_manager.py # Document upload/management UI
│       │   ├── chat_interface.py   # Chat interface UI
│       │   └── utils.py            # UI helper functions
│       └── api_client.py           # HTTP client for FastAPI backend
├── demos/
│   └── launch_ui.py                # Standalone UI launcher
├── docs/
│   ├── GRADIO_UI_PLAN.md          # This document
│   └── UI_GUIDE.md                # User guide for UI
├── tests/
│   └── ui/
│       ├── __init__.py
│       └── test_gradio_app.py      # UI component tests
└── pyproject.toml                  # Add gradio dependency
```

---

## 🔧 Implementation Tasks

### Task 10.1: Project Setup

**Priority:** 🔴 P0
**Duration:** 2 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.1.1** Add `gradio>=4.0.0` to `pyproject.toml` dependencies
- [ ] **10.1.2** Create `src/ui/` directory structure
- [ ] **10.1.3** Update `.gitignore` for UI-specific files
- [ ] **10.1.4** Document UI configuration in `.env.example`

**Environment Variables to Add:**

```bash
# UI Configuration
UI__HOST=0.0.0.0
UI__PORT=7860
UI__SHARE=false  # Gradio public URL sharing feature (disabled by default)
UI__API_URL=http://localhost:8000
```

---

### Task 10.2: API Client Module

**Priority:** 🔴 P0
**Duration:** 4 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.2.1** Create `src/ui/api_client.py`
- [ ] **10.2.2** Implement HTTP client using `httpx`
- [ ] **10.2.3** Add methods for:
  - Upload document (with progress tracking)
  - List documents
  - Delete document
  - Query/chat endpoint
  - Health check
- [ ] **10.2.4** Error handling and retry logic (3 retries, exponential backoff)
- [ ] **10.2.5** Add timeout configuration (30s for uploads, 60s for queries)
- [ ] **10.2.6** Implement session state management for chat history
- [ ] **10.2.7** Add connection resilience (health check on startup, graceful degradation)

**Key Features:**

```python
class ElasticRAGClient:
    def upload_document(self, file_path) -> dict
    def upload_document_async(self, file_path) -> str  # Returns task_id
    def get_upload_status(self, task_id) -> dict  # Polling interval: 1s, timeout: 5min
    def list_documents(self, page: int = 1, page_size: int = 20) -> dict
    def delete_document(self, doc_id) -> bool
    def query(self, question, top_k=5) -> dict
    def health_check() -> dict
```

**Connection Resilience:**
- Health check on UI startup
- Auto-retry failed requests (3 attempts, exponential backoff: 1s, 2s, 4s)
- Graceful error messages if API unavailable
- CORS configuration: UI origin (http://localhost:7860) must be whitelisted in FastAPI

---

### Task 10.3: Document Management UI

**Priority:** 🔴 P0
**Duration:** 6 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.3.1** Create `src/ui/components/document_manager.py`
- [ ] **10.3.2** Implement file upload component with validation
- [ ] **10.3.3** Add upload progress tracking
- [ ] **10.3.4** Create document list/table display
- [ ] **10.3.5** Add delete functionality with confirmation
- [ ] **10.3.6** Implement refresh mechanism
- [ ] **10.3.7** Add file type and size validation display
- [ ] **10.3.8** Show upload statistics (total docs, chunks, etc.)
- [ ] **10.3.9** Implement async upload status polling (1s interval, 5min timeout)
- [ ] **10.3.10** Add pagination for document list (20 per page)
- [ ] **10.3.11** Show document processing status badges (Processing/Ready)

**UI Components:**

```python
def create_upload_interface():
    # File upload widget
    # Supported formats display
    # Upload button
    # Progress indicator
    # Status messages

def create_document_list():
    # Document table
    # Refresh button
    # Delete buttons
    # Statistics panel
```

---

### Task 10.4: Chat Interface UI

**Priority:** 🔴 P0
**Duration:** 8 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.4.1** Create `src/ui/components/chat_interface.py`
- [ ] **10.4.2** Implement chat message display
- [ ] **10.4.3** Add message input and send functionality
- [ ] **10.4.4** Display source citations as expandable Accordion components
- [ ] **10.4.5** Add chat history management (Gradio State, max 50 messages)
- [ ] **10.4.6** Implement clear chat functionality (clears State)
- [ ] **10.4.7** Add typing indicator during processing
- [ ] **10.4.8** Format markdown in responses
- [ ] **10.4.9** Add Top-K slider control
- [ ] **10.4.10** Implement error handling and retry
- [ ] **10.4.11** Show warning if no documents indexed (disable query until ready)
- [ ] **10.4.12** Sanitize markdown rendering to prevent XSS

**Features:**

**Session State Management:**
- Chat history stored in Gradio State (persists during session)
- Max 50 messages (FIFO eviction)
- Clears on page refresh or manual clear
- No backend persistence (stateless)

```python
def create_chat_interface():
    # Chatbot component with history
    # Message input box
    # Send button
    # Clear button
    # Top-K slider
    # Loading indicator
    # Source display component
```

---

### Task 10.5: Main Gradio Application

**Priority:** 🔴 P0
**Duration:** 6 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.5.1** Create `src/ui/gradio_app.py`
- [ ] **10.5.2** Initialize Gradio Blocks interface
- [ ] **10.5.3** Create two-tab layout
- [ ] **10.5.4** Integrate document management tab
- [ ] **10.5.5** Integrate chat interface tab
- [ ] **10.5.6** Add global settings sidebar
- [ ] **10.5.7** Implement health status indicators
- [ ] **10.5.8** Add custom CSS styling (define color scheme, spacing)
- [ ] **10.5.9** Configure Gradio theme (gr.themes.Soft with custom colors)
- [ ] **10.5.10** Add footer with version info and system status

**Layout Structure:**

```python
with gr.Blocks(theme=gr.themes.Soft()) as app:
    with gr.Tab("📁 Document Management"):
        # Upload interface
        # Document list

    with gr.Tab("💬 Chat"):
        # Chat interface
        # Source display

    with gr.Accordion("⚙️ Settings", open=False):
        # System status
        # Configuration options
```

---

### Task 10.6: Launcher & Integration

**Priority:** 🟡 P1
**Duration:** 3 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.6.1** Create `demos/launch_ui.py` standalone launcher
- [ ] **10.6.2** Add UI startup to `Taskfile.yml`
- [ ] **10.6.3** Update Docker Compose (optional UI service)
- [ ] **10.6.4** Add health check integration
- [ ] **10.6.5** Implement graceful shutdown

**Task Commands:**

```yaml
# Taskfile.yml additions
ui:dev:
  desc: Start Gradio UI in development mode
  cmd: uv run python demos/launch_ui.py

ui:start:
  desc: Start UI with production settings
  cmd: uv run python demos/launch_ui.py --host 0.0.0.0 --share false
```

---

### Task 10.7: Testing

**Priority:** 🟡 P1
**Duration:** 4 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.7.1** Create `tests/ui/test_gradio_app.py`
- [ ] **10.7.2** Test API client methods (mocked)
- [ ] **10.7.3** Test UI component rendering
- [ ] **10.7.4** Test error handling
- [ ] **10.7.5** Integration test with running API
- [ ] **10.7.6** Test file upload validation
- [ ] **10.7.7** Test chat functionality
- [ ] **10.7.8** E2E browser testing with Playwright (upload → query → delete flow)
- [ ] **10.7.9** Test large file uploads and edge cases
- [ ] **10.7.10** Cross-browser testing (Chrome, Firefox)

**Target Coverage:** 70%+ for UI code

---

### Task 10.8: Documentation

**Priority:** 🟡 P1
**Duration:** 3 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.8.1** Create `docs/UI_GUIDE.md` - User manual
- [ ] **10.8.2** Create `docs/PHASE10_SUMMARY.md`
- [ ] **10.8.3** Update main `README.md` with UI section
- [ ] **10.8.4** Add screenshots/GIFs to documentation
- [ ] **10.8.5** Document UI configuration options
- [ ] **10.8.6** Add troubleshooting section
- [ ] **10.8.7** Create demo video/GIF showing key workflows

---

### Task 10.9: Deployment Configuration

**Priority:** 🟢 P2
**Duration:** 2 hours
**Status:** ⬜ NOT STARTED

- [ ] **10.9.1** Add UI service to `docker-compose.yml` (optional)
- [ ] **10.9.2** Update `.env.example` with UI settings
- [ ] **10.9.3** Add UI Dockerfile (if needed)
- [ ] **10.9.4** Update deployment documentation
- [ ] **10.9.5** Add reverse proxy configuration examples (nginx)

---

## 🎨 UI/UX Specifications

### Design Principles

1. **Simplicity:** Minimal learning curve for non-technical users
2. **Responsiveness:** Works on desktop and tablet
3. **Feedback:** Clear status messages and progress indicators
4. **Accessibility:** Proper labels, ARIA attributes
5. **Consistency:** Match Gradio design patterns

### Color Scheme

- **Primary:** Blue (#3b82f6) - Actions, links
- **Success:** Green (#10b981) - Successful operations
- **Warning:** Yellow (#f59e0b) - Warnings
- **Error:** Red (#ef4444) - Errors
- **Neutral:** Gray (#6b7280) - Text, borders

### Typography

- **Headings:** Bold, clear hierarchy
- **Body:** Readable font size (16px base)
- **Code:** Monospace for technical details

---

## 🔒 Security Considerations

1. **File Upload Security:**
   - Validate file extensions before upload
   - Enforce max file size limits
   - Sanitize filenames
   - Show virus scanning status (if applicable)

2. **Input Validation:**
   - Validate query length (1-500 chars)
   - Sanitize user inputs
   - Prevent injection attacks
   - Sanitize markdown rendering to prevent XSS

3. **CORS Configuration:**
   - FastAPI backend must whitelist UI origin: http://localhost:7860
   - Verify CORS middleware configuration in src/main.py

4. **Authentication (Future):**
   - Currently no auth (matching API)
   - Document plan for adding auth later
   - Use same auth as FastAPI when implemented

5. **Rate Limiting:**
   - Consider adding rate limiting on UI calls
   - Prevent abuse of upload/query endpoints

---

## 📊 Success Criteria

### Functional Requirements

- ✅ Users can upload documents via drag-and-drop
- ✅ Upload progress is clearly displayed
- ✅ Users can view list of indexed documents
- ✅ Users can delete documents
- ✅ Users can ask questions in chat interface
- ✅ Responses show source citations
- ✅ System status is visible
- ✅ Error messages are user-friendly

### Non-Functional Requirements

- ✅ UI loads in < 2 seconds
- ✅ File uploads work for all supported formats
- ✅ Chat responses appear within LLM response time
- ✅ UI is responsive (desktop + tablet)
- ✅ No browser console errors
- ✅ 70%+ test coverage for UI code

---

## 🔄 Migration & Rollout

### Phase 1: Development (Day 1-2)

- Set up UI structure
- Implement API client
- Build document management UI
- Build chat interface

### Phase 2: Integration (Day 3)

- Connect all components
- Add styling and polish
- Write tests
- Fix bugs

### Phase 3: Documentation (Day 4)

- Write user guide
- Update README
- Create deployment docs
- Add screenshots

### Phase 4: Optional (Future)

- Add authentication when API adds it
- Add user preferences (theme, settings)
- Add export chat history
- Add document preview feature

---

## 📦 Dependencies

### New Python Packages

```toml
# Add to pyproject.toml
dependencies = [
    # ... existing dependencies ...
    "gradio>=4.0.0",
    "httpx>=0.25.0",  # Already exists
]
```

### Optional Enhancements

```toml
dev = [
    # ... existing dev dependencies ...
    "playwright>=1.40.0",  # For UI testing
]
```

---

## 🚧 Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Gradio version compatibility | Medium | Pin version, test thoroughly |
| API connection failures | High | Implement retry logic, show clear errors |
| File upload failures | Medium | Validate client-side, show progress, allow retry |
| Large file handling | Medium | Show progress, implement chunked upload if needed |
| Browser compatibility | Low | Test on Chrome, Firefox, Safari |
| Concurrent users | Medium | Document limitations, implement rate limiting |

---

## 📝 Decision Log

### Architecture Decision: Option A (Standalone)

**Date:** October 25, 2025
**Decision:** Use standalone Gradio app communicating with FastAPI via HTTP
**Rationale:**

- Better separation of concerns
- No impact on production API code
- Easier to enable/disable independently
- Can scale UI separately if needed

### Docker Integration: Optional Service

**Date:** October 25, 2025
**Decision:** Add UI as optional Docker Compose service, disabled by default
**Rationale:**

- Keeps deployment flexible
- Dev users can enable if needed
- Production deployments can skip if using different UI

---

## 📅 Timeline Summary

| Task | Duration | Dependencies |
|------|----------|--------------|
| 10.1 Setup | 2h | None |
| 10.2 API Client | 6h | 10.1 |
| 10.3 Document UI | 8h | 10.2 |
| 10.4 Chat UI | 10h | 10.2 |
| 10.5 Main App | 6h | 10.3, 10.4 |
| 10.6 Launcher | 3h | 10.5 |
| 10.7 Testing | 6h | 10.6 |
| 10.8 Documentation | 4h | 10.6 |
| 10.9 Deployment | 2h | 10.8 |
| **Total** | **47 hours** | **(~6 days)** |

---

## ✅ Implementation Checklist

### Setup Phase

- [x] Create feature branch `feature/gradio-ui`
- [x] Document implementation plan
- [ ] Install Gradio dependency
- [ ] Create directory structure
- [ ] Update environment configuration

### Development Phase

- [ ] Implement API client
- [ ] Build document management UI
- [ ] Build chat interface UI
- [ ] Integrate components into main app
- [ ] Add styling and theming

### Testing Phase

- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Manual testing across browsers
- [ ] Performance testing

### Documentation Phase

- [ ] Create user guide
- [ ] Update README
- [ ] Add deployment documentation
- [ ] Create phase summary

### Deployment Phase

- [ ] Update Docker Compose
- [ ] Add Task commands
- [ ] Test deployment scenarios
- [ ] Create release notes

---

## 📞 Support & Maintenance

After implementation:

- Update `TROUBLESHOOTING.md` with UI-specific issues
- Add UI health monitoring
- Document common user questions
- Plan for future enhancements (v1.1.0)

---

## 🔗 Related Documents

- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Overall project plan
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API.md](./API.md) - API reference
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide

---

**Status:** Ready for implementation
**Next Step:** Begin Task 10.1 - Project Setup
