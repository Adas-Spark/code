# Ada's Spark Memory Engine - Project Status

## Project Overview
Ada's Spark Memory Engine is a semantic search system that allows users to ask questions about Ada Rose Swenson (who passed from leukemia at age 5) and receive answers based on her family's CaringBridge journal entries. The system uses vector embeddings to match user queries with pre-generated Q&A pairs.

## Current System State (Working End-to-End)
✅ **Fully functional** but with >300 Q&A pairs  
✅ **Frontend deployed** - Modern Vue.js interface for searching Ada's memories  
✅ **Backend working** - Pinecone vector database with semantic search  
✅ **Data pipeline** - Scraping → Processing → Q&A Generation → Vector Upload

## Current Data Pipeline
```
1. AG_system/scraping/scrape.py → scraped_data.json (CaringBridge scraping with Selenium)
2. AG_system/scraping/update_authors_and_text.py → scraped_data_with_author_and_text_changes.json (fix authorship errors)
3. Manual Q&A generation via Gemini app (chunked, ~50 questions per session). Potentially use AG_system/proof_of_concepts/enrich_qa_data.py for further processing or structuring.
4. AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb → merged Q&A validation.
5. AG_system/proof_of_concepts/pincecone/pinecone_QA_upload.py → Uploads embeddings to Pinecone vector database (index `adas-memory-qa-prod`). This script now embeds only `question_text` and stores answer details (including `source_title`, `source_url`, `source_date`, `source_post_id`) in `answers_json` metadata.
6. AG_system/static_website/ → Vue.js frontend for user queries. Displays source links and details. Uses cache busting for app.js and styles.css.
```

## Immediate Plan (Next 1-2 Weeks)
1. **Continue Q&A Generation & Enrichment**: Focus on increasing the number and quality of Q&A pairs.
2. **Integrate `enrich_qa_data.py`**: Fully define and integrate the role of `enrich_qa_data.py` into the Q&A generation and processing workflow.
3. **Re-run pipeline with updated scraping output** - Previous scraping was incomplete (missing lots of comments and some reactions).
4. **Frontend enhancements** - Consider randomizing answer order if multiple answers are returned for a single question.
5. **Document progress** - Continue updating documentation and GitHub issues.

### Example Enhanced Metadata Structure (as stored in Pinecone via `pinecone_QA_upload.py`)
The `question_text` is embedded. The following structure is stored in the `answers_json` metadata field (as a JSON string):
```json
[ // Array of answer objects
  {
    "answer_id": "unique_answer_id_1",
    "answer_text": "This is the first part of the answer...",
    "source_title": "Title of the First Source Document",
    "source_url": "https://example.com/source1",
    "source_date": "2023-01-15",
    "source_post_id": "original_post_id_1"
  },
  {
    "answer_id": "unique_answer_id_2",
    "answer_text": "This is a subsequent part of the answer from another source...",
    "source_title": "Title of the Second Source Document",
    "source_url": "https://example.com/source2",
    "source_date": "2023-01-16",
    "source_post_id": "original_post_id_2"
  }
]
```
Additional top-level metadata stored with the question embedding includes `category`, `question_text` (again, for retrieval), and potentially other fields like `source_type` (e.g., "caringbridge_post").

## Near-term Expansion Plans (Planned Future Corpuses)
- Ada's Spark newsletters
- Ada's Spark website content  
- Community-submitted memories
- Family photo captions (with associated images) - *Pinecone setup for this is `adas-memory-qa-poc` index, `photo-captions` namespace.*
- Media coverage (obituaries, magazine articles, etc. with document links)
- Official documents and records

