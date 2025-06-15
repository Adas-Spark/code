import pandas as pd
import os
import json
from pathlib import Path
import numpy as np # For NaN

def merge_wordpress_data():
    # Define the base directory relative to the script's location
    base_dir = Path(__file__).resolve().parent.parent

    # Define paths to input and output files
    # processing_lineage.json is now the source for lineage information
    processing_lineage_json_path = base_dir / 'processing_lineage.json'
    # wordpress_urls.csv remains the source for WordPress URLs
    wordpress_urls_path = base_dir / 'wordpress_urls.csv' # Assuming it's in the base_dir
    # Output file, assuming FINAL_MASTER_DATA.csv is the target
    output_path = base_dir / 'FINAL_MASTER_DATA.csv'

    # Check if input files exist
    if not processing_lineage_json_path.exists():
        print(f"❌ Error: Input file not found at '{processing_lineage_json_path}'")
        return
    if not wordpress_urls_path.exists():
        # If wordpress_urls.csv is optional or might not exist, handle accordingly.
        # For now, let's assume it's required for the merge.
        print(f"❌ Error: Input file not found at '{wordpress_urls_path}'")
        return

    # Load processing_lineage.json
    with open(processing_lineage_json_path, 'r') as f:
        processing_lineage_data = json.load(f)

    # Convert the dictionary to a DataFrame.
    # The keys of the JSON are original stems, which we'll use for merging.
    lineage_df = pd.DataFrame.from_dict(processing_lineage_data, orient='index')
    # Reset index to make the original stem a column for merging
    lineage_df.reset_index(inplace=True)
    lineage_df.rename(columns={'index': 'original_stem'}, inplace=True)

    # Load wordpress_urls.csv
    wordpress_df = pd.read_csv(wordpress_urls_path)
    
    # Check for the required 'filename' column in wordpress_df
    if 'filename' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'filename' was not found in '{wordpress_urls_path}'.")
        return
    if 'wordpress_url' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'wordpress_url' was not found in '{wordpress_urls_path}'.")
        return

    # Normalize keys for merging
    # For lineage_df, 'original_stem' is already suitable if it matches the stems from wordpress_df.
    # Let's assume 'original_stem' from processing_lineage.json (e.g., "image-adasstory")
    # needs to be matched with a stem derived from 'filename' in wordpress_urls.csv.
    
    def normalize_key_for_wp(series):
        # Extracts stem and normalizes: lowercase, replaces spaces with hyphens, removes tildes.
        return series.str.rsplit('.', n=1).str[0].str.lower().str.replace(' ', '-', regex=False).str.replace('~', '', regex=False)

    lineage_df['normalized_stem'] = lineage_df['original_stem'].str.lower().str.replace(' ', '-', regex=False).str.replace('~', '', regex=False)
    wordpress_df['normalized_stem'] = normalize_key_for_wp(wordpress_df['filename'])
    
    # Merge the data on the normalized stem
    # We use 'original_stem' from lineage_df as it's the key from processing_lineage.json
    # and 'normalized_stem' derived from wordpress_df['filename']
    merged_df = pd.merge(lineage_df, wordpress_df, on='normalized_stem', how='left', suffixes=('_lineage', '_wp'))

    # Add the new 'wordpress_url_thumbnail' field
    merged_df['wordpress_url_thumbnail'] = np.nan

    for index, row in merged_df.iterrows():
        wp_url = row.get('wordpress_url', '') # Get from wordpress_df columns
        thumb_status = row.get('thumbnail_generation_status', '') # Get from lineage_df columns

        # Thumbnail URL is derived if WordPress URL for main image exists AND thumbnail generation was successful
        if pd.notna(wp_url) and wp_url and thumb_status in ["success", "success_skipped_existing"]:
            if wp_url.endswith('.webp'):
                # Construct thumbnail URL using the new convention, e.g., -h360-thumb.webp
                # Assuming THUMBNAIL_HEIGHT was 360, as used in generate_thumbnails.py
                thumbnail_url = wp_url[:-5] + "-h360-thumb.webp"
                merged_df.loc[index, 'wordpress_url_thumbnail'] = thumbnail_url
            else:
                # Handle cases where the URL might not end with .webp as expected, or log this
                print(f"Warning: WordPress URL '{wp_url}' for stem '{row.get('original_stem')}' does not end with .webp. Cannot derive thumbnail URL.")
                merged_df.loc[index, 'wordpress_url_thumbnail'] = '' # Or some other placeholder/error indicator
        else:
            merged_df.loc[index, 'wordpress_url_thumbnail'] = ''

    # Clean up helper columns if desired, e.g., 'normalized_stem'
    # 'original_stem_lineage' might be useful to keep.
    # 'filename_wp' is the original filename from wordpress_urls.csv
    # 'wordpress_url' is the main image URL from wordpress_urls.csv
    
    # Select and rename columns for the final output if needed.
    # For example, if 'final_filename' from lineage is desired:
    # merged_df.rename(columns={'final_filename_lineage': 'final_filename'}, inplace=True)

    # Save the final output
    # Ensure output directory exists (base_dir in this case, which should exist)
    merged_df.to_csv(output_path, index=False)
    
    print(f"✅ WordPress data merged and thumbnail URLs generated.")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    merge_wordpress_data()