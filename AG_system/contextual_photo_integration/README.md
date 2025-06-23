### **Project Overview**

The goal of this project is to take a specific album of approximately 1,000 images from your Google Photos account and transform them into a rich, searchable dataset that seamlessly integrates with your Ada's Spark Memory Engine. Currently, these photos exist as static files in Google Photos - valuable visual memories that tell Ada's story but remain disconnected from your semantic search system. Through this process, each image will be downloaded at maximum quality, processed locally with complete lineage tracking, optimized for web delivery, hosted permanently on your WordPress site, and enriched with AI-generated captions that capture the emotional context and narrative significance of each moment. The end result is a contextual photo system that can automatically serve relevant images alongside text-based Q&A responses, transforming your memory engine from a text-only experience into a rich multimedia journey through Ada's story. When users ask questions about Ada's experiences, personality, or journey, they'll not only receive thoughtful written answers but also see photos that emotionally resonate with and visually illustrate those memories.

This process involves six main phases:

1. **Data Extraction:** Downloading your photos and their metadata using Google Takeout.
2. **Image Processing Pipeline:** Processing downloaded images into optimized WebP files with lineage tracking. This includes generating thumbnails and ensuring data integrity with MD5 checks.
3. **WordPress Hosting & URL Generation:** Uploading processed WebP files to WordPress for permanent hosting URLs.
4. **AI Enrichment:** Using AI (e.g., Google's Vertex AI Gemini) to generate multiple descriptive captions for each image.
5. **Upload Captions to Pinecone:** Uploading the AI-generated captions and their vector embeddings to a Pinecone vector database to enable semantic search.
6. **Vector Database Integration Strategy:** Defining and experimenting with approaches for optimal photo-to-answer matching using the Pinecone database.

The primary input for the vector database is the `lineage/multi_prompt_enrichment_output.csv` file, which contains the AI-generated captions and associated metadata. This file is then processed by the `scripts/upload_captions_to_pinecone.py` script to populate Pinecone. While a comprehensive `FINAL_MASTER_DATA.csv` may be generated, the enriched multi-prompt output is key for the semantic search functionality.

### Project Directory Structure

This diagram outlines the complete folder and file structure of the project. Comments denote which items are created manually by the user versus those that are generated automatically by the processing scripts.

```
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
├── processed_webp_thumbnails/ # AUTO-GENERATED: Thumbnail versions (360px height) of processed .webp images.
│   └── some-image-adasstory-h360-thumb.webp
│
├── lineage/                   # AUTO-GENERATED: Contains all tracking and metadata files from the pipeline.
│   ├── download_lineage.csv
│   ├── download_lineage.json
│   ├── processing_lineage.csv
│   ├── processing_lineage.json
│   ├── complete_image_lineage.csv
│   └── wordpress_urls.csv
│
├── scripts/                   # USER-CREATED: All the Python scripts for the project.
│   ├── prepare_takeout_data.py
│   ├── process_downloaded_images.py
│   ├── generate_thumbnails.py
│   ├── image_status_check.py
│   ├── merge_wordpress_data.py
│   ├── final_enrichment.py
│   ├── verify_processing.py
│   ├── download_and_append_urls.sh
│   ├── targeted_check.sh
│   ├── upload_captions_to_pinecone.py
│   ├── cleanup_lineage_data.py
│   ├── safe_merge_thumbnail_data.py
│   └── fix_lineage_MD5s.py
│
├── credentials.json           # USER-CREATED: Your secret credentials from Google Cloud. (Ignored by Git).
├── README.md                  # USER-CREATED: This project documentation file.
├── .env                       # USER-CREATED: Environment variables for WP Engine SSH access.
└── FINAL_MASTER_DATA.csv      # AUTO-GENERATED: A comprehensive CSV file that may be generated, consolidating all data. The `lineage/multi_prompt_enrichment_output.csv` is the direct input for Pinecone uploads.
```

Note: User-managed directories (like `takeout_extracted/`), auto-generated directories (like `original_downloads/`, `processed_webp/`, `lineage/`), and user-created data files (like `credentials.json`, `.env`) as well as the final output (`FINAL_MASTER_DATA.csv`) are typically managed locally and may be included in the project's main `.gitignore` file at the repository root. They are described here for completeness of the workflow.

### **Prerequisites**

### **Google Cloud SDK (gcloud) Setup**

The Python scripts in this project use the Google Cloud SDK to communicate with Google Cloud services. Follow these steps to install and configure the SDK and prepare your project to run the enrichment pipeline.

**Part 1: Installation and Authentication**

1.  **Download the SDK Archive**
    Go to the official Google Cloud SDK documentation page and download the appropriate archive for your system (e.g., macOS 64-bit). Your browser will typically save this to your Downloads folder.

    *Google Cloud SDK Download Page* (Note: You'll need to find and insert the actual link here if available, or leave as plain text if not.)

2.  **Position the SDK**
    Using Finder (macOS) or your file explorer, move the downloaded `.tar.gz` file from your Downloads folder to your Home directory (the directory named after your username).

3.  **Install from Terminal**
    Open your terminal and run the following commands one by one. This will extract the SDK and run the installer.

    ```bash
    # Navigate to your Home directory
    cd ~

    # Extract the archive (use the actual filename you downloaded)
    # Example: tar -xf google-cloud-sdk-YOUR_VERSION-darwin-x86_64.tar.gz
    tar -xf google-cloud-sdk-darwin-x86_64.tar.gz

    # Run the installation script
    ./google-cloud-sdk/install.sh
    ```
    When the installer asks if you want to Modify your PATH, answer yes (Y).

4.  **Update Your Current Terminal Session**
    To make the `gcloud` command available immediately without restarting your terminal, run the following command to load the updated configuration (for Zsh, common on macOS. If you use Bash, it might be `source ~/.bashrc` or `source ~/.bash_profile`):

    ```bash
    source ~/.zshrc
    ```

5.  **Initialize the SDK**
    This command will walk you through logging into your Google Account and selecting the Google Cloud project you want to use for this work.

    ```bash
    gcloud init
    ```

6.  **Set Up Application Default Credentials**
    This final authentication step authorizes the Python scripts to use your credentials to access Google Cloud APIs.

    ```bash
    gcloud auth application-default login
    ```

**Part 2: Project Configuration**

After initializing the SDK, you must configure your specific project to use the necessary services.

1.  **Link a Billing Account**
    A billing account is required to use services like Vertex AI. First, find your billing account ID:

    ```bash
    gcloud beta billing accounts list
    ```
    Copy the `ACCOUNT_ID` from the output, then use it to link billing to your project. Replace `[YOUR_PROJECT_ID]` and `[YOUR_BILLING_ACCOUNT_ID]` with your actual IDs.

    ```bash
    gcloud beta billing projects link [YOUR_PROJECT_ID] --billing-account=[YOUR_BILLING_ACCOUNT_ID]
    ```

2.  **Enable the Vertex AI API**
    The project requires the Vertex AI API to be enabled.

    ```bash
    gcloud services enable aiplatform.googleapis.com
    ```

3.  **Set Default AI Region**
    Configure your default region to match the one specified in the enrichment script (us-central1).

    ```bash
    gcloud config set ai/region us-central1
    ```

*Note: These instructions are current as of June 17, 2025. The Google Cloud platform and its tools evolve. For the most up-to-date information, always consult the official Google Cloud SDK documentation.*

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

### **Dual MD5 Tracking System**

Starting with pipeline version 2.1+, the system tracks two types of MD5 hashes for complete lineage and accurate file matching:

#### **MD5 Hash Types**
- **`md5_hash`**: Original file MD5 from Google Takeout download (for audit trail)
- **`processed_file_md5`**: Current processed WebP file MD5 (for accurate matching)

#### **Why Dual Tracking?**
During processing, files undergo transformations (format conversion, compression, resizing) that change their MD5 hashes. Tracking both allows:
- ✅ **Complete audit trail** from original source to final processed file
- ✅ **Accurate status checking** using current file hashes
- ✅ **WordPress matching** with files as they actually exist
- ✅ **Data integrity** without losing original source tracking

#### **Pipeline Integration**
- `scripts/prepare_takeout_data.py` records original download MD5s
- `scripts/process_downloaded_images.py` calculates and stores processed file MD5s
- `scripts/image_status_check.py` uses processed MD5s for accurate file matching
- `scripts/merge_wordpress_data.py` merges data using filename-based matching (WordPress standard)

---

### **Execution Workflow (Quick Start Guide)**

This section provides a concise summary of the commands needed to run the entire data processing pipeline.

1.  **Phase 1 - Prepare a Takeout Album:** Unzip a single Google Takeout album into a temporary staging folder (e.g., `takeout_extracted/`). Then run the preparation script, pointing it to the album's sub-folder. Repeat this step for each album.

    ```bash
    python scripts/prepare_takeout_data.py takeout_extracted/Name-Of-Album-Folder/
    ```

2.  **Phase 2 - Process Images to WebP:** Run the processing script. It automatically finds all new images from the previous step and converts them to WebP.

    ```bash
    python scripts/process_downloaded_images.py
    ```

2.1  **(Optional) Verify Processing:** Run the verification script to confirm all images were processed successfully and that lineage tracking is complete.

    ```bash
    python scripts/verify_processing.py
    ```

2.2 **Generate Thumbnails:** Run the thumbnail generation script.
     This script creates smaller, web-optimized thumbnails for faster loading in contexts where full-size images are not immediately needed.
    ```bash
    python scripts/generate_thumbnails.py
    ```
2.4.5 **Add Processed File MD5s:** Enable accurate status checking by adding processed file MD5 hashes to lineage.
```bash
python scripts/fix_lineage_MD5s.py
```  
3.  **Phase 3 - Pre-Upload Status Check:** Check what needs to be uploaded to avoid duplicates.
    ```bash
    python scripts/image_status_check.py
    ```
    **Note:** This check shows accurate WordPress status using dual MD5 tracking (original download MD5s and processed file MD5s).

3.1  **Manual Upload to WordPress:**
    *   Review the status check output and identify which images need uploading
    *   Navigate to your WordPress Media Library (ideally to the "Ada's Story Project" folder)
    *   Upload the necessary `.webp` files from `processed_webp/` AND their corresponding thumbnails from `processed_webp_thumbnails/`
    *   Upload only files identified as needing upload to prevent redundant uploads

3.2  **Export WordPress URLs and Download Locally:**
    *   On your WP Engine server, export WordPress filenames and URLs using WP-CLI:
        ```bash
        # SSH to server: ssh your_env@your_env.ssh.wpengine.net
        # Navigate: cd sites/your_env
        # Export: wp post list --post_type=attachment --fields=post_name,guid --format=csv | grep -- '-adasstory' > wordpress_urls.csv
        ```
    *   Download and append these URLs locally:
        ```bash
        chmod +x scripts/download_and_append_urls.sh && ./scripts/download_and_append_urls.sh
        ```
        Ensure your `.env` file is correctly configured at `AG_system/contextual_photo_integration/.env` before running this.

3.3  **Merge WordPress URLs:** Run the merge script to combine the processing lineage with WordPress URLs.

    ```bash
    python scripts/merge_wordpress_data.py
    ```

3.4  **Post-Merge Verification:** Verify that the upload and merge process worked correctly.
    ```bash
    python scripts/image_status_check.py
    ```
    **Note:** After merging WordPress URLs, this check will accurately show which images are on WordPress vs. which still need uploading. Most images should now show as "✅ On WordPress" if the pipeline worked correctly.

4.  **Phase 4 - Enrich with AI Captions:** Run the final script to generate AI captions.

    ```bash
    python scripts/final_enrichment.py --model YOUR_MODEL_CHOICE --ada-context --image-source thumbnail [--limit X]
    ```
    *(Note: You must first edit the `final_enrichment.py` script to set your GCP `PROJECT_ID`. The `--model` argument is required. Optional arguments like `--input-file` and `--force-reprocess` can be used for more specific needs.)*

5.  **Phase 5 - Upload Captions to Pinecone:** Upload the generated image captions to your Pinecone vector database.
    ```bash
    python scripts/upload_captions_to_pinecone.py --captions EMOTIONAL,CONTEXTUAL --namespace photo-captions
    ```
    *(Note: Ensure your `.env` file is configured with `PINECONE_API_KEY`. You can specify which caption types to upload using the `--captions` argument.)*
---

**Phase 1: Data Extraction with Google Takeout**

The goal of this phase is to download all your photos and their corresponding metadata from Google Photos using Google Takeout.

#### **Step 1.1: Perform a Google Takeout**

1.  Go to [Google Takeout](https://takeout.google.com/).
2.  Deselect all products, then select **Google Photos**.
3.  Choose the option to "Select all photo albums" or select specific albums you wish to export. Note that you will only be allowed to export items that you are the "owner" of and then only the photos that you "own" inside the album that you "own". The workaround is to open the shared album (do this in a somewhat clean google photos account), "save" all the photos to your library, then at the photos page in google photos find "recently added" on the left. Add the appropriate pictures to a new album, then google takeout should see it.
4.  Configure the export settings:
    *   **Delivery method:** "Send download link via email" is common.
    *   **Frequency:** "Export once."
    *   **File type & size:** Choose `.zip` or `.tgz`. Select a larger archive size (e.g., 50GB) if you have many photos to minimize the number of downloaded files.
5.  Click "Create export." This process can take some time, from hours to days, depending on the size of your library. Google will email you when your export is ready.
6.  Download the archive files. Create a dedicated staging directory on your local computer (e.g., `takeout_extracted/`) and extract the contents of a single album's `.zip` file into it.
7.  Inside the extracted album folder, you will find your image files (e.g., `.jpg`, `.png`, `.heic`) alongside JSON files that contain the metadata. Each image typically has its own supplemental JSON file (e.g., `image_name.JPG` and `image_name.JPG.supplemental-metadata.json`).
8.  **For a multi-album workflow:** After processing the first album, clear the staging directory and repeat step 6 for the next album's `.zip` file. The scripts are designed to add new photos without creating duplicates.

* **Output:** A local directory containing the photo files and their associated JSON metadata files from a single Takeout album, ready for processing. The `scripts/prepare_takeout_data.py` script will be run on this directory.

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

The script `scripts/prepare_takeout_data.py` will:
1.  Read the directory of extracted Takeout files.
2.  This script is state-aware. It loads the existing `lineage/download_lineage.csv` file at startup and uses MD5 hashes to automatically skip any images (by content) that have already been processed in previous runs.
3.  Parse relevant information from the JSON files (e.g., original filename, user caption (often `description` in the JSON), creation date (`photoTakenTime` -> `timestamp`), geolocation if available, etc.).
4.  Copy or move image files to the `original_downloads/` directory, organized by date, using the metadata from JSONs.
5.  Store the extracted metadata in a structured way, creating `lineage/download_lineage.json` and `lineage/download_lineage.csv`.

Run the `scripts/prepare_takeout_data.py` script, pointing it to the directory of a single extracted Takeout album (e.g., `takeout_extracted/Ada_headshot_ish_photos`).

Note: Repeat this process for each album. The script will intelligently organize all photos chronologically into the same `original_downloads/` directory.

#### **Step 2.3: Process Downloaded Images**

The script `scripts/process_downloaded_images.py` transforms images from `original_downloads/` into optimized WebP files:

* **Features (v2.1+):**
  * Automatically skips video files to prevent processing failures
  * Calculates both original download MD5s and processed file MD5s
  * State-aware processing (skips already processed files)
  * Complete transformation history tracking

* **Output:**
  * `original_downloads/` folder containing original images from Takeout, organized by date.
  * `processed_webp/` folder containing optimized WebP files ready for WordPress upload.
  * `lineage/processing_lineage.json` - Complete transformation history for each image.
  * `lineage/processing_lineage.csv` - Tabular format for Phase 3 integration.

After running the main processing script, you can use the optional `scripts/verify_processing.py` script to programmatically confirm that all expected files were processed successfully and that lineage tracking is complete.

#### **Step 2.4: Generate Thumbnails**

After the primary image processing is complete, thumbnails are generated using the `scripts/generate_thumbnails.py` script.

*   **Purpose:** This script creates lightweight, smaller versions of the processed `.webp` images. These thumbnails are intended for use in contexts where a full-resolution image is not immediately necessary, such as previews or gallery views, improving load times and user experience.
*   **Process:**
    1.  The script iterates through all images in the `processed_webp/` directory.
    2.  Before generating a new thumbnail, it checks if a thumbnail matching the new naming convention (`[original_stem]-h360-thumb.webp`) already exists in the `processed_webp_thumbnails/` directory.
    3.  If an existing thumbnail is found, the script skips the generation step for that image to save processing time. It will still attempt to gather metadata (dimensions, file size) from the existing file.
    4.  If no existing thumbnail is found, it generates a new one with a fixed height of 360 pixels, maintaining the original aspect ratio.
    5.  Thumbnails are saved (or confirmed to exist) in the `processed_webp_thumbnails/` directory.
    6.  The naming convention for thumbnails is `[original_stem]-h360-thumb.webp` (e.g., if the original is `image-adasstory.webp`, the thumbnail will be `image-adasstory-h360-thumb.webp`).
    7.  The script updates the `lineage/processing_lineage.json` file for each image, adding/updating metadata about the thumbnail.

*   **Output:**
    *   `processed_webp_thumbnails/` folder populated with thumbnail images.
    *   Updated `lineage/processing_lineage.json` with thumbnail-specific metadata for each image entry.

#### **Step 2.4.5: Add Processed File MD5s to Lineage**
This step uses the `scripts/fix_lineage_MD5s.py` script to enhance the lineage data by adding MD5 hashes of the *processed* files. This is crucial for accurate status checking and file matching in later pipeline stages, as processing (like WebP conversion or resizing) changes the file content and thus its MD5 hash from the original downloaded version.

*   **Purpose:** To ensure that lineage files (`complete_image_lineage.csv` and `processing_lineage.json`) contain both the MD5 hash of the original downloaded file (`md5_hash`) and the MD5 hash of the processed WebP file (`processed_file_md5`). This dual tracking allows for a complete audit trail while also enabling accurate matching against the files as they currently exist.

*   **Process:**
    1.  The script typically iterates through images listed in the lineage data.
    2.  For each image, it locates the corresponding processed file in the `processed_webp/` directory.
    3.  It calculates the MD5 hash of this processed file.
    4.  It updates the lineage records (e.g., `complete_image_lineage.csv`) by adding this new hash to a `processed_file_md5` column.
    5.  The script usually includes safety measures like creating backups of lineage files before modification.

*   **Usage:**
    ```bash
    python scripts/fix_lineage_MD5s.py
    ```

*   **Output:** Lineage files (e.g., `lineage/complete_image_lineage.csv`, `lineage/processing_lineage.json`) are updated with a `processed_file_md5` column, providing an enhanced dataset for subsequent pipeline operations. This enables more reliable status checks by `scripts/image_status_check.py`.

#### **Step 2.5: Lineage Benefits**

This Takeout-first approach provides complete traceability:

- **Source tracking:** Original filename from Takeout, and any identifiers available in the JSON metadata.
- **File integrity:** MD5 checksums for both original downloads and processed files.
- **Transformation log:** Every resize, rotation, format change with timestamps.
- **File evolution:** Original Takeout filename → final WordPress filename.
- **Quality metrics:** File sizes before/after each step.
- **Error handling:** Failed processing tracked with reasons.
- **Audit trail:** Complete history for compliance and debugging.
- **Local backup:** Original Takeout files are preserved.
- **Dual MD5 tracking:** Both original source MD5s and processed file MD5s for complete lineage.

### ---

### **Phase 3: WordPress Hosting & URL Generation**

Now upload your processed images to WordPress and capture their permanent URLs.

#### **Step 3.1: Organize Your WordPress Media Library**

Before uploading, log in to WordPress and install a **Media Library Folders plugin** (like Filebird). Create a new folder named "Ada's Story Project" to keep your images organized and separate from other media.

#### **Step 3.2: Check Image Status and Manually Upload Necessary Images**

Before uploading, it's crucial to identify which images need to be uploaded to avoid duplicates and resolve any local file issues.

1.  **Run the Image Status Check Script:**
    Execute the `scripts/image_status_check.py` script:
    ```bash
    python scripts/image_status_check.py
    ```
    This Python-based script provides reliable status checking with:
    *   **Local Duplicate Detection:** Reports files with identical content (based on MD5 checksums)
    *   **WordPress Status Check:** Uses dual MD5 tracking to accurately identify which files are already uploaded
    *   **Thumbnail Status:** Reports missing or orphaned thumbnails
    *   **Clear categorization:** Files are categorized as "✅ On WordPress", "⏳ In lineage, needs URL", or "📤 Ready for upload"

2.  **Review and Prepare for Upload:**
    Carefully review the output of the status check. Based on its report:
    *   Address any local duplicates found
    *   Identify files marked as "📤 Ready for upload" - these need to be uploaded
    *   Note files marked as "⏳ In lineage, needs URL" - these may already be uploaded but need URL merging

3.  **Manually Upload to WordPress:**
    Navigate to your WordPress Media Library (ideally to the "Ada's Story Project" folder). Bulk upload the necessary `.webp` files from your local `processed_webp/` folder AND their corresponding thumbnails from the `processed_webp_thumbnails/` folder. Upload both full-size images and their thumbnails to ensure complete media availability.

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
    This command lists all attachments, extracts their post name (slug) and GUID (URL), formats the output as CSV, and then filters for filenames containing `'-adasstory'` to capture only the relevant processed full-size images. The output is saved to `wordpress_urls.csv` in your site's root directory on the server.

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
    Replace the placeholder values with your actual credentials and paths.

2.  **Run the script:**
    ```bash
    chmod +x scripts/download_and_append_urls.sh && ./scripts/download_and_append_urls.sh
    ```
    The script will use `scp` to download the WordPress URLs and append them to your local `lineage/wordpress_urls.csv` file.

**Output:**
- All images hosted on WordPress with permanent URLs accessible via the server-generated `wordpress_urls.csv`.
- `lineage/wordpress_urls.csv` file locally, containing an aggregated list of filenames and their corresponding WordPress URLs.
- `lineage/complete_image_lineage.csv` (generated by `scripts/merge_wordpress_data.py` in the next step) - Full lineage from Google Takeout data, through local processing, to WordPress hosting.

### ---

**Phase 4: Final Merge and AI Enrichment**

This is the final step where all data, sourced from Google Takeout and processed locally, comes together.

#### **Step 4.1: Final Script Setup**

Install the necessary Vertex AI library:  
```bash
pip install google-cloud-aiplatform
```
#### Step 4.15: Caption Model and Prompt Evaluation with `final_enrichment.py`

The `final_enrichment.py` script is the primary tool for generating and evaluating AI captions for the images. This script automates the process of testing different models, prompts, and image sources. This section details how the script is structured and how it can be used for evaluation.

**Prompting Strategy:**

The script utilizes a predefined set of prompts designed to capture diverse aspects of each image. These prompts are defined in the `PROMPTS_TO_TEST` dictionary within the script:

```python
PROMPTS_TO_TEST = {
    "EMOTIONAL": "Describe the emotional moment and feelings in this image of a young girl's journey",
    "MOMENT": "A brief, poetic description of the emotional moment or action (15-20 words). Focus on: what's happening, the feeling, the discovery, the connection. Example: \"The wonder of discovering a butterfly on a sunny afternoon\"",
    "CONTEXTUAL": "What story does this moment tell about Ada's character, relationships, or journey? Focus on the emotions, interactions, and personality traits visible in this scene.",
    "STORY": "Describe the story this image tells about Ada's life and spirit. What does this moment reveal about her personality, her relationships, or her approach to challenges?",
    "CHARACTER": "What character traits, emotions, or relationships are evident in this image? Describe Ada's spirit and personality as shown in this moment."
}
```

These prompts guide the AI model to generate captions focusing on emotional content, the specific moment captured, broader contextual relevance to Ada's story, narrative elements, and character insights.

**Ada's Context (`ADA_CONTEXT`):**

To provide essential background information to the AI model, the script uses a global string variable `ADA_CONTEXT`. This context is prepended to the prompts when the `--ada-context` flag is used.

The `ADA_CONTEXT` is defined as:
```python
ADA_CONTEXT = """This image is from Ada's story - a brave 5-year-old girl
who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed.
Important dates: she was born 6-8-18, diagnosed 5-5-22,
bone marrow transplant from her brother on 9-13-22, and died 7-22-23.
It is possible that some photos have the incorrect date. When describing, be sensitive
to the medical journey while celebrating moments of joy and connection."""
```
This ensures that the generated captions are informed by Ada's overall story, key life events, and the desired tone of sensitivity and celebration.

**Temporal Context Awareness:**

The script incorporates temporal awareness using the `IMPORTANT_DATES_STR` dictionary and the `get_temporal_context` function.

`IMPORTANT_DATES_STR`:
```python
IMPORTANT_DATES_STR = {
    "birth": "2018-06-08",
    "diagnosis": "2022-05-05",
    "transplant": "2022-09-13",
    "death": "2023-07-22"
}
```
The `get_temporal_context` function compares the photo's creation date (if available) with these important dates. If a photo is taken on or near (within a `DAYS_WINDOW` of 7 days by default) one of these dates, or near a birthday or anniversary of passing, a relevant temporal context string is generated (e.g., "This photo was taken 3 days before Ada's diagnosis."). This temporal context is then appended to the `CONTEXTUAL`, `STORY`, and `CHARACTER` prompts to add further depth and relevance to the generated captions.

**Model and Image Source Testing Strategy:**

The `final_enrichment.py` script is designed to facilitate testing various models and image sources:

*   **Models:** The script supports multiple Gemini models via the `--model` command-line argument. Initial testing can start with high-performance models and then explore more cost-effective or faster options. The available choices (defined in `argparse`) include:
    *   `gemini-2.5-pro`
    *   `gemini-2.5-flash`
    *   `gemini-2.5-flash-lite-preview-06-17`
    *   `gemini-2.0-flash-001`
    *   `gemini-2.0-flash-lite-001`
    (Refer to the script's `parse_arguments` function for the most current list.)
*   **Image Source:** The `--image-source` flag allows testing with either `full` resolution WebP images or `thumbnail` images. This helps evaluate the trade-off between caption quality (potentially better with full-resolution images) and processing cost/speed (thumbnails are faster and cheaper to process).
*   **Iterative Evaluation:** The typical strategy involves:
    1.  Testing a small, representative batch of images with a powerful model (e.g., `gemini-2.5-pro`) and full-resolution images to establish a quality baseline.
    2.  Comparing results with thumbnail images using the same model to assess if quality remains acceptable.
    3.  Experimenting with simpler/faster/cheaper models (e.g., `gemini-2.5-flash` or `gemini-2.0-flash-lite`) with the chosen image source to find the best balance of quality, cost, and performance for the entire dataset.

**Output Structure:**

For each image, the `final_enrichment.py` script sends a single request to the AI model, asking it to generate responses for all five prompts. The model is instructed to return a single JSON object containing these responses. The script then parses this JSON and creates separate rows in the output CSV for each prompt-answer pair.

The expected JSON structure from the model is:
```json
{
    "EMOTIONAL": "[caption for emotional prompt]",
    "MOMENT": "[caption for moment prompt]",
    "CONTEXTUAL": "[caption for contextual prompt]",
    "STORY": "[caption for story prompt]",
    "CHARACTER": "[caption for character prompt]"
}
```
This structure is detailed in the main prompt constructed within the script that is sent to the Vertex AI API.

**Using `final_enrichment.py` for Evaluation:**

To evaluate different models or settings:
1.  Prepare your input CSV (default `lineage/complete_image_lineage.csv`, or a smaller subset for testing using `--input-file`).
2.  Run the `final_enrichment.py` script with the desired parameters:
    ```bash
    # Example: Test 'gemini-2.5-flash' with thumbnails and Ada context on 10 images
    python scripts/final_enrichment.py --model gemini-2.5-flash --image-source thumbnail --ada-context --limit 10
    ```
3.  Analyze the output `lineage/multi_prompt_enrichment_output.csv`. Each row in this CSV corresponds to one image and one specific prompt (e.g., one row for `image1.webp` with the `EMOTIONAL` caption, another row for `image1.webp` with the `MOMENT` caption, etc.).
4.  Review the generated captions for:
    *   Emotional accuracy and resonance.
    *   Semantic richness for potential vector search.
    *   Consistency with Ada's story and the desired tone.
    *   Relevance given the image, Ada's context, and any temporal context.
5.  Consider the `total_tokens` and processing time (by observing script execution) to evaluate cost-effectiveness.

By iteratively running the script with different configurations and evaluating the output, you can determine the optimal model, image source, and prompt settings for processing your entire photo collection. The script's stateful processing (it skips images+prompts that have already been successfully processed and exist in the output file, unless `--force-reprocess` is used) helps in efficiently resuming or extending evaluation runs.

---------- OVERALL STRATEGY (note that this section should be moved probably) ----------
🎯 Your Ada Photo Search & Recommendation System
📸 Caption Generation Strategy:

MOMENT caption: Generated for every image (15-20 word poetic descriptions)
CONTEXTUAL caption: Generated for every image (detailed character/relationship/journey context)
Cost-effective approach: Use thumbnails (28% savings, equivalent quality)

🔍 Search & Discovery Flow:
Step 1: Question Processing

User asks question about Ada → embed question
Search Pinecone for semantically similar question
Return relevant answer from your QA knowledge base

Step 2: Display 4 Photos Next to Relevant Answer
Embed the answer displayed to the user
2 images: Match answer using embedded MOMENT captions
2 images: Match answer using embedded CONTEXTUAL captions
Display strategy: Always show MOMENT caption to users (short, poetic, human-friendly)




#### **Step 4.3: The Final Enrichment Script**

The script `scripts/final_enrichment.py` is responsible for generating descriptive and contextual captions for each image using AI models. It takes consolidated image data, sends requests to a specified AI model, and records the generated captions along with other relevant information.

**Key Features:**

*   **Versatile Captioning**: Generates multiple captions per image based on a set of predefined prompts.
*   **Contextual Awareness**: Can incorporate Ada's overall story (`ADA_CONTEXT`) and specific temporal context related to important dates.
*   **Model Flexibility**: Allows selection from various Gemini models.
*   **Image Source Options**: Can process full-resolution images or thumbnails.
*   **Robustness**: Implements retry logic for transient API errors and stateful processing to resume or skip already completed work.
*   **Detailed Output**: Produces a CSV file with comprehensive information for each generated caption, including tokens used, status, and traceability hashes.

**Configuration:**

*   **GCP Project ID**: Crucially, you **must configure your Google Cloud `PROJECT_ID` as a constant directly within the `final_enrichment.py` script**. This is required for the script to authenticate with and utilize Vertex AI services.
    ```python
    # --- Configuration ---
    PROJECT_ID = "your-gcp-project-id-here"  # Update this line in the script
    LOCATION = "us-central1"
    ```

**Command-Line Options:**

The script's behavior can be customized using the following command-line arguments:

*   `--model MODEL_NAME`: (Required) Specifies the AI model to use.
    *   Choices: `gemini-2.5-pro`, `gemini-2.5-flash`, `gemini-2.5-flash-lite-preview-06-17`, `gemini-2.0-flash-001`, `gemini-2.0-flash-lite-001`.
*   `--input-file FILE_PATH`: Specifies the path to the input CSV file (defaults to `lineage/complete_image_lineage.csv`). This file should contain image metadata, including URLs.
*   `--image-source [full|thumbnail]`: Specifies whether to use `full` resolution WebP images (from the `url` column in the input CSV) or `thumbnail` images (from the `wordpress_url_thumbnail` column) for captioning. Defaults to `full`. Using thumbnails can speed up processing and reduce costs.
*   `--ada-context`: If specified, enables the inclusion of Ada's temporal context (defined in `ADA_CONTEXT` and `IMPORTANT_DATES_STR` within the script) in the prompts for `CONTEXTUAL`, `STORY`, and `CHARACTER`.
*   `--limit N`: Optionally limits the number of images to process from the input file (useful for testing).
*   `--force-reprocess`: If specified, reprocesses **all** images and their prompt combinations, even if they have existing successfully processed entries in the output file. Consider just deleting the records from the output file if it errored or you want to rerun it.

**Prompts Used:**

The script utilizes a predefined dictionary (`PROMPTS_TO_TEST`) to generate diverse captions for each image. For each image, it generates a caption for each of the following prompt keys:

*   `EMOTIONAL`
*   `MOMENT`
*   `CONTEXTUAL`
*   `STORY`
*   `CHARACTER`

(Refer to the `PROMPTS_TO_TEST` dictionary in the script for the full text of each prompt.)

**Robustness and Efficiency:**

*   **Retry Logic**: The script incorporates a retry mechanism (via the `process_image_with_retry` function) to handle transient API errors (e.g., timeouts). It will attempt to reprocess an image up to `MAX_RETRIES` times with exponential backoff.
*   **Stateful Processing**: To avoid redundant work and allow for interruption and resumption, the script loads existing results from `lineage/multi_prompt_enrichment_output.csv` upon starting. It calculates a `param_hash` (using `calculate_processing_hash`) for each unique combination of image, model, prompt, and other processing parameters. If a hash corresponding to a successful prior attempt is found, that specific image-prompt combination is skipped, unless the `--force-reprocess` flag is used.

Note: you may want to run it with caffeinate (e.g. caffeinate -i python scripts/final_enrichment.py --model gemini-2.5-flash --input-file lineage/complete_image_lineage.csv --ada-context --image-source thumbnail) for long runs

**Traceability Hashes:**

The script includes hashing mechanisms for traceability and state management:

*   `param_hash`: This hash is calculated by `calculate_processing_hash` based on the original filename, model used, image URL, prompt name, whether Ada context was included, and the image source. It is stored in the output CSV for successfully processed records and is used internally by the script to identify unique processing parameter combinations for stateful processing (i.e., skipping already processed items).
*   `generate_record_hash`: This function is defined in the script to create a unique hash from original filename, model, prompt name, and a processing timestamp. The script uses this to generate an `error_hash` for records that encounter errors. While the subtask mentioned `record_hash` for each output row, currently, successfully processed rows get a `param_hash` and error rows get an `error_hash`.

**Output File (`lineage/multi_prompt_enrichment_output.csv`):**

The script generates `lineage/multi_prompt_enrichment_output.csv`. Unlike a wide format with one row per image and multiple caption columns, this file has a long format: **each row represents a single caption generated for a specific image using a specific prompt.**

Key columns in this output file include:
*   `processing_order`: The order in which the image was processed from the input file.
*   `image_url`: The URL of the image that was actually used for analysis (full or thumbnail).
*   `original_filename`: The original filename of the image.
*   `model_used`: The AI model that generated the caption.
*   `total_tokens`, `prompt_tokens`, `candidates_tokens`: Token usage information for the generation request.
*   `prompt_name`: The key from `PROMPTS_TO_TEST` that was used (e.g., `EMOTIONAL`, `STORY`).
*   `prompt_answer`: The AI-generated caption for that specific prompt.
*   `photo_taken_time`: The creation date of the photo, if available.
*   `temporal_context`: Any temporal context string that was added to the prompt.
*   `ada_context_included`: Boolean indicating if `ADA_CONTEXT` was used.
*   `image_source_used`: Indicates whether `full` or `thumbnail` image source was used for generating the caption.
*   `status`: Indicates if the processing for this specific image-prompt was a `success` or `error`.
*   `param_hash` (for successful records) or `error_hash` (for error records): The hash for traceability/state management.

**Usage Example:**

```bash
python scripts/final_enrichment.py --model gemini-2.5-flash --ada-context --image-source thumbnail --limit 10
```
This example would process the first 10 images from the default input CSV, using their thumbnails, incorporating Ada's temporal context, and utilizing the 'gemini-2.5-flash' model. The output CSV would contain up to 50 new rows (10 images x 5 prompts each), plus any pre-existing data if not using `--force-reprocess`.

* If you get authentication issues:
# Set up authentication
gcloud auth application-default login

### ---

### **Phase 5: Upload Captions to Pinecone**

This phase takes the AI-generated captions and other metadata from the enrichment process and uploads them as vector embeddings to a Pinecone vector database. This enables powerful semantic search capabilities, allowing users to find relevant photos based on the meaning and context of their queries.

The `scripts/upload_captions_to_pinecone.py` script is responsible for this process.

**Key Functionality:**

*   Reads enriched caption data from the output of `final_enrichment.py` (typically `lineage/multi_prompt_enrichment_output.csv`, configurable via `--input-file`).
*   Merges this data with `lineage/complete_image_lineage.csv` (configurable via `--lineage-file`) to access essential information like WordPress URLs and original image details.
*   Allows the user to specify which types of generated captions (e.g., `EMOTIONAL`, `CONTEXTUAL`, `STORY`) should be embedded and uploaded. This is controlled by the mandatory `--captions` argument, which accepts a comma-separated list.
*   Generates vector embeddings for the selected captions using a text embedding model (e.g., `text-embedding-ada-002` or similar, specified within the script or Pinecone client).
*   Uploads these embeddings to a specified Pinecone index (default in script: `adas-memory-qa-poc`) and namespace (default in script: `photo-captions`). It's important to note that the main Q&A system uses a different index (`adas-memory-qa-prod`). Ensure the correct index is targeted for photo captions.
*   Includes rich metadata with each vector. This metadata is crucial for filtering, context presentation, and linking back to the original image. It typically includes:
    *   WordPress URLs for the full-size image and thumbnail.
    *   The original filename and photo creation date.
    *   Ada's age at the time the photo was taken.
    *   The specific caption text that was embedded.
    *   Details about the AI model and prompts used for caption generation.
    *   A traceability hash (`record_hash`) from the enrichment output.

**Prerequisites:**

*   A `.env` file must be present in the project root directory and configured with your `PINECONE_API_KEY`.

**Command-Line Options:**

*   `--captions CAPTION_LIST`: (Required) Comma-separated list of caption types to upload (e.g., `EMOTIONAL,CONTEXTUAL,STORY`). These correspond to the prompt keys used during enrichment.
*   `--input-file FILE_PATH`: Path to the CSV file containing enriched captions. Defaults to `lineage/multi_prompt_enrichment_output.csv`.
*   `--lineage-file FILE_PATH`: Path to the complete image lineage CSV file. Defaults to `lineage/complete_image_lineage.csv`.
*   `--index-name INDEX_NAME`: Specifies the Pinecone index to upload to. Defaults to `adas-memory-qa-poc`.
*   `--namespace NAMESPACE`: Specifies the namespace within the Pinecone index. Defaults to `photo-captions`.
*   `--dry-run`: If specified, the script will prepare data and show what would be uploaded without actually performing any uploads to Pinecone.
*   `--batch-size SIZE`: The number of records to process and upload in a single batch. Defaults to 90.

**Usage Example:**

```bash
python scripts/upload_captions_to_pinecone.py --captions EMOTIONAL,STORY --namespace photo-captions-test
```
This command would upload the `EMOTIONAL` and `STORY` captions to the `photo-captions-test` namespace in your Pinecone index.

**Output:**

The script uploads the generated vectors and their associated metadata directly to your Pinecone index. Progress and status messages are printed to the console.

### ---

### **Phase 6: Vector Database Integration Strategy**

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

#### **`scripts/cleanup_lineage_data.py` - Removing Failed Processing Records**

*   **Purpose:** Cleans processing lineage files by removing records for files that failed to process or don't exist, keeping only successful processing records.
*   **Common Causes:**
    *   Video files that were downloaded but can't be processed as images (`.mp4`, `.mov`, etc.)
    *   Processing failures that left incomplete records
    *   Files that were processed but later deleted or moved
*   **Symptoms:** 
    *   Status check shows all files as "Not In Lineage" even after merging
    *   Processing lineage has more records than actual processed files
    *   Many lineage records have `final_filename: null`
*   **Solution:** 
    ```bash
    python scripts/cleanup_lineage_data.py
    python scripts/merge_wordpress_data.py
    ```
*   **Prevention:** Updated `scripts/process_downloaded_images.py` (v2.1+) now skips video files automatically to prevent this issue.

#### **`scripts/safe_merge_thumbnail_data.py` - Fixing Misplaced Lineage Files**

*   **Purpose:** This utility script resolves a specific issue where `scripts/generate_thumbnails.py` creates a `processing_lineage.json` file in the project root instead of the `lineage/` directory, causing data structure conflicts.
*   **The Problem:** 
    *   Root file: Dictionary structure with thumbnail metadata keyed by image stems
    *   Lineage file: Array structure with complete processing records including MD5 hashes
    *   Attempting to merge these incompatible structures causes `AttributeError: 'str' object has no attribute 'get'`
*   **The Solution:** 
    *   Safely extracts thumbnail metadata from the misplaced root file
    *   Matches records by filename stems derived from `final_filename` field
    *   Merges thumbnail data into the proper lineage array structure
    *   Cleans up the misplaced file to prevent future conflicts
*   **When to Use:** Run this script if you encounter the above error or find a `processing_lineage.json` file in your project root that should be in `lineage/`
*   **How to Use:**
    ```bash
    python scripts/safe_merge_thumbnail_data.py
    ```
*   **Prevention:** Fixed in `scripts/generate_thumbnails.py` (v2.1+) to use correct file paths.
*   **Safety:** The script preserves all existing data and only removes the misplaced file after successful merge completion.

#### **`scripts/image_status_check.py` - Python-based Status Checking**

*   **Purpose:** Reliable Python-based replacement for the bash status check script. Provides accurate file categorization using pandas for robust CSV parsing.
*   **Advantages over bash version:**
    *   ✅ Handles complex CSV data (JSON fields with commas)
    *   ✅ Uses dual MD5 tracking for accurate matching
    *   ✅ Clear error messages and debugging information
    *   ✅ Structured, readable output
*   **Usage:**
    ```bash
    python scripts/image_status_check.py
    ```
*   **Output Categories:**
    *   **✅ On WordPress**: Files with WordPress URLs in lineage
    *   **⏳ In lineage, needs URL**: Files processed but missing WordPress URLs
    *   **📤 Ready for upload**: Files not in lineage (typically from recent processing)
    *   **❌ Other issues**: Parse errors or missing lineage file

#### **`scripts/targeted_check.sh` - Diagnosing Filename Discrepancies**

*   **Purpose:** This script is designed to help debug issues where specific files are not merging correctly between `lineage/processing_lineage.csv` and `lineage/wordpress_urls.csv`. This often occurs due to subtle filename mismatches (e.g., case differences, spaces vs. hyphens, presence/absence of special characters).
*   **How it Works:**
    *   The script contains a hard-coded array of problematic filename *stems* (the part of the filename before the extension).
    *   It iterates through this list. For each filename stem, it uses `grep` to search for matching lines in both `lineage/processing_lineage.csv` and `lineage/wordpress_urls.csv`.
    *   It then displays any matching lines found in both files, allowing for a direct visual comparison of how the filename appears in each CSV.
*   **Utility:** This script is particularly useful for quickly spotting the exact nature of a filename discrepancy. It was instrumental in identifying the need for more robust filename normalization during the development of the main processing scripts.
*   **How to Use:**
    ```bash
    cd scripts/
    ./targeted_check.sh
    ```
    You may need to `chmod +x targeted_check.sh` first.

#### **Common Pipeline Issues**

**Issue: Status check shows all files as "Not In Lineage" despite being on WordPress**
- **Cause:** MD5 mismatch between lineage records and actual files
- **Solution:** Run `python scripts/fix_lineage_MD5s.py` to add processed file MD5s
- **Prevention:** Use pipeline version 2.1+ with automatic dual MD5 tracking

**Issue: Status check shows all files as "Ready for upload" but they're already uploaded**
- **Cause:** Same as above - MD5 mismatch preventing proper matching
- **Solution:** Run `python scripts/fix_lineage_MD5s.py`
- **Verification:** After fix, re-run `python scripts/image_status_check.py`

**Issue: Processing lineage has failed records with null final_filename**
- **Cause:** Video files causing image processing failures
- **Solution:** Run `python scripts/cleanup_lineage_data.py` to remove failed records
- **Prevention:** Pipeline version 2.1+ automatically skips video files

**Issue: Processing lineage in wrong location**
- **Cause:** Bug in `scripts/generate_thumbnails.py` file path
- **Solution:** Run `python scripts/safe_merge_thumbnail_data.py`
- **Prevention:** Use updated `scripts/generate_thumbnails.py` with correct paths

**Issue: CSV parsing errors in bash scripts**
- **Cause:** Complex data (JSON) breaking simple comma-splitting logic
- **Solution:** Use `python scripts/image_status_check.py` instead of bash version
- **Prevention:** Prefer Python scripts for robust CSV handling

### ---

### **Q&A Integration Strategy (To Be Determined)**

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

**Hybrid with Post-Context (C+D) - Recommended Approach:**
Combine Approach C (Hybrid Scoring) with D (Post-Context Matching):

Primary matching: Semantic similarity (0.4 weight) + Sentiment (0.3 weight) + Post context (0.3 weight)

Metadata structure:
```json
{
  "image_url": "https://...",
  "caption": "AI-generated caption",
  "original_caption": "User caption from Google Photos",
  "emotions": ["joy", "resilience", "connection"],
  "post_id": "caringbridge_post_123",
  "creation_date": "2019-03-15",
  "processing_date": "2025-06-13"
}
```

**Implementation Strategy:**
Create partitions of your data with namespaces using Pinecone namespaces to separate:
- `photo-captions` namespace for image embeddings. The `scripts/upload_captions_to_pinecone.py` script is used to populate the `photo-captions` namespace with the chosen image caption embeddings and their metadata.
- `qa-answers` namespace for text Q&A pairs.
- This allows independent scaling and management.

**Next Steps:** Implement small-scale tests of each approach using your existing Q&A pairs and a subset of photos to evaluate user experience impact before choosing primary strategy.

---

### **Pipeline Version History**

**Version 2.1+ (Current)**
- ✅ Dual MD5 tracking (original + processed file hashes)
- ✅ Automatic video file skipping during processing
- ✅ Python-based status checking with robust CSV parsing
- ✅ Correct file paths for all scripts
- ✅ Enhanced error handling and prevention
- ✅ Complete thumbnail generation with lineage tracking
- ✅ Reliable WordPress URL merging

**Version 2.0 (Previous)**
- ✅ Single MD5 tracking (original download hashes only)
- ❌ Video files caused processing failures
- ❌ Bash-based status checking with CSV parsing issues
- ❌ Some file path bugs in thumbnail generation
- ❌ Inconsistent lineage tracking

**Migration from v2.0 to v2.1:** 
Run `python scripts/fix_lineage_MD5s.py` to upgrade existing v2.0 lineage files to v2.1 format with dual MD5 tracking.

---

### **Development Notes**

#### **File Naming Conventions**
- **Original files:** Preserved exactly as they appear in Google Takeout
- **Processed files:** `[original_stem]-adasstory.webp`
- **Thumbnails:** `[original_stem]-adasstory-h360-thumb.webp`
- **WordPress URLs:** Derived automatically from processed filenames

#### **Error Handling Strategy**
- **Graceful degradation:** Scripts continue processing even if individual files fail
- **Comprehensive logging:** All errors logged with context for debugging
- **State preservation:** Failed processing doesn't corrupt existing lineage data
- **Recovery mechanisms:** Utility scripts available to fix common issues

#### **Performance Considerations**
- **Batch processing:** Images processed in batches with progress indicators
- **Memory management:** Large images processed individually to prevent memory issues
- **Network efficiency:** WordPress URL downloads use incremental updates
- **Storage optimization:** WebP format provides excellent compression while maintaining quality

#### **Security and Privacy**
- **Credential management:** Google Cloud credentials stored locally and git-ignored
- **SSH security:** WP Engine access uses SSH keys and environment variables
- **Data isolation:** Each album processed independently to limit exposure
- **Backup strategy:** Original files preserved throughout pipeline

#### **Testing and Validation**
- **Status verification:** Multiple validation scripts ensure data integrity
- **Hash verification:** MD5 checksums validate file integrity throughout pipeline
- **Lineage validation:** Complete audit trail from source to final output
- **WordPress validation:** URLs tested for accessibility and correct serving

---

### **Future Enhancements**

#### **Planned Features**
- **Enhanced metadata:** EXIF data extraction and preservation in lineage
- **Parallelize final_enrichment.py:** Input rows could be split and batches run in parallel, captions could be run in parallel, etc. If you go those two routes make sure to rejoin into one file for pinecone upload (or change the upload workflow)

#### **Scalability Considerations**
- **Cloud processing:** Migration to cloud-based image processing for large datasets
- **CDN integration:** Automatic WordPress CDN configuration for global image delivery
- **Database sharding:** Strategies for handling tens of thousands of images
- **API rate limiting:** Intelligent throttling for AI caption generation at scale

---

### **License and Usage**

This project is part of the Ada's Spark Memory Engine initiative. The code and documentation are designed to preserve and make searchable the visual memories of Ada's journey. While the specific implementation is tailored to this use case, the techniques and approaches may be valuable for other memorial and archival projects.

---

### **Acknowledgments**

This pipeline was developed to honor Ada's memory and make her story more accessible through visual search and AI-enhanced discovery. The technical approach prioritizes data integrity, emotional sensitivity, and long-term preservation of precious memories.

Special thanks to the open-source community for the tools that make this pipeline possible:
- **Pillow** for robust image processing
- **Pandas** for reliable data manipulation  
- **Google Cloud** for AI capabilities
- **WordPress/WP Engine** for reliable hosting
- **Pinecone** for vector search capabilities