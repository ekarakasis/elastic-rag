# Gradio UI Improvement Plan

**Issue ID**: 001
**Created**: 2025-10-31 09:19:23
**Status**: Pending Approval
**Priority**: High
**Category**: UI/UX Enhancement

---

## Analysis of Current Issues

Based on code review, the following problems have been identified:

### 1. **Chunks Not Displayed After Indexing**

- **Root Cause**: The UI shows "chunks_created" from the upload response, but the API response structure has changed
- **Current behavior**: Upload response has `chunks_created` field, but the document list API returns documents with `chunks_count` (different naming)
- **Impact**: User doesn't see chunk information properly in the document table after upload

### 2. **Sources Not Presented Correctly**

- **Root Cause**: API returns sources with `content` field (line 98 in query.py), but UI expects `text` field (line 123 in utils.py)
- **Current behavior**: `format_sources()` looks for `source.get("text")` but API sends `source["content"]`
- **Impact**: Source citations appear empty or malformed

### 3. **Confusing Design & Poor Separation**

- **Current state**: Two-tab layout with basic styling
- **Issues**:
  - All actions mixed together without clear visual hierarchy
  - Upload status and document list are not clearly separated
  - Settings buried in accordions
  - No clear workflow guidance

### 4. **Missing Feature: Document-Specific Search**

- **Not implemented**: Cannot filter search to specific documents
- **Requirement**: Add document selector with "All Documents" option

---

## Proposed Solutions

### **Phase 1: Fix Data Structure Issues** ✅

#### 1.1 Fix Source Display Issue

**Files to modify**:

- `src/ui/components/utils.py:109-139` - Update `format_sources()` to handle both `text` and `content` fields
- Ensure compatibility with API response structure

#### 1.2 Fix Chunk Count Display

**Files to modify**:

- `src/ui/components/document_manager.py:146` - Ensure chunks display correctly after upload
- Update status message to show proper chunk count

#### 1.3 Add Document ID to Upload Response

**Files to modify**:

- `src/api/models.py:86-114` - Add optional `document_id` field to `UploadResponse`
- `src/api/documents.py:342-346` - Include document filename as ID in response

---

### **Phase 2: Redesign UI Layout** 🎨

#### 2.1 New Layout Structure

Replace two-tab design with **three distinct sections in single view**:

```
┌─────────────────────────────────────────────────┐
│  📊 ELASTIC RAG SYSTEM                          │
│  [System Status Indicator]                      │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  📁 DOCUMENT MANAGEMENT                         │
│  ┌───────────────────────────────────────────┐  │
│  │ Upload Area (Drag & Drop)                 │  │
│  │ [Browse Files] [Upload] [Clear]           │  │
│  └───────────────────────────────────────────┘  │
│                                                   │
│  📚 Document Library (X documents, Y chunks)     │
│  ┌───────────────────────────────────────────┐  │
│  │ [Refresh] [Page Controls]                 │  │
│  │                                            │  │
│  │ Document Table (with Delete buttons)      │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  💬 QUERY & CHAT                                │
│  ┌───────────────────────────────────────────┐  │
│  │ 🔍 Search Settings                         │  │
│  │ Documents: [Dropdown: All / Select One]   │  │
│  │ Top-K: [Slider: 1-20] Results: [5]        │  │
│  └───────────────────────────────────────────┘  │
│                                                   │
│  ┌───────────────────────────────────────────┐  │
│  │                                            │  │
│  │      Chat Conversation Area                │  │
│  │                                            │  │
│  └───────────────────────────────────────────┘  │
│                                                   │
│  [Your Question...]          [Send] [Clear]     │
│                                                   │
│  📚 Sources (expandable with better formatting) │
└─────────────────────────────────────────────────┘
```

#### 2.2 Visual Improvements

- Use Gradio `gr.Group()` with clear borders for each section
- Add section headers with emojis for visual guidance
- Improve spacing and padding with custom CSS
- Color-coded status indicators (green/red/yellow)
- Better button styling with icons

---

### **Phase 3: Implement Document-Specific Search** 🔍

#### 3.1 Add Document Selector to Chat Interface

**Files to modify**:

