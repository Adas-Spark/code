### **Project Overview**

The goal of this project is to take a specific album of approximately 1,000 images from your Google Photos account and transform them into a rich, searchable dataset that seamlessly integrates with your Ada's Spark Memory Engine. Currently, these photos exist as static files in Google Photos - valuable visual memories that tell Ada's story but remain disconnected from your semantic search system. Through this process, each image will be downloaded at maximum quality, processed locally with complete lineage tracking, optimized for web delivery, hosted permanently on your WordPress site, and enriched with AI-generated captions that capture the emotional context and narrative significance of each moment. The end result is a contextual photo system that can automatically serve relevant images alongside text-based Q&A responses, transforming your memory engine from a text-only experience into a rich multimedia journey through Ada's story. When users ask questions about Ada's experiences, personality, or journey, they'll not only receive thoughtful written answers but also see photos that emotionally resonate with and visually illustrate those memories.

This process involves four main phases:

1. **Data Extraction:** Downloading your photos and their metadata using Google Takeout. Google Takeout allows you to export your Google Photos library, including original image files and accompanying JSON metadata files for each image.
2. **Download & Processing:** Processing the downloaded original images from Google Takeout into optimized WebP files with complete lineage tracking throughout the transformation pipeline.
3. **Hosting & URL Generation:** Uploading the processed WebP files to your WP Engine WordPress site to get a permanent, high-performance hosting URL for each image.  
4. **Enrichment & Consolidation:** Merging all the data (extracted from Takeout JSONs and WordPress URLs) and then using Google's Vertex AI (Gemini) or another model (TBD) to generate a high-quality, descriptive caption for each image.
5. **Vector Database Integration Strategy:** The generated captions will be embedded and stored in Pinecone alongside your existing Q&A pairs
6. **Q&A integration experimentation:** Multiple approaches need testing to determine optimal photo-to-answer matching

The final deliverable will be a single master CSV file containing all this information, ready to be used to populate your Pinecone vector database. This CSV will be built from the information extracted from the Google Takeout JSON files and subsequent processing steps.

### Project Directory Structure

This diagram outlines the complete folder and file structure of the project. Comments denote which items are created manually by the user versus those that are generated automatically by the processing scripts.

project_root/
├── takeout_extracted/         # USER-MANAGED: Temporary staging area for unzipping one Takeout album at a time.
│
├── original_downloads/        # AUTO-GENERATED: Original photos, organized by date by prepare_takeout_data.py.
│   ├── 2022-05-05/
│   └── ...
│
├── processed_webp/            # AUTO-GENERATED: Optimized .webp images ready for upload to WordPress.
│   └── some-image-adasstory.webp
│
├── lineage/                   # AUTO-GENERATED: Contains all tracking and metadata files from the pipeline.
│   ├── download_lineage.csv
│   ├── download_lineage.json
│   ├── processing_lineage.csv
│   ├── processing_lineage.json
│   ├── complete_image_lineage.csv
│   ├── image_caption_experiments.json # AUTO-GENERATED: Stores results of multiple AI caption generation experiments.
│
├── scripts/                   # USER-CREATED: All the Python scripts for the project.
│   ├── prepare_takeout_data.py
│   ├── process_downloaded_images.py
│   ├── merge_wordpress_data.py
│   ├── final_enrichment.py
│   ├── generate_final_csv.py
│   └── verify_processing.py
│
├── credentials.json           # USER-CREATED: Your secret credentials from Google Cloud. (Ignored by Git).
├── README.md                  # USER-CREATED: This project documentation file.
├── wordpress_urls.csv         # USER-CREATED: Manually exported from WordPress after uploading WebP files.
└── FINAL_MASTER_DATA.csv      # AUTO-GENERATED: The final, enriched output of the entire pipeline.

