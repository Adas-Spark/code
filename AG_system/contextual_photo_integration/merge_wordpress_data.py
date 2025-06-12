import pandas as pd
import os

def merge_wordpress_lineage():
    # Load Phase 2 lineage data
    lineage_df = pd.read_csv('processing_lineage.csv')
    
    # Load WordPress export data  
    wordpress_df = pd.read_csv('wordpress_urls.csv')  # From your WordPress export
    
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