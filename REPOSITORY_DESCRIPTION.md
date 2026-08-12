# Repository Description: Ada's Living Story / Ada's Spark Memory Engine

This document provides a highly detailed, comprehensive overview of the repository "Ada's Living Story" (also referred to as "Ada's Spark Memory Engine"). This description is designed to be used as source material for other AI systems to generate summaries, diagrams, and varying levels of architectural descriptions. Note that the `email_app` directory has been intentionally excluded from this description.

## 1. High-Level Project Overview

**Purpose:** Ada's Living Story is a semantic search system designed to allow users to ask questions about Ada Rose Swenson and receive answers based on her family's CaringBridge journal entries. It acts as a digital memory engine to preserve and interact with her life story.

**Current State:** The system is fully functional end-to-end, with over 300 pre-generated Question & Answer (Q&A) pairs. It uses vector embeddings to match user queries with these pre-generated Q&A pairs, linking answers back to the original source posts, and contextually serving relevant photos alongside the text.

**Future Expansions (Planned Corpuses):**

- Ada's Spark newsletters
- Ada's Spark website content
- Community-submitted memories
- Additional family photo captions
- Media coverage and official records

---

## 2. Core Architecture & Technology Stack

The project utilizes a decoupled architecture split into data pipelines, a backend API, a vector database, and a static frontend.

**Key Technologies:**

- **Frontend:** Vue.js 3, Vanilla JS, HTML, Modern CSS (WCAG AA compliant).
- **Backend/API:** Node.js serverless functions (deployed on Vercel).
- **Vector Database:** Pinecone (primary indices: `adas-memory-qa-prod` for Q&A, `adas-memory-qa-poc` with `photo-captions` namespace for images).
- **Data Pipeline & Scraping:** Python (Selenium, BeautifulSoup, Pandas).
- **Embeddings:** Pinecone's `llama-text-embed-v2` model for both question text and image captions.
- **Hosting:** Frontend deployed to WP Engine (embedded via iframe in WordPress), API on Vercel.
- **AI/ML:** Google Vertex AI (for image captioning), Gemini app (for manual Q&A generation).

---

## 3. Component Breakdown

### 3.1 Data Pipeline: Scraping & Processing (`AG_system/scraping/`)

This module handles the extraction of raw journal entries from CaringBridge.

- `scrape.py`: Uses Selenium and BeautifulSoup with a persistent Chrome profile to navigate CaringBridge, click "View More" and "Read More" buttons, and extract posts (author, date, title, text, and photo URLs). Output is saved to `scraped_data.json`.
- `update_authors_and_text.py`: Processes the raw scraped data to fix authorship errors and text formatting issues, outputting `scraped_data_with_author_and_text_changes.json`.

### 3.2 Q&A Generation & Validation Pipeline (`AG_system/proof_of_concepts/`)

The system converts the journal posts into a searchable format by generating Q&A pairs.

- **Generation:** Currently a manual process using Google Gemini with chunked inputs (~50 questions per session). Prompts are stored in `AG_system/answer_generation_prompt.txt`.
- **Validation:** `QC_and_merge_jsons.ipynb` merges the generated Q&A JSON files and performs data quality control.
- **Enrichment:** `enrich_qa_data.py` takes the merged Q&A output and the processed scraped data to append source attribution fields (`source_title`, `source_url`, `source_date`, `source_post_id`) to each answer.

### 3.3 Vector Database Upload & Management (`AG_system/proof_of_concepts/pincecone/`)

Manages the embeddings in Pinecone for semantic search.

- `pinecone_QA_upload.py`: Uploads the enriched Q&A pairs to the `adas-memory-qa-prod` Pinecone index. Crucially, it only embeds the `question_text` to create the vector, while the answer text and all source attribution metadata are stored as a JSON string in the `answers_json` metadata field attached to the vector.
- `visualization_analysis.ipynb`: Provides quality control and visualization of the embeddings.

### 3.4 Contextual Photo Integration (`AG_system/contextual_photo_integration/`)

A sophisticated subsystem to serve contextually relevant photos alongside text answers by semantic and emotional matching.

- **Workflow:**
  1. **Takeout Preparation:** `scripts/prepare_takeout_data.py` prepares Google Photos Takeout data.
  2. **Image Processing:** `scripts/process_downloaded_images.py` resizes/formats images. `scripts/generate_thumbnails.py` creates thumbnails (WebP format). It uses MD5 hashes (original and processed) for lineage tracking.
  3. **WP Merge:** `scripts/merge_wordpress_data.py` integrates with WordPress media URLs.
  4. **AI Captioning:** `scripts/final_enrichment.py` uses vision-language models (e.g., Vertex AI) to generate rich, descriptive captions focusing on emotions and context (categorized via prompts like "MOMENT" and "CONTEXTUAL"). Handles JSON error sanitization from AI filters.
  5. **Pinecone Upload:** `scripts/upload_captions_to_pinecone.py` embeds the AI-generated captions and uploads them to the `adas-memory-qa-poc` index under the `photo-captions` namespace.
