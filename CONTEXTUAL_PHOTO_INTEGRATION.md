### **Project Overview**

The goal of this project is to take a specific album of approximately 1,000 images from your Google Photos account and transform them into a rich, searchable dataset for your web application.

This process involves four main phases:

1. **Data Extraction:** Programmatically pulling all available metadata (captions, creation dates, permanent links) for each photo from your Google Photos album.  
2. **Image Processing:** Downloading the images, converting them to the optimized WebP format, resizing them for the web, and renaming them with a unique project tag for easy filtering.  
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

**Phase 2: Local Image Processing**

Now you will download the actual image files and prepare them for the web.

#### **Step 2.1: Download Your Album**

Go to your album on the Google Photos website, click the three-dot menu in the top right, and select **"Download all"**. Unzip the resulting .zip file into a folder on your computer. Let's call this folder originals.

#### **Step 2.2: Prepare Your Local Environment**

Install the Python library for image processing from your terminal:  
pip install Pillow

#### **Step 2.3: Convert, Resize, and Rename Images**

Create a new Python script to perform the local processing. This script will read from your originals folder and save the processed files to a new processed\_webp folder.

**process\_local\_images.py**

Python

import os  
from PIL import Image  
import datetime

\# \--- Configuration \---  
SOURCE\_DIRECTORY \= 'originals' \# The folder with your downloaded JPGs  
OUTPUT\_DIRECTORY \= 'processed\_webp' \# The folder where processed WebP files will be saved  
LOG\_FILE \= 'conversion\_log.txt'  
MAX\_DIMENSION \= 1920 \# Max width or height in pixels  
WEBP\_QUALITY \= 85 \# Quality setting from 0 to 100  
FILENAME\_TAG \= '-adasstory' \# Your unique project tag

\# \--- Main Logic \---  
if not os.path.exists(OUTPUT\_DIRECTORY):  
    os.makedirs(OUTPUT\_DIRECTORY)

log\_entries \= \[\]

print(f"Starting image processing from '{SOURCE\_DIRECTORY}'...")

for filename in os.listdir(SOURCE\_DIRECTORY):  
    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):  
        try:  
            source\_path \= os.path.join(SOURCE\_DIRECTORY, filename)  
            img \= Image.open(source\_path)

            \# Preserve orientation info if it exists  
            if hasattr(img, '\_getexif'):  
                exif \= img.\_getexif()  
                if exif:  
                    orientation\_key \= 274 \# EXIF tag for orientation  
                    if orientation\_key in exif:  
                        orientation \= exif\[orientation\_key\]  
                        \# Rotate image based on orientation tag  
                        if orientation \== 3: img \= img.rotate(180, expand=True)  
                        elif orientation \== 6: img \= img.rotate(270, expand=True)  
                        elif orientation \== 8: img \= img.rotate(90, expand=True)

            \# Resize the image while maintaining aspect ratio  
            img.thumbnail((MAX\_DIMENSION, MAX\_DIMENSION))

            \# Construct the new filename  
            file\_stem \= os.path.splitext(filename)\[0\]  
            new\_filename \= f"{file\_stem}{FILENAME\_TAG}.webp"  
            output\_path \= os.path.join(OUTPUT\_DIRECTORY, new\_filename)

            \# Save as WebP  
            img.save(output\_path, 'webp', quality=WEBP\_QUALITY)  
              
            log\_message \= f"SUCCESS: Converted '{filename}' \-\> '{new\_filename}'"  
            print(log\_message)  
            log\_entries.append(log\_message)

        except Exception as e:  
            error\_message \= f"ERROR: Failed to convert '{filename}'. Reason: {e}"  
            print(error\_message)  
            log\_entries.append(error\_message)

\# Write the log file  
with open(LOG\_FILE, 'w') as f:  
    f.write(f"--- Image Conversion Log \- {datetime.datetime.now()} \---\\n")  
    for entry in log\_entries:  
        f.write(entry \+ '\\n')

print(f"\\nProcessing complete. Log saved to '{LOG\_FILE}'.")

* **Output:** A new folder named **processed\_webp** containing your optimized images, and a **conversion\_log.txt** file.

### ---

**Phase 3: WordPress Hosting**

Now, let's get your optimized images onto your website.

#### **Step 3.1: Organize Your Media Library (Recommended)**

Before you upload, log in to WordPress and install a **Media Library Folders plugin** (like Filebird). Create a new folder named "ADAS Story Project" or similar. This will keep your new images neatly organized and separate from your other media.

#### **Step 3.2: Upload Processed Images**

Navigate to your new folder in the Media Library and bulk upload all the .webp files from your local processed\_webp folder.

#### **Step 3.3: Export WordPress URLs**

Use your "Export Media Library" plugin to export the data for your new uploads. It's often easiest to filter the export to show only images uploaded today to isolate your new files.

* **Output:** A CSV file named **wordpress\_urls.csv**. It should contain at least the filename (e.g., my-photo-adasstory.webp) and the permanent URL.

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

    \# Load source data  
    google\_df \= pd.read\_csv('google\_data.csv')  
    wordpress\_df \= pd.read\_csv('wordpress\_urls.csv')

    \# \--- Prepare for Merge \---  
    \# Create a clean 'stem' column in both dataframes to merge on  
    \# Example: 'IMG\_1234.JPG' \-\> 'IMG\_1234'  
    google\_df\['file\_stem'\] \= google\_df\['original\_filename'\].apply(lambda x: os.path.splitext(x)\[0\])  
    \# Example: 'IMG\_1234-adasstory.webp' \-\> 'IMG\_1234'  
    wordpress\_df\['file\_stem'\] \= wordpress\_df\['filename'\].apply(lambda x: os.path.splitext(x)\[0\].replace('-adasstory', ''))  
      
    \# Merge the dataframes  
    master\_df \= pd.merge(google\_df, wordpress\_df, on='file\_stem', how='left')  
      
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