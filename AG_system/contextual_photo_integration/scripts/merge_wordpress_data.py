import pandas as pd
import os
import json
from pathlib import Path
import numpy as np # For NaN

def merge_wordpress_data():
    # Define the base directory relative to the script's location
    base_dir = Path(__file__).resolve().parent.parent

    # Define paths to input and output files
    processing_lineage_json_path = base_dir / 'lineage' / 'processing_lineage.json'
    wordpress_urls_path = base_dir / 'lineage' / 'wordpress_urls.csv'
    output_path = base_dir / 'lineage' / 'complete_image_lineage.csv'

    # Check if we already have an enhanced complete lineage file
    if output_path.exists():
        print("Found existing complete_image_lineage.csv - preserving enhanced data...")
        # Load existing complete lineage to preserve any enhanced columns
        lineage_df = pd.read_csv(output_path)
        print(f"Loaded {len(lineage_df)} records from existing complete lineage")
        existing_columns = lineage_df.columns.tolist()
        enhanced_cols = [col for col in existing_columns if col not in ['filename', 'url', 'wordpress_url_thumbnail', 'normalized_stem']]
        print(f"Preserving enhanced columns: {len(enhanced_cols)} columns including processed_file_md5, takeout metadata, etc.")
    else:
        # Load from JSON as before (first-time run)
        if not processing_lineage_json_path.exists():
            print(f"❌ Error: Input file not found at '{processing_lineage_json_path}'")
            return
        
        with open(processing_lineage_json_path, 'r') as f:
            processing_lineage_data = json.load(f)
        lineage_df = pd.DataFrame(processing_lineage_data)
        print(f"Loaded {len(lineage_df)} records from processing lineage JSON")

    # Check if WordPress URLs file exists
    if not wordpress_urls_path.exists():
        print(f"❌ Error: Input file not found at '{wordpress_urls_path}'")
        return

    # Load wordpress_urls.csv
    wordpress_df = pd.read_csv(wordpress_urls_path)
    
    # Check for the required 'filename' column in wordpress_df
    if 'filename' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'filename' was not found in '{wordpress_urls_path}'.")
        return
    if 'url' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'url' was not found in '{wordpress_urls_path}'.")
        return

    # Normalize keys for merging - UPDATED to handle parentheses and ampersands like WordPress does
    def normalize_key_for_wp(series):
        import re
        
        def normalize_single_string(s):
            if pd.isna(s):
                return s
            # Convert to lowercase
            s = s.lower()
            # Replace special characters with dashes
            s = s.replace('&', '-')
            s = s.replace(' ', '-') 
            s = s.replace('~', '')
            s = s.replace('(', '')
            s = s.replace(')', '')
            # Collapse multiple consecutive dashes into single dash
            s = re.sub(r'-+', '-', s)
            # Remove leading/trailing dashes
            s = s.strip('-')
            return s
        
        # Extract stem (remove extension)
        stems = series.str.rsplit('.', n=1).str[0]
        # Apply normalization to each stem
        return stems.apply(normalize_single_string)

    # Create or update normalized stems
    lineage_df['normalized_stem'] = normalize_key_for_wp(lineage_df['final_filename'])
    wordpress_df['normalized_stem'] = normalize_key_for_wp(wordpress_df['filename'])
    
    # Remove existing WordPress URL columns to avoid conflicts
    wordpress_cols_to_remove = ['filename', 'url', 'wordpress_url_thumbnail']
    for col in wordpress_cols_to_remove:
        if col in lineage_df.columns:
            lineage_df = lineage_df.drop(columns=[col])
    
    # Merge the data on the normalized stem
    merged_df = pd.merge(lineage_df, wordpress_df, on='normalized_stem', how='left', suffixes=('_lineage', '_wp'))

    # Add the new 'wordpress_url_thumbnail' field
    merged_df['wordpress_url_thumbnail'] = np.nan

    for index, row in merged_df.iterrows():
        wp_url = row.get('url', '') # Get from wordpress_df columns
        thumb_status = row.get('thumbnail_generation_status', '') # Get from lineage_df columns

        # Thumbnail URL is derived if WordPress URL for main image exists AND thumbnail generation was successful
        if pd.notna(wp_url) and wp_url and thumb_status in ["success", "success_skipped_existing"]:
            if wp_url.endswith('.webp'):
                # Construct thumbnail URL using the new convention, e.g., -h360-thumb.webp
                thumbnail_url = wp_url[:-5] + "-h360-thumb.webp"
                merged_df.loc[index, 'wordpress_url_thumbnail'] = thumbnail_url
            else:
                # Handle cases where the URL might not end with .webp as expected
                print(f"Warning: WordPress URL '{wp_url}' for stem '{row.get('final_filename')}' does not end with .webp. Cannot derive thumbnail URL.")
                merged_df.loc[index, 'wordpress_url_thumbnail'] = ''
        else:
            merged_df.loc[index, 'wordpress_url_thumbnail'] = ''

    # Save the final output
    merged_df.to_csv(output_path, index=False)
    
    print(f"✅ WordPress data merged and thumbnail URLs generated.")
    print(f"✅ Enhanced data preserved (processed_file_md5, takeout metadata, etc.)")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    merge_wordpress_data()