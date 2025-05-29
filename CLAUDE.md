# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

If you are an LLM do not parse or read AG_system/scraping/scraped_data.json or AG_system/scraping/scraped_data_with_author_and_text_changes.json

## Project Overview

Ada's Spark is a memory engine project that scrapes CaringBridge journal data, processes it for quality control, and provides semantic search capabilities through vector databases. The project combines web scraping, data processing, and machine learning to create a searchable knowledge base from personal journal entries.

## Environment Setup

The project uses a conda environment named `caringbridge_project` with Python 3.13:

```bash
# Activate the conda environment
conda activate caringbridge_project

# Alternative: use the local virtual environment
source adasparkenv/bin/activate
```

## Key Commands

### Web Scraping
```bash
# Run the CaringBridge scraper (requires Chrome browser)
cd AG_system/scraping
python scrape.py

# Update scraped data with corrections
python update_authors_and_text.py scraped_data.json authorship_and_text_changes.json updated_data.json
```

### Vector Database Operations
```bash
# Run the Milvus Lite proof of concept
cd AG_system/proof_of_concepts/milvus
python Milvus_Lite_local_poc.py

# Run the Pinecone proof of concept
cd AG_system/proof_of_concepts/pincecone
jupyter notebook pinecone_poc.ipynb

# Start Jupyter for interactive development
jupyter lab
```

### Data Analysis
```bash
# Open the QC and merge notebook for data quality analysis
cd AG_system/proof_of_concepts
jupyter notebook QC_and_merge_jsons.ipynb
```

### Static Website Development
```bash
# Navigate to static website
cd AG_system/static_website

# Start local development server
python -m http.server 8000
# OR
npx http-server
```

## Architecture

**Data Flow:**
1. `AG_system/scraping/scrape.py` → `scraped_data.json` (raw CaringBridge data)
2. `AG_system/scraping/update_authors_and_text.py` → corrected data files
3. `AG_system/proof_of_concepts/milvus/Milvus_Lite_local_poc.py` → vector embeddings for semantic search
4. `AG_system/proof_of_concepts/pinecone_poc.ipynb` → Pinecone vector database implementation
5. `AG_system/proof_of_concepts/QC_and_merge_jsons.ipynb` → quality control and analysis
6. `AG_system/static_website/` → web interface for semantic search

**Key Components:**
- **Web Scraping**: Selenium-based scraper for CaringBridge journals with incremental loading
- **Data Processing**: Author/text correction pipeline with JSON validation
- **Vector Search**: 
  - Local Milvus Lite database with SentenceTransformer embeddings
  - Pinecone cloud vector database for production deployment
- **Quality Control**: Comprehensive data validation and reporting system
- **Web Interface**: Modern responsive website for semantic search queries

**Core Dependencies:**
- Web scraping: `selenium`, `beautifulsoup4`
- Vector operations: `pymilvus`, `pinecone`, `sentence-transformers`, `torch`
- Data science: `pandas`, `numpy`, `scikit-learn`, `matplotlib`
- Web interface: Vue.js 3, modern CSS, Font Awesome

## File Structure Notes

- `AG_system/scraping/` - Web scraping scripts and scraped data
- `AG_system/proof_of_concepts/` - Research and POC implementations
  - `milvus/` - Local vector database implementation
  - `pincecone/` - Cloud vector database implementation
- `AG_system/static_website/` - Production web interface
- Main Python scripts handle different pipeline stages (scraping → processing → search)
- Jupyter notebooks provide interactive analysis and proof-of-concept development
- Mixed dependency management uses both conda environment and pip requirements files

## Data Formats

**Scraped Data Structure:**
- Posts with hierarchical comments/replies
- Reaction data with user lists
- Photo attachments and metadata
- Incremental scraping support via post ID tracking

**Vector Database Schema:**
- Question-answer pairs with semantic embeddings
- Source post ID tracking for provenance
- COSINE similarity search with configurable thresholds