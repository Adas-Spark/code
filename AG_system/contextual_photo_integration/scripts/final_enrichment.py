import pandas as pd
from pathlib import Path
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
from datetime import datetime, timedelta
import json

# --- Configuration ---
PROJECT_ID = "your-gcp-project-id"  # Your Google Cloud project ID
LOCATION = "us-central1"           # The GCP region for Vertex AI
MODEL_NAME = "gemini-pro-vision"   # The generative model for vision tasks

INCLUDE_ADA_CONTEXT = True  # Flag to control Ada's context inclusion
DAYS_WINDOW = 14            # Window for checking "nearness" to important dates
IMPORTANT_DATES_STR = {
    "birth": "2018-06-08",
    "diagnosis": "2022-05-05",
    "transplant": "2022-09-13",
    "death": "2023-07-22"
}

ADA_CONTEXT = """This image is from Ada's story - a brave 5-year-old girl who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. It is possible that some photos have the incorrect date. When describing, be sensitive to the medical journey while celebrating moments of joy and connection."""

PROMPTS_TO_TEST = {
    "EMOTIONAL": "Describe the emotional moment and feelings in this image of a young girl's journey",
    "MOMENT": "A brief, poetic description of the emotional moment or action (15-20 words) Focus on: what's happening, the feeling, the discovery, the connection Example: \"The wonder of discovering a butterfly on a sunny afternoon\"",
    "CONTEXTUAL": "What story does this moment tell about Ada's character, relationships, or journey? Focus on the emotions, interactions, and personality traits visible in this scene.",
    "STORY": "Describe the story this image tells about Ada's life and spirit. What does this moment reveal about her personality, her relationships, or her approach to challenges?",
    "CHARACTER": "What character traits, emotions, or relationships are evident in this image? Describe Ada's spirit and personality as shown in this moment."
}
--- Main Logic ---
def final_enrich_data():
    base_dir = Path(__file__).resolve().parent.parent

    # --- Input/Output Configuration ---
    input_csv_name = 'complete_image_lineage.csv'
    input_csv_path = base_dir / 'lineage' / input_csv_name
    # output_csv_path is defined later before saving

    # Initialize Vertex AI
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Load the vision model
    vision_model = GenerativeModel(MODEL_NAME)
    # Load merged lineage data
    master_df = pd.read_csv(input_csv_path)

    # Convert IMPORTANT_DATES_STR to datetime objects
    IMPORTANT_DATES_DT = {name: datetime.fromisoformat(date_str) for name, date_str in IMPORTANT_DATES_STR.items()}
  
# --- AI Enrichment ---  
    all_output_records = []
print("\nStarting Vertex AI enrichment...")

for index, row in master_df.iterrows():  
    try:  
        wp_url = row['url'] # WordPress URL of the image
        actual_photo_time_str = row.get('creation_date')
        actual_photo_dt = None

        if actual_photo_time_str and isinstance(actual_photo_time_str, str):
            if "_fallback_mtime" in actual_photo_time_str:
                actual_photo_time_str = actual_photo_time_str.replace("_fallback_mtime", "")
            try:
                actual_photo_dt = datetime.fromisoformat(actual_photo_time_str)
            except ValueError:
                print(f"Warning: Could not parse date string '{actual_photo_time_str}' for {row['original_filename']}")
                actual_photo_dt = None

        current_prompts = PROMPTS_TO_TEST.copy() # Use .copy() for mutable dicts if modified per item

        if actual_photo_dt:
            for date_name, important_date_dt in IMPORTANT_DATES_DT.items():
                if abs((actual_photo_dt - important_date_dt).days) <= DAYS_WINDOW:
                    date_proximity_notice = " If the actual_photo_time is near an important date, tastefully and with respect weave that into your response."
                    for key in ['CONTEXTUAL', 'STORY', 'CHARACTER']:
                        if key in current_prompts:
                             current_prompts[key] += date_proximity_notice
                    break # Found a nearby date, no need to check others

        api_prompt_text = ""
        if INCLUDE_ADA_CONTEXT:
            api_prompt_text += ADA_CONTEXT + "\n\n"

        api_prompt_text += f"Generate captions for this image using each of these prompts: {json.dumps(current_prompts)}\n\nFormat your response as valid JSON: {{ \"EMOTIONAL\": \"[your description]\", \"MOMENT\": \"[your description]\", \"CONTEXTUAL\": \"[your description]\", \"STORY\": \"[your description]\", \"CHARACTER\": \"[your description]\" }}"

        image_part = Part.from_uri(wp_url, mime_type="image/webp")  

        response = vision_model.generate_content([image_part, api_prompt_text])
        parsed_captions = json.loads(response.text.strip())

        try:
            tokens_used = response.usage_metadata.total_token_count
        except AttributeError:
            tokens_used = 'N/A'

        for prompt_key, answer in parsed_captions.items():
            output_record = {
                "image_url": wp_url,
                "original_filename": row.get('original_filename', 'N/A'),
                "model_used": MODEL_NAME,
                "tokens_used": tokens_used,
                "prompt_name": prompt_key,
                "prompt_answer": answer,
                "photo_taken_time": actual_photo_time_str if actual_photo_dt else 'N/A', # Use string version, or N/A if parsing failed
                "ada_context_included": INCLUDE_ADA_CONTEXT
            }
            all_output_records.append(output_record)

        print(f"  Successfully processed '{row.get('original_filename', 'N/A')}'")

    except Exception as e:  
        error_message = f"ERROR on '{row.get('original_filename', 'N/A')}': {e}"
        print(error_message)
        output_record = {
            "image_url": wp_url,
            "original_filename": row.get('original_filename', 'N/A'),
            "model_used": MODEL_NAME,
            "tokens_used": 'N/A',
            "prompt_name": 'ERROR',
            "prompt_answer": error_message,
            "photo_taken_time": actual_photo_time_str if actual_photo_dt else 'N/A', # Use string version, or N/A if parsing failed
            "ada_context_included": INCLUDE_ADA_CONTEXT
        }
        all_output_records.append(output_record)
  
# Save the output
    output_df = pd.DataFrame(all_output_records)
    output_csv_path = base_dir / 'lineage' / 'multi_prompt_enrichment_output.csv'
    output_df.to_csv(output_csv_path, index=False)
  
    print("\n\n--- Process Complete ---")
    print(f"Enrichment output saved to '{output_csv_path}'")

if __name__ == '__main__':
    final_enrich_data()