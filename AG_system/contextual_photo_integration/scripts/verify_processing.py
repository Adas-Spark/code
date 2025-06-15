# scripts/verify_processing.py

import pandas as pd
from pathlib import Path

def verify_processing_output():
    """
    Verifies that all successfully prepared files were successfully processed.
    """
    lineage_dir = Path('lineage')
    download_lineage_path = lineage_dir / 'download_lineage.csv'
    processing_lineage_path = lineage_dir / 'processing_lineage.csv'

    # --- 1. Check if both lineage files exist ---
    if not download_lineage_path.exists() or not processing_lineage_path.exists():
        print("❌ Error: One or both lineage files not found. Cannot perform verification.")
        print(f"  - Check for: {download_lineage_path}")
        print(f"  - Check for: {processing_lineage_path}")
        return

    print("Loading lineage files for verification...")
    download_df = pd.read_csv(download_lineage_path)
    processing_df = pd.read_csv(processing_lineage_path)

    # --- 2. Check for any processing failures ---
    failed_processing = processing_df[processing_df['processing_status'] == 'processing_failed']
    if not failed_processing.empty:
        print("\n--- ⚠️ Found Processing Failures ---")
        for index, row in failed_processing.iterrows():
            print(f"  - File: {row['original_filename']}")
            print(f"    Error: {row['processing_error']}")
        print("-" * 35)
    else:
        print("✅ No processing failures found in the lineage.")

    # --- 3. Compare the set of successful inputs vs. successful outputs ---
    # Get the unique hash of every file that was ready for processing.
    expected_hashes = set(download_df[download_df['status'].isin(['processed', 'processed_with_warnings'])]['md5_hash'])
    
    # Get the unique hash of every file that was successfully processed.
    actual_hashes = set(processing_df[processing_df['processing_status'] == 'completed']['md5_hash'])

    print(f"\n- Expected unique files to process: {len(expected_hashes)}")
    print(f"- Actually completed files: {len(actual_hashes)}")

    # --- 4. Final Verdict ---
    if expected_hashes == actual_hashes:
        print("\n✅ Verification Successful: All prepared files have been successfully processed.")
    else:
        print("\n❌ Verification Failed: Mismatch between expected files and processed files.")
        missing_hashes = expected_hashes - actual_hashes
        if missing_hashes:
            print("\nThe following files were expected but not found in the final processing lineage:")
            # To find the filenames for the missing hashes, we can look them up in the download_df
            missing_files = download_df[download_df['md5_hash'].isin(missing_hashes)]['original_filename']
            for filename in missing_files:
                print(f"  - {filename}")

if __name__ == '__main__':
    verify_processing_output()
