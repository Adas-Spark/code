import os
import json
import datetime
import pandas as pd
import argparse
import shutil
from pathlib import Path
import hashlib

# Supported image and video file extensions (can be expanded)
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

    def find_json_metadata_file(self, media_file_path):
        """
        Finds the corresponding JSON metadata file for a given media file.
        Handles common Takeout naming patterns:
        - media_file.ext.json
        - media_file.json (if media_file.ext has a recognized extension)
        - media_file_without_ext.json (less common, for files like 'Photo on 12-12-12 at 10.10 AM')
        """
        # Pattern 1: media_file.ext.json
        json_path_pattern1 = media_file_path.with_suffix(media_file_path.suffix + '.json')
        if json_path_pattern1.exists():
            return json_path_pattern1

        # Pattern 2: media_file.json (e.g. IMG_1234.HEIC -> IMG_1234.json)
        # This is common if the original filename in JSON 'title' field does not match media_file_path.name
        # We will rely on the JSON's 'title' field later to confirm matches if needed,
        # but for finding the file, this pattern is often seen.
        json_path_pattern2 = media_file_path.with_suffix('.json')
        if json_path_pattern2.exists():
            return json_path_pattern2

        # Pattern 3: Check if the JSON is named after the media file name *without* its extension
        # e.g., for "My Photo.jpg", it might be "My Photo.json"
        # This is similar to pattern2 but covers cases where suffix might be complex (e.g. .JPEG)
        json_path_pattern3 = media_file_path.parent / (media_file_path.stem + '.json')
        if json_path_pattern3.exists():
            return json_path_pattern3

        return None

    def process_takeout_item(self, media_file_path, json_file_path):
        """Processes a single media file and its JSON metadata."""
        lineage_record = {
            'original_takeout_path': str(media_file_path),
            'original_takeout_json_path': str(json_file_path),
            'original_filename': media_file_path.name, # Default, might be overwritten by JSON's title
            'user_caption': '',
            'creation_date': '',
            'geo_data_latitude': None,
            'geo_data_longitude': None,
            'geo_data_altitude': None,
            'local_path': '',
            'metadata_file_path': '',
            'status': 'pending',
            'error_message': ''
        }

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            # Extract original filename from JSON 'title' if available
            # Takeout JSON 'title' usually holds the original filename as it was in Google Photos
            original_filename_from_json = metadata.get('title')
            if original_filename_from_json:
                 # Ensure the extension from the actual file is preserved if JSON title lacks it or has a different one
                base_json_title, _ = os.path.splitext(original_filename_from_json)
                actual_file_ext = media_file_path.suffix
                lineage_record['original_filename'] = base_json_title + actual_file_ext
            else:
                # Fallback to the actual filename from Takeout if 'title' is missing
                lineage_record['original_filename'] = media_file_path.name


            lineage_record['user_caption'] = metadata.get('description', '')

            # Extract creation date
            photo_taken_time = metadata.get('photoTakenTime', {}).get('timestamp')
            if photo_taken_time:
                # Convert Unix timestamp (string) to datetime object
                creation_dt = datetime.datetime.fromtimestamp(int(photo_taken_time))
                lineage_record['creation_date'] = creation_dt.isoformat()
                date_folder_name = creation_dt.strftime('%Y-%m-%d')
            else:
                # Fallback to file modification time if 'photoTakenTime' is missing
                # This is less accurate but better than nothing.
                creation_dt = datetime.datetime.fromtimestamp(media_file_path.stat().st_mtime)
                lineage_record['creation_date'] = creation_dt.isoformat() + "_fallback_mtime"
                date_folder_name = creation_dt.strftime('%Y-%m-%d')
                lineage_record['error_message'] += "Used file modification time for creation date. "


            # Extract geo data
            geo_data = metadata.get('geoData', {})
            # Ensure geoData values are not the default "empty" ones from Takeout (0.0, 0.0, 0.0)
            if geo_data.get('latitude') != 0.0 or geo_data.get('longitude') != 0.0:
                 lineage_record['geo_data_latitude'] = geo_data.get('latitude')
                 lineage_record['geo_data_longitude'] = geo_data.get('longitude')
                 lineage_record['geo_data_altitude'] = geo_data.get('altitude')

            # Create dated subdirectory
            date_output_dir = self.output_dir / date_folder_name
            date_output_dir.mkdir(exist_ok=True)

            # Define local path for the media file and new metadata sidecar
            # Use the (potentially corrected) original_filename for the destination
            local_media_path = date_output_dir / lineage_record['original_filename']
            local_metadata_path = local_media_path.with_suffix(local_media_path.suffix + '.metadata.json')
            
            # Copy media file
            try:
                shutil.copy2(media_file_path, local_media_path)
                lineage_record['local_path'] = str(local_media_path)
            except Exception as copy_err:
                lineage_record['status'] = 'error_copying_file'
                lineage_record['error_message'] += f"Error copying file: {copy_err}. "
                print(f"❌ Error copying {media_file_path.name}: {copy_err}")
                self.all_lineage_records.append(lineage_record)
                return

            # Create new metadata sidecar file
            sidecar_content = {
                'original_takeout_path': str(media_file_path),
                'original_takeout_json_path': str(json_file_path),
                'original_filename': lineage_record['original_filename'],
                'user_caption': lineage_record['user_caption'],
                'creation_date_iso': lineage_record['creation_date'],
                'geo_data': {
                    'latitude': lineage_record['geo_data_latitude'],
                    'longitude': lineage_record['geo_data_longitude'],
                    'altitude': lineage_record['geo_data_altitude'],
                }
            }
            try:
                with open(local_metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(sidecar_content, f, indent=4)
                lineage_record['metadata_file_path'] = str(local_metadata_path)
            except Exception as json_write_err:
                lineage_record['status'] = 'error_writing_sidecar'
                lineage_record['error_message'] += f"Error writing metadata sidecar: {json_write_err}. "
                # Still consider the file processed if copy was successful
                # The main error here is about the sidecar, not the media file itself.

            if not lineage_record['error_message']: # If no errors appended so far
                lineage_record['status'] = 'processed'
                print(f"✅ Processed: {lineage_record['original_filename']}")
            else: # Some non-fatal error occurred (e.g. mtime fallback, sidecar write error)
                lineage_record['status'] = 'processed_with_warnings'
                print(f"⚠️ Processed with warnings: {lineage_record['original_filename']} - {lineage_record['error_message']}")


        except Exception as e:
            lineage_record['status'] = 'error_processing_json'
            lineage_record['error_message'] += f"Error processing JSON or metadata: {e}. "
            print(f"❌ Error processing JSON for {media_file_path.name}: {e}")
        
        self.all_lineage_records.append(lineage_record)

    def scan_takeout_directory(self):
        """Scans the Takeout directory for media and metadata files."""
        print(f"Scanning Takeout directory: {self.takeout_dir}...")
        processed_files = 0
        found_media_files = 0

        for root, _, files in os.walk(self.takeout_dir):
            for filename in files:
                media_file_path = Path(root) / filename

                # Check if it's a supported media file type
                if media_file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue

                found_media_files +=1

                # Attempt to find its JSON metadata file
                json_file_path = self.find_json_metadata_file(media_file_path)

                if json_file_path and json_file_path.exists():
                    self.process_takeout_item(media_file_path, json_file_path)
                    processed_files += 1
                else:
                    # Log as an error or warning if JSON is missing
                    print(f"⚠️ Warning: Missing JSON for media file: {media_file_path}")
                    lineage_record = {
                        'original_takeout_path': str(media_file_path),
                        'original_filename': media_file_path.name,
                        'status': 'error_missing_json',
                        'error_message': 'JSON metadata file not found.'
                    }
                    self.all_lineage_records.append(lineage_record)
        
        print(f"\nFound {found_media_files} potential media files.")
        if found_media_files == 0:
            print("No media files found. Please check the Takeout directory structure and supported file types.")
            print("Expected structure: Takeout Album Folders / media files + json files")


    def save_lineage(self):
        """Saves the accumulated lineage records to JSON and CSV."""
        json_path = self.lineage_dir / 'download_lineage.json'
        csv_path = self.lineage_dir / 'download_lineage.csv' # Changed from root to lineage_dir

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.all_lineage_records, f, indent=4)

        if self.all_lineage_records:
            df = pd.DataFrame(self.all_lineage_records)
            # Select and order columns for CSV for better readability
            columns = [
                'original_takeout_path', 'original_filename', 'creation_date',
                'user_caption', 'local_path', 'metadata_file_path', 'status',
                'error_message', 'geo_data_latitude', 'geo_data_longitude',
                'geo_data_altitude', 'original_takeout_json_path'
            ]
            # Ensure all desired columns are present, add if missing (e.g., if no geo data found at all)
            for col in columns:
                if col not in df.columns:
                    df[col] = None
            df = df[columns]
            df.to_csv(csv_path, index=False, encoding='utf-8')
        else:
            # Create empty CSV with headers if no records
            pd.DataFrame(columns=[
                'original_takeout_path', 'original_filename', 'creation_date',
                'user_caption', 'local_path', 'metadata_file_path', 'status',
                'error_message', 'geo_data_latitude', 'geo_data_longitude',
                'geo_data_altitude', 'original_takeout_json_path'
            ]).to_csv(csv_path, index=False, encoding='utf-8')


        print(f"\nLineage data saved to {json_path} and {csv_path}")
        successful_items = len([r for r in self.all_lineage_records if r['status'] == 'processed' or r['status'] == 'processed_with_warnings'])
        print(f"✅ Processing complete! {successful_items}/{len(self.all_lineage_records)} items processed successfully (or with warnings).")


def main():
    parser = argparse.ArgumentParser(description="Process Google Takeout photo data.")
    parser.add_argument("takeout_dir",
                        help="Path to the root Google Takeout directory (e.g., 'Takeout/Google Photos').")
    parser.add_argument("--output_dir", default="original_downloads",
                        help="Directory to save processed original_downloads files.")
    parser.add_argument("--lineage_dir", default="lineage",
                        help="Directory to save lineage files.")
    
    args = parser.parse_args()

    try:
        processor = TakeoutProcessor(args.takeout_dir, args.output_dir, args.lineage_dir)
        processor.scan_takeout_directory()
        processor.save_lineage()
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
