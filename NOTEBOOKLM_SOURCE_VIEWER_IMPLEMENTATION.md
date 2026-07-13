# NotebookLM-Style Source Viewer Implementation

## Overview

This document describes the implementation of a professional PDF source viewer with automatic page navigation, text highlighting, and NotebookLM-style UX for the INDUS MIND AI Assistant.

## Features Implemented

### ✅ 1. PDF Serving Backend
- **Endpoint**: `/api/documents/{document_id}/pdf`
- **Location**: Already existed in `backend/routes/documents.py`
- **Storage**: PDFs stored in `data/raw` directory
- **Resolution**: Uses document_id to locate and serve PDF files

### ✅ 2. React PDF Viewer
**Component**: `frontend/src/components/pdf-viewer/pdf-viewer.tsx`

**Features**:
- Page navigation (Previous/Next buttons)
- Current page indicator (e.g., "Page 3 of 45")
- Zoom controls (50% to 300%)
- Fullscreen mode
- PDF download
- Search functionality
- Smooth animations and transitions

**Performance Optimizations**:
- Memoized PDF file object to prevent re-fetching
- Configured PDF.js with cMap and standard fonts
- Disabled unnecessary auto-fetch, stream, and range options
- Loading states for document and individual pages
- useCallback hooks for event handlers

### ✅ 3. Text Highlighting System
**Component**: `frontend/src/components/pdf-viewer/pdf-highlight-layer.tsx`

**Features**:
- Automatic text matching across PDF text layer
- Fuzzy matching using Levenshtein distance algorithm
- Handles text split across multiple spans
- Yellow translucent overlay (rgba(255, 235, 59, 0.4))
- Smooth fade-in animation
- Auto-scroll to highlighted text
- Handles whitespace and punctuation differences

**Matching Algorithm**:
1. Normalizes text (lowercase, remove punctuation, collapse whitespace)
2. Uses sliding window to match text across spans
3. Allows up to 10% character difference for fuzzy matching
4. Highlights all matching spans with yellow overlay

### ✅ 4. Source Viewer Drawer
**Component**: `frontend/src/components/assistant/source-pdf-viewer-drawer.tsx`

**Features**:
- Smooth slide-in animation from right
- Full-screen overlay with backdrop blur
- Responsive design (full width on mobile, 75-80% on desktop)
- ESC key to close
- Backdrop click to close

### ✅ 5. Citation Metadata Panel
**Displayed Information**:
- Document filename
- Page number (single page or range)
- Relevance score (retrieval score percentage)
- Confidence score (if available)
- Chunk ID
- "Source used by AI" animated badge
- Highlighted text preview (up to 200 characters)

### ✅ 6. Multi-Citation Navigation
**Features**:
- Previous/Next buttons when multiple sources exist
- Current position indicator (e.g., "2 / 5")
- Seamless navigation between citations
- PDF automatically jumps to new page
- Highlighting updates for each citation
- Copy citation button

### ✅ 7. Citation Connectivity
**Integration Points**:
- Connected via `handleSourceClick` in `assistant.tsx`
- Triggered by clicking:
  - Enterprise citation cards in AssistantMessage
  - Source references in the answer
  - Any clickable source element
- Passes source, all sources, and confidence score

### ✅ 8. Performance Optimizations

**PDF Caching**:
- Custom hook: `frontend/src/hooks/use-pdf-cache.ts`
- LRU (Least Recently Used) eviction strategy
- Maximum 5 PDFs cached
- 1 hour cache expiry
- Metadata persisted to localStorage

**React Optimizations**:
- `memo` wrapper on PDFViewer component
- `useCallback` for all event handlers
- `useMemo` for computed values
- Conditional rendering of highlight layer

**PDF.js Configuration**:
- cMap URL for better font rendering
- Packed cMaps for smaller downloads
- Standard font data URL
- Disabled unnecessary features

## File Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── assistant/
│   │   │   └── source-pdf-viewer-drawer.tsx  (Updated)
│   │   └── pdf-viewer/
│   │       ├── pdf-viewer.tsx                (New)
│   │       ├── pdf-highlight-layer.tsx       (New)
│   │       └── source-viewer-drawer.tsx      (New, not used)
│   └── hooks/
│       └── use-pdf-cache.ts                   (New)
├── package.json                               (Updated)

backend/
└── routes/
    └── documents.py                           (Already existed)
