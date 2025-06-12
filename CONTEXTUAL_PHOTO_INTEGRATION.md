### **Project Overview**

The goal of this project is to take a specific album of approximately 1,000 images from your Google Photos account and transform them into a rich, searchable dataset that seamlessly integrates with your Ada's Spark Memory Engine. Currently, these photos exist as static files in Google Photos - valuable visual memories that tell Ada's story but remain disconnected from your semantic search system. Through this process, each image will be optimized for web delivery, hosted permanently on your WordPress site, and enriched with AI-generated captions that capture the emotional context and narrative significance of each moment. The end result is a contextual photo system that can automatically serve relevant images alongside text-based Q&A responses, transforming your memory engine from a text-only experience into a rich multimedia journey through Ada's story. When users ask questions about Ada's experiences, personality, or journey, they'll not only receive thoughtful written answers but also see photos that emotionally resonate with and visually illustrate those memories.

This process involves four main phases:

1. **Data Extraction:** Programmatically pulling all available metadata (captions, creation dates, permanent links) for each photo from your Google Photos album.  
2. **Image Processing:** This phase streams images directly from Google Photos, processes them in memory, and saves optimized files locally - eliminating the need for storing original files while maintaining complete lineage tracking.
3. **Hosting & URL Generation:** Uploading the processed WebP files to your WP Engine WordPress site to get a permanent, high-performance hosting URL for each image.  
4. **Enrichment & Consolidation:** Merging all the data and then using Google's Vertex AI (Gemini) to generate a high-quality, descriptive caption for each image.
5. **Vector Database Integration Strategy:** The generated captions will be embedded and stored in Pinecone alongside your existing Q&A pairs
6. **Q&A integration experimentation:** Multiple approaches need testing to determine optimal photo-to-answer matching

The final deliverable will be a single master CSV file containing all this information, ready to be used to populate your Pinecone vector database.

### **Prerequisites**

Before you begin, make sure you have the following:

* **Accounts:**  
  * A Google Cloud account with a project created.  
  * Billing enabled for the project (required for API usage, though you will likely stay within free tiers).  
  * APIs Enabled: **Google Photos Library API** and **Vertex AI API**.  
  * A WordPress administrator account on your WP Engine site.  
* **Software:**  
  * Python 3 installed on your local computer.  
  * A code editor (like Visual Studio Code).  
* **Credentials:**  
  * Your OAuth 2.0 credentials.json file downloaded from your Google Cloud project for the Photos API.  
  * Application Default Credentials set up for Vertex AI (this is often handled automatically when you install the Google Cloud CLI and run gcloud auth application-default login).

### ---

**Phase 1: Gather All Metadata from Google Photos**

The goal here is to get a master list of all photos in your album and their associated metadata from Google.

#### **Step 1.1: Find Your Album's ID**

You'll need the unique ID for the album you want to process. Run the find\_album\_id.py script from our previous discussion to list all your albums and their IDs. Find your target album in the terminal output and copy its ID.

#### **Step 1.2: Export All Album Metadata**

Use the process\_album\_photos.py script from our previous discussion. Ensure it is modified to save all the critical identifiers we discussed:

Python

\# In process\_album\_photos.py, inside the loop...  
all\_photo\_data.append({  
    'api\_id': item.get('id'),  
    'google\_photos\_link': item.get('productUrl'),  
    'original\_filename': item.get('filename'),  
    'user\_caption': item.get('description', ''),  
    'creation\_date': item.get('mediaMetadata', {}).get('creationTime')  
})

**Run the script.**

* **Output:** This will produce a CSV file named **google\_data.csv**. This file is your foundational dataset.

### ---

### **Phase 2: Direct Processing Pipeline (Streamlined Local Processing)**

This phase streams images directly from Google Photos, processes them in memory, and saves optimized files locally - eliminating the need for storing original files while maintaining complete lineage tracking.

#### **Step 2.1: Prepare Your Processing Environment**

