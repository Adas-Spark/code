import os
import json
import datetime
import pandas as pd
import argparse
import shutil
from pathlib import Path
import hashlib
import re

# --- Supported File Types ---
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.heic', '.webp']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.m4v', '.3gp', '.mpg', '.mpeg', '.avi', '.mkv']
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS + SUPPORTED_VIDEO_EXTENSIONS

class TakeoutProcessor:
    def __init__(self, takeout_dir, output_dir='original_downloads', lineage_dir='lineage'):
        self.takeout_dir = Path(takeout_dir)
        if not self.takeout_dir.is_dir():
            raise FileNotFoundError(f"Takeout directory not found: {takeout_dir}")

        self.output_dir = Path(output_dir)
        self.lineage_dir = Path(lineage_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.lineage_dir.mkdir(exist_ok=True)
        
        self.all_lineage_records = []
        self.processed_hashes = set()
        self.load_existing_lineage()

    def load_existing_lineage(self):
        """Loads the existing lineage CSV to avoid reprocessing files."""
        lineage_csv_path = self.lineage_dir / 'download_lineage.csv'
        if lineage_csv_path.exists():
            print(f"Found existing lineage file. Loading processed file hashes...")
            df = pd.read_csv(lineage_csv_path)
            # Use a set for fast lookups
            self.processed_hashes = set(df['md5_hash'].dropna())
            self.all_lineage_records = df.to_dict('records')
            print(f"Loaded {len(self.processed_hashes)} unique file hashes. Will skip any duplicates.")

    def calculate_hash(self, file_path, block_size=65536):
        """Calculates the MD5 hash of a file."""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()

    def find_json_metadata_file(self, media_file_path):
        """Finds the corresponding JSON metadata file using a flexible matching strategy."""
        # Strategy 1: Direct match
        direct_match_path = media_file_path.with_suffix(media_file_path.suffix + '.supplemental-metadata.json')
        if direct_match_path.exists():
            return direct_match_path

        # Strategy 2: Flexible Prefix Match (handles typos)
        media_filename_prefix = media_file_path.name + '.'
        for potential_json_path in media_file_path.parent.glob('*.json'):
            if potential_json_path.name.startswith(media_filename_prefix):
                return potential_json_path
        
        # Strategy 3: Handle edited filenames with numbers, like 'image(1).jpg'
        media_stem = media_file_path.stem
        match = re.match(r'(.+?)\((\d+)\)$', media_stem)
        if match:
            base_name, number = match.group(1), match.group(2)
            for potential_json_path in media_file_path.parent.glob('*.json'):
                if base_name in potential_json_path.name and f'({number})' in potential_json_path.name:
                    return potential_json_path
        return None

    def process_takeout_item(self, media_file_path, json_file_path, file_hash):
        """Processes a single media file and its JSON metadata."""
        lineage_record = {
            'md5_hash': file_hash,
            'original_takeout_path': str(media_file_path),
            'original_takeout_json_path': str(json_file_path),
            'original_filename': media_file_path.name,
            'user_caption': '',
            'creation_date': '',
            'geo_data_latitude': None, 'geo_data_longitude': None, 'geo_data_altitude': None,
            'local_path': '', 'metadata_file_path': '',
            'status': 'pending', 'error_message': ''
        }
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            original_filename_from_json = metadata.get('title')
            if original_filename_from_json:
                base_json_title, _ = os.path.splitext(original_filename_from_json)
                actual_file_ext = media_file_path.suffix
                lineage_record['original_filename'] = base_json_title + actual_file_ext
            
            lineage_record['user_caption'] = metadata.get('description', '')

            photo_taken_time = metadata.get('photoTakenTime', {}).get('timestamp')
            if photo_taken_time:
                creation_dt = datetime.datetime.fromtimestamp(int(photo_taken_time))
                lineage_record['creation_date'] = creation_dt.isoformat()
                date_folder_name = creation_dt.strftime('%Y-%m-%d')
            else:
                creation_dt = datetime.datetime.fromtimestamp(media_file_path.stat().st_mtime)
                lineage_record['creation_date'] = creation_dt.isoformat() + "_fallback_mtime"
                date_folder_name = creation_dt.strftime('%Y-%m-%d')
                lineage_record['error_message'] += "Used file modification time. "

            geo_data = metadata.get('geoData', {})
            if geo_data.get('latitude') != 0.0 or geo_data.get('longitude') != 0.0:
                 lineage_record.update({
                     'geo_data_latitude': geo_data.get('latitude'),
                     'geo_data_longitude': geo_data.get('longitude'),
                     'geo_data_altitude': geo_data.get('altitude')
                 })

            date_output_dir = self.output_dir / date_folder_name
            date_output_dir.mkdir(exist_ok=True)

            local_media_path = date_output_dir / lineage_record['original_filename']
            shutil.copy2(media_file_path, local_media_path)
            lineage_record['local_path'] = str(local_media_path)

            if not lineage_record['error_message']:
                lineage_record['status'] = 'processed'
                print(f"✅ Processed new file: {lineage_record['original_filename']}")
            else:
                lineage_record['status'] = 'processed_with_warnings'
                print(f"⚠️ Processed with warnings: {lineage_record['original_filename']} - {lineage_record['error_message']}")

        except Exception as e:
            lineage_record['status'] = 'error_processing_json'
            lineage_record['error_message'] += f"Error: {e}. "
            print(f"❌ Error processing JSON for {media_file_path.name}: {e}")
        
        self.all_lineage_records.append(lineage_record)

    def scan_takeout_directory(self):
        """Scans the Takeout directory, skipping already processed files based on MD5 hash."""
        print(f"Scanning Takeout directory: {self.takeout_dir}...")
        
        for root, _, files in os.walk(self.takeout_dir):
            for filename in files:
                media_file_path = Path(root) / filename
                if media_file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                # --- HASH CHECK ---
                file_hash = self.calculate_hash(media_file_path)
                if file_hash in self.processed_hashes:
                    print(f"⏭️ Skipping duplicate content: {filename}")
                    continue
                
                json_file_path = self.find_json_metadata_file(media_file_path)
                if json_file_path:
                    self.process_takeout_item(media_file_path, json_file_path, file_hash)
                    self.processed_hashes.add(file_hash) # Add new hash to set
                else:
                    print(f"⚠️ Warning: Missing JSON for media file: {media_file_path}")
                    lineage_record = {
                        'md5_hash': file_hash,
                        'original_takeout_path': str(media_file_path),
                        'original_filename': media_file_path.name,
                        'status': 'error_missing_json',
                        'error_message': 'JSON metadata file not found.'
                    }
                    self.all_lineage_records.append(lineage_record)

    def save_lineage(self):
        """Saves the final, combined lineage records to JSON and CSV, overwriting the old files."""
        json_path = self.lineage_dir / 'download_lineage.json'
        csv_path = self.lineage_dir / 'download_lineage.csv'

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.all_lineage_records, f, indent=4)

        if self.all_lineage_records:
            df = pd.DataFrame(self.all_lineage_records)
            columns = [
                'md5_hash', 'original_takeout_path', 'original_filename', 'creation_date',
                'user_caption', 'local_path', 'status', 'error_message',
                'geo_data_latitude', 'geo_data_longitude', 'geo_data_altitude',
                'original_takeout_json_path'
            ]
            for col in columns:
                if col not in df.columns:
                    df[col] = None
            df = df[columns]
            df.to_csv(csv_path, index=False, encoding='utf-8')
        
        print(f"\nLineage data saved to {json_path} and {csv_path}")

def main():
    parser = argparse.ArgumentParser(description="Process Google Takeout data, with duplicate content detection.")
    parser.add_argument("takeout_dir", help="Path to the directory of an unzipped Takeout album.")
    args = parser.parse_args()
    try:
        processor = TakeoutProcessor(args.takeout_dir)
        processor.scan_takeout_directory()
        processor.save_lineage()
        print("\n✅ Processing complete!")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()