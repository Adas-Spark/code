import argparse
import json
import pandas as pd
# import vertexai
# from vertexai.preview.generative_models import GenerativeModel, Part

# --- Ada's Context and Prompts ---
ADA_CONTEXT = """This image is from Ada's story - a brave 5-year-old girl
who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. It is possible that some photos have the incorrect date. When describing, be sensitive to the medical journey while celebrating moments of joy and connection."""

PROMPTS = {
    "emotional": "Describe the emotional moment and feelings in this image of a young girl's journey",
    "MOMENT": """A brief, poetic description of the emotional moment or action (15-20 words)
   Focus on: what's happening, the feeling, the discovery, the connection
   Example: "The wonder of discovering a butterfly on a sunny afternoon\"""",
    "CONTEXT": "What story does this moment tell about Ada's character, relationships, or journey? Focus on the emotions, interactions, and personality traits visible in this scene.",
    "STORY": "Describe the story this image tells about Ada's life and spirit. What does this moment reveal about her personality, her relationships, or her approach to challenges?",
    "CHARACTER": "What character traits, emotions, or relationships are evident in this image? Describe Ada's spirit and personality as shown in this moment."
}

def construct_final_prompt(prompts_dict, include_ada_context):
    prompt_lines = []
    instruction = "Generate captions for this image using each of these prompts:"

    if include_ada_context:
        prompt_lines.append(ADA_CONTEXT)
        prompt_lines.append("\n") # Add a newline for separation

    prompt_lines.append(instruction)
    prompt_lines.append("\n") # Add a newline

    for key, value in prompts_dict.items():
        prompt_lines.append(f'"{key}": "{value}"')

    prompt_lines.append("\n") # Add a newline
    prompt_lines.append("Format your response as valid JSON:")
    prompt_lines.append("{")
    for key in prompts_dict.keys():
        prompt_lines.append(f'     "{key}": "[your description]",')
    # Remove trailing comma from the last item if any prompts exist
    if prompts_dict:
        prompt_lines[-1] = prompt_lines[-1].rstrip(',')
    prompt_lines.append("}")

    return "\n".join(prompt_lines)

# --- Configuration ---
PROJECT_ID = "your-gcp-project-id"  # Your Google Cloud project ID
LOCATION = "us-central1"           # The GCP region for Vertex AI
MODEL_NAME = "gemini-pro-vision"   # The generative model for vision tasks

# --- Main Logic ---
def final_enrich_data(use_ada_context_flag):
    print(f"--- Script Configuration ---")
    print(f"PROJECT_ID: {PROJECT_ID}")
    print(f"LOCATION: {LOCATION}")
    print(f"MODEL_NAME: {MODEL_NAME}")
    print(f"ADA_CONTEXT: {ADA_CONTEXT[:100]}...") # Print first 100 chars
    print(f"PROMPTS: {PROMPTS}")
    print(f"Using Ada Context Flag: {use_ada_context_flag}")
    print("--- Starting Processing ---")
# Initialize Vertex AI
# vertexai.init(project=PROJECT_ID, location=LOCATION)
# Load the vision model
# vision_model = GenerativeModel(MODEL_NAME)
# Load merged lineage data from Phase 3
    master_df = pd.read_csv('complete_image_lineage.csv')
  
    # --- AI Enrichment ---
    output_records = []
    print("\nStarting Vertex AI enrichment...")

    for index, row in master_df.iterrows():
        try:
            wp_url = row['url'] # Adjust column name if needed
            # image_part = Part.from_uri(wp_url, mime_type="image/webp") # Commented out for test

            current_prompt_text_for_api = construct_final_prompt(PROMPTS, use_ada_context_flag)

            # response = vision_model.generate_content([image_part, current_prompt_text_for_api]) # Commented out for test

            print(f"\nProcessing image: {row.get('original_filename', wp_url)}")
            print(f"Constructed API Prompt:\n{current_prompt_text_for_api}")

            # Simulate API response
            simulated_response_text = ""
            if "image1" in row.get('original_filename', ''):
                simulated_response_text = '''
                {
                     "emotional": "Simulated emotional description for image1.",
                     "MOMENT": "Simulated moment for image1.",
                     "CONTEXT": "Simulated context for image1.",
                     "STORY": "Simulated story for image1.",
                     "CHARACTER": "Simulated character for image1."
                }
                '''
            else: # For image2 or any other
                simulated_response_text = '''
                {
                     "emotional": "A different emotional take for image2.",
                     "MOMENT": "A fleeting moment captured in image2.",
                     "CONTEXT": "The broader context of image2's scene.",
                     "STORY": "The narrative image2 conveys.",
                     "CHARACTER": "Traits observed in image2."
                }
                '''
            print(f"Simulated API Response Text:\n{simulated_response_text.strip()}")

            class MockResponse: # Helper class to mimic actual response object
                def __init__(self, text):
                    self.text = text

            response = MockResponse(simulated_response_text) # Use simulated response

            # Attempt to parse the JSON response
            try:
                parsed_answers = json.loads(response.text.strip())
                for prompt_key, prompt_text_template in PROMPTS.items():
                    answer = parsed_answers.get(prompt_key, "Error: Prompt key not found in response")

                    record = {
                        'image_identifier': row.get('original_filename', wp_url), # Prioritize original_filename
                        'model_used': MODEL_NAME,
                        'tokens_used': 'N/A', # As per plan
                        'prompt_key': prompt_key,
                        'prompt_text': prompt_text_template, # Store the template
                        'answer': answer
                    }
                    output_records.append(record)
                print(f"  Successfully processed '{row.get('original_filename', wp_url)}' for all prompts.")

            except json.JSONDecodeError as json_e:
                print(f"  ERROR: JSONDecodeError for '{row.get('original_filename', wp_url)}': {json_e}. Response text: {response.text.strip()}")
                # Record a single error entry for this image if JSON parsing fails
                record = {
                    'image_identifier': row.get('original_filename', wp_url),
                    'model_used': MODEL_NAME,
                    'tokens_used': 'N/A',
                    'prompt_key': 'json_parsing_error',
                    'prompt_text': current_prompt_text_for_api, # Store the full prompt sent
                    'answer': f"JSONDecodeError: {json_e}. Raw response: {response.text.strip()}"
                }
                output_records.append(record)

        except Exception as e:
            error_message = f"ERROR during API call or general processing for '{row.get('original_filename', wp_url)}': {e}"
            print(error_message)
            # Record a single error entry for this image for other exceptions
            record = {
                'image_identifier': row.get('original_filename', wp_url),
                'model_used': MODEL_NAME,
                'tokens_used': 'N/A',
                'prompt_key': 'general_api_error',
                'prompt_text': "N/A - Error before/during API call",
                'answer': error_message
            }
            # If current_prompt_text_for_api was defined, use it
            if 'current_prompt_text_for_api' in locals():
                 record['prompt_text'] = current_prompt_text_for_api
            output_records.append(record)

    # Create DataFrame from the collected records
    output_df = pd.DataFrame(output_records)

    # Save the new DataFrame
    output_df.to_csv('FINAL_MASTER_DATA.csv', index=False)
  
    print("\n\n--- Process Complete ---")
    print("Final, unified dataset saved to 'FINAL_MASTER_DATA.csv'")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Enrich image data with AI-generated captions using multiple prompts.")
    parser.add_argument(
        '--use_ada_context',
        action='store_true',
        help="Include Ada's context at the beginning of the API prompt."
    )
    args = parser.parse_args()

    final_enrich_data(args.use_ada_context)