Install the required libraries:
```bash
pip install Pillow requests
```

#### **Step 2.2:  Streaming Processing Script**

Create a new Python script that combines download, processing, and upload in a single pipeline:
direct_processing_pipeline.py

```Python
import os
import requests
from PIL import Image
from io import BytesIO
import datetime
import pandas as pd
import json

# --- Configuration ---
GOOGLE_DATA_CSV = 'google_data.csv'  # From Phase 1
LINEAGE_LOG_FILE = 'processing_lineage.json'
MAX_DIMENSION = 1920
FILENAME_TAG = '-adasstory'
# Adaptive quality based on source
if source_image_size < 500000:  # Under 500KB
    WEBP_QUALITY = 90  # Higher quality for already compressed images
else:
    WEBP_QUALITY = 85

# --- Processing Pipeline ---
def process_image_with_lineage(photo_row):
    """Process a single image with complete lineage tracking"""
    
    lineage_record = {
        'original_filename': photo_row['original_filename'],
        'google_photos_id': photo_row['api_id'],
        'google_photos_link': photo_row['google_photos_link'], # Should this be 'base_url'? I don't think so but double-check
        'creation_date': photo_row['creation_date'],
        'user_caption': photo_row['user_caption'],
        'processing_timestamp': datetime.datetime.now().isoformat(),
        'transformations': [],
        'status': 'processing'
    }
    
    try:
        # Step 1: Stream download from Google Photos
        # Note: You'll need to append '=w1920-h1920' to the baseUrl from Google Photos API
        download_url = photo_row['base_url'] + '=w1920-h1920'
        response = requests.get(download_url)
        response.raise_for_status()
        lineage_record['transformations'].append({
            'step': 'downloaded',
            'source': 'google_photos_api',
            'size_bytes': len(response.content)
        })
        
        # Step 2: Load and process image in memory
        img = Image.open(BytesIO(response.content))
        original_size = img.size
        lineage_record['transformations'].append({
            'step': 'loaded_to_memory',
            'original_dimensions': f"{original_size[0]}x{original_size[1]}",
            'original_format': img.format
        })
        
        # Handle EXIF orientation
        if hasattr(img, '_getexif') and img._getexif():
            exif = img._getexif()
            orientation_key = 274
            if orientation_key in exif:
                orientation = exif[orientation_key]
                if orientation == 3: 
                    img = img.rotate(180, expand=True)
                    lineage_record['transformations'].append({'step': 'rotated_180'})
                elif orientation == 6: 
                    img = img.rotate(270, expand=True)
                    lineage_record['transformations'].append({'step': 'rotated_270'})
                elif orientation == 8: 
                    img = img.rotate(90, expand=True)
                    lineage_record['transformations'].append({'step': 'rotated_90'})
        
        # Resize while maintaining aspect ratio
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION))
        new_size = img.size
        lineage_record['transformations'].append({
            'step': 'resized',
            'new_dimensions': f"{new_size[0]}x{new_size[1]}",
            'max_dimension_limit': MAX_DIMENSION
        })
        
        # Convert to WebP in memory
        webp_buffer = BytesIO()
        img.save(webp_buffer, 'webp', quality=WEBP_QUALITY)
        webp_buffer.seek(0)
        
        # Generate new filename
        file_stem = os.path.splitext(photo_row['original_filename'])[0]
        new_filename = f"{file_stem}{FILENAME_TAG}.webp"
        lineage_record['final_filename'] = new_filename
        lineage_record['transformations'].append({
            'step': 'converted_to_webp',
            'quality': WEBP_QUALITY,
            'final_size_bytes': len(webp_buffer.getvalue())
        })
        
        # Step 3: Save processed file locally
        processed_dir = 'processed_webp'
        if not os.path.exists(processed_dir):
            os.makedirs(processed_dir)
            
        output_path = os.path.join(processed_dir, new_filename)
        webp_buffer.seek(0)
        with open(output_path, 'wb') as f:
            f.write(webp_buffer.getvalue())
            
        lineage_record['local_file_path'] = output_path
        lineage_record['transformations'].append({
            'step': 'saved_locally',
            'file_path': output_path
        })  

        lineage_record['status'] = 'completed'
        print(f"✅ Successfully processed: {photo_row['original_filename']} -> {new_filename}")
        
    except Exception as e:
        lineage_record['status'] = 'failed'
        lineage_record['error'] = str(e)
        print(f"❌ Failed to process: {photo_row['original_filename']} - {e}")
    
    return lineage_record

# --- Main Processing Loop ---
def main():
    # Load Google Photos data from Phase 1
    google_df = pd.read_csv(GOOGLE_DATA_CSV)
    
    all_lineage_records = []
    
    print(f"Starting direct processing pipeline for {len(google_df)} images...")
    
    for index, row in google_df.iterrows():
        lineage_record = process_image_with_lineage(row)
        all_lineage_records.append(lineage_record)
        
        # Save incremental progress
        if (index + 1) % 10 == 0:
            with open(LINEAGE_LOG_FILE, 'w') as f:
                json.dump(all_lineage_records, f, indent=2)
            print(f"Progress: {index + 1}/{len(google_df)} images processed")
    
    # Final save
    with open(LINEAGE_LOG_FILE, 'w') as f:
        json.dump(all_lineage_records, f, indent=2)
    
    # Convert to CSV for easier Phase 4 integration
    lineage_df = pd.DataFrame(all_lineage_records)
    lineage_df.to_csv('processing_lineage.csv', index=False)
    
    print(f"✅ Pipeline complete! Lineage saved to {LINEAGE_LOG_FILE}")

if __name__ == '__main__':
    main()
```
* **Output:**

