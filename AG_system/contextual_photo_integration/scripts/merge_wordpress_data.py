import pandas as pd
import os
from pathlib import Path

# Script modified to support merging WordPress URLs for both full-size
# images and thumbnails. It now expects `processing_lineage.csv` to
# potentially contain `thumbnail_final_filename` and expects
# `wordpress_urls.csv` to contain URLs for both types of images.
# The script adds `wordpress_url_fullsize` and `wordpress_url_thumbnail`
# to the output `complete_image_lineage.csv`.

# Helper function to get a normalized stem from a filename series
def get_normalized_stem_from_filename(filename_series):
    """
    Takes a pandas Series of filenames, extracts the stem (filename without extension),
    handles potential NaN or empty values, and normalizes the stem.
    Normalization: lowercases, replaces spaces with hyphens, removes tildes.
    """
    stems = []
    for fname in filename_series:
        if pd.isna(fname) or fname == '':
            stems.append('') # Keep it as an empty string for consistent type, merge will fail as expected
        else:
            stems.append(os.path.splitext(str(fname))[0])

    stem_series = pd.Series(stems, index=filename_series.index)
    # Normalize: lowercasing, replacing spaces with hyphens, and REMOVING tildes.
    return stem_series.str.lower().str.replace(' ', '-', regex=False).str.replace('~', '', regex=False)

