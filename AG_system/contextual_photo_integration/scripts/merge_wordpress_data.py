import pandas as pd
import os
from pathlib import Path

def merge_wordpress_data():
    # Define the directory where all data files are located
    lineage_dir = Path('lineage')

    # Define paths to input and output files using the lineage_dir
    processing_lineage_path = lineage_dir / 'processing_lineage.csv'
    wordpress_urls_path = lineage_dir / 'wordpress_urls.csv'
    output_path = lineage_dir / 'complete_image_lineage.csv'

    # Check if input files exist
    if not processing_lineage_path.exists():
        print(f"❌ Error: Input file not found at '{processing_lineage_path}'")
        return
    if not wordpress_urls_path.exists():
        print(f"❌ Error: Input file not found at '{wordpress_urls_path}'")
        return

    # Load the data using the full path variables
    lineage_df = pd.read_csv(processing_lineage_path)
    wordpress_df = pd.read_csv(wordpress_urls_path)
    
    # Check for the required 'filename' column
    if 'filename' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'filename' was not found in '{wordpress_urls_path}'.")
        return

    # This function now perfectly mimics WordPress's "slugify" behavior
    # by lowercasing, replacing spaces with hyphens, and REMOVING tildes.
    def normalize_key(series):
        return series.str.lower().str.replace(' ', '-', regex=False).str.replace('~', '', regex=False)

    # Create the original file stems
    lineage_df['file_stem'] = lineage_df['final_filename'].apply(lambda x: os.path.splitext(x)[0])
    wordpress_df['file_stem'] = wordpress_df['filename'].apply(lambda x: os.path.splitext(x)[0])

    # Create new, fully normalized columns to merge on
    lineage_df['normalized_stem'] = normalize_key(lineage_df['file_stem'])
    wordpress_df['normalized_stem'] = normalize_key(wordpress_df['file_stem'])
    
    # Merge the data on the new, robust normalized key
    merged_df = pd.merge(lineage_df, wordpress_df, on='normalized_stem', how='left', suffixes=('_proc', '_wp'))
    
    # Clean up all temporary helper columns
    merged_df.drop(columns=['file_stem_proc', 'file_stem_wp', 'normalized_stem'], inplace=True)
    # --- END FINAL FIX ---
    
    # Save the final output to the lineage directory
    merged_df.to_csv(output_path, index=False)
    
    print("✅ WordPress URLs merged with processing lineage")
    print(f"Output: {output_path}")

if __name__ == '__main__':
    merge_wordpress_data()