- **Matching Strategy:** Uses a hybrid scoring approach combining Semantic Similarity, Sentiment Matching, and Post-Context Matching. On the frontend/API, when an answer is fetched, its text is embedded on-the-fly to search the `photo-captions` namespace and retrieve the most relevant photos.

### 3.5 Static Website Frontend (`AG_system/static_website/`)

A responsive search interface meant to be embedded on WordPress via an iframe.

- **Core Files:** `index.html`, `styles.css`, `app.js`.
- **Features:**
  - Dynamic semantic search bar.
  - Display of answers with clickable source reference numbers that open popups detailing source title, URL, date, and post ID.
  - Integration of contextual photos alongside the text responses.
  - Cache-busting implemented via URL parameters for static assets (`?v=TIMESTAMP`).
- **Serverless API (`AG_system/static_website/api/`):**
  - `search.js`: The main Vercel serverless function endpoint. It receives queries from the frontend, queries Pinecone, parses the `answers_json` metadata, and returns formatted responses including source data.
  - `questions.js`: Provides dynamic example questions.
  - `debug_photos.js`: Debugging endpoint for photo integration.

---

## 4. Data Models & Metadata Structures

### 4.1 Enriched Q&A Payload (Uploaded to Pinecone)

Pinecone stores a vector (embedded `question_text`) and associated metadata:

```json
{
  "id": "vector_id_123",
  "values": [0.1, -0.2, ...], // Embedding of question_text
  "metadata": {
    "question_text": "What did Ada love to do?",
    "category": "hobbies",
    "answers_json": "[{\"answer_id\": \"ans_1\", \"answer_text\": \"Ada loved to paint...\", \"source_title\": \"A Day of Painting\", \"source_url\": \"https://caringbridge.org/...\", \"source_date\": \"2023-01-15\", \"source_post_id\": \"post_1\"}]"
  }
}
```

### 4.2 Photo Caption Metadata (Uploaded to Pinecone `photo-captions` namespace)

```json
{
  "id": "photo_id_456",
  "values": [0.3, 0.4, ...], // Embedding of the AI caption
  "metadata": {
    "image_url": "https://adas-spark.org/wp-content/uploads/...",
    "caption": "AI-generated description highlighting joy and resilience.",
    "original_caption": "User caption from Google Photos",
    "emotions": ["joy", "resilience"],
    "post_id": "caringbridge_post_123",
    "creation_date": "2019-03-15",
    "processing_date": "2025-06-13"
  }
}
```

### 4.3 Scraped Data Structure (`scraped_data.json`)

```json
[
  {
    "post_id": "caringbridge_id_abc",
    "author_name": "Family Member",
    "post_date": "March 15, 2019",
    "title": "Update on Ada",
    "text": "Full text of the journal entry...",
    "photos": ["https://.../photo1.jpg", "https://.../photo2.jpg"]
  }
]
```

---

## 5. End-to-End Workflows

### 5.1 Content Ingestion Workflow

1. Execute `scrape.py` to extract CaringBridge entries.
2. Clean data with `update_authors_and_text.py`.
3. Use LLM (Gemini) to generate Q&A pairs from text chunks based on `answer_generation_prompt.txt`.
4. Run `QC_and_merge_jsons.ipynb` to aggregate and validate Q&A pairs.
5. Run `enrich_qa_data.py` to map answers back to the cleaned scraped data for source URLs/Titles.
6. Use `pinecone_QA_upload.py` to embed questions and upload metadata to `adas-memory-qa-prod`.

### 5.2 Photo Integration Workflow

1. Download Google Photos Takeout.
2. Pre-process and generate thumbnails (`prepare_takeout_data.py`, `generate_thumbnails.py`).
3. Fetch corresponding WordPress URLs (`merge_wordpress_data.py`).
4. Generate emotional and semantic AI captions (`final_enrichment.py`).
5. Upload captions to Pinecone `photo-captions` namespace (`upload_captions_to_pinecone.py`).

### 5.3 User Search Flow

1. User enters a query on the Vue.js frontend embedded in the WordPress site.
2. Frontend calls `/api/search` on Vercel.
3. Serverless API embeds the user query.
4. API queries `adas-memory-qa-prod` for top matching Q&A vectors.
5. API parses the `answers_json` metadata to retrieve answer text and source links.
6. API simultaneously embeds the retrieved answer text and queries `adas-memory-qa-poc` (namespace `photo-captions`) to find matching photos.
7. Aggregated JSON (text answers + photo URLs + source attribution) is returned to the frontend.
8. Vue app renders text, source reference popups, and corresponding imagery.