def merge_wordpress_data():
    # Define the directory where all data files are located
    script_dir = Path(__file__).resolve().parent
    lineage_dir = script_dir.parent / 'lineage' # Assumes script is in scripts/, lineage is one level up

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

    print(f"🔄 Loading processing lineage data from: {processing_lineage_path}")
    lineage_df = pd.read_csv(processing_lineage_path)
    print(f"🔄 Loading WordPress URL data from: {wordpress_urls_path}")
    wordpress_df = pd.read_csv(wordpress_urls_path)
    
    # Check for the required columns
    if 'filename' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'filename' was not found in '{wordpress_urls_path}'.")
        return
    if 'url' not in wordpress_df.columns:
        print(f"❌ Error: The required column 'url' was not found in '{wordpress_urls_path}'.")
        return
    if 'final_filename' not in lineage_df.columns:
        print(f"❌ Error: The required column 'final_filename' was not found in '{processing_lineage_path}'.")
        return

    # Ensure 'thumbnail_final_filename' exists in lineage_df, add if not (with NaNs)
    if 'thumbnail_final_filename' not in lineage_df.columns:
        print(f"⚠️ Warning: 'thumbnail_final_filename' column not found in '{processing_lineage_path}'. Adding it with empty values.")
        lineage_df['thumbnail_final_filename'] = pd.NA


    # --- First Merge: Full-size image URLs ---
    print("🔄 Preparing for full-size image URL merge...")
    lineage_df['normalized_stem_lineage_full'] = get_normalized_stem_from_filename(lineage_df['final_filename'])
    wordpress_df['normalized_stem_wp'] = get_normalized_stem_from_filename(wordpress_df['filename'])

    # Merge for full-size images
    # Suffixes: _lineage will be applied to overlapping columns from lineage_df (left), _wp_full to those from wordpress_df (right)
    merged_df = pd.merge(lineage_df, wordpress_df[['normalized_stem_wp', 'filename', 'url']],
                         left_on='normalized_stem_lineage_full', right_on='normalized_stem_wp',
                         how='left', suffixes=('_lineage', '_wp_full'))

    # Rename columns from the first merge
    merged_df.rename(columns={'url': 'wordpress_url_fullsize',
                              'filename': 'wordpress_filename_fullsize'}, inplace=True)
    print("✅ Full-size image URLs merged.")

    # --- Second Merge: Thumbnail image URLs ---
    print("🔄 Preparing for thumbnail image URL merge...")
    # Create normalized stem for thumbnails in the merged_df (which is lineage_df + fullsize URL info)
    # Handle cases where thumbnail_final_filename might be NaN or empty string
    merged_df['normalized_stem_lineage_thumb'] = get_normalized_stem_from_filename(merged_df['thumbnail_final_filename'])

    # wordpress_df['normalized_stem_wp'] can be reused from the first merge preparation.
    # Suffixes: _main will be applied to overlapping columns from merged_df (left), _wp_thumb to those from wordpress_df (right)
    # We only need 'url' and 'filename' from wordpress_df for thumbnails
    final_merged_df = pd.merge(merged_df, wordpress_df[['normalized_stem_wp', 'filename', 'url']],
                               left_on='normalized_stem_lineage_thumb', right_on='normalized_stem_wp',
                               how='left', suffixes=('_main', '_wp_thumb'))

    # Rename columns from the second merge
    final_merged_df.rename(columns={'url': 'wordpress_url_thumbnail',
                                    'filename': 'wordpress_filename_thumbnail'}, inplace=True)
    print("✅ Thumbnail image URLs merged.")

    # --- Column Cleanup ---
    columns_to_drop = [
        'normalized_stem_lineage_full',      # Used for 1st merge
        'normalized_stem_wp_main',           # wp_stem from 1st merge (if not overwritten or suffixed correctly) - check actual name
        'normalized_stem_wp_wp_full',        # wp_stem from 1st merge (another possible name due to suffixes)
        'normalized_stem_lineage_thumb',     # Used for 2nd merge
        'normalized_stem_wp_wp_thumb',       # wp_stem from 2nd merge
        'normalized_stem_wp',                # Original normalized stem in wordpress_df if it gets carried over
        # Check for columns like 'normalized_stem_wp_x', 'normalized_stem_wp_y' if suffixes caused them
    ]
    # Add specific suffixed versions of 'normalized_stem_wp' that might have been created
    # The suffixes in pd.merge apply to overlapping columns *other than the merge key*.
    # The right key ('normalized_stem_wp') might appear as 'normalized_stem_wp_wp_full' or 'normalized_stem_wp_wp_thumb'
    # if it was also in the left df before merge, or just 'normalized_stem_wp' if it was unique.
    # Let's inspect columns and drop defensively.

    # Drop columns that exist in the dataframe
    existing_cols_to_drop = [col for col in columns_to_drop if col in final_merged_df.columns]
    
    # The key 'normalized_stem_wp' from wordpress_df was used in two merges.
    # In the first merge, it was `right_on='normalized_stem_wp'`. It won't be in `merged_df` unless it was also in `lineage_df`.
    # In the second merge, it was `right_on='normalized_stem_wp'`.
    # Let's explicitly drop the helper columns created on the main dataframe:
    final_cleanup_cols = ['normalized_stem_lineage_full', 'normalized_stem_lineage_thumb']
    # Also drop the 'normalized_stem_wp' if it was brought from the right side and not renamed.
    # After the first merge, 'normalized_stem_wp' (from wordpress_df) is not needed.
    # After the second merge, 'normalized_stem_wp' (from wordpress_df) is not needed.
    # The `wordpress_df[['normalized_stem_wp', ...]]` syntax should prevent other columns from wordpress_df from polluting.
    # The `suffixes` ensure that 'filename' and 'url' are uniquely named.
    # The `normalized_stem_wp` on the right side of the merge does not get added to the final_merged_df unless specified in select, or if it was also a col in left.
    # So, the primary columns to drop are those created on the left DataFrame for merging.

    if 'normalized_stem_wp_main' in final_merged_df.columns: # From first merge if 'normalized_stem_wp' was also in lineage_df
        final_cleanup_cols.append('normalized_stem_wp_main')
    if 'normalized_stem_wp_wp_full' in final_merged_df.columns: # From first merge, if right df's key was suffixed
         final_cleanup_cols.append('normalized_stem_wp_wp_full')

    # The 'normalized_stem_wp' from `wordpress_df` is used as a merge key but should not remain as a separate column
    # in `final_merged_df` unless it was part of the selection or an overlapping column name from the left table.
    # The explicit selection `wordpress_df[['normalized_stem_wp', 'filename', 'url']]` means `normalized_stem_wp` is used as the key
    # and `filename`, `url` are the values brought in. If `normalized_stem_wp` is not also in the left table's columns,
    # it won't be duplicated.
    # The `suffixes` only apply if columns *other than the merge key* have the same name.

    # Let's be explicit about what we expect in `wordpress_df` for the merge:
    # `wordpress_df_subset_full = wordpress_df[['normalized_stem_wp', 'filename', 'url']]`
    # `merged_df = pd.merge(lineage_df, wordpress_df_subset_full, ...)`
    # `wordpress_df_subset_thumb = wordpress_df[['normalized_stem_wp', 'filename', 'url']]`
    # `final_merged_df = pd.merge(merged_df, wordpress_df_subset_thumb, ...)`
    # This structure means 'normalized_stem_wp' is used as the key and won't create extra output columns named 'normalized_stem_wp_x' etc.
    # So, we only need to drop the keys created on the left dataframe:
    
    final_merged_df.drop(columns=final_cleanup_cols, inplace=True, errors='ignore')
    
    # Save the final output to the lineage directory
    final_merged_df.to_csv(output_path, index=False)
    
    print(f"✅ WordPress URLs for full-size and thumbnails merged with processing lineage.")
    print(f"Output: {output_path}")
    expected_cols = ['md5_hash', 'final_filename', 'thumbnail_final_filename', 'wordpress_url_fullsize', 'wordpress_filename_fullsize', 'wordpress_url_thumbnail', 'wordpress_filename_thumbnail']
    print(f"Expected columns include: {', '.join(expected_cols)}")
    print("Please verify all expected columns are present and helper columns are dropped.")

if __name__ == '__main__':
    merge_wordpress_data()