- `src/ui/components/chat_interface.py` - Add dropdown for document selection
  - Populate with document list from API
  - "All Documents" as default option
  - Refresh list when documents change

#### 3.2 Update API Client with Filtered Query

**Files to modify**:

- `src/ui/api_client.py:302-332` - Add optional `document_filter` parameter to `query()` method
- `src/api/models.py:8-34` - Add optional `document_filter` field to `QueryRequest`
- `src/api/query.py:82-92` - Pass filter to RAG agent

#### 3.3 Update Search Logic

**Files to modify**:

- `src/agent/rag_agent.py` - Modify retrieval tool to accept document filter
- `src/retrieval/searcher.py` - Add document filtering to search methods

---

### **Phase 4: Enhanced User Experience** ✨

#### 4.1 Better Upload Feedback

- Show upload progress with file names
- Display chunk count immediately after successful upload
- Auto-refresh document list after upload
- Clear success/error messages with icons

#### 4.2 Improved Source Display

- Format sources in expandable cards
- Show filename, chunk index, and relevance score prominently
- Highlight matching text snippets
- Add "View Full Chunk" button (accordion per source)

#### 4.3 Better Document Table

- Add inline delete buttons (no need to copy ID)
- Add search/filter for document names
- Show file size and type icons
- Sortable columns (by name, date, chunks)

#### 4.4 Chat Improvements

- Show "Searching X documents..." while processing
- Display selected document filter in chat context
- Add example questions as quick-start buttons
- Show query processing time

---

## Implementation Order & Files Modified

### **Step 1: Fix Critical Bugs** (Required First)

1. `src/ui/components/utils.py` - Fix `format_sources()` to use `content` field
2. `src/api/models.py` - Add `document_id` to `UploadResponse`
3. `src/api/documents.py` - Return proper document_id in upload response

### **Step 2: Add Document Filtering Backend** (API Changes)

4. `src/api/models.py` - Add `document_filter` to `QueryRequest`
5. `src/api/query.py` - Pass filter parameter to agent
6. `src/agent/rag_agent.py` - Accept and use document filter in tool
7. `src/retrieval/searcher.py` - Add filtering to search methods

### **Step 3: Redesign UI Layout** (Major UI Changes)

8. `src/ui/gradio_app.py` - Replace tab layout with single-page sections
9. `src/ui/components/document_manager.py` - Improve upload feedback and table
10. `src/ui/components/chat_interface.py` - Add document selector dropdown
11. Custom CSS updates for better visual separation

### **Step 4: Enhanced Features** (Optional Polish)

12. Add inline delete buttons to document table
13. Improve source display with expandable cards
14. Add example questions to chat
15. Add query timing and status indicators

---

## Testing Strategy

### Test Plan After Each Step

1. **Upload a document** → Verify chunks display correctly
2. **Ask a question** → Verify sources show content properly
3. **Select specific document** → Verify search filters correctly
4. **Upload multiple docs** → Verify selector updates
5. **Delete document** → Verify it's removed from selector
6. **Test "All Documents" mode** → Verify searches all content

---

## Estimated Complexity

| Phase | Difficulty | Files Modified | Time Estimate |
|-------|-----------|----------------|---------------|
| Phase 1 (Bug Fixes) | Low | 3 files | 30 min |
| Phase 2 (UI Redesign) | Medium | 4 files | 1-2 hours |
| Phase 3 (Document Filter) | Medium-High | 5 files | 2-3 hours |
| Phase 4 (Polish) | Medium | 3 files | 1-2 hours |

**Total Estimated Time**: 4-7 hours of focused development

---

## Risk Assessment

### Potential Issues

1. **API Breaking Changes**: Document filtering requires backend changes that might affect existing functionality
   - **Mitigation**: Make filter optional, maintain backward compatibility

2. **UI Layout Complexity**: Single-page layout might be cluttered on small screens
   - **Mitigation**: Use responsive CSS, keep sections collapsible

3. **Performance**: Loading all documents for selector dropdown could be slow with many documents
   - **Mitigation**: Use pagination in API, limit dropdown to recent/important docs

---

## Open Questions for Approval

