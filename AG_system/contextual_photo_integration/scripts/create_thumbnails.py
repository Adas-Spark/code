import os
import pandas as pd
from pathlib import Path
from PIL import Image

# =======================================================================
# IMPORTANT NOTE: UNTESTED SCRIPT
# This script has been code-generated and reviewed, but it has NOT been
# run in a live environment with actual data.
# THOROUGH TESTING IS REQUIRED before relying on its output.
# Key areas to test:
#   - Correct loading and parsing of processing_lineage.csv.
#   - Accurate path construction for source and thumbnail images.
#   - Successful thumbnail generation to the specified dimensions.
#   - Correct population of new thumbnail-related columns in the CSV.
#   - Statefulness (skipping already processed items on re-runs).
#   - Error handling for missing files or corrupted images.
# =======================================================================

# Constants
THUMBNAIL_HEIGHT = 360
LINEAGE_DIR_NAME = "lineage"
PROCESSED_LINEAGE_FILENAME = "processing_lineage.csv"
SOURCE_WEBP_DIR_NAME = "processed_webp"
THUMBNAIL_OUTPUT_DIR_NAME = "processed_webp_thumbnails"
THUMBNAIL_SUFFIX = "-thumb.webp"

def main():
    # Construct paths
    script_path = Path(__file__).resolve()
    parent_dir = script_path.parent.parent  # AG_system/contextual_photo_integration/

    lineage_dir = parent_dir / LINEAGE_DIR_NAME
    input_csv_path = lineage_dir / PROCESSED_LINEAGE_FILENAME
    source_webp_dir = parent_dir / SOURCE_WEBP_DIR_NAME
    thumbnail_output_dir = parent_dir / THUMBNAIL_OUTPUT_DIR_NAME

    # Create thumbnail output directory
    os.makedirs(thumbnail_output_dir, exist_ok=True)
    print(f"Thumbnail output directory: {thumbnail_output_dir}")

    # Check if input CSV exists
    if not input_csv_path.exists():
        print(f"Error: Input CSV file not found at {input_csv_path}")
        return

    print(f"Loading CSV from: {input_csv_path}")
    df = pd.read_csv(input_csv_path)

    # Initialize new thumbnail-related columns if they don't exist
    thumbnail_columns = {
        'thumbnail_final_filename': None,
        'thumbnail_processed_path': None,
        'thumbnail_width': None,
        'thumbnail_height': None,
        'thumbnail_file_size_bytes': None,
        'thumbnail_generation_status': '', # empty string for not processed yet
        'thumbnail_error_message': ''
    }

    for col, default_value in thumbnail_columns.items():
        if col not in df.columns:
            df[col] = default_value
            if default_value is None and col in ['thumbnail_width', 'thumbnail_height', 'thumbnail_file_size_bytes']:
                 df[col] = pd.NA # Use pd.NA for numeric types for better pandas handling
            elif default_value is None:
                 df[col] = ''


    processed_count = 0
    skipped_count = 0
    error_count = 0

    print("\n" + "="*60)
    print("IMPORTANT: This script (`create_thumbnails.py`) is UNTESTED.")
    print("Please verify its output carefully after the first run.")
    print("="*60 + "\n")

    print(f"Starting thumbnail generation for {len(df)} entries...")

    for index, row in df.iterrows():
        try:
            # Get source WebP image details
            source_processed_file_path_str = row.get('processed_file_path', '')
            source_final_filename = row.get('final_filename', '')

            # Handle potential NaN or empty values for path
            if pd.isna(source_processed_file_path_str) or not source_processed_file_path_str:
                source_processed_file_path_str = '' # Ensure it's a string for Path object

            if not source_final_filename: # Should ideally not happen if CSV is clean
                print(f"Row {index}: Skipping due to missing 'final_filename'.")
                df.loc[index, 'thumbnail_generation_status'] = 'error_missing_data'
                df.loc[index, 'thumbnail_error_message'] = "Missing 'final_filename' in source CSV row."
                error_count += 1
                continue

            # Check thumbnail_generation_status
            if row.get('thumbnail_generation_status') == 'completed':
                print(f"Row {index}: Thumbnail for '{source_final_filename}' already marked as 'completed'. Skipping.")
                skipped_count += 1
                continue

            # Construct expected thumbnail filename
            source_path_obj = Path(source_final_filename)
            thumbnail_filename = f"{source_path_obj.stem}{THUMBNAIL_SUFFIX}"
            thumbnail_full_output_path = thumbnail_output_dir / thumbnail_filename

            # Construct full source path
            # The 'processed_file_path' in CSV is expected to be relative to 'source_webp_dir' or absolute
            # For robustness, let's assume it's either absolute or relative to the parent_dir/SOURCE_WEBP_DIR_NAME
            if not source_processed_file_path_str: # if empty after initial check
                 full_source_webp_path = source_webp_dir / source_final_filename
            else:
                path_from_csv = Path(source_processed_file_path_str)
                if path_from_csv.is_absolute():
                    full_source_webp_path = path_from_csv
                else:
                    # This assumes processed_file_path is like "processed_webp/image.webp"
                    # and we want to ensure it's correctly joined with the base source_webp_dir
                    # If it already contains SOURCE_WEBP_DIR_NAME, Path should handle it.
                    # If it's just the filename, it will be joined.
                    full_source_webp_path = source_webp_dir / path_from_csv.name


            print(f"Row {index}: Processing '{source_final_filename}'. Source: '{full_source_webp_path}'")

            if not full_source_webp_path.exists():
                print(f"Row {index}: Source WebP file not found at '{full_source_webp_path}'.")
                df.loc[index, 'thumbnail_generation_status'] = 'error_source_missing'
                df.loc[index, 'thumbnail_error_message'] = f"Source file not found: {full_source_webp_path}"
                error_count += 1
                continue

            # Image Processing
            try:
                img = Image.open(str(full_source_webp_path))
                original_width, original_height = img.size

                if original_height == 0: # Avoid division by zero
                    raise ValueError("Original image height is zero.")

                new_width = int((original_width / original_height) * THUMBNAIL_HEIGHT)
                if new_width == 0: # Ensure minimum width of 1px for safety
                    new_width = 1

                resized_img = img.resize((new_width, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)

                # Ensure the image mode is compatible with WebP saving if it's not already
                if resized_img.mode not in ['RGB', 'RGBA']:
                    print(f"Row {index}: Converting image from mode {resized_img.mode} to RGB for WebP saving.")
                    resized_img = resized_img.convert('RGB')

                resized_img.save(str(thumbnail_full_output_path), 'WEBP')
                thumbnail_file_size = os.path.getsize(str(thumbnail_full_output_path))

                # Update DataFrame
                df.loc[index, 'thumbnail_final_filename'] = thumbnail_filename
                df.loc[index, 'thumbnail_processed_path'] = str(thumbnail_full_output_path.relative_to(parent_dir))
                df.loc[index, 'thumbnail_width'] = new_width
                df.loc[index, 'thumbnail_height'] = THUMBNAIL_HEIGHT
                df.loc[index, 'thumbnail_file_size_bytes'] = thumbnail_file_size
                df.loc[index, 'thumbnail_generation_status'] = 'completed'
                df.loc[index, 'thumbnail_error_message'] = ''

                print(f"Row {index}: Successfully created thumbnail '{thumbnail_filename}' ({new_width}x{THUMBNAIL_HEIGHT}).")
                processed_count += 1

            except Exception as e:
                print(f"Row {index}: Error processing image '{source_final_filename}': {e}")
                df.loc[index, 'thumbnail_generation_status'] = 'error_generating'
                df.loc[index, 'thumbnail_error_message'] = str(e)
                error_count += 1
                # Do not delete thumbnail_full_output_path if it exists but was partial/corrupt
                # The next run might re-process or it can be manually checked.

        except Exception as outer_e: # Catch errors in row processing logic itself
            print(f"Row {index}: Critical error processing row: {outer_e}")
            # Ensure some status is set if not already
            if pd.isna(df.loc[index, 'thumbnail_generation_status']) or not df.loc[index, 'thumbnail_generation_status']:
                 df.loc[index, 'thumbnail_generation_status'] = 'error_processing_row'
            df.loc[index, 'thumbnail_error_message'] = df.loc[index, 'thumbnail_error_message'] + f" | Outer error: {str(outer_e)}"
            error_count +=1


    # Save the updated DataFrame
    try:
        df.to_csv(input_csv_path, index=False)
        print(f"\nUpdated CSV saved to: {input_csv_path}")
    except Exception as e:
        print(f"\nError saving updated CSV to {input_csv_path}: {e}")
        print("Please check file permissions or disk space.")

    # Print summary
    print("\n--- Thumbnail Generation Summary ---")
    print(f"Total entries in CSV: {len(df)}")
    print(f"Successfully processed: {processed_count}")
    print(f"Skipped (already completed): {skipped_count}")
    print(f"Failed (errors): {error_count}")
    print("----------------------------------")

if __name__ == '__main__':
    main()
