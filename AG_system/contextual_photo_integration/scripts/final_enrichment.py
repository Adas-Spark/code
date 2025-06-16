import pandas as pd
import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import json
import datetime
import os

# --- Configuration ---
PROJECT_ID = "your-gcp-project-id"  # IMPORTANT: Your Google Cloud project ID - set this correctly!
LOCATION = "us-central1"           # The GCP region for Vertex AI
MODEL_NAME = "gemini-pro-vision"   # The generative model for vision tasks
INPUT_CSV = 'complete_image_lineage.csv'
OUTPUT_JSON = 'lineage/image_caption_experiments.json'

# --- Main Logic ---
def final_enrich_data():
    # Initialize Vertex AI
    # Ensure PROJECT_ID is set before running.
    if PROJECT_ID == "your-gcp-project-id":
        print("ERROR: PROJECT_ID is not set. Please set your Google Cloud project ID in the script.")
        return

    vertexai.init(project=PROJECT_ID, location=LOCATION)
    # Load the vision model
    vision_model = GenerativeModel(MODEL_NAME)

    # Define prompts
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

    # Load merged lineage data
    if not os.path.exists(INPUT_CSV):
        print(f"ERROR: Input file '{INPUT_CSV}' not found. Please ensure the file exists in the correct location.")
        return
    master_df = pd.read_csv(INPUT_CSV)

    all_images_caption_data = []
    print(f"\nStarting Vertex AI enrichment for {len(master_df)} images using {len(prompts_to_test)} prompts each...")

    for index, row in master_df.iterrows():
        image_identifier = row.get('wordpress_url', row.get('original_filename', f"unknown_image_{index}"))
        print(f"\nProcessing image: {image_identifier} ({index + 1}/{len(master_df)})")

        image_data_entry = {
            "image_identifier": image_identifier,
            "lineage_data": dict(row),
            "caption_experiments": []
        }

        wp_url = row.get('wordpress_url')
        if not wp_url or pd.isna(wp_url):
            print(f"  Skipping image {image_identifier} due to missing 'wordpress_url'.")
            # If we want to include images even if they can't be processed, append here:
            # image_data_entry["caption_experiments"].append({
            #     "prompt_id": "N/A", "error": "Missing wordpress_url",
            #     "timestamp": datetime.datetime.now().isoformat()
            # })
            # all_images_caption_data.append(image_data_entry)
            continue # Skip to next image if no URL to process

        try:
            # Assuming image_part needs to be valid for any prompt to work.
            image_part = Part.from_uri(wp_url, mime_type="image/webp")
        except Exception as e:
            print(f"  ERROR creating image part for {image_identifier} from URL {wp_url}: {e}")
            # Add entry with error for this image, as it affects all prompts
            for prompt_info in prompts_to_test:
                 image_data_entry['caption_experiments'].append({
                    "prompt_id": prompt_info['prompt_id'],
                    "prompt_text": prompt_info['prompt_text'],
                    "generated_caption": "Error: Could not load image part.",
                    "model_used": MODEL_NAME,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "selected": False,
                    "error": str(e)
                })
            all_images_caption_data.append(image_data_entry)
            continue # Skip to next image

        for prompt_info in prompts_to_test:
            prompt_id = prompt_info['prompt_id']
            prompt_text = prompt_info['prompt_text']
            print(f"  Testing prompt: {prompt_id}")

            experiment_result = {
                "prompt_id": prompt_id,
                "prompt_text": prompt_text,
                "generated_caption": None,
                "model_used": MODEL_NAME,
                "timestamp": datetime.datetime.now().isoformat(),
                "selected": False,
                "error": None
            }

            try:
                response = vision_model.generate_content([image_part, prompt_text])
                experiment_result["generated_caption"] = response.text.strip()
                print(f"    Successfully generated caption for prompt {prompt_id}")
            except Exception as e:
                error_message = f"API ERROR for prompt '{prompt_id}' on '{image_identifier}': {e}"
                print(f"    {error_message}")
                experiment_result["error"] = str(e)
                experiment_result["generated_caption"] = "Error during generation."

            image_data_entry['caption_experiments'].append(experiment_result)

        all_images_caption_data.append(image_data_entry)
          
    # Save all experiment data to JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True) # Ensure 'lineage' directory exists
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(all_images_caption_data, f, indent=4)

    print("\n\n--- Process Complete ---")
    print(f"All caption experiments saved to {OUTPUT_JSON}")
    print(f"Reminder: Ensure PROJECT_ID ('{PROJECT_ID}') is correctly set for Vertex AI functionality if you haven't already.")

if __name__ == '__main__':
    final_enrich_data()