### **Project Overview**

The goal of this project is to take a specific album of approximately 1,000 images from your Google Photos account and transform them into a rich, searchable dataset that seamlessly integrates with your Ada's Spark Memory Engine. Currently, these photos exist as static files in Google Photos - valuable visual memories that tell Ada's story but remain disconnected from your semantic search system. Through this process, each image will be downloaded at maximum quality, processed locally with complete lineage tracking, optimized for web delivery, hosted permanently on your WordPress site, and enriched with AI-generated captions that capture the emotional context and narrative significance of each moment. The end result is a contextual photo system that can automatically serve relevant images alongside text-based Q&A responses, transforming your memory engine from a text-only experience into a rich multimedia journey through Ada's story. When users ask questions about Ada's experiences, personality, or journey, they'll not only receive thoughtful written answers but also see photos that emotionally resonate with and visually illustrate those memories.

This process involves four main phases:

1. **Data Extraction:** Downloading your photos and their metadata using Google Takeout. Google Takeout allows you to export your Google Photos library, including original image files and accompanying JSON metadata files for each image.
2. **Download & Processing:** Processing the downloaded original images from Google Takeout into optimized WebP files with complete lineage tracking throughout the transformation pipeline.
3. **Hosting & URL Generation:** Uploading the processed WebP files to your WP Engine WordPress site to get a permanent, high-performance hosting URL for each image.  
4. **Enrichment & Consolidation:** Merging all the data (extracted from Takeout JSONs and WordPress URLs) and then using Google's Vertex AI (Gemini) to generate a high-quality, descriptive caption for each image.
5. **Vector Database Integration Strategy:** The generated captions will be embedded and stored in Pinecone alongside your existing Q&A pairs
6. **Q&A integration experimentation:** Multiple approaches need testing to determine optimal photo-to-answer matching

The final deliverable will be a single master CSV file containing all this information, ready to be used to populate your Pinecone vector database. This CSV will be built from the information extracted from the Google Takeout JSON files and subsequent processing steps.

### **Prerequisites**

Before you begin, make sure you have the following:

* **Accounts:**  
  * A Google Cloud account with a project created.  
  * Billing enabled for the project (required for API usage, though you will likely stay within free tiers).  
  * APIs Enabled: **Vertex AI API**. (Google Photos Library API is no longer required for data extraction).
  * A WordPress administrator account on your WP Engine site.  
* **Software:**  
  * Python 3 installed on your local computer.  
  * A code editor (like Visual Studio Code).  
* **Credentials:**  
  * Application Default Credentials set up for Vertex AI (this is often handled automatically when you install the Google Cloud CLI and run gcloud auth application-default login).
  * Access to your Google Account to perform a Google Takeout.

### ---

**Phase 1: Data Extraction with Google Takeout**

The goal of this phase is to download all your photos and their corresponding metadata from Google Photos using Google Takeout.

#### **Step 1.1: Perform a Google Takeout**

