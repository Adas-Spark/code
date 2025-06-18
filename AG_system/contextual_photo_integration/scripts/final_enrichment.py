#!/usr/bin/env python3
"""
Final Enhanced Caption Generation Script for Ada's Photos
Generates multiple captions per image with optional Ada context and temporal awareness.

USAGE EXAMPLES:
===============
# NEW: Run analysis on thumbnails to save on cost/time
python final_enrichment.py --model gemini-2.5-pro --ada-context --image-source thumbnail

# NEW: Run on a hand-picked subset of images for testing
python final_enrichment.py --model gemini-2.5-pro --input-file lineage/my_test_images.csv

# Basic run with default model and Ada context
python final_enrichment.py --model gemini-2.5-pro --ada-context

# Test with first 5 images using Flash model
python final_enrichment.py --model gemini-2.5-flash --ada-context --limit 5

REQUIRED SETUP:
==============
1. Update PROJECT_ID constant with your Google Cloud project ID
2. Ensure input CSV exists and contains 'url' and 'wordpress_url_thumbnail' columns
3. Verify all image URLs in CSV are accessible
4. Install: pip install pandas "google-cloud-aiplatform>=1.55"

COMMAND LINE OPTIONS:
====================
--model MODEL_NAME          Required. Gemini model to use.
--input-file FILE_PATH      Optional. Path to the input CSV.
--image-source [full|thumb] Optional. Use full .webp or thumbnail for analysis. (default: full)
--ada-context               Optional. Include Ada's story context in prompts.
--limit N                   Optional. Limit processing to first N images.

OUTPUT:
=======
Creates 'multi_prompt_enrichment_output.csv' in ../lineage/ with detailed logs, including:
- ... (all previous columns)
- image_source_used: Tracks if the 'full' or 'thumbnail' URL was used for analysis.
- record_hash: Unique identifier for each caption record for traceability.
"""

import pandas as pd
from pathlib import Path
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from datetime import datetime, timedelta
import json
import argparse
import hashlib
import uuid
import time
import random

# --- Configuration ---
PROJECT_ID = "adas-living-story-pics-2025"  # Your Google Cloud project ID
LOCATION = "us-central1"           # The GCP region for Vertex AI
DAYS_WINDOW = 7                    # Window for checking "nearness" to important dates (days)
MAX_RETRIES = 3
BASE_DELAY = 2.0  # Base delay between retries in seconds
MAX_DELAY = 10.0  # Maximum delay between retries

# --- (Ada's context, important dates, and prompts remain the same) ---
IMPORTANT_DATES_STR = {
    "birth": "2018-06-08",
    "diagnosis": "2022-05-05",
    "transplant": "2022-09-13",
    "death": "2023-07-22"
}

ADA_CONTEXT = """This image is from Ada's story - a brave 5-year-old girl who fought leukemia with remarkable spirit. Some photos are from before she was diagnosed. Important dates: she was born 6-8-18, diagnosed 5-5-22, bone marrow transplant from her brother on 9-13-22, and died 7-22-23. It is possible that some photos have the incorrect date. When describing, be sensitive to the medical journey while celebrating moments of joy and connection."""

PROMPTS_TO_TEST = {
    "EMOTIONAL": "Describe the emotional moment and feelings in this image of a young girl's journey",
    "MOMENT": "A brief, poetic description of the emotional moment or action (15-20 words). Focus on: what's happening, the feeling, the discovery, the connection. Example: \"The wonder of discovering a butterfly on a sunny afternoon\"",
    "CONTEXTUAL": "What story does this moment tell about Ada's character, relationships, or journey? Focus on the emotions, interactions, and personality traits visible in this scene.",
    "STORY": "Describe the story this image tells about Ada's life and spirit. What does this moment reveal about her personality, her relationships, or her approach to challenges?",
    "CHARACTER": "What character traits, emotions, or relationships are evident in this image? Describe Ada's spirit and personality as shown in this moment."
}

