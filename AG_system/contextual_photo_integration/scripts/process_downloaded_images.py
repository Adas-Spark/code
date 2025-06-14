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
        
        # Processing configuration
        self.MAX_DIMENSION = 1920
        self.FILENAME_TAG = '-adasstory'
        
    def get_adaptive_quality(self, file_size_bytes):
        """Determine WebP quality based on source file size"""
        if file_size_bytes < 500000:  # Under 500KB  
            return 90  # Higher quality for already compressed images
        else:
            return 85  # Standard quality for larger files
    
    def process_image_with_lineage(self, download_record):
        """Process a downloaded image into optimized WebP"""
        
        # Skip items that were not successfully processed in the previous step
        if download_record.get('status') not in ['processed', 'processed_with_warnings']:
            # If the record is from an older version of download_lineage.csv that used 'downloaded'
            if download_record.get('status') == 'downloaded':
                # This block can be removed once all download_lineage.csv files are updated
                pass # Allow processing for backward compatibility
            else:
                # For new statuses, if not 'processed' or 'processed_with_warnings', skip
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
            # Load downloaded image
            local_path_str = download_record.get('local_path')
            if not local_path_str or not Path(local_path_str).exists():
                processing_record.update({
                    'processing_status': 'processing_failed',
                    'processing_error': f"Local file not found: {local_path_str}"
                })
                print(f"❌ Failed to process: {download_record.get('original_filename', 'Unknown file')} - File not found at {local_path_str}")
                return processing_record

            local_path = Path(local_path_str)
            img = Image.open(local_path)
            
            original_size = img.size
            # Get file size for adaptive quality, as it's not in download_record anymore
            file_size_bytes = local_path.stat().st_size
            processing_record['original_file_size_bytes'] = file_size_bytes # Log the original file size

            processing_record['transformations'].append({
                'step': 'loaded_from_disk',
                'original_dimensions': f"{original_size[0]}x{original_size[1]}",
                'original_format': img.format,
                'original_mode': img.mode,
                'original_file_size_bytes': file_size_bytes
            })
            
            # Handle EXIF orientation
            if hasattr(img, '_getexif') and img._getexif():
                exif = img._getexif()
                orientation_key = 274
                if orientation_key in exif:
                    orientation = exif[orientation_key]
                    if orientation == 3: 
                        img = img.rotate(180, expand=True)
                        processing_record['transformations'].append({'step': 'rotated_180'})
                    elif orientation == 6: 
                        img = img.rotate(270, expand=True)
                        processing_record['transformations'].append({'step': 'rotated_270'})
                    elif orientation == 8: 
                        img = img.rotate(90, expand=True)
                        processing_record['transformations'].append({'step': 'rotated_90'})
            
            # Resize while maintaining aspect ratio
            img.thumbnail((self.MAX_DIMENSION, self.MAX_DIMENSION), Image.Resampling.LANCZOS)
            new_size = img.size
            processing_record['transformations'].append({
                'step': 'resized',
                'new_dimensions': f"{new_size[0]}x{new_size[1]}",
                'max_dimension_limit': self.MAX_DIMENSION
            })
            
            # Generate output filename
            original_filename = download_record.get('original_filename', 'unknown_original')
            file_stem = os.path.splitext(original_filename)[0]
            new_filename = f"{file_stem}{self.FILENAME_TAG}.webp"
            output_path = self.processed_dir / new_filename
            
            # Determine quality based on original file size (obtained above)
            webp_quality = self.get_adaptive_quality(file_size_bytes)
            
            # Convert and save as WebP
            img.save(output_path, 'webp', quality=webp_quality)
            
            processing_record.update({
                'final_filename': new_filename,
                'processed_file_path': str(output_path),
                'webp_quality': webp_quality,
                'processing_status': 'completed'
            })
            
            processing_record['transformations'].append({
                'step': 'converted_to_webp',
                'quality': webp_quality,
                'output_path': str(output_path),
                'final_size_bytes': output_path.stat().st_size
            })
            
            print(f"✅ Processed: {download_record['original_filename']} -> {new_filename}")
            
        except Exception as e:
            processing_record.update({
                'processing_status': 'processing_failed',
                'processing_error': str(e)
            })
            print(f"❌ Failed to process: {download_record['original_filename']} - {e}")
        
        return processing_record

def main():
    # Load download lineage
    # Ensure the CSV path is correct, lineage_dir might be better if it was saved there.
    # However, the previous script saved it to the root, so we load from root.
    download_lineage_path = 'download_lineage.csv'
    if not Path(download_lineage_path).exists():
        # Try path inside lineage folder, if the previous script's save location is changed.
        download_lineage_path = Path('lineage') / 'download_lineage.csv'
        if not Path(download_lineage_path).exists():
            print(f"Error: download_lineage.csv not found in root or lineage/ directory.")
            return

    download_df = pd.read_csv(download_lineage_path)
    
    processor = ImageProcessor()
    all_processing_records = []
    
    print(f"Starting processing for {len(download_df)} downloaded images...")
    
    for index, row in download_df.iterrows():
        processing_record = processor.process_image_with_lineage(row.to_dict())
        all_processing_records.append(processing_record)
        
        # Save incremental progress
        if (index + 1) % 25 == 0:
            with open('lineage/processing_lineage.json', 'w') as f:
                json.dump(all_processing_records, f, indent=2)
            print(f"Progress: {index + 1}/{len(download_df)} images processed")
    
    # Final save
    with open('lineage/processing_lineage.json', 'w') as f:
        json.dump(all_processing_records, f, indent=2)
    
    # Create CSV for Phase 3
    processing_df = pd.DataFrame(all_processing_records)
    processing_df.to_csv('processing_lineage.csv', index=False)
    
    successful_processing = len([r for r in all_processing_records if r.get('processing_status') == 'completed'])
    print(f"✅ Processing complete! {successful_processing}/{len(download_df)} images processed successfully")

if __name__ == '__main__':
    main()