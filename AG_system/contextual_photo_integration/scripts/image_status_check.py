#!/usr/bin/env python3

import pandas as pd
import hashlib
from pathlib import Path
from collections import defaultdict, Counter
import os

def calculate_md5(file_path, block_size=65536):
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read(block_size)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(block_size)
    return hasher.hexdigest()

def check_image_status():
    """
    Comprehensive image status check using pandas for reliable CSV parsing.
    """
    print("=== Python Image Status Check ===")
    base_dir = Path(__file__).resolve().parent.parent
    
    # Define paths
    processed_webp_dir = base_dir / 'processed_webp'
    thumbnails_dir = base_dir / 'processed_webp_thumbnails'
    lineage_file = base_dir / 'lineage' / 'complete_image_lineage.csv'
    
    print(f"Processed images directory: {processed_webp_dir}")
    print(f"Thumbnails directory: {thumbnails_dir}")
    print(f"Lineage file: {lineage_file}")
    print()
    
    # Step 1: Scan local files and calculate hashes
    print("--- Step 1: Scanning Local Files ---")
    if not processed_webp_dir.exists():
        print(f"❌ Directory not found: {processed_webp_dir}")
        return
    
    local_files = list(processed_webp_dir.glob('*.webp'))
    print(f"Found {len(local_files)} .webp files")
    
    if len(local_files) == 0:
        print("No files to check!")
        return
    
    # Calculate MD5s and detect duplicates
    print("Calculating MD5 hashes...")
    file_hashes = {}
    hash_to_files = defaultdict(list)
    
    for file_path in local_files:
        try:
            md5_hash = calculate_md5(file_path)
            file_hashes[file_path] = md5_hash
            hash_to_files[md5_hash].append(file_path)
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
    
    # Step 2: Check for local duplicates
    print("\n--- Step 2: Local Duplicate Detection ---")
    duplicate_sets = {h: files for h, files in hash_to_files.items() if len(files) > 1}
    
    if duplicate_sets:
        print(f"Found {len(duplicate_sets)} sets of duplicate files:")
        for hash_val, files in duplicate_sets.items():
            print(f"  Hash {hash_val}:")
            for file_path in files:
                print(f"    - {file_path}")
    else:
        print("✅ No local duplicates found")
    
    # Step 3: Load and parse lineage file
    print("\n--- Step 3: Loading Lineage Data ---")
    if not lineage_file.exists():
        print(f"❌ Lineage file not found: {lineage_file}")
        all_files_status = {f: "no_lineage_file" for f in local_files}
    else:
        try:
            # Use pandas for robust CSV parsing
            lineage_df = pd.read_csv(lineage_file)
            print(f"✅ Loaded lineage file with {len(lineage_df)} records")
            print(f"   Columns: {list(lineage_df.columns)}")
            
            # Create lookup by processed file MD5 (preferred) or original MD5 (fallback)
            lineage_by_hash = {}
            for _, row in lineage_df.iterrows():
                # Use processed_file_md5 if available, otherwise fall back to original md5_hash
                processed_md5 = row.get('processed_file_md5')
                original_md5 = row.get('md5_hash')
                
                # Prefer processed MD5 for matching current files
                lookup_md5 = processed_md5 if pd.notna(processed_md5) and processed_md5 != '' else original_md5
                
                has_wp_url = pd.notna(row.get('url')) and row.get('url').strip()
                if pd.notna(lookup_md5):
                    lineage_by_hash[lookup_md5] = {
                        'has_wp_url': bool(has_wp_url),
                        'final_filename': row.get('final_filename'),
                        'wp_url': row.get('url', ''),
                        'original_md5': original_md5,
                        'processed_md5': processed_md5,
                        'used_md5_type': 'processed' if pd.notna(processed_md5) else 'original'
                    }
            
            print(f"   Records with MD5 hash: {len(lineage_by_hash)}")
            records_with_url = sum(1 for r in lineage_by_hash.values() if r['has_wp_url'])
            processed_md5_count = sum(1 for r in lineage_by_hash.values() if r['used_md5_type'] == 'processed')
            print(f"   Records with WordPress URL: {records_with_url}")
            print(f"   Records using processed MD5s: {processed_md5_count}")
            
            # Categorize files
            all_files_status = {}
            for file_path in local_files:
                file_hash = file_hashes[file_path]
                
                if file_hash in lineage_by_hash:
                    lineage_record = lineage_by_hash[file_hash]
                    if lineage_record['has_wp_url']:
                        all_files_status[file_path] = "on_wordpress"
                    else:
                        all_files_status[file_path] = "in_lineage_no_url"
                else:
                    all_files_status[file_path] = "not_in_lineage"
        
        except Exception as e:
            print(f"❌ Error loading lineage file: {e}")
            all_files_status = {f: "lineage_parse_error" for f in local_files}
    
    # Step 4: Check thumbnail status
    print("\n--- Step 4: Thumbnail Status Check ---")
    thumbnail_status = {}
    missing_thumbnails = []
    orphan_thumbnails = []
    
    if thumbnails_dir.exists():
        # Check for missing thumbnails
        for file_path in local_files:
            stem = file_path.stem
            expected_thumb = thumbnails_dir / f"{stem}-h360-thumb.webp"
            thumbnail_status[file_path] = expected_thumb.exists()
            if not expected_thumb.exists():
                missing_thumbnails.append(file_path)
        
        # Check for orphan thumbnails
        thumbnail_files = list(thumbnails_dir.glob('*-h360-thumb.webp'))
        for thumb_file in thumbnail_files:
            # Extract the original stem (remove -h360-thumb)
            original_stem = thumb_file.stem.replace('-h360-thumb', '')
            expected_original = processed_webp_dir / f"{original_stem}.webp"
            if not expected_original.exists():
                orphan_thumbnails.append(thumb_file)
    else:
        print(f"❌ Thumbnails directory not found: {thumbnails_dir}")
        thumbnail_status = {f: False for f in local_files}
        missing_thumbnails = local_files.copy()
    
    # Step 5: Report Results
    print("\n" + "="*60)
    print("SUMMARY REPORT")
    print("="*60)
    
    # Count by status
    status_counts = Counter(all_files_status.values())
    
    print(f"\nTotal unique files: {len(local_files)}")
    print(f"Local duplicate sets: {len(duplicate_sets)}")
    print()
    
    print("WordPress Status:")
    print(f"  ✅ On WordPress (has URL): {status_counts.get('on_wordpress', 0)}")
    print(f"  ⏳ In lineage, needs URL: {status_counts.get('in_lineage_no_url', 0)}")
    print(f"  📤 Ready for upload: {status_counts.get('not_in_lineage', 0)}")
    print(f"  ❌ Other issues: {status_counts.get('lineage_parse_error', 0) + status_counts.get('no_lineage_file', 0)}")
    print()
    
    print("Thumbnail Status:")
    print(f"  ✅ Thumbnails found: {sum(thumbnail_status.values())}")
    print(f"  ❌ Missing thumbnails: {len(missing_thumbnails)}")
    print(f"  🗑️  Orphan thumbnails: {len(orphan_thumbnails)}")
    
    # Detailed listings for files that need action
    if status_counts.get('not_in_lineage', 0) > 0:
        print(f"\n--- Files Ready for Upload ({status_counts['not_in_lineage']}) ---")
        for file_path, status in all_files_status.items():
            if status == 'not_in_lineage':
                thumb_status = "✅" if thumbnail_status.get(file_path, False) else "❌"
                print(f"  {thumb_status} {file_path.name}")
    
    if status_counts.get('in_lineage_no_url', 0) > 0:
        print(f"\n--- Files In Lineage But Missing WordPress URL ({status_counts['in_lineage_no_url']}) ---")
        for file_path, status in all_files_status.items():
            if status == 'in_lineage_no_url':
                thumb_status = "✅" if thumbnail_status.get(file_path, False) else "❌"
                print(f"  {thumb_status} {file_path.name}")
    
    if missing_thumbnails:
        print(f"\n--- Missing Thumbnails ({len(missing_thumbnails)}) ---")
        for file_path in missing_thumbnails[:10]:  # Show first 10
            print(f"  ❌ {file_path.name}")
        if len(missing_thumbnails) > 10:
            print(f"  ... and {len(missing_thumbnails) - 10} more")
    
    if orphan_thumbnails:
        print(f"\n--- Orphan Thumbnails ({len(orphan_thumbnails)}) ---")
        for thumb_path in orphan_thumbnails[:10]:  # Show first 10
            print(f"  🗑️  {thumb_path.name}")
        if len(orphan_thumbnails) > 10:
            print(f"  ... and {len(orphan_thumbnails) - 10} more")

if __name__ == '__main__':
    check_image_status()