def generate_record_hash(original_filename, model_used, prompt_name, processing_timestamp):
    """
    Generate a deterministic unique hash for each caption record.
    This ensures we can always trace back how any specific caption was generated.
    
    Args:
        original_filename: The source image filename
        model_used: The AI model that generated the caption
        prompt_name: The specific prompt type used
        processing_timestamp: When this record was processed
    
    Returns:
        A short, unique hash string (8 characters)
    """
    # Create a deterministic string from the key parameters
    hash_input = f"{original_filename}_{model_used}_{prompt_name}_{processing_timestamp}"
    
    # Generate SHA-256 hash and take first 8 characters for readability
    full_hash = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    return full_hash[:8]

# --- (get_temporal_context and save_intermediate_results remain the same) ---
def get_temporal_context(actual_photo_dt, important_dates_dt):
    if not actual_photo_dt:
        return ""
    for date_name, important_date_dt in important_dates_dt.items():
        days_diff = (actual_photo_dt - important_date_dt).days
        if abs(days_diff) <= DAYS_WINDOW:
            if days_diff == 0: return f" This photo was taken on the day of Ada's {date_name}."
            elif days_diff < 0: return f" This photo was taken {abs(days_diff)} days before Ada's {date_name}."
            else: return f" This photo was taken {days_diff} days after Ada's {date_name}."
    birth_date = important_dates_dt["birth"]
    if (actual_photo_dt.month == birth_date.month and actual_photo_dt.day == birth_date.day and actual_photo_dt.year > birth_date.year):
        age = actual_photo_dt.year - birth_date.year
        return f" This photo was taken on Ada's {age}{'st' if age == 1 else 'nd' if age == 2 else 'rd' if age == 3 else 'th'} birthday."
    # Check near birthday anniversaries
    if actual_photo_dt.month == birth_date.month and actual_photo_dt.year > birth_date.year:
        age = actual_photo_dt.year - birth_date.year
        days_to_birthday = birth_date.day - actual_photo_dt.day
        
        if abs(days_to_birthday) <= DAYS_WINDOW:
            ordinal = f"{age}{'st' if age == 1 else 'nd' if age == 2 else 'rd' if age == 3 else 'th'}"
            if days_to_birthday > 0:
                return f" This photo was taken {days_to_birthday} days before Ada's {ordinal} birthday."
            elif days_to_birthday < 0:
                return f" This photo was taken {abs(days_to_birthday)} days after Ada's {ordinal} birthday."
    
    # Check death anniversaries (any July 22nd after 2023)
    death_date = important_dates_dt["death"]
    if (actual_photo_dt.month == death_date.month and 
        actual_photo_dt.day == death_date.day and 
        actual_photo_dt.year > death_date.year):
        
        years_since = actual_photo_dt.year - death_date.year
        ordinal = f"{years_since}{'st' if years_since == 1 else 'nd' if years_since == 2 else 'rd' if years_since == 3 else 'th'}"
        return f" This photo was taken on the {ordinal} anniversary of Ada's passing."
    
    # Check near death anniversaries
    if (actual_photo_dt.month == death_date.month and 
        actual_photo_dt.year > death_date.year):
        
        years_since = actual_photo_dt.year - death_date.year
        days_to_anniversary = death_date.day - actual_photo_dt.day
        
        if abs(days_to_anniversary) <= DAYS_WINDOW:
            ordinal = f"{years_since}{'st' if years_since == 1 else 'nd' if years_since == 2 else 'rd' if years_since == 3 else 'th'}"
            if days_to_anniversary > 0:
                return f" This photo was taken {days_to_anniversary} days before the {ordinal} anniversary of Ada's passing."
            elif days_to_anniversary < 0:
                return f" This photo was taken {abs(days_to_anniversary)} days after the {ordinal} anniversary of Ada's passing."
    return ""

def save_intermediate_results(records, base_dir):
    if records:
        temp_df = pd.DataFrame(records)
        temp_path = base_dir / 'lineage' / 'temp_enrichment_progress.csv'
        temp_df.to_csv(temp_path, index=False)
        return temp_path
    return None

