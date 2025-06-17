import json
import pandas as pd
from pathlib import Path

def cleanup_lineage_data():
    """
    Remove lineage records for files that don't actually exist,
    keeping only records for files that were successfully processed.
    """
    lineage_dir = Path('lineage')
    json_path = lineage_dir / 'processing_lineage.json'
    csv_path = lineage_dir / 'processing_lineage.csv'
    processed_dir = Path('processed_webp')
    
    print("Loading processing lineage...")
    
    # Load the JSON data
    with open(json_path, 'r') as f:
        lineage_data = json.load(f)
    
    print(f"Original lineage records: {len(lineage_data)}")
    
    # Filter to only records where the processed file actually exists
    valid_records = []
    missing_files = []
    
    for record in lineage_data:
        final_filename = record.get('final_filename')
        if final_filename:
            file_path = processed_dir / final_filename
            if file_path.exists():
                valid_records.append(record)
            else:
                missing_files.append(final_filename)
                print(f"  Removing record for missing file: {final_filename}")
    
    print(f"\nCleaned lineage records: {len(valid_records)}")
    print(f"Removed records for missing files: {len(missing_files)}")
    
    # Save the cleaned data
    with open(json_path, 'w') as f:
        json.dump(valid_records, f, indent=2)
    
    # Regenerate CSV with proper formatting
    df = pd.DataFrame(valid_records)
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Cleaned lineage files saved")
    print(f"  - JSON: {json_path}")
    print(f"  - CSV: {csv_path}")
    
    # Now check if our test file exists and might need to be added
    test_files = ['20190420_101951-adasstory.webp', '0P5A0006-adasstory.webp']
    print(f"\nChecking for untracked files...")
    
    for test_file in test_files:
        file_path = processed_dir / test_file
        if file_path.exists():
            # Check if this file is in our cleaned records
            found = any(record.get('final_filename') == test_file for record in valid_records)
            if not found:
                print(f"  ⚠️  File exists but not tracked: {test_file}")
            else:
                print(f"  ✅ File tracked: {test_file}")

if __name__ == '__main__':
    cleanup_lineage_data()