```

## User Flow

### Opening a Source

1. User asks question to AI Assistant
2. AI returns answer with citations
3. User clicks on any citation card
4. **Drawer smoothly slides in from right**
5. PDF loads with loading spinner
6. **Automatically jumps to cited page**
7. **Yellow highlight appears on extracted text**
8. **Auto-scrolls to highlighted paragraph**

### Navigating Sources

1. User clicks "Next" button
2. **New source loads (same or different PDF)**
3. **Page changes automatically**
4. **Highlighting updates to new text**
5. **Metadata panel updates**
6. User can navigate back/forth seamlessly

### Reading Context

1. **Highlighted text is visible with yellow overlay**
2. User can scroll up/down to read surrounding context
3. **Rest of PDF remains fully readable**
4. User can zoom in/out for better readability
5. User can change pages manually if needed
6. User can search within the document

## API Integration

### Request Flow
```
Frontend Citation Click
  ↓
source.metadata.document_id
  ↓
GET /api/documents/{document_id}/pdf
  ↓
Backend serves PDF from data/raw/
  ↓
Frontend renders with react-pdf
  ↓
Highlight layer finds and marks text
```

### Source Object Structure
```typescript
{
  chunk_id: string;
  text: string;              // The extracted text to highlight
  page_start: number;        // Page to jump to
  page_end?: number;         // Optional end page
  score?: number;            // Relevance score (0-1)
  metadata: {
    document_id: string;     // Used to fetch PDF
    filename: string;        // Display name
    heading?: string;
    title?: string;
  }
}
```

## Technical Implementation Details

### Text Highlighting Algorithm

The highlighting uses a sophisticated multi-span matching algorithm:

1. **Normalization**: Convert both search text and PDF text to lowercase, remove punctuation, collapse whitespace
2. **Sliding Window**: Accumulate text across multiple spans until match is found
3. **Fuzzy Matching**: Allow up to 10% character difference using Levenshtein distance
4. **Position Calculation**: Get bounding rectangles of all matching spans
5. **Overlay Creation**: Create yellow div overlays at exact positions
6. **Auto-scroll**: Scroll first matching span into center view

### Performance Considerations

**For Large Documents (>300 pages)**:
- react-pdf only renders current page (not entire document)
- Text layer only loaded for visible page
- Annotations only loaded for visible page
- Minimal memory footprint

**For Multiple Citations**:
- PDF stays loaded when navigating between pages
- No re-fetch when changing pages within same document
- Smooth transitions without flashing

**Caching Strategy**:
- LRU cache keeps 5 most recent PDFs in memory
- Blobs stored in memory (not localStorage due to size)
- Metadata persisted for cache awareness
- 1-hour expiry to ensure fresh content

## Testing Scenarios

### Test Case 1: Single Citation Click
```
Given: AI answer with source from "Pump_Manual.pdf", Page 37
When: User clicks the citation card
Then:
  ✓ Drawer opens smoothly from right
  ✓ PDF loads with "Loading PDF..." spinner
  ✓ Automatically jumps to page 37
  ✓ Yellow highlight appears on exact paragraph
  ✓ Paragraph scrolls to center of view
  ✓ Metadata shows "Pump_Manual.pdf • Page 37"
```

### Test Case 2: Multiple Citations Navigation
```
Given: AI answer with 5 sources from different PDFs
When: User clicks first citation
Then: PDF 1 opens at page 10 with highlighted text
When: User clicks "Next (2/5)"
Then: PDF 2 opens at page 25 with different highlighted text
When: User clicks "Previous (1/5)"
Then: PDF 1 returns to page 10 with original highlighting
```

### Test Case 3: Text Spanning Multiple Lines
```
Given: Retrieved text: "The maintenance procedure requires... [200 words]... every six months"
When: Text spans 5 lines in PDF
Then:
  ✓ All 5 lines are highlighted
  ✓ Yellow overlay covers complete text area
  ✓ Highlight follows line breaks correctly
  ✓ No gaps in highlighting
```

### Test Case 4: Whitespace Differences
```
Given: Retrieved text has different whitespace than PDF
  Retrieved: "The  pump   requires maintenance"
  PDF:       "The pump requires maintenance"
When: Viewer attempts to highlight
Then:
  ✓ Normalization removes extra spaces
  ✓ Text matches successfully
  ✓ Highlighting appears correctly
```

### Test Case 5: Large Document Performance
```
Given: 500-page PDF
When: Opening page 237
Then:
  ✓ Loads in < 3 seconds
  ✓ Only page 237 is rendered
  ✓ Page navigation is smooth
  ✓ No memory issues