Note: User-managed directories (like `takeout_extracted/`), auto-generated directories (like `original_downloads/`, `processed_webp/`, `lineage/`), and user-created data files (like `wordpress_urls.csv`, `credentials.json`) as well as the final output (`FINAL_MASTER_DATA.csv`) are typically managed locally and may be included in the project's main `.gitignore` file at the repository root. They are described here for completeness of the workflow.

### **Prerequisites**

Before you begin, make sure you have the following:

* **Accounts:**  
  * A Google Cloud account with a project created.  
  * Billing enabled for the project (required for API usage, though you will likely stay within free tiers).  
  * APIs Enabled: **Vertex AI API**.
  * A WordPress administrator account on your WP Engine site.  
* **Software:**  
  * Python 3 installed on your local computer.  
  * A code editor (like Visual Studio Code).  
* **Credentials:**  
  * Application Default Credentials set up for Vertex AI (this is often handled automatically when you install the Google Cloud CLI and run gcloud auth application-default login).
  * Access to your Google Account to perform a Google Takeout.

### ---

### **Execution Workflow (Quick Start Guide)**

This section provides a concise summary of the commands needed to run the entire data processing pipeline.

1.  **Prepare a Takeout Album:** Unzip a single Google Takeout album into a temporary staging folder (e.g., `takeout_extracted/`). Then run the preparation script, pointing it to the album's sub-folder. Repeat this step for each album.

    ```bash
    python scripts/prepare_takeout_data.py takeout_extracted/Name-Of-Album-Folder/
    ```

2.  **Process Images to WebP:** Run the processing script. It automatically finds all new images from the previous step and converts them to WebP.

    ```bash
    python scripts/process_downloaded_images.py
    ```

2.5.  **(Optional) Verify Processing:** Run the verification script to confirm all images were processed successfully and that lineage tracking is complete.

    ```bash
    python scripts/verify_processing.py
    ```

3.  **Check Image Status, Upload to WordPress, Export URLs, and Download/Append:**
    *   Run the `check_image_status.sh` script to identify local duplicates and images already on WordPress:
        ```bash
        bash scripts/check_image_status.sh
        ```
        Review the script's output, which includes detailed file lists and a final summary of statistics, to understand the status of your images. Then, manually upload only the new/unique images from `processed_webp/` to your WordPress media library (specifically to the media folder associated with this project). This step helps prevent redundant uploads.
        Note: The script's report on which images are 'already on WordPress' is based on your `lineage/complete_image_lineage.csv` file. Ensure this file is current by running `scripts/download_and_append_urls.sh` (Step 3.4) and `scripts/merge_wordpress_data.py` (Step 4) after any manual uploads for the most accurate results from `check_image_status.sh` on subsequent runs.
    *   On your WP Engine server, find the wordpress filenames and URLs using the WP-CLI command and create a remote file with this info (Phase 3, Step 3.3):
        ```bash
        # Example: ssh your_env@your_env.ssh.wpengine.net "cd sites/your_env && wp post list --post_type=attachment --fields=post_name,guid --format=csv | grep -- '-adasstory' > wordpress_urls.csv"
        ```
    *   Then, run the local script to download and append these URLs:
        ```bash
        chmod +x scripts/download_and_append_urls.sh && ./scripts/download_and_append_urls.sh
        ```
        Ensure your `.env` file is correctly configured at `AG_system/contextual_photo_integration/.env` before running this.

4.  **Merge WordPress URLs:** Run the merge script to combine the processing lineage with your (now locally updated) WordPress URLs.

    ```bash
    python scripts/merge_wordpress_data.py
    ```

5.  **Enrich with AI Captions:** Run the enrichment script to generate AI captions using multiple prompts. This script now outputs `lineage/image_caption_experiments.json`. *(Note: You must first edit `scripts/final_enrichment.py` to set your GCP Project ID).*

    ```bash
    python scripts/final_enrichment.py
    ```