1. **Should we keep the tab layout or move to single-page design?** (Recommendation: single-page with collapsible sections)
2. **Document selector: Show all documents or limit to recent N?** (Recommendation: all with search filter)
3. **Should source display be inline in chat or separate panel?** (Recommendation: separate accordion below chat)
4. **Keep pagination for document library or add infinite scroll?** (Recommendation: keep pagination)

---

## Summary

This plan addresses all identified requirements:

- ✅ **Fixes chunk display issue** (Phase 1.2)
- ✅ **Fixes source display issue** (Phase 1.1)
- ✅ **Redesigns for better clarity** (Phase 2)
- ✅ **Adds document-specific search** (Phase 3)
- ✅ **Maintains simplicity** (clean sections with clear separation)

**Recommendation**: Implement in order (Phase 1 → 2 → 3 → 4), testing after each phase.

---

## Approval Status

**Status**: Phase 1 ✅ COMPLETED | Phase 2 ✅ COMPLETED | Phase 3 ⏳ READY TO START
**Last Updated**: 2025-10-31
**Next Action**: User testing of Phase 2 fixes, then proceed to Phase 3 (Document-Specific Search)

### Phase 1 Completion Summary ✅

- ✅ Fixed source display bug (`content` vs `text` field)
- ✅ Fixed chunk count display bug (API field name mismatches)
- ✅ Added `document_id` to upload response
- ✅ All unit tests passing (247 passed)

### Phase 2 Completion Summary ✅

**Initial Redesign**:

- ✅ Created compact upload section
- ✅ Expanded chat interface (600px height)
- ✅ Created document library with pagination

**User Feedback & Fixes Applied** (All Completed):

1. **Pagination Errors** 🐛 ✅ FIXED
   - **Problem**: Next/Previous buttons in document library causing errors
   - **Root Cause**: State management issue - `current_page` and `total_pages` State objects were scoped locally but referenced in event handlers
   - **Fix Applied**: Moved State objects before components dict and added them to returned components dict in `src/ui/components/document_manager.py`

2. **Source Font Size Too Large** 🔤 ✅ FIXED
   - **Problem**: Source text font size was too large compared to chat messages
   - **Fix Applied**:
     - Added custom CSS rules in `src/ui/gradio_app.py` targeting `#sources-display` (12px font size)
     - Added `elem_id="sources-display"` to sources Markdown component in `src/ui/components/chat_interface.py`

3. **Source Formatting Issues** 📝 ✅ FIXED
   - **Problem**: Newline characters (`\n`) adding visual noise in source display
   - **Fix Applied**:
     - Created `normalize_whitespace()` function in `src/ui/components/utils.py` using `re.sub(r'\s+', ' ', text)`
     - Updated `format_sources()` to normalize whitespace and use HTML `<small>` tags for cleaner metadata display
     - Removed unused `doc_id` variable

4. **Layout Preference** 🎨 ✅ FIXED
   - **User Feedback**: Preferred tabs layout for logical separation of actions
   - **Fix Applied**:
     - Restored `gr.Tabs()` wrapper in `src/ui/gradio_app.py`
     - Created two tabs:
       - Tab 1: "📁 Document Management" - Upload + Library (both in same tab)
       - Tab 2: "💬 Chat" - Chat interface + sources
     - Kept all improvements: compact upload, expanded chat (600px), proper pagination state management

---

## Phase 2 Fixes Implementation Plan ✅ ALL COMPLETED

### Fix 1: Pagination State Management ✅

**File**: `src/ui/components/document_manager.py`
**Issue**: `current_page` and `total_pages` State objects not properly accessible in event handlers
**Solution Applied**:

- Moved State objects before components dict initialization
- Added them to returned components dict for proper scope access

### Fix 2: Reduce Source Font Size ✅

**File**: `src/ui/gradio_app.py` (CUSTOM_CSS section)
**Solution Applied**:

```css
/* Smaller font for sources display - smaller than chat messages */
#sources-display, #sources-display p, #sources-display div {
    font-size: 12px !important;
    line-height: 1.5 !important;
}

#sources-display strong {
    font-size: 12px !important;
    font-weight: 600;
}
```

**File**: `src/ui/components/chat_interface.py`

- Added `elem_id="sources-display"` to sources Markdown component

