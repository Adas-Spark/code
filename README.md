# Ada's Living Story & Associated Utilities

## Overview of Ada's Living Story

Ada's Living Story is a semantic search system designed to allow users to ask questions about Ada Rose Swenson and receive answers based on her family's journal entries, currently sourced from CaringBridge. The system utilizes vector embeddings to match user queries with pre-generated Q&A pairs, aiming to provide a meaningful way to interact with Ada's memories. There are plans to incorporate additional corpora in the future, such as Ada's Spark newsletters and website content.

You can access Ada's Living Story at [adas-spark.org/adas-living-story](https://adas-spark.org/adas-living-story).

For a detailed understanding of the current project status, ongoing plans, and development roadmap for Ada's Living Story, please see the [Project Status Document](./PROJECT_STATUS.md).

## Key Components of Ada's Living Story

This project is composed of several key systems:

* **Static Frontend Search Interface:** A modern, responsive web interface for searching Ada's memories using semantic search.
    * For detailed information on the frontend, including features, setup, and deployment, please refer to the [Static Website README](./AG_system/static_website/README.md).
* **Backend System & Data Pipeline:** Handles search queries, generates vector embeddings (currently using Pinecone's `llama-text-embed-v2` model), and queries the Pinecone vector index (`adas-memory-qa-poc`). The data pipeline involves scraping, processing, Q&A generation, quality control, and vector uploading.
    * Scraping: `AG_system/scraping/scrape.py`
    * Data Processing: `AG_system/scraping/update_authors_and_text.py`
    * Q&A Generation & Merging: Manual Q&A generation followed by `AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb` for merging and JSON validation.
    * Embedding QC & Vector DB Operations (Pinecone): `AG_system/proof_of_concepts/pincecone/visualization_analysis.ipynb` for embedding quality control, and `AG_system/proof_of_concepts/pincecone/pinecone_poc.ipynb` for uploading embeddings to Pinecone.

## Associated Utilities

### Custom Email Merge Tool

This repository also contains a custom mail merge tool used for tasks such as emailing 5K participants. This tool is separate from Ada's Living Story.
* For more details on its usage, see the [Email App README](./email_app/README.md).

## Architecture Overview (Ada's Living Story)

**Data Flow:**
1.  `AG_system/scraping/scrape.py` → `scraped_data.json` (raw CaringBridge data).
2.  `AG_system/scraping/update_authors_and_text.py` → corrected data files.
3.  Manual Q&A generation (currently via Gemini app).
4.  `AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb` → Merges Q&A JSON files and performs data quality control and validation.
5.  `AG_system/proof_of_concepts/pincecone/visualization_analysis.ipynb` → Quality control of embeddings.
6.  `AG_system/proof_of_concepts/pincecone/pinecone_poc.ipynb` → Upload embeddings to Pinecone vector database.
7.  `AG_system/static_website/` → Vue.js frontend (deployed to WP Engine and embedded via iframe) calls API endpoints (Node.js serverless functions deployed on Vercel) for user queries.

**Key Technologies (Ada's Living Story):**
* **Frontend:** Vue.js 3, modern CSS.
* **Static Site Hosting:** WP Engine (with iframe embedding). [cite: adas-spark/code/code-9b892