5.5. **Generate Final CSV:** Run the `generate_final_csv.py` script to process the `image_caption_experiments.json` and produce the `FINAL_MASTER_DATA.csv` file.
    ```bash
    python scripts/generate_final_csv.py
    ```

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
6.  Download the archive files. Create a dedicated staging directory on your local computer (e.g., `takeout_extracted/`) and extract the contents of a single album's `.zip` file into it.
7.  Inside the extracted album folder, you will find your image files (e.g., `.jpg`, `.png`, `.heic`) alongside JSON files that contain the metadata. Each image typically has its own supplemental JSON file (e.g., `image_name.JPG` and `image_name.JPG.supplemental-metadata.json`).
8.  **For a multi-album workflow:** After processing the first album, clear the staging directory and repeat step 6 for the next album's `.zip` file. The scripts are designed to add new photos without creating duplicates.

* **Output:** A local directory containing the photo files and their associated JSON metadata files from a single Takeout album, ready for processing. The `prepare_takeout_data.py` script will be run on this directory. The `google_data.csv` file mentioned in previous versions of this documentation is no longer used; instead, scripts process the data directly from your Takeout export.

### ---

### **Phase 2: Image Processing Pipeline**

This phase takes the original images downloaded via Google Takeout, stores them with lineage tracking, and processes them into optimized WebP files ready for WordPress hosting. The JSON metadata files from Takeout will be used in this phase to guide processing and extract relevant information.

#### **Step 2.1: Prepare Your Processing Environment**

Install the required libraries:
```bash
pip install Pillow requests pandas
```

Create your directory structure as illustrated in the "Project Directory Structure" section.

#### **Step 2.2: Organize Takeout Files and Extract Metadata**

Since Google Takeout provides the original images directly, the primary task is to organize these files and parse the accompanying JSON metadata.

A script `prepare_takeout_data.py` will:
1.  Read the directory of extracted Takeout files.
2.  This script is state-aware. It loads the existing lineage/download_lineage.csv file at startup and uses MD5 hashes to automatically skip any images (by content) that have already been processed in previous runs.
3.  Parse relevant information from the JSON files (e.g., original filename, user caption (often `description` in the JSON), creation date (`photoTakenTime` -> `timestamp`), geolocation if available, etc.).
4.  Copy or move image files to the `original_downloads/` directory, perhaps organized by date as originally planned, using the metadata from JSONs.
5.  Store the extracted metadata in a structured way, possibly creating an initial version of the `lineage/download_lineage.json` or a new CSV file that will serve a similar purpose to the old `google_data.csv` but derived from Takeout.

Run the prepare_takeout_data.py script, pointing it to the directory of a single extracted Takeout album (e.g., takeout_extracted/Ada_headshot_ish_photos).

Note: Repeat this process for each album. The script will intelligently organize all photos chronologically into the same original_downloads/ directory.

#### **Step 2.3: Process Downloaded Images**

Create the processing script that transforms images from `original_downloads/` into optimized WebP files:

**process_downloaded_images.py** (This script will likely remain similar, but its input data source changes from API-downloaded files to Takeout-sourced files, using the metadata extracted in Step 2.2).

* **Output:**

- `original_downloads/` folder containing original images from Takeout, organized by date.
- `processed_webp/` folder containing optimized WebP files ready for WordPress upload.
- `lineage/takeout_metadata_log.json` (or similar) - Log of metadata extracted from Takeout JSONs.
- `lineage/processing_lineage.json` - Complete transformation history for each image.
- `processing_lineage.csv` - Tabular format for Phase 3 integration, now based on Takeout data.

After running the main processing script, you can use the optional `scripts/verify_processing.py` script to programmatically confirm that all expected files were processed successfully and that lineage tracking is complete.

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

#### **Step 3.2: Check Image Status and Manually Upload Necessary Images**

Before uploading, it's crucial to identify which images need to be uploaded to avoid duplicates and resolve any local file issues.

