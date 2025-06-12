import os
import requests
import datetime
import pandas as pd
import json
import hashlib
from pathlib import Path

class ImageDownloader:
    def __init__(self, download_dir='original_downloads', lineage_dir='lineage'):
        self.download_dir = Path(download_dir)
        self.lineage_dir = Path(lineage_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.lineage_dir.mkdir(exist_ok=True)
        
    def download_with_lineage(self, photo_row):
        """Download original images with complete lineage tracking"""
        
        lineage_record = {
            'google_photos_id': photo_row['api_id'],
            'google_photos_link': photo_row['google_photos_link'],
            'original_filename': photo_row['original_filename'],
            'user_caption': photo_row['user_caption'],
            'creation_date': photo_row['creation_date'],
            'download_timestamp': datetime.datetime.now().isoformat(),
            'status': 'downloading'
        }
        
        try:
            # Create structured directory by date
            date_folder = photo_row['creation_date'][:10]  # YYYY-MM-DD
            full_path = self.download_dir / date_folder
            full_path.mkdir(exist_ok=True)
            
            # Use API ID as filename to ensure uniqueness
            original_ext = os.path.splitext(photo_row['original_filename'])[1]
            local_filename = f"{photo_row['api_id']}{original_ext}"
            local_path = full_path / local_filename
            
            # Download with maximum quality (=d parameter)
            download_url = photo_row['base_url'] + '=d'
            
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()
            
            # Save original file
            with open(local_path, 'wb') as f:
                f.write(response.content)
            
            # Calculate checksum for integrity verification
            file_hash = hashlib.sha256(response.content).hexdigest()
            
            # Update lineage record
            lineage_record.update({
                'local_path': str(local_path),
                'file_size_bytes': len(response.content),
                'sha256_hash': file_hash,
                'download_url': download_url,
                'status': 'downloaded'
            })
            
            # Create sidecar metadata file
            metadata_path = local_path.with_suffix('.metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(lineage_record, f, indent=2)
            
            print(f"✅ Downloaded: {photo_row['original_filename']}")
            
        except Exception as e:
            lineage_record.update({
                'status': 'download_failed',
                'error': str(e)
            })
            print(f"❌ Failed to download: {photo_row['original_filename']} - {e}")
        
        return lineage_record

def main():
    # Load Google Photos metadata from Phase 1
    google_df = pd.read_csv('google_data.csv')
    
    downloader = ImageDownloader()
    all_lineage_records = []
    
    print(f"Starting download for {len(google_df)} images...")
    
    for index, row in google_df.iterrows():
        lineage_record = downloader.download_with_lineage(row)
        all_lineage_records.append(lineage_record)
        
        # Save incremental progress
        if (index + 1) % 25 == 0:
            with open('lineage/download_lineage.json', 'w') as f:
                json.dump(all_lineage_records, f, indent=2)
            print(f"Progress: {index + 1}/{len(google_df)} images downloaded")
    
    # Final save
    with open('lineage/download_lineage.json', 'w') as f:
        json.dump(all_lineage_records, f, indent=2)
    
    # Create CSV for next phase
    lineage_df = pd.DataFrame(all_lineage_records)
    lineage_df.to_csv('download_lineage.csv', index=False)
    
    successful_downloads = len([r for r in all_lineage_records if r['status'] == 'downloaded'])
    print(f"✅ Download complete! {successful_downloads}/{len(google_df)} images downloaded successfully")

if __name__ == '__main__':
    main()