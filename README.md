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
* **Contextual Photo Integration System:** A system to enrich Ada's Living Story by linking textual Q&A with contextually relevant images from Ada's life. This system aims to provide a richer, multimedia experience.
    *   For detailed information on its design, workflow, and current status, please refer to the [Contextual Photo Integration README](./AG_system/contextual_photo_integration/README.md).
    *   This component has been integrated into the main system. For detailed information on its design, workflow, and current status, please refer to the Contextual Photo Integration README.
    * Q&A Generation & Merging: Manual Q&A generation followed by `AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb` for merging and JSON validation.
    * Q&A Data Enrichment: `enrich_qa_data.py` script takes the output from the Q&A merging step and enriches it with `source_title` and `source_url` for each answer. This information is derived from the scraped CaringBridge data and is primarily used to allow the front-end to display and link back to the original source posts.
        *   **Usage:** `python enrich_qa_data.py <path_to_qa_json_input> <path_to_scraped_data_json> <path_to_output_enriched_qa_json>`
        *   **Example:** `python enrich_qa_data.py AG_system/proof_of_concepts/EXAMPLE_generated_qa_pairs_combined_clean_20250603_214922.json AG_system/EXAMPLE_scraped_data_with_author_and_text_changes.json enriched_qa_output.json`
    * Embedding QC & Vector DB Operations (Pinecone): `AG_system/proof_of_concepts/pincecone/visualization_analysis.ipynb` for embedding quality control, and `AG_system/proof_of_concepts/pincecone/pinecone_poc.ipynb` for uploading embeddings to Pinecone.
    * **Suggestion for Future Enhancement:** To potentially optimize performance and reduce token usage, consider experimenting with sending thumbnails (instead of full-resolution images, where appropriate) to the image-to-text models used in the `AG_system/contextual_photo_integration/scripts/final_enrichment.py` script. This could be particularly relevant for generating brief descriptions or captions.

**Important Note on Deployment:** Before uploading or making significant changes to the images or related data on your WP-engine instance (especially after processing data from this system), it is strongly recommended to perform a full backup of your WP-engine environment. It's also a good practice to take another backup after the changes have been successfully implemented.

## Associated Utilities

### Custom Email Merge Tool

This repository also contains a custom mail merge tool used for tasks such as emailing 5K participants. This tool is separate from Ada's Living Story.
* For more details on its usage, see the [Email App README](./email_app/README.md).

## Architecture Overview (Ada's Living Story)

**Data Flow:**
1.  `AG_system/scraping/scrape.py` → `scraped_data.json` (raw CaringBridge data).
2.  `AG_system/scraping/update_authors_and_text.py` → corrected data files.
3.  Manual Q&A generation (currently via Gemini app).
4.  `AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb` → Merges Q&A JSON files and performs data quality control and validation, producing an intermediate QA file.
5.  `enrich_qa_data.py` → Takes the merged QA file and the scraped data file (e.g., `AG_system/EXAMPLE_scraped_data_with_author_and_text_changes.json`) to produce an enriched QA file with `source_title` and `source_url` for linking on the frontend.
6.  `AG_system/proof_of_concepts/pincecone/visualization_analysis.ipynb` → Quality control of embeddings using the enriched QA file.
7.  `AG_system/proof_of_concepts/pincecone/pinecone_poc.ipynb` → Upload embeddings from the enriched QA file to Pinecone vector database.
8.  `AG_system/static_website/` → Vue.js frontend (deployed to WP Engine and embedded via iframe) calls API endpoints (Node.js serverless functions deployed on Vercel) for user queries.
8.  `AG_system/contextual_photo_integration/` scripts → Process Google Photos Takeout data, generate AI captions, and prepare `FINAL_MASTER_DATA.csv` for enriching the Pinecone vector database with image-related context.

**Key Technologies (Ada's Living Story):**
* **Frontend:** Vue.js 3, modern CSS.
* **Static Site Hosting:** WP Engine (with iframe embedding).