1.  **Run the Image Status Check Script:**
    Execute the `check_image_status.sh` script:
    ```bash
    bash AG_system/contextual_photo_integration/scripts/check_image_status.sh
    ```
    This script performs two main checks:
    *   **Local Duplicate Detection:** It looks for any files within your `processed_webp/` folder that have identical content (based on MD5 checksums) and reports them.
    *   **WordPress Existing Image Check (via Lineage File):** It checks images from `processed_webp/` against the `lineage/complete_image_lineage.csv` file. An image is considered "already on WordPress" if its MD5 checksum is found in this lineage file *and* is associated with a WordPress URL (or GUID/post_name) in that same record. It also categorizes images found in lineage but missing a URL, and images not found in lineage at all.
        **Important:** The accuracy of this WordPress status check depends entirely on the `complete_image_lineage.csv` file being up-to-date. This means you must have successfully run the `scripts/download_and_append_urls.sh` (Step 3.4) and `scripts/merge_wordpress_data.py` (Step 4) scripts after your last batch of manual image uploads for `check_image_status.sh` to accurately identify recently uploaded images.
    The script will output detailed lists of files in each category, followed by a summary of counts (total unique files, local duplicate sets, and files in each WordPress status category based on lineage).

2.  **Review and Prepare for Upload:**
    Carefully review the output of `check_image_status.sh` (both the detailed lists and the summary statistics). Based on its report:
    *   Address any local duplicates found.
    *   Identify the subset of images in `processed_webp/` that are *not* yet on WordPress and are unique. These are the files you need to upload.

3.  **Manually Upload to WordPress:**
    Navigate to your WordPress Media Library (ideally to the "Ada's Story Project" folder you created in Step 3.1) and bulk upload only the necessary `.webp` files from your local `processed_webp/` folder. Using the WordPress interface for this manual upload is generally robust.

This process, guided by the `check_image_status.sh` script, ensures you only upload new, unique images, preventing clutter and potential issues in your WordPress media library.

#### **Step 3.3: Export WordPress URLs using WP-CLI**

This step involves using WP-CLI directly on your WP Engine server to export the necessary image URLs.

1.  **SSH into WP Engine:**
    ```bash
    ssh environmentname@environmentname.ssh.wpengine.net
    ```
    Replace `environmentname` with your specific WP Engine environment name.

2.  **Navigate to your site's root directory:**
    ```bash
    cd sites/environmentname
    ```
    Again, replace `environmentname` with your site's name.

3.  **Run the WP-CLI command:**
    ```bash
    wp post list --post_type=attachment --fields=post_name,guid --format=csv | grep -- '-adasstory' > wordpress_urls.csv
    ```
    This command lists all attachments, extracts their post name (slug) and GUID (URL), formats the output as CSV, and then filters for filenames containing `'-adasstory'` (or your chosen suffix) to capture only the relevant processed images. The output is saved to `wordpress_urls.csv` in your site's root directory on the server. **Note:** The `grep` suffix (`'-adasstory'`) might need to be adjusted based on the filename convention established in `process_downloaded_images.py`.

#### **Step 3.4: Download and Append URLs**

This step uses the `scripts/download_and_append_urls.sh` script to securely download the `wordpress_urls.csv` file from your server and append its contents to a local version.

1.  **Configure Environment Variables:**
    The script requires a `.env` file located at `AG_system/contextual_photo_integration/.env`. This file must contain the following variables for `scp` to connect to your server:
    ```
    REMOTE_USER="your_ssh_username"
    REMOTE_HOST="your_wpengine_ssh_host"
    # (e.g., environmentname.ssh.wpengine.net)
    REMOTE_PATH="/sites/environmentname/wordpress_urls.csv"
    # (full path to the csv on the server)
    ```
    Replace the placeholder values with your actual credentials and paths. For example:
    ```
    REMOTE_USER="mywpuser"
    REMOTE_HOST="mysite.ssh.wpengine.net"
    REMOTE_PATH="/sites/mysite/wordpress_urls.csv"
    ```