1.  Go to [Google Takeout](https://takeout.google.com/).
2.  Deselect all products, then select **Google Photos**.
3.  Choose the option to "Select all photo albums" or select specific albums you wish to export.
4.  Configure the export settings:
    *   **Delivery method:** "Send download link via email" is common.
    *   **Frequency:** "Export once."
    *   **File type & size:** Choose `.zip` or `.tgz`. Select a larger archive size (e.g., 50GB) if you have many photos to minimize the number of downloaded files.
5.  Click "Create export." This process can take some time, from hours to days, depending on the size of your library. Google will email you when your export is ready.
6.  Download the archive files and extract them to a dedicated directory on your local computer. You will find your image files (e.g., .jpg, .png, .heic) alongside JSON files that contain metadata for each image. Each image typically has its own identically named JSON file (e.g., `image_name.jpg` and `image_name.jpg.json`).

*   **Output:** A local directory containing your photo files and their associated JSON metadata files. This directory will be the starting point for the next phases. The `google_data.csv` file mentioned in previous versions of this documentation is no longer the initial input; instead, scripts will process the data directly from your Takeout export directory.

### ---

### **Phase 2: Image Processing Pipeline**

This phase takes the original images downloaded via Google Takeout, stores them with lineage tracking, and processes them into optimized WebP files ready for WordPress hosting. The JSON metadata files from Takeout will be used in this phase to guide processing and extract relevant information.

#### **Step 2.1: Prepare Your Processing Environment**

Install the required libraries:
```bash
pip install Pillow requests pandas
```

Create your directory structure:
```
project_root/
├── original_downloads/        # Original files (can delete after project)
│   ├── 2019-03-15/           # Organized by date
│   └── 2022-05-05/
├── processed_webp/           # Your WebP files
├── lineage/                  # Complete tracking
│   ├── download_lineage.json
│   ├── processing_lineage.json
│   └── master_lineage.json
└── scripts/                  # Your processing scripts
```

#### **Step 2.2: Organize Takeout Files and Extract Metadata**

Since Google Takeout provides the original images directly, the primary task is to organize these files and parse the accompanying JSON metadata.

A script (e.g., `prepare_takeout_data.py`) will be needed to:
1.  Read the directory of extracted Takeout files.
2.  Identify image files and their corresponding JSON metadata files.
3.  Parse relevant information from the JSON files (e.g., original filename, user caption (often `description` in the JSON), creation date (`photoTakenTime` -> `timestamp`), geolocation if available, etc.).
4.  Copy or move image files to the `original_downloads/` directory, perhaps organized by date as originally planned, using the metadata from JSONs.
5.  Store the extracted metadata in a structured way, possibly creating an initial version of the `lineage/download_lineage.json` or a new CSV file that will serve a similar purpose to the old `google_data.csv` but derived from Takeout.

This script replaces the need for `download_originals.py` which previously fetched images using the API.

#### **Step 2.3: Process Downloaded Images**

Create the processing script that transforms images from `original_downloads/` into optimized WebP files:

**process_downloaded_images.py** (This script will likely remain similar, but its input data source changes from API-downloaded files to Takeout-sourced files, using the metadata extracted in Step 2.2).

* **Output:**

- `original_downloads/` folder containing original images from Takeout, organized by date.
- `processed_webp/` folder containing optimized WebP files ready for WordPress upload.
- `lineage/takeout_metadata_log.json` (or similar) - Log of metadata extracted from Takeout JSONs.
- `lineage/processing_lineage.json` - Complete transformation history for each image.
- `processing_lineage.csv` - Tabular format for Phase 3 integration, now based on Takeout data.

#### **Step 2.4: Lineage Benefits**

This Takeout-first approach provides complete traceability:

- **Source tracking:** Original filename from Takeout, and any identifiers available in the JSON metadata.
- **File integrity:** SHA256 checksums can still be used for verification post-Takeout and during processing.
- **Transformation log:** Every resize, rotation, format change with timestamps.
- **File evolution:** Original Takeout filename → final WordPress filename.
- **Quality metrics:** File sizes before/after each step.
- **Error handling:** Failed processing tracked with reasons.
- **Audit trail:** Complete history for compliance and debugging.
- **Local backup:** Original Takeout files are preserved.

### ---

### **Phase 3: WordPress Hosting & URL Generation**

Now upload your processed images to WordPress and capture their permanent URLs.

#### **Step 3.1: Organize Your WordPress Media Library**

Before uploading, log in to WordPress and install a **Media Library Folders plugin** (like Filebird). Create a new folder named "Ada's Story Project" to keep your images organized and separate from other media.

#### **Step 3.2: Bulk Upload Processed Images**

Navigate to your WordPress Media Library folder and bulk upload all `.webp` files from your local `processed_webp/` folder created in Phase 2.

**Benefits of bulk upload via WordPress interface:**
- Faster than API uploads for 1,000+ images
- Better error handling and progress visibility
- Native WordPress optimization and organization

#### **Step 3.3: Export WordPress URLs**

Use an "Export Media Library" plugin to export metadata for your uploads. Filter the export to show only images uploaded today to isolate your new files.

#### **Step 3.4: Merge with Processing Lineage**

Create a simple script to merge WordPress URLs with your Phase 2 lineage data:

**merge_wordpress_data.py**

Output:

- All images hosted on WordPress with permanent URLs
- complete_image_lineage.csv - Full lineage from Google Takeout data, through local processing, to WordPress hosting.
- Organized WordPress Media Library for easy management

### ---

**Phase 4: Final Merge and AI Enrichment**

This is the final step where all data, now sourced from Google Takeout and processed locally, comes together.

#### **Step 4.1: Final Script Setup**

Install the necessary Vertex AI library:  
pip install google-cloud-aiplatform

#### Step 4.15: Caption Model Evaluation (Pre-Implementation)

Before running the full pipeline, conduct a comparative test of caption generation models:

**Test Setup:**
- Select 20-30 representative photos from your dataset
- Generate captions using both:
  - Vertex AI (Gemini Pro Vision) 
  - Claude-3.5-Sonnet or GPT-4V via API
- Note that perhaps I want two captions per photo (see below)
- Develop and test multiple prompt approaches to optimize caption quality: (Note that model won't know who is Ada in the picture if there is more than one person in the picture, I'll have to think about how to deal with that in the prompt)
  - Emotional focus: "Describe Ada's emotional state and the moment's context..."
  - Activity focus: "What is Ada doing in this image and what does it reveal about her personality..."
  - Story integration: "How does this moment fit into Ada's larger journey..." (should I provide an overview of the story for the model to have in context?)
  - Technical description: "Describe the visual elements, setting, and people in this image..."
  - Zero Shot: "Describe this photo in detail."
- Should test prompts systematically:
```python
prompts = {
    "emotional": "Describe the emotional moment and feelings in this image of a young girl's journey",
    "contextual": "What story does this image tell about childhood resilience?",
    "descriptive": "Describe what you see, focusing on the people and their interactions",
    "medical_journey": "Describe this moment in a child's medical journey with sensitivity"
}

# Include context on Ada's story
context = """This image is from Ada's story - a brave 5-year-old girl 
who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. When describing, be sensitive to the medical journey while celebrating moments of joy and connection."""
```

caption_prompt = """
Generate two captions per photo? The "Moment" one could be attached to a photo and that photo could be served somewhat randomly until I get semantic matching of photos working

1. MOMENT: A brief, poetic description of the emotional moment or action (15-20 words)
   Focus on: what's happening, the feeling, the discovery, the connection
   Example: "The wonder of discovering a butterfly on a sunny afternoon"

2. DETAILS: Specific visual and contextual information (30-40 words)
   Include: Who's in the photo (young girl, family members), setting, activities, 
   medical context if visible, season/time indicators
   Example: "A young girl in a yellow dress gently observes a monarch butterfly 
   in a hospital garden. Her careful movements show both curiosity and gentleness."

Format your response as:
MOMENT: [your moment description]
DETAILS: [your detailed description]
"""

- Evaluate based on:
  - Emotional accuracy (captures Ada's state/context)
  - Semantic richness (useful for vector search)
  - Consistency with Ada's story tone
  - Cost per image

**Decision criteria:** Choose the model that best balances caption quality with cost-effectiveness for your 1,000+ image scale.

#### **Step 4.2: The Final Enrichment Script**

This master script will take the `complete_image_lineage.csv` (which includes original metadata from Takeout JSONs, processing details, and WordPress URLs) and call the Vertex AI API for enrichment.

**final_enrichment.py**

* **Output:** A file named **FINAL_MASTER_DATA.csv**. This is your final product, a single source of truth containing every piece of information for each photo (original metadata from Takeout, processing details, WordPress URL, AI-generated captions), ready for you to use in populating your Pinecone database.

### ---

### Phase 5: Vector Database Integration Strategy

The generated captions will be embedded and stored in Pinecone alongside your existing Q&A pairs:

**Data Structure:**
- Each photo caption becomes a searchable vector
- Metadata includes: image URL, emotional tags, source post correlation
- Enables semantic matching between user queries and visual content

**Search Integration:**
- When users receive Q&A responses, system searches photo captions for semantic similarity
- Serves contextually relevant images alongside text answers
- Maintains separate caption and Q&A vector spaces for targeted retrieval 

### ---

### Q&A Integration Strategy (To Be Determined)

Multiple approaches need testing to determine optimal photo-to-answer matching:

**Approach A: Sentiment Matching**
- Extract emotional sentiment from Q&A answers
- Match with photos tagged for similar emotional context
- Pros: Emotionally resonant pairings
- Cons: May miss factual/contextual connections

**Approach B: Semantic Similarity**
- Embed Q&A answers and photo captions in same vector space
- Use cosine similarity for nearest neighbor matching
- Pros: Captures nuanced conceptual relationships
- Cons: May prioritize keyword overlap over emotional resonance

**Approach C: Hybrid Scoring**
- Combine sentiment + semantic similarity + manual category tags
- Weighted scoring system for multi-factor matching
- Pros: Balances multiple relevance factors
- Cons: Added complexity in tuning weights

**Approach D: Post-Context Matching**
- Link photos to specific CaringBridge posts they originated from
- When Q&A references content from a specific post, serve photos from that same post
- Pros: Maintains narrative continuity
- Cons: Limited to photos that have clear post associations

**One idea: Hybrid with Post-Context (C+D)**
Combine Approach C (Hybrid Scoring) with D (Post-Context Matching):

Primary matching: Semantic similarity (0.4 weight) + Sentiment (0.3 weight) + Post context (0.3 weight)
Metadata structure:

json{
  "image_url": "https://...",
  "caption": "AI-generated caption",
  "original_caption": "User caption from Google Photos",
  "emotions": ["joy", "resilience", "connection"],
  "post_id": "caringbridge_post_123",
  "creation_date": "2019-03-15",
  "processing_date": "2025-06-13"
}

**Implementation Strategy**
Create partitions of your data with namespaces to ensure tenant isolation The vector database to build knowledgeable AI | Pinecone - Use Pinecone namespaces to separate:

- photo-captions namespace for image embeddings
- qa-answers namespace for text Q&A pairs
- This allows independent scaling and management

**Next Steps:** Implement small-scale tests of each approach using your existing 300+ Q&A pairs and a subset of photos to evaluate user experience impact before choosing primary strategy.