# Ada's Spark Memory Engine - Project Summary

## Project Overview
Ada's Spark Memory Engine is a semantic search system that allows users to ask questions about Ada Rose Swenson (who passed from leukemia at age 5) and receive answers based on her family's CaringBridge journal entries. The system uses vector embeddings to match user queries with pre-generated Q&A pairs.

## Current System State (Working End-to-End)
✅ **Fully functional** but with limited Q&A pairs (around 5 questions)
✅ **Frontend deployed** - Modern Vue.js interface for searching Ada's memories
✅ **Backend working** - Pinecone vector database with semantic search
✅ **Data pipeline** - Scraping → Processing → Q&A Generation → Vector Upload

## Current Data Pipeline
```
1. scrape.py → scraped_data.json (CaringBridge scraping with Selenium)
2. update_authors_and_text.py → scraped_data_with_author_and_text_changes.json (fix authorship errors)
3. Manual Q&A generation via Gemini app (chunked, ~50 questions per session)
4. QC_and_merge_jsons.ipynb → merged Q&A validation
5. pinecone_poc.ipynb → upload embeddings to Pinecone vector database
6. static_website/ → Vue.js frontend for user queries
```

## Immediate Plan (Next 1-2 Weeks)
1. **Add source tracking** - Create `add_source_type.py` to add `source_type: "caringbridge_post"` to existing data
2. **Update answer generation prompt** - Modify prompt to include `source_type`, `post_title`, and optional `media`/`media_type` fields in output JSON structure
3. **Generate more Q&A pairs** - Run through current pipeline with source-enhanced data to create ~300+ questions
4. **Frontend enhancements** - Display source attribution and randomize answer order
5. **Deploy expanded system** - Give users access to much richer question set with better UX
6. **Document progress** - Create GitHub issue for source tracking implementation

## Near-term Expansion Plans (Planned Future Corpuses)
- Ada's Spark newsletters
- Ada's Spark website content  
- Community-submitted memories
- **Contextual photo integration via semantic matching with AI-generated captions**
- Media coverage (obituaries, magazine articles, etc. with document links)
- Official documents and records

### Contextual Photo Serving (High Priority)
- **Dynamic photo serving**: When users receive Q&A responses, system will:
  - Embed the answer text on-the-fly using Pinecone
  - Search against pre-generated photo captions (focusing on emotions/moments)
  - Serve relevant photos with AI-generated descriptions alongside text answers
- **Implementation approach**: 
  - Use LMM (Large Multimodal Model) to process all CaringBridge photos and perhaps Google photos with her face in them (use celebration of life album?)
  - Generate emotion-rich captions (e.g., "Ada smiling during treatment," "family moment of joy")
  - Store caption embeddings in Pinecone with image ID/URL metadata
  - Real-time semantic matching between answers and photo moments
- **User experience**: Transform text-only responses into rich, multimedia memories

## Frontend Enhancement Plans
- **Source Attribution**: Display source type and post title in search results so users know what the answer is grounded in
- **Answer Randomization**: Randomize order of multiple answers to avoid repetition
- **Media Display**: Show associated images, documents, or links when available (obituary links, photos of Ada, etc.)
- **Future Filtering**: Enable users to filter by source type or topic categories

## Long-term Automation Vision (Future Work)
Transform manual pipeline into fully automated system with:
- API-driven question generation
- Question clustering and theme analysis (HDBSCAN)
- Intelligent chunking based on themes
- Automated answer generation via API calls
- Smart overlap detection for new corpuses
- Corpus-agnostic processing pipeline

## Key Technical Architecture
- **Frontend**: Vue.js 3 with modern responsive design
- **Vector Database**: Pinecone (cloud-hosted, embeddings + metadata)
- **Embedding Model**: Server-side via Pinecone API
- **Data Format**: JSON throughout pipeline
- **Deployment**: Static hosting (WP Engine planned)

## Recent Architectural Decision
**Source Tracking for Future-Proofing**: Adding `source_type` field to all data structures now to avoid expensive re-processing when adding new corpuses (newsletters, website content, etc.). This is backward-compatible and prevents technical debt while enabling source attribution in search results.

**Example Enhanced Metadata**:
```json
{
  "answers_json": "[{...answers...}]",
  "category": "character",
  "question_text": "What was Ada like as a person?",
  "source_type": "caringbridge_post",  // NEW FIELD - prevents future migration pain
  "post_title": "Ada's Amazing Day at the Hospital",  // NEW FIELD - for display attribution
  "media": null,                       // NEW FIELD - future-proof for images/documents
  "media_type": null                   // NEW FIELD - "image" | "document" | "video" etc.
}
```

## Current Priority
**User Value + Future-Proofing** - Get more Q&A pairs to users immediately while ensuring architectural decisions don't create technical debt. We're adding source tracking now (simple implementation) specifically to avoid expensive data migration later when adding new corpuses. The approach prioritizes: working system → forward-compatible enhancements → user value delivery.

## Key Files & Locations
- **Main repo**: GitHub (Adas-Spark/code)
- **Scraping**: `AG_system/scraping/scrape.py`
- **Data processing**: `AG_system/scraping/update_authors_and_text.py`
- **Q&A generation**: Manual via Gemini app with prompts in Google Doc
- **Vector DB**: `AG_system/proof_of_concepts/pinecone_poc.ipynb`
- **Frontend**: `AG_system/static_website/`
- **Documentation**: Google Doc (detailed project plan) + GitHub README

## Success Metrics
- ✅ Working end-to-end search system
- 🎯 Expand from ~5 to ~300+ searchable questions
- 🎯 Source attribution in search results
- 🎯 Foundation for easy addition of new corpuses
- 🔄 Future: Fully automated multi-corpus pipeline

## Context for Future Conversations
The system is **working and deployed** but needs more content. We're adding source tracking as **future-proofing foundation** for multi-corpus expansion, then scaling up Q&A pairs using existing pipeline before building automation. Philosophy: deliver user value while making architectural choices that won't create technical debt or require expensive refactoring later.
