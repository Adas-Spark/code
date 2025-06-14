import os
from PIL import Image
import datetime
import pandas as pd
import json
from pathlib import Path

class ImageProcessor:
    def __init__(self, processed_dir='processed_webp', lineage_dir='lineage'):
        self.processed_dir = Path(processed_dir)
        self.lineage_dir = Path(lineage_dir)
        self.processed_dir.mkdir(exist_ok=True)
        self.lineage_dir.mkdir(exist_ok=True) # Ensure lineage dir exists
        
        # Processing configuration
        self.MAX_DIMENSION = 1920
        self.FILENAME_TAG = '-adasstory'
        
        # NEW: State-aware properties
        self.all_processing_records = []
        self.processed_hashes = set()
        self.load_existing_lineage()

    def load_existing_lineage(self):
        """Loads the existing processing lineage file to avoid re-processing."""
        lineage_csv_path = self.lineage_dir / 'processing_lineage.csv'
        if lineage_csv_path.exists():
            print(f"Found existing processing lineage file. Loading processed hashes...")
            df = pd.read_csv(lineage_csv_path)
            # Use md5_hash to uniquely identify content that has been processed
            self.processed_hashes = set(df['md5_hash'].dropna())
            self.all_processing_records = df.to_dict('records')
            print(f"Loaded {len(self.processed_hashes)} hashes of already processed images.")
        
    def get_adaptive_quality(self, file_size_bytes):
        """Determine WebP quality based on source file size"""
        if file_size_bytes < 500000:  # Under 500KB  
            return 90
        else:
            return 85
    
    def process_image_with_lineage(self, download_record):
        """Processes a single downloaded image into optimized WebP"""
        # This check is still good practice.
        if download_record.get('status') not in ['processed', 'processed_with_warnings']:
            processing_record = download_record.copy()
            processing_record['processing_status'] = 'skipped_due_to_download_status'
            return processing_record

        processing_record = download_record.copy()
        processing_record.update({
            'processing_timestamp': datetime.datetime.now().isoformat(),
            'transformations': [],
            'processing_status': 'processing'
        })
        
        try:
            local_path_str = download_record.get('local_path')
            if not local_path_str or not Path(local_path_str).exists():
                raise FileNotFoundError(f"Local file not found: {local_path_str}")

            local_path = Path(local_path_str)
            with Image.open(local_path) as img:
                original_size = img.size
                file_size_bytes = local_path.stat().st_size
                processing_record['original_file_size_bytes'] = file_size_bytes

                processing_record['transformations'].append({
                    'step': 'loaded_from_disk', 'original_dimensions': f"{original_size[0]}x{original_size[1]}",
                    'original_format': img.format, 'original_mode': img.mode,
                    'original_file_size_bytes': file_size_bytes
                })
                
                if hasattr(img, '_getexif') and img._getexif():
                    exif = img._getexif()
                    orientation_key = 274
                    if orientation_key in exif:
                        orientation = exif[orientation_key]
                        if orientation == 3: img = img.rotate(180, expand=True)
                        elif orientation == 6: img = img.rotate(270, expand=True)
                        elif orientation == 8: img = img.rotate(90, expand=True)
                
                img.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), Image.Resampling.LANCZOS)
                
                original_filename = download_record.get('original_filename', 'unknown_original')
                file_stem = Path(original_filename).stem
                new_filename = f"{file_stem}{self.FILENAME_TAG}.webp"
                output_path = self.processed_dir / new_filename
                
                webp_quality = self.get_adaptive_quality(file_size_bytes)
                img.save(output_path, 'webp', quality=webp_quality)
                
                processing_record.update({
                    'final_filename': new_filename,
                    'processed_file_path': str(output_path),
                    'webp_quality': webp_quality,
                    'processing_status': 'completed'
                })
            
        except Exception as e:
            processing_record.update({ 'processing_status': 'processing_failed', 'processing_error': str(e) })
        
        return processing_record

    def save_lineage(self):
        """Saves the final, combined processing lineage records."""
        json_path = self.lineage_dir / 'processing_lineage.json'
        csv_path = self.lineage_dir / 'processing_lineage.csv'

        if not self.all_processing_records:
            print("No records to save.")
            return

        df = pd.DataFrame(self.all_processing_records)
        df.to_csv(csv_path, index=False)
        with open(json_path, 'w') as f:
            json.dump(self.all_processing_records, f, indent=2)
        
        print(f"\nProcessing lineage saved to {csv_path} and {json_path}")

def main():
    lineage_dir = Path('lineage')
    download_lineage_path = lineage_dir / 'download_lineage.csv'
    
    if not download_lineage_path.exists():
        print(f"❌ Error: Input file not found at '{download_lineage_path}'")
        print("Please run the 'prepare_takeout_data.py' script first.")
        return

    print(f"Loading download records from '{download_lineage_path}'...")
    download_df = pd.read_csv(download_lineage_path).fillna('')
    
    processor = ImageProcessor()
    
    # NEW: Filter out images that have already been processed
    unprocessed_df = download_df[~download_df['md5_hash'].isin(processor.processed_hashes)]
    total_to_process = len(unprocessed_df)

    if total_to_process == 0:
        print("✅ All images have already been processed. Nothing to do.")
        return
    
    print(f"Starting processing for {total_to_process} new images...")
    
    for index, row in unprocessed_df.iterrows():
        current_num = index + 1
        progress_prefix = f"[{current_num}/{total_to_process}]"
        
        record = row.to_dict()
        md5_hash = record.get('md5_hash')

        print(f"{progress_prefix} Processing: {record.get('original_filename')}")
        processing_record = processor.process_image_with_lineage(record)
        processor.all_processing_records.append(processing_record)

        # NEW: Add the hash to the set of processed hashes for the current session
        if md5_hash and processing_record.get('processing_status') == 'completed':
            processor.processed_hashes.add(md5_hash)
    
    # NEW: Save all records (old and new)
    processor.save_lineage()
    
    successful_processing = len([r for r in processor.all_processing_records if r.get('processing_status') == 'completed'])
    print(f"✅ Processing complete! A total of {successful_processing} images are now processed.")

if __name__ == '__main__':
    main()