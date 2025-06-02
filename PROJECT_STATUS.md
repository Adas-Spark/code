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
2. **Update answer generation prompt** - Modify prompt to include `source_type` and `post_title` in output JSON structure
3. **Generate more Q&A pairs** - Run through current pipeline with source-enhanced data to create ~300+ questions
4. **Frontend enhancements** - Display source attribution and randomize answer order
5. **Deploy expanded system** - Give users access to much richer question set with better UX
6. **Document progress** - Create GitHub issue for source tracking implementation

## Near-term Expansion Plans (Planned Future Corpuses)
- Ada's Spark newsletters
- Ada's Spark website content  
- Community-submitted memories
- Family photo captions
- Media coverage (obituaries, magazine articles, etc.)

## Frontend Enhancement Plans
- **Source Attribution**: Display source type and post title in search results
- **Answer Randomization**: Randomize order of multiple answers to avoid repetition
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
  "post_title": "Ada's Amazing Day at the Hospital"  // NEW FIELD - for display attribution
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