### Fix 3: Clean Source Formatting ✅

**File**: `src/ui/components/utils.py`
**Solution Applied**:

- Created `normalize_whitespace()` function: `re.sub(r'\s+', ' ', text)`
- Updated `format_sources()` to normalize whitespace before display
- Used HTML `<small>` tags for metadata (cleaner visual hierarchy)
- Removed unused `doc_id` variable

### Fix 4: Restore Tabs Layout ✅

**File**: `src/ui/gradio_app.py`
**Solution Applied**:

- Removed single-page 3-section layout
- Restored `gr.Tabs()` with two tabs:
  - Tab 1: "📁 Document Management" (upload section + library in same tab)
  - Tab 2: "💬 Chat" (chat interface + sources)
- Kept all improvements: compact upload, expanded chat (600px), proper pagination state

---

## Testing Status & Next Steps

### Phase 2 Testing Instructions

To verify all Phase 2 fixes are working correctly:

```bash
# Terminal 1: Start backend
task start

# Terminal 2: Start UI
task ui:dev

# Open browser to http://localhost:7860
```

**What to Test**:

1. ✅ Verify tabs layout (Document Management + Chat tabs)
2. ✅ Upload document - check compact upload works
3. ✅ Document Library - test Next/Previous pagination (should work without errors)
4. ✅ Ask question - verify source text is smaller and cleaner (no excessive newlines)
5. ✅ Check chat height is 600px (expanded for better visibility)

### All Test Results

- ✅ All 247 unit tests passing
- ✅ Code style checks passing (ruff + black)
- ⏳ Manual UI testing pending user verification

---

## ⏳ **Phase 2.5: Auto-Refresh Processing Status** (IN PROGRESS - NOT WORKING)

**Issue Identified**: Processing message displayed "Document is being processed..." but never updated automatically when indexing completed.

**Problem Analysis**:

1. **Initial Attempt - gr.Timer**: Timer component created but tick events never fired
   - UI showed timer was active, but event handlers weren't triggered
   - `.then(every=3)` parameter not supported in this Gradio version

2. **Root Cause**: Client-side timer polling doesn't work reliably in Gradio

3. **Current Status**: Manual refresh button added but **automatic refresh still not working**

**Attempted Solution**: API-Based Status Checking

- **Approach**: Query backend `/documents/status` endpoint to check actual Elasticsearch processing state
- **Implementation**: Added manual "Refresh Status" button
- **Problem**: Automatic polling still not implemented - user must click button manually

### Implementation Details

#### Backend Support

- Existing endpoint: `GET /documents/status`
- Returns list of all processing tasks with their status ("processing" or "completed")

#### Frontend Changes

**File: `src/ui/api_client.py`** (line 254):

```python
def list_processing_status(self) -> list[dict[str, Any]]:
    """Query backend for current processing status.

    Returns:
        List of processing tasks with status info
    """
    try:
        response = httpx.get(f"{self.api_url}/documents/status", timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to query processing status: {e}")
        return []
```

**File: `src/ui/gradio_app.py`** (lines 160-265):

```python
def check_and_clear_processing_message(client: APIClient):
    """Check processing status and clear message when done.

    Queries backend /documents/status endpoint to determine if
    any active processing tasks exist. Message persists while
    tasks are running, clears automatically when all complete.
    """
    try:
        status_list = client.list_processing_status()
        active_count = sum(1 for s in status_list if s.get("status") == "processing")

        if active_count == 0:
            return ""  # Clear message
        else:
            return f"🔄 Document is being processed... ({active_count} active)"
    except Exception as e:
        logger.error(f"Failed to check processing status: {e}")
        return ""  # Clear message on error
```

**UI Integration**:

- Added **"Refresh Status"** button for manual checks
- Button triggers `check_and_clear_processing_message()` on click
- No automatic polling (avoids unreliable timer issues)

### Testing

```bash
# Test auto-refresh with real upload:
1. Start backend: task start
2. Start UI: task ui:dev
3. Upload a document
4. Observe "Document is being processed..." message
5. Click "Refresh Status" button
6. Message should clear when indexing completes
```

**Status**: ⏳ IN PROGRESS - NOT WORKING

