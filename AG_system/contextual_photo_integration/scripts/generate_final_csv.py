import json
import pandas as pd
import os

# Define file paths
# The script is in AG_system/contextual_photo_integration/scripts/
# Input JSON is in AG_system/contextual_photo_integration/lineage/
# Output CSV should be in AG_system/contextual_photo_integration/

# Correctly determine the base path to go one level up from 'scripts'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR) # This should be AG_system/contextual_photo_integration/

INPUT_JSON_PATH = os.path.join(BASE_DIR, 'lineage', 'image_caption_experiments.json')
OUTPUT_CSV_PATH = os.path.join(BASE_DIR, 'FINAL_MASTER_DATA.csv')

def create_master_csv():
    """
    Loads image caption experiment data from a JSON file,
    flattens the structure, and saves it as a CSV file.
    """
    # Check if input JSON file exists
    if not os.path.exists(INPUT_JSON_PATH):
        print(f"Error: Input JSON file not found at {INPUT_JSON_PATH}")
        return

    # Load JSON data
    try:
        with open(INPUT_JSON_PATH, 'r') as f:
            data = json.load(f)
        print(f"Successfully loaded data from {INPUT_JSON_PATH}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {INPUT_JSON_PATH}. File might be corrupted.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while loading JSON: {e}")
        return

    if not data:
        print("Input JSON data is empty. No CSV will be generated.")
        # Optionally, create an empty CSV with headers if desired
        # pd.DataFrame([]).to_csv(OUTPUT_CSV_PATH, index=False)
        return

    all_rows_for_csv = []

    # Process data and flatten structure
    for image_data_entry in data:
        lineage_data = image_data_entry.get('lineage_data', {})

        if not image_data_entry.get('caption_experiments'):
            # Handle cases where an image might have no experiments (e.g., skipped due to URL error)
            # Create a row with lineage data and empty caption fields if desired
            # For now, we only create rows if there are experiments.
            print(f"Image {image_data_entry.get('image_identifier', 'Unknown')} has no caption experiments. Skipping.")
            continue

        for experiment in image_data_entry['caption_experiments']:
            row_for_csv = lineage_data.copy()  # Start with lineage data

            # Add/overwrite fields from the experiment
            row_for_csv['prompt_id'] = experiment.get('prompt_id')
            row_for_csv['prompt_text'] = experiment.get('prompt_text')
            row_for_csv['ai_description'] = experiment.get('generated_caption') # Renamed
            row_for_csv['caption_model_used'] = experiment.get('model_used')
            row_for_csv['caption_timestamp'] = experiment.get('timestamp')
            row_for_csv['caption_selected'] = experiment.get('selected', False) # Default to False if missing
            row_for_csv['caption_error'] = experiment.get('error', None) # Safely get 'error'

            all_rows_for_csv.append(row_for_csv)

    if not all_rows_for_csv:
        print("No data rows were processed to create the CSV. Output file will not be created.")
        return

    # Create Pandas DataFrame
    try:
        master_df = pd.DataFrame(all_rows_for_csv)
        print(f"Successfully created DataFrame with {len(master_df)} rows.")
    except Exception as e:
        print(f"Error creating DataFrame: {e}")
        return

    # Save to CSV
    try:
        master_df.to_csv(OUTPUT_CSV_PATH, index=False)
        print(f"Successfully saved final master data to {OUTPUT_CSV_PATH}")
    except Exception as e:
        print(f"Error saving DataFrame to CSV: {e}")
        return

if __name__ == '__main__':
    create_master_csv()