### High Priority: Contextual Photo Integration
**Status**: The contextual photo integration system has been successfully merged and integrated. Core scripts and a detailed workflow for the photo integration pipeline are in place. The system uploads photo caption embeddings to the `adas-memory-qa-poc` Pinecone index in the `photo-captions` namespace.
**Overview**: Dynamic photo serving system that matches user Q&A responses with relevant photos using semantic search.
- Embed the answer text (from the Q&A) on-the-fly using the API's embedding model.
- Search against pre-generated photo captions in Pinecone (index `adas-memory-qa-poc`, namespace `photo-captions`).
- Serve relevant photos with AI-generated descriptions alongside text answers.
**Key Phases & Scripts**:
- Google Takeout preparation: `AG_system/contextual_photo_integration/scripts/prepare_takeout_data.py`
- Image processing & thumbnails: `AG_system/contextual_photo_integration/scripts/process_downloaded_images.py`, `AG_system/contextual_photo_integration/scripts/generate_thumbnails.py`
- WordPress integration: `AG_system/contextual_photo_integration/scripts/merge_wordpress_data.py`
- AI captioning: `AG_system/contextual_photo_integration/scripts/final_enrichment.py`
- Pinecone upload for captions: `AG_system/contextual_photo_integration/scripts/upload_captions_to_pinecone.py`
**Detailed Plan**: See [Contextual Photo Integration README](./AG_system/contextual_photo_integration/README.md) for complete technical specification and implementation roadmap.


## Technical Improvements & Quality Assurance Pipeline

### Data Quality & Verification (High Priority)
- **Post-generation QA validation/Truth verification syste** - After initial Q&A generation, loop through all Q&As and send them to another LLM along with the relevant posts (cited by the answers) to improve factual accuracy and storytelling
- **Enhanced metadata fields** - Potentially add JSON fields for:
  - Whether questions should be used as examples
  - Whether source posts have associated pictures
  - Question categorization for better organization

### User Experience Enhancements
- **Query logging system** - Log all questions users ask, especially ones that don't yield matches and user-submitted questions for continuous improvement (https://gemini.google.com/share/05b343dfb528)
- **Display improvements** - Show post titles that answers came from for better source attribution
- **Random contextual photos** - Serve photos from CaringBridge associated with the sources that answers came from (maybe)
- **URL optimization** - Set up adas-spark.org/memory-engine to redirect to adas-spark.org/adas-living-story (or keep memory-engine for dev)
- **Frontend Cache Busting**: Implemented cache busting for `index.html` assets (`app.js`, `styles.css`) using URL parameters to ensure users receive the latest versions.

### Image Processing Pipeline
- **Image caption generation** - Process CaringBridge and Google Photos using vision-language models (vertex with imagetext?)
- **Proper image orientation** - Ensure images are correctly oriented before processing
- **Optimal model configuration** - Define input prompts, model selection, context caching, structured JSON output, image resizing, and batching strategy
- **Semantic photo serving** - When fetching answers, embed the response and search previously embedded photo captions (focusing on emotions) to serve relevant photos with captions

### Specific Questions to Add to Pipeline
- **Memorial content** - "Stories that people added in the comments when she passed away"
- **Family context** - "Who is Oliver?" and other family member questions
- **Final moments** - "What were Ada's last words?"
- **Character insights** - More questions about Ada's personality, humor, and daily life

### Technical Infrastructure Improvements
- **Comprehensive logging** - Add logging to Ada's Living Story for user analytics and system monitoring
- **Repository organization** - Update README files so they properly reference each other and ensure top-level documentation accuracy
- **Long query optimization** - Use JavaScript or quick Pinecone API calls to make overly specific suggested questions more generic and user-friendly

## Community Engagement Analysis Pipeline
Based on research needs identified, these question areas should be prioritized for Q&A generation:

### Community Connection Questions
- How did the comments section serve as a source of community and connection?
- What kinds of memories did people write about in the comments?
- How did the community express support for Ada and her family?
- What forms of support (emotional, spiritual, etc.) were most evident?

### Strength and Encouragement Themes
- Did commenters mention Ada's strength or the family's strength?
- Were there comments offering encouragement during difficult updates?
- Did commenters discuss shared experiences with childhood illness?
- What connections were revealed through shared experiences?

