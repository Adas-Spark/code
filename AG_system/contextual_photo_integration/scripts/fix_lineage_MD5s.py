import pandas as pd
import hashlib
from pathlib import Path

def calculate_md5(file_path):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

def fix_lineage_md5s():
    """
    Add processed_file_md5 column to lineage file with current MD5 hashes.
    Preserves original download MD5s in md5_hash column for complete lineage tracking.
    """
    print("=== Adding Processed File MD5s to Lineage ===")
    print("This preserves original MD5s while adding processed file MD5s for matching")
    
    lineage_file = Path('lineage/complete_image_lineage.csv')
    processed_dir = Path('processed_webp')
    
    if not lineage_file.exists():
        print(f"❌ Lineage file not found: {lineage_file}")
        return
    
    if not processed_dir.exists():
        print(f"❌ Processed directory not found: {processed_dir}")
        return
    
    # Load lineage data
    print("Loading lineage data...")
    df = pd.read_csv(lineage_file)
    print(f"Loaded {len(df)} lineage records")
    
    # Create mapping of filename to current MD5
    print("Calculating current MD5s for all processed files...")
    current_md5s = {}
    processed_files = list(processed_dir.glob('*.webp'))
    
    for i, file_path in enumerate(processed_files):
        if i % 50 == 0:  # Progress indicator
            print(f"  Processed {i}/{len(processed_files)} files...")
        
        try:
            current_md5 = calculate_md5(file_path)
            current_md5s[file_path.name] = current_md5
        except Exception as e:
            print(f"  ❌ Error processing {file_path}: {e}")
    
    print(f"Calculated MD5s for {len(current_md5s)} files")
    
    # Add new column for processed file MD5s while preserving original
    print("Adding processed_file_md5 column...")
    
    # Add the new column if it doesn't exist
    if 'processed_file_md5' not in df.columns:
        df['processed_file_md5'] = None
    
    updated_count = 0
    
    for index, row in df.iterrows():
        final_filename = row.get('final_filename')
        if pd.notna(final_filename) and final_filename in current_md5s:
            original_md5 = row.get('md5_hash')
            processed_md5 = current_md5s[final_filename]
            
            # Update the processed file MD5
            df.at[index, 'processed_file_md5'] = processed_md5
            updated_count += 1
            
            if updated_count <= 5:  # Show first few updates
                print(f"  {final_filename}:")
                print(f"    Original MD5:  {original_md5}")
                print(f"    Processed MD5: {processed_md5}")
                print(f"    Match: {'✅' if original_md5 == processed_md5 else '❌'}")
    
    print(f"Added processed MD5s for {updated_count} records")
    
    # Save updated lineage
    backup_file = lineage_file.with_suffix('.csv.backup')
    print(f"Creating backup: {backup_file}")
    df.to_csv(backup_file, index=False)
    
    print(f"Saving updated lineage: {lineage_file}")
    df.to_csv(lineage_file, index=False)
    
    print("✅ Processed file MD5s added successfully!")
    print(f"\nColumns now include:")
    print(f"  - md5_hash: Original download MD5s (preserved)")
    print(f"  - processed_file_md5: Current processed file MD5s (for matching)")

if __name__ == '__main__':
    fix_lineage_md5s()