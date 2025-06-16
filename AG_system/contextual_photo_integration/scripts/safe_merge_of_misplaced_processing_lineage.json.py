import json
from pathlib import Path

def merge_thumbnail_data():
    """
    Safely merges thumbnail data from the misplaced root file into the proper lineage file.
    """
    root_file = Path('processing_lineage.json')
    lineage_file = Path('lineage/processing_lineage.json')
    
    print("=== Merging Thumbnail Data ===")
    
    # Load thumbnail data from root file (dictionary structure)
    if root_file.exists():
        with open(root_file, 'r') as f:
            thumbnail_data = json.load(f)
        print(f"Loaded thumbnail data for {len(thumbnail_data)} images from root file")
    else:
        print("No root file found - nothing to merge")
        return
    
    # Load existing lineage data (array structure)
    if lineage_file.exists():
        with open(lineage_file, 'r') as f:
            lineage_records = json.load(f)
        print(f"Loaded {len(lineage_records)} existing lineage records")
    else:
        print("No existing lineage file found")
        lineage_records = []
    
    # Merge thumbnail data into lineage records
    merged_count = 0
    
    for record in lineage_records:
        # Extract the stem from final_filename to match with thumbnail data keys
        final_filename = record.get('final_filename', '')
        if final_filename:
            # Remove .webp extension to get the stem
            file_stem = final_filename.rsplit('.', 1)[0]
            
            # Check if we have thumbnail data for this stem
            if file_stem in thumbnail_data:
                # Merge thumbnail information into the record
                thumbnail_info = thumbnail_data[file_stem]
                record.update(thumbnail_info)
                merged_count += 1
                print(f"  Merged thumbnail data for: {final_filename}")
    
    print(f"\nMerged thumbnail data for {merged_count} records")
    
    # Save the updated lineage file
    with open(lineage_file, 'w') as f:
        json.dump(lineage_records, f, indent=2)
    
    print(f"Updated lineage saved to: {lineage_file}")
    
    # Remove the misplaced root file
    root_file.unlink()
    print(f"Removed misplaced file: {root_file}")
    
    print("\n✅ Merge complete!")

if __name__ == '__main__':
    merge_thumbnail_data()