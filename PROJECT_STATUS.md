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
3. **Re-run pipeline with updated scraping output** - Previous scraping was incomplete (missing lots of comments and some reactions)
4. **Frontend enhancements** - Display source attribution and randomize answer order
6. **Document progress** - Create GitHub issue for source tracking implementation

### Example Enhanced Metadata Structure
```json
{
  "answers_json": "[{...answers...}]",
  "category": "character",
  "question_text": "What was Ada like as a person?",
  "source_type": "caringbridge_post",
  "post_title": "Ada's Amazing Day at the Hospital",
  "media": null,
  "media_type": null
}
```

## Near-term Expansion Plans (Planned Future Corpuses)
- Ada's Spark newsletters
- Ada's Spark website content  
- Community-submitted memories
- Family photo captions (with associated images)
- Media coverage (obituaries, magazine articles, etc. with document links)
- Official documents and records

### High Priority: Contextual Photo Integration
**Status**: Planning phase - detailed implementation plan in progress
**Overview**: Dynamic photo serving system that matches user Q&A responses with relevant photos using semantic search
- Embed the answer text (from the Q&A) on-the-fly using Pinecone
- Search against pre-generated photo captions (focusing on emotions/moments or perhaps scene descriptions)
- Serve relevant photos with AI-generated descriptions alongside text answers
**Detailed Plan**: See [README.md](/AG_system/contextual_photo_integration/README.md) for complete technical specification and implementation roadmap. Currently being developed in contextual-photo-integration branch


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

## Recent Development Updates

### 5-22-2025 Meeting (Joel & Julio)
**Key Decisions:**
- Continue using Google Doc for project planning (skip GitHub wiki for now due to time constraints)
- Implement PR workflow: Open PR → iterate → squash merge
- Focus on data pipeline completion before infrastructure changes

**Current Workflow Confirmed:**
1. Scraping → Processing → Q&A Generation → QC/Merge → Vector Upload → Frontend
2. Manual Q&A generation via Gemini app remains current approach
3. Chunking strategy: ~50 questions per session for optimal LLM performance

**Future Directions Identified:**
- README.md improvements needed
- Image caption extraction for corpus expansion
- Technical blog post for website (high-level + technical sections)
- Consider making GitHub repository public (requires PII scanning and token removal)
- UI mockups available: [AG_system_mock_UIs](https://docs.google.com/presentation/d/1XySDoq-5Mdl8WnBfTrbOWAdv6mW0N-_fZklUtjcs8T4/edit?usp=sharing)

## Current Priority ✅ MILESTONE ACHIEVED
**300+ Questions Generated!** - Successfully expanded the Q&A database from ~5 to 300+ questions, significantly improving user experience and search coverage.

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
