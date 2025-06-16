import os
import json
from PIL import Image

# Define paths
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
processed_webp_dir = os.path.join(base_dir, 'processed_webp')
processed_webp_thumbnails_dir = os.path.join(base_dir, 'processed_webp_thumbnails')
lineage_file_path = os.path.join(base_dir, 'processing_lineage.json')

# Create thumbnails directory if it doesn't exist
os.makedirs(processed_webp_thumbnails_dir, exist_ok=True)

# Load processing_lineage.json
if os.path.exists(lineage_file_path):
    try:
        with open(lineage_file_path, 'r') as f:
            processing_lineage = json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: {lineage_file_path} is corrupted. Initializing empty lineage.")
        processing_lineage = {}
else:
    processing_lineage = {}

THUMBNAIL_HEIGHT = 360

def generate_thumbnails():
    """Generates thumbnails for images in the processed_webp directory."""
    processed_files = 0
    skipped_existing = 0
    error_count = 0

    for filename in os.listdir(processed_webp_dir):
        if not filename.endswith(".webp"):
            continue

        original_stem = filename.split('.')[0]
        # The -adasstory check is removed as per understanding that stem is just original filename without .webp
        # if not original_stem.endswith("-adasstory"):
        #     print(f"Skipping {filename} as it does not follow the '-adasstory' naming convention for stem.")
        #     continue

        thumbnail_filename = f"{original_stem}-h{THUMBNAIL_HEIGHT}-thumb.webp"
        thumbnail_path = os.path.join(processed_webp_thumbnails_dir, thumbnail_filename)
        original_image_path = os.path.join(processed_webp_dir, filename)

        # Initialize lineage entry for the original_stem if not present
        if original_stem not in processing_lineage:
            processing_lineage[original_stem] = {}
        lineage_entry = processing_lineage[original_stem]

        try:
            if os.path.exists(thumbnail_path):
                # Thumbnail exists, get its info and update lineage
                with Image.open(thumbnail_path) as thumb_img:
                    thumbnail_width, thumbnail_height = thumb_img.size
                thumbnail_file_size_bytes = os.path.getsize(thumbnail_path)

                lineage_entry['thumbnail_final_filename'] = thumbnail_filename
                lineage_entry['thumbnail_processed_path'] = thumbnail_path
                lineage_entry['thumbnail_width'] = thumbnail_width
                lineage_entry['thumbnail_height'] = thumbnail_height
                lineage_entry['thumbnail_file_size_bytes'] = thumbnail_file_size_bytes
                lineage_entry['thumbnail_generation_status'] = "success_skipped_existing"
                lineage_entry['thumbnail_error_message'] = None
                print(f"Skipping existing thumbnail, metadata updated for: {thumbnail_filename}")
                skipped_existing += 1
            else:
                # Thumbnail does not exist, generate it
                with Image.open(original_image_path) as img:
                    original_width, original_height = img.size
                    new_width = int((original_width / original_height) * THUMBNAIL_HEIGHT)

                    resized_img = img.resize((new_width, THUMBNAIL_HEIGHT), Image.Resampling.LANCZOS)
                    resized_img.save(thumbnail_path, 'WEBP')

                    thumbnail_file_size_bytes = os.path.getsize(thumbnail_path)
                    thumbnail_width, thumbnail_height = resized_img.size # Dimensions of the saved thumb

                    lineage_entry['thumbnail_final_filename'] = thumbnail_filename
                    lineage_entry['thumbnail_processed_path'] = thumbnail_path
                    lineage_entry['thumbnail_width'] = thumbnail_width
                    lineage_entry['thumbnail_height'] = thumbnail_height
                    lineage_entry['thumbnail_file_size_bytes'] = thumbnail_file_size_bytes
                    lineage_entry['thumbnail_generation_status'] = "success"
                    lineage_entry['thumbnail_error_message'] = None
                    print(f"Successfully generated thumbnail: {thumbnail_filename}")
            processed_files += 1

        except Exception as e:
            print(f"Error processing {filename} (or its existing thumbnail {thumbnail_filename}): {e}")
            lineage_entry['thumbnail_final_filename'] = thumbnail_filename # Store intended name
            lineage_entry['thumbnail_processed_path'] = thumbnail_path # Store intended path
            lineage_entry['thumbnail_generation_status'] = "failure"
            lineage_entry['thumbnail_error_message'] = str(e)
            # Optionally clear other fields if error occurs
            lineage_entry.pop('thumbnail_width', None)
            lineage_entry.pop('thumbnail_height', None)
            lineage_entry.pop('thumbnail_file_size_bytes', None)
            error_count += 1
            processed_files +=1 # Count as processed even if error

    # Save the updated processing_lineage dictionary
    try:
        with open(lineage_file_path, 'w') as f:
            json.dump(processing_lineage, f, indent=4)
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