- `processing_lineage.json` - Complete transformation history for each image
- `processing_lineage.csv` - Tabular format for Phase 3 integration  
- `processed_webp/` folder containing optimized WebP files ready for WordPress upload
- Complete lineage tracking without requiring local storage of original files

#### **Step 2.3: Lineage Benefits**

This approach provides complete traceability:

- Source tracking: Google Photos API ID and original URL
- Transformation log: Every resize, rotation, format change
- File evolution: Original filename → final WordPress filename
- Quality metrics: File sizes before/after each step
- Error handling: Failed processing tracked with reasons
- Audit trail: Timestamps for compliance and debugging

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
```python
import pandas as pd
import os

def merge_wordpress_lineage():
    # Load Phase 2 lineage data
    lineage_df = pd.read_csv('processing_lineage.csv')
    
    # Load WordPress export data  
    wordpress_df = pd.read_csv('wordpress_urls.csv')  # From your WordPress export
    
    # Create matching keys
    # Assumes WordPress export has 'filename' column
    lineage_df['file_stem'] = lineage_df['final_filename'].apply(
        lambda x: os.path.splitext(x)[0]
    )
    wordpress_df['file_stem'] = wordpress_df['filename'].apply(
        lambda x: os.path.splitext(x)[0] 
    )
    
    # Merge the data
    merged_df = pd.merge(lineage_df, wordpress_df, on='file_stem', how='left')
    
    # Clean up and save
    merged_df.drop(columns=['file_stem'], inplace=True)
    merged_df.to_csv('complete_image_lineage.csv', index=False)
    
    print("✅ WordPress URLs merged with processing lineage")
    print("Output: complete_image_lineage.csv")

if __name__ == '__main__':
    merge_wordpress_lineage()
```
Output:

- All images hosted on WordPress with permanent URLs
- complete_image_lineage.csv - Full lineage from Google Photos through WordPress hosting
- Organized WordPress Media Library for easy management

### ---

**Phase 4: Final Merge and AI Enrichment**