2.  **Run the script:**
    The script will:
    *   Use `scp` to download `wordpress_urls.csv` from the `REMOTE_PATH` on your `REMOTE_HOST` using `REMOTE_USER`.
    *   Create `lineage/wordpress_urls.csv` locally if it doesn't exist, adding the headers `filename,url`.
    *   Append the newly downloaded URLs to this local file, skipping the header row from the downloaded file to avoid duplication.

    This ensures that subsequent runs of `merge_wordpress_data.py` (Step 4 in the Quick Start Guide) will use the most up-to-date list of WordPress URLs.

Output:

- All images hosted on WordPress with permanent URLs accessible via the server-generated `wordpress_urls.csv`.
- `lineage/wordpress_urls.csv` file locally, containing an aggregated list of filenames and their corresponding WordPress URLs, ready for merging by `merge_wordpress_data.py`.
- `complete_image_lineage.csv` (generated by `merge_wordpress_data.py` in a later step) - Full lineage from Google Takeout data, through local processing, to WordPress hosting.
- Organized WordPress Media Library for easy management.

### ---

**Phase 4: Final Merge and AI Enrichment**

This is the final step where all data, now sourced from Google Takeout and processed locally, comes together.

#### **Step 4.1: Final Script Setup**

Install the necessary Vertex AI library:  
pip install google-cloud-aiplatform

#### Step 4.15: AI Caption Generation with Multiple Prompts

The `final_enrichment.py` script is designed to facilitate the testing of multiple AI-generated caption approaches for each image. Instead of manually conducting a pre-implementation test with a small subset, this script automates the generation of captions using various prompts for all images in your `complete_image_lineage.csv`.

**How it Works:**
- The script iterates through each image.
- For each image, it iterates through a predefined list of prompts (which you can configure within `final_enrichment.py`).
- It calls the configured Vertex AI model (e.g., Gemini Pro Vision) for each image-prompt combination.
- The example prompts below illustrate the types of prompts you might define in the script:
```python
prompts_to_test = [
    {
        "prompt_id": "emotional_v1",
        "prompt_text": "Describe the emotional moment and feelings in this image of a young girl's journey. This image is from Ada's story - a brave 5-year-old girl who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. When describing, be sensitive to the medical journey while celebrating moments of joy and connection."
    },
    {
        "prompt_id": "descriptive_v1",
        "prompt_text": "Describe what you see in this image, focusing on the people, setting, and their interactions. This image is from Ada's story - a brave 5-year-old girl who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. Be sensitive to the medical journey."
    },
    {
        "prompt_id": "story_integration_v1",
        "prompt_text": "How does this moment fit into Ada's larger journey? Ada was a brave 5-year-old girl who fought leukemia. Born 6-8-18, diagnosed 5-5-22, BMT from brother 9-13-22, died 7-22-23. Focus on resilience, connection, or challenges depicted."
    }
]
```
*(The above is an example; refer to `final_enrichment.py` for the actual prompts used).*

**Output of Experiments:**
The results of these caption generation experiments are stored in `lineage/image_caption_experiments.json`. This JSON file contains a list of objects, where each object corresponds to an image and includes:
- `image_identifier`: The WordPress URL or original filename.
- `lineage_data`: The original row of data for that image from `complete_image_lineage.csv`.
- `caption_experiments`: A list of results, one for each prompt tested. Each result includes:
    - `prompt_id`: Identifier for the prompt used.
    - `prompt_text`: The full text of the prompt.
    - `generated_caption`: The caption produced by the AI.
    - `model_used`: The AI model used.
    - `timestamp`: When the caption was generated.
    - `selected`: A boolean field (default `False`) that you can later manually or programmatically set to `True` to mark a preferred caption for an image.
    - `error`: Any error message if the caption generation failed for that specific prompt.