```

## Comparison with NotebookLM

| Feature | NotebookLM | INDUS MIND | Status |
|---------|-----------|------------|--------|
| Auto-navigate to page | ✅ | ✅ | ✅ Implemented |
| Highlight exact text | ✅ | ✅ | ✅ Implemented |
| Smooth animations | ✅ | ✅ | ✅ Implemented |
| Multi-citation nav | ✅ | ✅ | ✅ Implemented |
| Metadata display | ✅ | ✅ | ✅ Implemented |
| Zoom controls | ✅ | ✅ | ✅ Implemented |
| Search in document | ✅ | ✅ | ✅ Implemented |
| Download PDF | ✅ | ✅ | ✅ Implemented |
| Fullscreen mode | ✅ | ✅ | ✅ Implemented |
| Mobile responsive | ✅ | ✅ | ✅ Implemented |

## Known Limitations

1. **Highlight Accuracy**: 
   - Depends on PDF text layer quality
   - May not work with scanned PDFs (no text layer)
   - Complex layouts might have positioning issues

2. **Browser Compatibility**:
   - Requires modern browser with ES6 support
   - Fullscreen API may not work in all browsers
   - Clipboard API requires HTTPS

3. **Performance**:
   - Very large PDFs (>1000 pages) may be slow to load
   - Many simultaneous citations may impact performance
   - Highlight calculation can be slow for very long texts

4. **Text Matching**:
   - 10% fuzzy threshold may miss very different texts
   - RTL (right-to-left) languages not tested
   - Special characters may cause matching issues

## Future Enhancements

### Potential Improvements
1. **Thumbnail Sidebar**: Show page thumbnails for quick navigation
2. **Multiple Highlight Colors**: Different colors for different citation types
3. **Annotation Tools**: Allow users to add notes and highlights
4. **Text Selection**: Copy text directly from PDF
5. **OCR Integration**: Handle scanned PDFs without text layer
6. **Print View**: Optimized printing of cited pages
7. **Share Citation**: Generate shareable links to specific citations
8. **Keyboard Navigation**: Arrow keys for page navigation
9. **Touch Gestures**: Swipe to change pages on mobile
10. **Prefetching**: Load next/previous pages in background

### Performance Improvements
1. **Web Workers**: Offload PDF parsing to separate thread
2. **Virtual Scrolling**: For very long documents
3. **Progressive Rendering**: Render visible viewport first
4. **Image Compression**: Optimize PDF rendering quality vs speed
5. **IndexedDB Caching**: Store PDFs in IndexedDB for offline access

## Deployment Checklist

### Before Deploying
- [x] Backend PDF serving endpoint working
- [x] react-pdf dependencies installed
- [x] PDF viewer component tested
- [x] Text highlighting tested
- [x] Drawer animations smooth
- [x] Metadata display correct
- [x] Navigation between sources works
- [x] Performance optimizations applied
- [ ] Test with various PDF types
- [ ] Test on different browsers
- [ ] Test on mobile devices
- [ ] Verify memory usage is acceptable
- [ ] Check accessibility compliance

### Post-Deployment Monitoring
- Monitor PDF load times
- Track highlight match success rate
- Measure user engagement with feature
- Collect feedback on UX
- Monitor error rates

## Maintenance

### Regular Tasks
- Update PDF.js version when new releases available
- Monitor cache hit rates and adjust strategy if needed
- Review error logs for PDF loading failures
- Update fuzzy matching threshold based on user feedback
- Optimize highlight positioning algorithm if issues reported

### Troubleshooting

**PDF Not Loading**:
1. Check document_id is correct
2. Verify PDF exists in data/raw
3. Check backend endpoint is accessible
4. Look for CORS issues
5. Check network tab for 404/500 errors

**Highlighting Not Working**:
1. Verify PDF has text layer (not scanned)
2. Check text normalization is working
3. Increase fuzzy matching threshold
4. Check browser console for errors
5. Verify PDF.js text layer rendered

**Performance Issues**:
1. Check PDF file size
2. Monitor memory usage
3. Verify only current page is rendered
4. Check for memory leaks
5. Review cache effectiveness

## Conclusion

The NotebookLM-style source viewer has been successfully implemented with:
- ✅ Professional PDF viewing with full controls
- ✅ Automatic page navigation to citations
- ✅ Intelligent text highlighting with fuzzy matching
- ✅ Smooth animations and transitions
- ✅ Multi-citation navigation
- ✅ Performance optimizations for large documents
- ✅ Comprehensive metadata display
- ✅ Mobile-responsive design

The implementation provides a user experience similar to NotebookLM's evidence viewer, allowing users to immediately see the source context for AI-generated answers.

**Status**: ✅ IMPLEMENTATION COMPLETE - READY FOR TESTING
