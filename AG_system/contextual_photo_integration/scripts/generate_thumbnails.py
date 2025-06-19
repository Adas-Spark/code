import json
from PIL import Image
from pathlib import Path

# Define paths
base_dir = Path(__file__).resolve().parent.parent
processed_webp_dir = base_dir / 'processed_webp'
processed_webp_thumbnails_dir = base_dir / 'processed_webp_thumbnails'
lineage_file_path = base_dir / 'lineage' / 'processing_lineage.json'

# Create thumbnails directory if it doesn't exist
processed_webp_thumbnails_dir.mkdir(parents=True, exist_ok=True)

if lineage_file_path.exists():
    try:
        with open(lineage_file_path, 'r') as f:
            processing_lineage_list = json.load(f)
        print(f"Loaded {len(processing_lineage_list)} records from lineage file")
    except json.JSONDecodeError:
        print(f"Warning: {lineage_file_path} is corrupted. Initializing empty lineage.")
        processing_lineage_list = []
else:
    processing_lineage_list = []
    print("No existing lineage file found. Starting fresh.")

THUMBNAIL_HEIGHT = 360

def generate_thumbnails():
    """Generates thumbnails for images in the processed_webp directory."""
    processed_files = 0
    skipped_existing = 0
    error_count = 0

    lineage_by_filename = {}
    for record in processing_lineage_list:
        final_filename = record.get('final_filename')
        if final_filename:
            lineage_by_filename[final_filename] = record

    for filename_path_obj in processed_webp_dir.iterdir():
        if not filename_path_obj.name.endswith(".webp"):
            continue

        # Extract stem for thumbnail naming (remove .webp extension)
        original_stem = filename_path_obj.stem
        thumbnail_filename = f"{original_stem}-h{THUMBNAIL_HEIGHT}-thumb.webp"
        thumbnail_path = processed_webp_thumbnails_dir / thumbnail_filename
        original_image_path = filename_path_obj # Use the Path object directly

        lineage_record = lineage_by_filename.get(filename_path_obj.name)
        if not lineage_record:
            print(f"Warning: No lineage record found for {filename_path_obj.name}")
            continue

        try:
            if thumbnail_path.exists():
                # Thumbnail exists, get its info and update lineage
                with Image.open(thumbnail_path) as thumb_img:
                    thumbnail_width, thumbnail_height = thumb_img.size
                thumbnail_file_size_bytes = thumbnail_path.stat().st_size

                lineage_record['thumbnail_final_filename'] = thumbnail_filename
                lineage_record['thumbnail_processed_path'] = str(thumbnail_path) # Store as string for JSON
                lineage_record['thumbnail_width'] = thumbnail_width
                lineage_record['thumbnail_height'] = thumbnail_height
                lineage_record['thumbnail_file_size_bytes'] = thumbnail_file_size_bytes
                lineage_record['thumbnail_generation_status'] = "success_skipped_existing"
                lineage_record['thumbnail_error_message'] = None
                print(f"Skipping existing thumbnail, metadata updated for: {thumbnail_filename}")
                skipped_existing += 1
            else:
                # Thumbnail does not exist, generate it
                with Image.open(original_image_path) as img:
                    original_width, original_height = img.size
                    new_width = int((original_width / original_height) * THUMBNAIL_HEIGHT)

                    resized_img = img.resize((new_width, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
                    resized_img.save(thumbnail_path, 'WEBP')

                    thumbnail_file_size_bytes = thumbnail_path.stat().st_size
                    thumbnail_width, thumbnail_height = resized_img.size

                    lineage_record['thumbnail_final_filename'] = thumbnail_filename
                    lineage_record['thumbnail_processed_path'] = str(thumbnail_path) # Store as string for JSON
                    lineage_record['thumbnail_width'] = thumbnail_width
                    lineage_record['thumbnail_height'] = thumbnail_height
                    lineage_record['thumbnail_file_size_bytes'] = thumbnail_file_size_bytes
                    lineage_record['thumbnail_generation_status'] = "success"
                    lineage_record['thumbnail_error_message'] = None
                    print(f"Successfully generated thumbnail: {thumbnail_filename}")
            
            processed_files += 1

        except Exception as e:
            print(f"Error processing {filename_path_obj.name} (or its existing thumbnail {thumbnail_filename}): {e}")
            lineage_record['thumbnail_final_filename'] = thumbnail_filename
            lineage_record['thumbnail_processed_path'] = str(thumbnail_path) # Store as string for JSON
            lineage_record['thumbnail_generation_status'] = "failure"
            lineage_record['thumbnail_error_message'] = str(e)
            # Clear other fields if error occurs
            lineage_record.pop('thumbnail_width', None)
            lineage_record.pop('thumbnail_height', None)
            lineage_record.pop('thumbnail_file_size_bytes', None)
            error_count += 1
            processed_files += 1

    try:
        with open(lineage_file_path, 'w') as f:
            json.dump(processing_lineage_list, f, indent=2)
        print(f"Processing lineage saved to {lineage_file_path}")
    except IOError as e:
        print(f"Error saving processing lineage to {lineage_file_path}: {e}")

    print(f"\nThumbnail generation summary:")
    print(f"Total images processed/checked: {processed_files}")
    print(f"Thumbnails generated: {processed_files - skipped_existing - error_count}")
    print(f"Skipped existing thumbnails (metadata updated): {skipped_existing}")
    print(f"Errors encountered: {error_count}")


if __name__ == '__main__':
    generate_thumbnails()
    print("\nThumbnail generation process completed.")