This is the final step where all data comes together.

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
- Develop and test multiple prompt approaches to optimize caption quality: (Note that model won't know who is Ada in the picture if there is more than one person in the picture, I'll have to think about how to deal with that in the prompt)
  - Emotional focus: "Describe Ada's emotional state and the moment's context..."
  - Activity focus: "What is Ada doing in this image and what does it reveal about her personality..."
  - Story integration: "How does this moment fit into Ada's larger journey..." (should I provide an overview of the story for the model to have in context?)
  - Technical description: "Describe the visual elements, setting, and people in this image..."
  - Zero Shot: "Describe this photo in detail."

- Evaluate based on:
  - Emotional accuracy (captures Ada's state/context)
  - Semantic richness (useful for vector search)
  - Consistency with Ada's story tone
  - Cost per image

**Decision criteria:** Choose the model that best balances caption quality with cost-effectiveness for your 1,000+ image scale.

#### **Step 4.2: The Final Enrichment Script**

This master script will merge your data and call the Vertex AI API.

**final\_enrichment.py**

Python

import pandas as pd  
import vertexai  
from vertexai.preview.generative\_models import GenerativeModel, Part

\# \--- Configuration \---  
PROJECT\_ID \= "your-gcp-project-id"  \# Your Google Cloud project ID  
LOCATION \= "us-central1"           \# The GCP region for Vertex AI  
MODEL\_NAME \= "gemini-pro-vision"   \# The generative model for vision tasks

\# \--- Main Logic \---  
def final\_enrich\_data():  
    \# Initialize Vertex AI  
    vertexai.init(project=PROJECT\_ID, location=LOCATION)  
    \# Load the vision model  
    vision\_model \= GenerativeModel(MODEL\_NAME)

    \# Load merged lineage data from Phase 3
    master_df = pd.read_csv('complete_image_lineage.csv')
      
    \# \--- AI Enrichment \---  
    ai\_descriptions \= \[\]  
    print("\\nStarting Vertex AI enrichment...")

    for index, row in master\_df.iterrows():  
        try:  
            wp\_url \= row\['wordpress\_url'\] \# Adjust column name if needed  
            image\_part \= Part.from\_uri(wp\_url, mime\_type="image/webp")  
              
            \# The prompt for the AI model  
            prompt \= "TBD - See Caption Generation Prompt Strategy"  
              
            response \= vision\_model.generate\_content(\[image\_part, prompt\])  
            caption \= response.text.strip()  
              
            ai\_descriptions.append(caption)  
            print(f"  Processed '{row\['original\_filename'\]}' \-\> AI Caption: '{caption}'")  
        except Exception as e:  
            error\_message \= f"ERROR on '{row\['original\_filename'\]}': {e}"  
            print(error\_message)  
            ai\_descriptions.append(error\_message)  
              
    master\_df\['ai\_description'\] \= ai\_descriptions  
      
    \# Clean up and save  
    master\_df.drop(columns=\['file\_stem\_x', 'file\_stem\_y', 'filename'\], inplace=True, errors='ignore')  
    master\_df.to\_csv('FINAL\_MASTER\_DATA.csv', index=False)  
      
    print("\\n\\n--- Process Complete \---")  
    print("Final, unified dataset saved to 'FINAL\_MASTER\_DATA.csv'")

if \_\_name\_\_ \== '\_\_main\_\_':  
    final\_enrich\_data()

* **Output:** A file named **FINAL\_MASTER\_DATA.csv**. This is your final product, a single source of truth containing every piece of information for each photo, ready for you to use in populating your Pinecone database.

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

**Next Steps:** Implement small-scale tests of each approach using your existing 300+ Q&A pairs and a subset of photos to evaluate user experience impact before choosing primary strategy.

**Sources**  
1\. [https://github.com/danielkoh99/SMB-image-gallery](https://github.com/danielkoh99/SMB-image-gallery)  
2\. [https://github.com/leew0nseok/computer-vision](https://github.com/leew0nseok/computer-vision)  
3\. [https://github.com/3La221/Blog](https://github.com/3La221/Blog)