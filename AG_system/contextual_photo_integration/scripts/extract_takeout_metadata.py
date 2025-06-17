#!/usr/bin/env python3

import pandas as pd
import json
from pathlib import Path
import os

def extract_takeout_metadata():
    """
    Extracts additional metadata from Google Takeout JSON files and adds it to the existing lineage.
    This script enhances the complete_image_lineage.csv with rich metadata from original Takeout exports.
    """
    print("=== Extracting Takeout Metadata ===")
    base_dir = Path(__file__).resolve().parent.parent
    
    # Define paths
    lineage_file = base_dir / 'lineage' / 'complete_image_lineage.csv'
    
    if not lineage_file.exists():
        print(f"❌ Error: Lineage file not found at {lineage_file}")
        print("Please run the full pipeline through Step 7 (merge WordPress data) first.")
        return
    
    # Load existing lineage data
    print(f"Loading existing lineage data from {lineage_file}...")
    df = pd.read_csv(lineage_file)
    print(f"Loaded {len(df)} existing lineage records")
    
    # Check if we already have the new metadata columns
    new_columns = [
        'google_photo_views', 'google_photos_url', 'google_origin_type',
        'takeout_geo_lat', 'takeout_geo_lon', 'takeout_geo_altitude',
        'takeout_photo_taken_time', 'takeout_creation_time',
        'takeout_raw_metadata'
    ]
    
    existing_new_cols = [col for col in new_columns if col in df.columns]
    if existing_new_cols:
        print(f"⚠️  Found existing metadata columns: {existing_new_cols}")
        print("This script will update existing values.")
    
    # Add new columns if they don't exist
    for col in new_columns:
        if col not in df.columns:
            df[col] = None
    
    # Process each record
    print("\nProcessing Takeout JSON files...")
    processed_count = 0
    error_count = 0
    missing_json_count = 0
    
    for index, row in df.iterrows():
        json_path = row.get('original_takeout_json_path')
        original_filename = row.get('original_filename', 'unknown')
        
        if pd.isna(json_path) or not json_path:
            missing_json_count += 1
            continue
        
        json_file = Path(json_path)
        
        # If the exact path doesn't exist, search for the JSON file in takeout_extracted/
        if not json_file.exists():
            # Extract just the filename from the original path
            json_filename = Path(json_path).name
            
            # Search for the JSON file in all takeout_extracted subdirectories
            found_json = None
            takeout_dir = base_dir / 'takeout_extracted'
            if takeout_dir.exists():
                for json_candidate in takeout_dir.rglob(json_filename):
                    found_json = json_candidate
                    break
            
            if found_json:
                json_file = found_json
                print(f"  📁 Found JSON file in different location: {json_file}")
            else:
                print(f"  ❌ JSON file not found anywhere for {original_filename}: {json_filename}")
                error_count += 1
                continue
        
        try:
            # Load and parse JSON metadata
            with open(json_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract Google Photos specific data
            df.at[index, 'google_photo_views'] = metadata.get('imageViews', '')
            df.at[index, 'google_photos_url'] = metadata.get('url', '')
            
            # Extract origin information
            google_origin = metadata.get('googlePhotosOrigin', {})
            if 'fromSharedAlbum' in google_origin:
                df.at[index, 'google_origin_type'] = 'shared_album'
            elif 'fromUpload' in google_origin:
                df.at[index, 'google_origin_type'] = 'upload'
            else:
                df.at[index, 'google_origin_type'] = 'unknown'
            
            # Extract enhanced geo data from Takeout (often more reliable than EXIF)
            geo_data = metadata.get('geoData', {})
            takeout_lat = geo_data.get('latitude', 0.0)
            takeout_lon = geo_data.get('longitude', 0.0)
            takeout_alt = geo_data.get('altitude', 0.0)
            
            # Only store if we have real coordinates (not 0,0)
            if takeout_lat != 0.0 or takeout_lon != 0.0:
                df.at[index, 'takeout_geo_lat'] = takeout_lat
                df.at[index, 'takeout_geo_lon'] = takeout_lon
                df.at[index, 'takeout_geo_altitude'] = takeout_alt
            
            # Extract timestamp information
            photo_taken = metadata.get('photoTakenTime', {})
            creation_time = metadata.get('creationTime', {})
            
            if 'timestamp' in photo_taken:
                df.at[index, 'takeout_photo_taken_time'] = photo_taken.get('formatted', '')
            
            if 'timestamp' in creation_time:
                df.at[index, 'takeout_creation_time'] = creation_time.get('formatted', '')
            
            # Store complete raw metadata for future use (as JSON string)
            df.at[index, 'takeout_raw_metadata'] = json.dumps(metadata, separators=(',', ':'))
            
            processed_count += 1
            
            if processed_count % 100 == 0:
                print(f"  Processed {processed_count} JSON files...")
        
        except Exception as e:
            print(f"  ❌ Error processing {original_filename}: {e}")
            error_count += 1
    
    # Create backup of original lineage
    backup_file = lineage_file.with_suffix('.csv.backup_before_metadata')
    print(f"\nCreating backup: {backup_file}")
    df.to_csv(backup_file, index=False)
    
    # Save updated lineage
    print(f"Saving enhanced lineage: {lineage_file}")
    df.to_csv(lineage_file, index=False)
    
    # Report results
    print(f"\n✅ Takeout metadata extraction complete!")
    print(f"\nResults:")
    print(f"  Successfully processed: {processed_count}")
    print(f"  Errors encountered: {error_count}")
    print(f"  Missing JSON paths: {missing_json_count}")
    print(f"  Total records: {len(df)}")
    
    # Show sample of new data
    if processed_count > 0:
        print(f"\nSample of extracted metadata:")
        sample_cols = ['original_filename', 'google_photo_views', 'google_origin_type', 'takeout_geo_lat']
        sample_data = df[sample_cols].dropna(subset=['google_photo_views']).head(3)
        for _, row in sample_data.iterrows():
            print(f"  {row['original_filename']}: {row['google_photo_views']} views, {row['google_origin_type']}, GPS: {row['takeout_geo_lat']}")
    
    print(f"\nNew columns added to lineage:")
    for col in new_columns:
        non_null_count = df[col].notna().sum()
        print(f"  - {col}: {non_null_count} records with data")
    
    print(f"\nNext step: Run 'python scripts/final_enrichment.py' to add AI captions")

if __name__ == '__main__':
    extract_takeout_metadata()