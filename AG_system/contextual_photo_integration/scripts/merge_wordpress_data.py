import pandas as pd
import os
from pathlib import Path # Import Path

def merge_wordpress_lineage():
    # Define paths to input files
    processing_lineage_path = Path('processing_lineage.csv')
    wordpress_urls_path = Path('wordpress_urls.csv')

    # Check if input files exist
    if not processing_lineage_path.exists():
        print(f"❌ Error: Input file not found at '{processing_lineage_path}'")
        print("Please run the 'process_downloaded_images.py' script first.")
        return
        
    if not wordpress_urls_path.exists():
        print(f"❌ Error: Input file not found at '{wordpress_urls_path}'")
        print("Please upload your images to WordPress and export their URLs to this file.")
        return

    # Load Phase 2 lineage data
    lineage_df = pd.read_csv('processing_lineage.csv')
    
    # Load WordPress export data  
    wordpress_df = pd.read_csv('wordpress_urls.csv')  # From your WordPress export
    
    # Check for the required 'filename' column
    if 'filename' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'filename' was not found in '{wordpress_urls_path}'.")
        print("Please ensure your WordPress export CSV contains a column with the exact name 'filename'.")
        return


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