def calculate_processing_hash(original_filename, model_used, image_url, prompt_name, ada_context_included, image_source_used):
    """Calculate a hash representing the unique processing parameters"""
    # Create a string of all the parameters that affect processing
    param_string = f"{original_filename}|{model_used}|{image_url}|{prompt_name}|{ada_context_included}|{image_source_used}"
    
    # Return a short hash
    return hashlib.md5(param_string.encode()).hexdigest()[:12]

def process_image_with_retry(vision_model, image_part, api_prompt_text, original_filename, max_retries=MAX_RETRIES):
    """Process image with exponential backoff retry logic"""
    
    for attempt in range(max_retries + 1):
        try:
            # Add a small delay before each attempt (except first)
            if attempt > 0:
                delay = min(BASE_DELAY * (2 ** (attempt - 1)) + random.uniform(0, 1), MAX_DELAY)
                print(f"       ⏳ Retry {attempt}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)
            
            response = vision_model.generate_content([image_part, api_prompt_text])
            return response  # Success!
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a timeout/fetch error that might be worth retrying
            if any(keyword in error_str.upper() for keyword in ['TIMEOUT', 'REJECTED_FC_TIMEOUT', 'URL_TIMEOUT', 'FETCH']):
                if attempt < max_retries:
                    print(f"       ⚠️  Timeout error on attempt {attempt + 1}: {error_str}")
                    continue  # Try again
                else:
                    print(f"       ❌ Max retries ({max_retries}) exceeded for {original_filename}")
                    raise  # Re-raise the last exception
            else:
                # For non-timeout errors, don't retry
                print(f"       ❌ Non-retryable error: {error_str}")
                raise
    
    # This shouldn't be reached, but just in case
    raise Exception(f"Failed after {max_retries} retries")

def add_processing_delay():
    """Add a small delay between image processing to be nice to the API"""
    delay = random.uniform(1.0, 3.0)  # Random delay between 1-3 seconds
    time.sleep(delay)

def load_existing_results(output_csv_path):
    """Load existing results and return a set of processed parameter hashes and the existing DataFrame"""
    if output_csv_path.exists():
        try:
            existing_df = pd.read_csv(output_csv_path)
            # Create a set of processed parameter hashes
            processed_hashes = set()
            for _, row in existing_df.iterrows():
                # Only include successful records in the hash check
                if row.get('status') == 'success':
                    param_hash = calculate_processing_hash(
                        original_filename=row['original_filename'],
                        model_used=row['model_used'],
                        image_url=row['image_url'],
                        prompt_name=row['prompt_name'],
                        ada_context_included=row['ada_context_included'],
                        image_source_used=row['image_source_used']
                    )
                    processed_hashes.add(param_hash)
            
            print(f"📁 Found existing results: {len(existing_df)} records")
            print(f"🔍 Already processed: {len(processed_hashes)} unique parameter combinations")
            return processed_hashes, existing_df
        except Exception as e:
            print(f"⚠️  Warning: Could not load existing results: {e}")
            return set(), pd.DataFrame()
    else:
        print("📄 No existing results file found - starting fresh")
        return set(), pd.DataFrame()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Generate multiple captions for Ada\'s photos using Gemini models',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--model', 
                        required=True,
                        choices=[
                            'gemini-2.5-pro',                        # Most advanced reasoning model (auto-updating alias)
                            'gemini-2.5-flash',                      # Best price/performance with thinking capabilities (auto-updating alias)
                            'gemini-2.5-flash-lite-preview-06-17',   # Most balanced model, optimized for low latency
                            'gemini-2.0-flash-001',                  # Latest stable - multimodal, 1M token context
                            'gemini-2.0-flash-lite-001',             # Latest stable - cost efficient, faster than 1.5 Flash
                        ],
                        help='Gemini model to use for caption generation')

    parser.add_argument('--input-file',
                        type=str,
                        default='lineage/complete_image_lineage.csv',
                        help='Path to the input CSV file relative to the project root. (default: %(default)s)')
    
    # --- NEW ARGUMENT to choose between full and thumbnail images ---
    parser.add_argument('--image-source',
                        type=str,
                        default='full',
                        choices=['full', 'thumbnail'],
                        help="Choose image version for analysis: 'full' for processed .webp, 'thumbnail' for the smaller version. (default: %(default)s)")

    parser.add_argument('--ada-context', 
                        action='store_true',
                        help='Include Ada\'s story context in prompts')
    
    parser.add_argument('--limit', 
                        type=int,
                        help='Limit processing to first N images (default: process all)')
    
    parser.add_argument('--force-reprocess', 
                        action='store_true',
                        help='Reprocess all images even if they already exist in output file')

    return parser.parse_args()