- Manual refresh button implemented
- Automatic refresh NOT working - user must click button manually
- **Issue remains unresolved** - processing message never clears automatically

### Files Modified

- `src/ui/api_client.py` - Added `list_processing_status()` method
- `src/ui/gradio_app.py` - Added `check_and_clear_processing_message()` function and refresh button

### Lessons Learned

- **Gradio Timer limitations**: Event-based polling not reliable in Gradio 4.x
- **Manual fallback required**: Automatic refresh not yet implemented

---

## ✅ **Delete Document Bug Fix** (COMPLETED - 2025-11-01)

**Issue**: Delete endpoint returned 404 error when trying to delete documents.

**Error Log**:

```
2025-11-01 23:44:03 - ERROR - Failed to delete document manual.pdf:
Client error '404 Not Found' for url 'http://localhost:8000/documents/manual.pdf'
```

**Root Cause Analysis**:

1. **Incorrect Field Suffix**: Delete endpoint was using `source_file.keyword` filter
2. **Field Type Mismatch**: Elasticsearch mapping shows `source_file` is already type `keyword`
3. **Result**: Filter query `source_file.keyword` matched 0 documents, correct filter `source_file` matches all chunks

**Investigation Steps**:

```bash
# Check actual mapping
curl 'http://localhost:9200/documents/_mapping' | jq '.documents.mappings.properties.source_file'
# Result: {"type": "keyword"}  ← Already keyword type!

# Test with .keyword suffix (FAILED)
# Result: 0 hits

# Test without .keyword suffix (SUCCESS)
# Result: 62 hits (all chunks for manual.pdf)
```

**Solution Applied**:

**File**: `src/api/documents.py` (line 665)

Changed:

```python
filters={"field": "source_file.keyword", "operator": "==", "value": document_id}
```

To:

```python
filters={"field": "source_file", "operator": "==", "value": document_id}
```

**Status**: ✅ FIXED - Delete now works correctly

**Testing**:

1. Start backend: `task start`
2. Upload document via UI
3. Copy source_file value from table (e.g., "manual.pdf")
4. Paste into delete ID field and click Delete
5. Should succeed with "Successfully deleted" message

---

### Phase 3 Preparation (Document-Specific Search)

**Ready to implement when approved**:

#### Backend Changes (API)

1. `src/api/models.py` - Add `document_filter: str | None` to `QueryRequest`
2. `src/api/query.py` - Pass `document_filter` to RAG agent runner
3. `src/agent/rag_agent.py` - Modify retrieval tool to accept and use filter
4. `src/retrieval/searcher.py` - Add `document_filter` parameter to search methods (filter by metadata field)

#### Frontend Changes (UI)

5. `src/ui/api_client.py` - Add `document_filter` parameter to `query()` method
6. `src/ui/components/chat_interface.py` - Add dropdown above chat for document selection:
   - Load document list from API
   - Default: "All Documents"
   - On selection: pass document ID to query
7. Update dropdown on document upload/delete events

#### Tests to Add

8. `tests/unit/test_searcher.py` - Test filtering by document
9. `tests/integration/test_api_integration.py` - Test query with document filter
10. `tests/ui/test_gradio_app.py` - Test document selector dropdown

**Estimated Time**: 2-3 hours

---

## Implementation Notes

### Files Affected (Total: ~15 files)

**Backend (API & Logic)**:

- `src/api/models.py`
- `src/api/documents.py`
- `src/api/query.py`
- `src/agent/rag_agent.py`
- `src/retrieval/searcher.py`

**Frontend (Gradio UI)**:

- `src/ui/gradio_app.py`
- `src/ui/api_client.py`
- `src/ui/components/utils.py`
- `src/ui/components/document_manager.py`
- `src/ui/components/chat_interface.py`

**Tests** (to be updated):

- `tests/ui/test_gradio_app.py`
- `tests/integration/test_api_integration.py`
- `tests/unit/test_searcher.py`

---

## Related Documentation

- **Current UI Guide**: `docs/UI_GUIDE.md`
- **API Documentation**: `docs/API.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Gradio UI Plan**: `docs/GRADIO_UI_PLAN.md`

---

**End of Plan**