**Using the Results:**
You can review `lineage/image_caption_experiments.json` to:
- Compare the effectiveness of different prompts across your image set.
- Identify which prompts yield the most emotionally accurate, semantically rich, or contextually appropriate captions.
- Inform your decision on which caption(s) to ultimately use for each image. You might manually update the `selected: true` field in this JSON for your preferred captions before generating the final CSV, or use this data to refine prompts for future runs.

#### **Step 4.2: The Final Enrichment Script (`final_enrichment.py`)**

This script takes the `complete_image_lineage.csv` (which includes original metadata from Takeout JSONs, processing details, and WordPress URLs) as input. For each image, it iterates through a defined set of prompts (see Step 4.15) and calls the Vertex AI API to generate captions.

**Input:** `complete_image_lineage.csv`
**Processing:**
1.  Reads each image entry from the input CSV.
2.  For each image, loops through a list of predefined prompts.
3.  Calls the Vertex AI API (e.g., Gemini Pro Vision) with the image and each prompt.
4.  Collects all generated captions, prompt details, model information, and timestamps.
**Output:** A file named `lineage/image_caption_experiments.json`. This JSON file stores a detailed record of all caption generation attempts for every image and every prompt. Its structure is detailed in Step 4.15. This file serves as an intermediate data store before the final CSV is generated.

#### **Step 4.3: Generating the Master CSV File (`generate_final_csv.py`)**

This script processes the `lineage/image_caption_experiments.json` file to produce the final, flattened CSV dataset.

**Input:** `lineage/image_caption_experiments.json`
**Processing:**
1.  Reads the JSON file containing all caption experiments.
2.  For each image, it iterates through every caption experiment that was performed (i.e., for every prompt tested).
3.  It creates a new row for each experiment by combining the original `lineage_data` for the image with the specific details from that experiment.
4.  This means an image that had three prompts tested against it will result in three rows in the output CSV. These rows will share the same lineage data but will differ in their caption-related columns.
**Output:** `FINAL_MASTER_DATA.csv`. This CSV file contains all the original lineage data for each image, plus the following columns derived from each caption experiment:
    - `prompt_id`: The identifier of the prompt used.
    - `prompt_text`: The full text of the prompt.
    - `ai_description`: The AI-generated caption for that prompt (renamed from `generated_caption` in the JSON).
    - `caption_model_used`: The model used for that specific caption.
    - `caption_timestamp`: The timestamp of when that caption was generated.
    - `caption_selected`: The boolean value indicating if this caption was marked as selected.
    - `caption_error`: Any error message recorded during that caption generation.
This file is your final product, ready for populating your Pinecone database or for other analytical purposes.

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

### **Troubleshooting and Utility Scripts**

This section details various scripts that can help diagnose issues or perform specific utility functions within the project.

#### **`targeted_check.sh` - Diagnosing Filename Discrepancies**

*   **Purpose:** This script is designed to help debug issues where specific files are not merging correctly between `lineage/processing_lineage.csv` and `lineage/wordpress_urls.csv`. This often occurs due to subtle filename mismatches (e.g., case differences, spaces vs. hyphens, presence/absence of special characters).
*   **How it Works:**
    *   The script contains a hard-coded array of problematic filename *stems* (the part of the filename before the extension).
    *   It iterates through this list. For each filename stem, it uses `grep` to search for matching lines in both `lineage/processing_lineage.csv` and `lineage/wordpress_urls.csv`.
    *   It then displays any matching lines found in both files, allowing for a direct visual comparison of how the filename appears in each CSV.
*   **Utility:** This script is particularly useful for quickly spotting the exact nature of a filename discrepancy. It was instrumental in identifying the need for more robust filename normalization during the development of the main processing scripts.
*   **How to Use:**
    ```bash
    cd AG_system/contextual_photo_integration/scripts/
    ./targeted_check.sh
    ```
    (Adjust the path if you are running it from the project root, e.g., `./AG_system/contextual_photo_integration/scripts/targeted_check.sh`). You may need to `chmod +x targeted_check.sh` first.

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