def final_enrich_data(args):
    base_dir = Path(__file__).resolve().parent.parent
    input_csv_path = base_dir / args.input_file
    output_csv_path = base_dir / 'lineage' / 'multi_prompt_enrichment_output.csv'
    
    if not input_csv_path.exists():
        print(f"❌ Error: Input file not found: {input_csv_path}")
        return

    # Load existing results for stateful processing
    processed_hashes, existing_df = load_existing_results(output_csv_path)

    print("🔧 Initializing Vertex AI...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    
    vision_model = GenerativeModel(args.model)
    master_df = pd.read_csv(input_csv_path)
    
    if args.limit:
        master_df = master_df.head(args.limit)
        print(f"🔍 Limiting to first {args.limit} images for testing from {args.input_file}")

    # Filter out already processed parameter combinations
    images_and_prompts_to_process = []
    skipped_count = 0
    total_combinations = 0
    
    for index, row in master_df.iterrows():
        original_filename = row.get('original_filename', 'N/A')
        
        # Determine which URL will be used (same logic as in processing loop)
        url_to_use = None
        image_source_used = 'full'
        
        if args.image_source == 'thumbnail':
            thumbnail_url = row.get('wordpress_url_thumbnail')
            if thumbnail_url and pd.notna(thumbnail_url):
                url_to_use = thumbnail_url
                image_source_used = 'thumbnail'
            else:
                url_to_use = row.get('url')
        else:
            url_to_use = row.get('url')
        
        # Check each prompt combination
        for prompt_name in PROMPTS_TO_TEST.keys():
            total_combinations += 1
            
            if not args.force_reprocess:
                param_hash = calculate_processing_hash(
                    original_filename=original_filename,
                    model_used=args.model,
                    image_url=url_to_use,
                    prompt_name=prompt_name,
                    ada_context_included=args.ada_context,
                    image_source_used=image_source_used
                )
                
                if param_hash in processed_hashes:
                    skipped_count += 1
                    continue
            
            # This combination needs processing
            images_and_prompts_to_process.append((index, row, prompt_name, url_to_use, image_source_used))
    
    # Group by image for cleaner processing
    images_to_process = []
    images_seen = set()
    
    for index, row, prompt_name, url_to_use, image_source_used in images_and_prompts_to_process:
        image_key = (index, row['original_filename'])
        if image_key not in images_seen:
            images_to_process.append((index, row))
            images_seen.add(image_key)
    
    unique_images_to_process = len(images_to_process)
    print(f"📊 Total images in input: {len(master_df)}")
    print(f"📊 Total image+prompt combinations: {total_combinations}")
    print(f"⏭️  Already processed combinations (skipping): {skipped_count}")
    print(f"🔄 New images to process: {unique_images_to_process}")
    print(f"🔄 New combinations to process: {len(images_and_prompts_to_process)}")

    IMPORTANT_DATES_DT = {name: datetime.fromisoformat(date_str) for name, date_str in IMPORTANT_DATES_STR.items()}
  
    # --- Display Configuration ---
    print("\n" + "="*60)
    print("🚀 STARTING ENHANCED CAPTION GENERATION")
    print("="*60)
    print(f"📄 Input File: {args.input_file}")
    print(f"🖼️  Image Source: {args.image_source.upper()}")
    print(f"📊 Dataset: {len(master_df)} images to process")
    print(f"🤖 Model: {args.model}")
    print(f"📖 Ada Context: {'✅ Enabled' if args.ada_context else '❌ Disabled'}")
    print("-" * 60)
  
    # Start with existing records
    all_output_records = existing_df.to_dict('records') if not existing_df.empty else []
    successful_count = 0
    error_count = 0
    total_tokens = 0

    # Get current timestamp for this processing run
    processing_timestamp = datetime.now().isoformat()

    for index, row in images_to_process:  
        try:
            original_filename = row.get('original_filename', 'N/A')
            
            # --- Select the correct URL based on the --image-source argument ---
            url_to_use = None
            source_used_for_log = 'full'  # Default to full

            if args.image_source == 'thumbnail':
                thumbnail_url = row.get('wordpress_url_thumbnail')
                # Check if thumbnail URL exists and is not empty/null
                if thumbnail_url and pd.notna(thumbnail_url):
                    url_to_use = thumbnail_url
                    source_used_for_log = 'thumbnail'
                else:
                    print(f"   ⚠️  Warning: Thumbnail URL not found for '{original_filename}'. Falling back to full size.")
                    url_to_use = row.get('url')
            else:  # Default case if --image-source is 'full'
                url_to_use = row.get('url')

            # Verify that we found a usable URL before proceeding
            if not url_to_use or pd.isna(url_to_use):
                raise ValueError(f"No valid URL found for '{original_filename}'")

            # --- Get temporal context ---
            actual_photo_time_str = row.get('creation_date')
            actual_photo_dt = None
            if actual_photo_time_str and isinstance(actual_photo_time_str, str):
                try:
                    actual_photo_dt = datetime.fromisoformat(actual_photo_time_str.replace("_fallback_mtime", ""))
                except ValueError:
                    actual_photo_dt = None
            
            current_prompts = PROMPTS_TO_TEST.copy()
            temporal_context = get_temporal_context(actual_photo_dt, IMPORTANT_DATES_DT)
            if temporal_context:
                temporal_instruction = f"{temporal_context} If this timing is significant, tastefully and with respect weave that context into your response."
                for key in ['CONTEXTUAL', 'STORY', 'CHARACTER']:
                    if key in current_prompts:
                        current_prompts[key] += temporal_instruction

            api_prompt_text = ""
            if args.ada_context:
                api_prompt_text += ADA_CONTEXT + "\n\n"
            api_prompt_text += f"Generate captions for this image using each of these prompts:\n\nprompts = {json.dumps(current_prompts, indent=2)}\n\nFormat your response as valid JSON:\n{{\n    \"EMOTIONAL\": \"[your description]\",\n    \"MOMENT\": \"[your description]\",\n    \"CONTEXTUAL\": \"[your description]\",\n    \"STORY\": \"[your description]\",\n    \"CHARACTER\": \"[your description]\"\n}}"

            # Use the selected URL for the API call with retry logic
            image_part = Part.from_uri(url_to_use, mime_type="image/webp")
            
            try:
                response = process_image_with_retry(vision_model, image_part, api_prompt_text, original_filename)
            except Exception as retry_error:
                # If all retries failed, treat as a regular error
                raise retry_error
            
            response_text = response.text.strip()
            # JSON parsing and token extraction logic
            try:
                parsed_captions = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    response_text = response_text[json_start:json_end].strip()
                    parsed_captions = json.loads(response_text)
                else: raise

            usage_metadata = response.usage_metadata
            tokens_used = usage_metadata.total_token_count
            prompt_tokens = getattr(usage_metadata, 'prompt_token_count', 'N/A')
            candidates_tokens = getattr(usage_metadata, 'candidates_token_count', 'N/A')
            total_tokens += tokens_used if isinstance(tokens_used, int) else 0

            # --- Output record to include the source used + unique hash ---
            for prompt_key, answer in parsed_captions.items():
                # Check if this specific combination was already processed
                param_hash = calculate_processing_hash(
                    original_filename=original_filename,
                    model_used=args.model,
                    image_url=url_to_use,
                    prompt_name=prompt_key,
                    ada_context_included=args.ada_context,
                    image_source_used=source_used_for_log
                )
                
                # Skip if this exact combination was already processed (shouldn't happen with proper filtering)
                if not args.force_reprocess and param_hash in processed_hashes:
                    continue
                
                output_record = {
                    "processing_order": index + 1,
                    "image_url": url_to_use, # Log the URL that was actually used
                    "original_filename": original_filename,
                    "model_used": args.model,
                    "total_tokens": tokens_used,
                    "prompt_tokens": prompt_tokens,
                    "candidates_tokens": candidates_tokens,
                    "prompt_name": prompt_key,
                    "prompt_answer": answer,
                    "photo_taken_time": actual_photo_time_str if actual_photo_dt else 'N/A',
                    "temporal_context": temporal_context.strip() if temporal_context else 'N/A',
                    "ada_context_included": args.ada_context,
                    "image_source_used": source_used_for_log,  # Track which source was used
                    "status": "success",
                    "param_hash": param_hash  # Optional: store hash for debugging
                }
                all_output_records.append(output_record)

            successful_count += 1
            print(f"  ✅ [{index+1:3d}/{len(images_to_process)}] {original_filename} ({source_used_for_log})")
            
            # Add delay between images to be respectful to the API
            if successful_count < len(images_to_process):  # Don't delay after the last image
                add_processing_delay()
            
            if (successful_count) % 10 == 0:
                temp_path = save_intermediate_results(all_output_records, base_dir)
                if temp_path:
                    print(f"   💾 Progress saved after {successful_count} successful images to {temp_path.name}")

        except Exception as e:  
            error_count += 1
            error_message = f"ERROR: {str(e)}"
            print(f"  ❌ [{index+1:3d}/{len(images_to_process)}] FAILED: {original_filename}")
            print(f"       Error: {error_message}")
            
            # Generate error record hash for consistency
            error_hash = generate_record_hash(original_filename, args.model, 'ERROR', processing_timestamp)
            
            output_record = {
                "processing_order": index + 1,
                "image_url": url_to_use if 'url_to_use' in locals() and url_to_use else row.get('url', 'N/A'),
                "original_filename": original_filename,
                "model_used": args.model,
                "total_tokens": 0, "prompt_tokens": 0, "candidates_tokens": 0,
                "prompt_name": 'ERROR',
                "prompt_answer": error_message,
                "photo_taken_time": 'N/A',
                "temporal_context": 'N/A',
                "ada_context_included": args.ada_context,
                "image_source_used": args.image_source, # Track which source was attempted
                "processing_timestamp": processing_timestamp,
                "record_hash": error_hash,
                "status": "error"
            }
            all_output_records.append(output_record)
  
    # --- Final summary and file saving logic ---
    output_df = pd.DataFrame(all_output_records)
    output_df.to_csv(output_csv_path, index=False)
    
    # Update summary stats to reflect total (existing + new)
    total_records = len(all_output_records)
    total_processed_images = len(set(f"{record['original_filename']}_{record['model_used']}" 
                                    for record in all_output_records if record['status'] == 'success'))
    
    temp_path = base_dir / 'lineage' / 'temp_enrichment_progress.csv'
    if temp_path.exists():
        temp_path.unlink()
  
    print("\n" + "="*60)
    print("🎉 ENRICHMENT COMPLETE!")
    print("="*60)
    print(f"📁 Output saved to: {output_csv_path.name}")
    print(f"✅ Successfully processed this run: {successful_count}/{len(images_to_process)} new images")
    print(f"❌ Failed this run: {error_count}/{len(images_to_process)} new images")
    print(f"📊 Total caption records in file: {total_records:,}")
    print(f"🎯 Total unique images processed: {total_processed_images:,}")
    if skipped_count > 0:
        print(f"⏭️  Images skipped (already processed): {skipped_count}")
    if successful_count > 0:
        avg_tokens = total_tokens / successful_count if isinstance(total_tokens, int) else "N/A"
        print(f"📈 Average tokens per image: {avg_tokens}")
    print("="*60)


if __name__ == '__main__':
    args = parse_arguments()
    final_enrich_data(args)