## Recent Development Updates (as of June 23, 2025)

*   **Source Linking & Enhanced Metadata:**
    *   The frontend (`index.html`, `app.js`) now displays source reference numbers and a popup with detailed source information (title, URL, date, post ID) for each answer.
    *   The backend API (`api/search.js`) has been updated to parse and provide this new source information, which is stored in an `answers_json` field in Pinecone.
    *   The Q&A upload script (`AG_system/proof_of_concepts/pincecone/pinecone_QA_upload.py`) was modified to:
        *   Embed only the `question_text`.
        *   Store answer details, including the new source fields (`source_title`, `source_url`, `source_date`, `source_post_id`), in the `answers_json` metadata.
*   **Pinecone Q&A Index Update:**
    *   The primary Pinecone index for Q&A data has been updated to `adas-memory-qa-prod`. Scripts interacting with this index have been updated accordingly.
*   **Cache Busting for Frontend Assets:**
    *   Implemented cache busting for `styles.css` and `app.js` in `index.html` by appending a version query string (e.g., `?v=TIMESTAMP_OR_VERSION`) to force browsers to download updated versions.
*   **Addition of `enrich_qa_data.py`:**
    *   The script `enrich_qa_data.py` (from the main branch) has been added to `AG_system/proof_of_concepts/`. Its specific role in the current Q&A pipeline is being integrated/evaluated.

### 5-22-2025 Meeting (Joel & Julio)
**Key Decisions:**
- Continue using Google Doc for project planning (skip GitHub wiki for now due to time constraints)
- Implement PR workflow: Open PR → iterate → squash merge
- Focus on data pipeline completion before infrastructure changes

**Current Workflow Confirmed:**
1. Scraping → Processing → Q&A Generation (potentially using `enrich_qa_data.py`) → QC/Merge → Vector Upload (to `adas-memory-qa-prod` via updated `pinecone_QA_upload.py`) → Frontend (with source linking and cache busting)
2. Manual Q&A generation via Gemini app remains current approach
3. Chunking strategy: ~50 questions per session for optimal LLM performance

**Future Directions Identified:**
- README.md improvements needed (ongoing)
- Image caption extraction for corpus expansion
- Technical blog post for website (high-level + technical sections)
- Consider making GitHub repository public (requires PII scanning and token removal)
- UI mockups available: [AG_system_mock_UIs](https://docs.google.com/presentation/d/1XySDoq-5Mdl8WnBfTrbOWAdv6mW0N-_fZklUtjcs8T4/edit?usp=sharing)

## Current Priority ✅ MILESTONE ACHIEVED
**300+ Questions Generated!** - Successfully expanded the Q&A database from ~5 to 300+ questions, significantly improving user experience and search coverage.
**Source Linking Implemented!** - Frontend and backend now support detailed source attribution for answers.

**Next Phase Focus: Quality & User Experience** 
1. **Quality assurance pipeline** - Implement post-generation validation and truth verification
2. **Enhanced user experience** - Add query logging, source attribution display, and contextual photo serving
3. **Technical infrastructure** - Deploy logging system and repository organization improvements

**Approach Prioritization:**
1. Working system → Forward-compatible enhancements → User value delivery
2. Avoid technical debt through proactive metadata structure design
3. Scale content before building automation

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
- ✅ **Expanded from ~5 to 300+ searchable questions** 
- 🎯 Source attribution in search results  
- 🎯 Foundation for easy addition of new corpuses
- 🔄 Future: Fully automated multi-corpus pipeline

## Context for Future Development
The system is **working and deployed** but needs more content. We're adding source tracking as **future-proofing foundation** for multi-corpus expansion, then scaling up Q&A pairs using existing pipeline before building automation. Philosophy: deliver user value while making architectural choices that won't create technical debt or require expensive refactoring later.
