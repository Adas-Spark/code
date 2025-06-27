#!/usr/bin/env python3
"""
Upload Photo Captions to Pinecone Vector Database
Reads enriched caption data and uploads selected caption types to Pinecone.

USAGE EXAMPLES:
===============
# Upload emotional and contextual captions to photo-captions namespace
python scripts/upload_captions_to_pinecone.py --captions CONTEXTUAL,MOMENT # Used for POC and initial Prod

# Upload just emotional captions with dry-run to see what would be uploaded
python upload_captions_to_pinecone.py --captions EMOTIONAL --dry-run

# Upload to a specific index (if different from default)
python upload_captions_to_pinecone.py --captions EMOTIONAL,CONTEXTUAL --index-name my-custom-index

# Upload from a specific enrichment file
python upload_captions_to_pinecone.py --captions EMOTIONAL --input-file lineage/my_test_enrichment.csv

REQUIRED SETUP:
==============
1. Ensure .env file exists with PINECONE_API_KEY
2. Verify enrichment CSV contains required columns: original_filename, prompt_name, prompt_answer, record_hash
3. Ensure complete_image_lineage.csv exists for WordPress URL lookup

COMMAND LINE OPTIONS:
====================
--captions CAPTION_LIST     Required. Comma-separated list of caption types to upload.
                           Available: EMOTIONAL, MOMENT, CONTEXTUAL, STORY, CHARACTER
--input-file FILE_PATH      Optional. Path to enrichment CSV. (default: lineage/multi_prompt_enrichment_output.csv)
--lineage-file FILE_PATH    Optional. Path to complete lineage CSV. (default: lineage/complete_image_lineage.csv)
--index-name INDEX_NAME     Optional. Pinecone index name. (default: adas-memory-qa-prod)
--namespace NAMESPACE       Optional. Pinecone namespace. (default: photo-captions)
--dry-run                   Optional. Show what would be uploaded without actually uploading.
--batch-size SIZE           Optional. Embedding batch size. (default: 90)

OUTPUT:
=======
Uploads caption embeddings to Pinecone with metadata including:
- WordPress image and thumbnail URLs
- Photo creation date and Ada's age
- Caption generation details (model, prompt type, etc.)
- Unique traceability hash
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse
import json
import time
import os
from datetime import datetime
from tqdm.auto import tqdm
from pinecone import Pinecone
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def calculate_ada_age(photo_date_str):
    """
    Calculate Ada's age at the time a photo was taken.
    Ada was born on 2018-06-08.
    
    Args:
        photo_date_str: Date string in ISO format
    
    Returns:
        Age in years as float, or None if date cannot be parsed
    """
    if not photo_date_str or pd.isna(photo_date_str) or photo_date_str == 'N/A':
        return None
    
    try:
        # Handle fallback mtime suffix
        clean_date_str = str(photo_date_str).replace("_fallback_mtime", "")
        photo_date = datetime.fromisoformat(clean_date_str)
        ada_birth = datetime(2018, 6, 8)
        
        # Calculate age in years (including fractional years)
        age_delta = photo_date - ada_birth
        age_years = age_delta.days / 365.25
        
        return round(age_years, 2)
    except (ValueError, TypeError):
        return None

def extract_filename_stem(filename):
    """
    Extract the stem (filename without extension) for ID generation.
    
    Args:
        filename: Original filename
    
    Returns:
        Filename stem
    """
    if not filename or pd.isna(filename):
        return "unknown"
    
    # Remove file extension
    stem = Path(filename).stem
    
    # Clean up any problematic characters for IDs
    # Replace spaces, dots, and other special chars with underscores
    clean_stem = stem.replace(" ", "_").replace(".", "_").replace("-", "_")
    
    return clean_stem

def generate_pinecone_id(original_filename, prompt_name, record_hash):
    """
    Generate Pinecone vector ID following the pattern:
    {filename_stem}_{prompt_type}_{unique_hash}
    
    Args:
        original_filename: Source image filename
        prompt_name: Caption type (EMOTIONAL, CONTEXTUAL, etc.)
        record_hash: Unique hash from enrichment process
    
    Returns:
        Pinecone-compatible vector ID
    """
    filename_stem = extract_filename_stem(original_filename)
    return f"{filename_stem}_{prompt_name}_{record_hash}"

def generate_embeddings_in_batches(texts, pc, model_name, batch_size=90):
    """
    Generate embeddings in batches using Pinecone's hosted model.
    
    Args:
        texts: List of caption texts to embed
        pc: Pinecone client instance
        model_name: Embedding model name
        batch_size: Number of texts per batch
    
    Returns:
        List of embedding vectors
    """
    all_embeddings = []
    
    print(f"Generating embeddings for {len(texts)} captions in batches of {batch_size}...")
    
    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i + batch_size]
        
        # Generate embeddings for this batch
        batch_response = pc.inference.embed(
            model=model_name,
            inputs=batch,
            parameters={"input_type": "passage"}  # Using "passage" for stored content
        )
        
        # Extract embeddings from batch response
        batch_embeddings = []
        for embedding_obj in batch_response:
            if hasattr(embedding_obj, 'values'):
                batch_embeddings.append(embedding_obj.values)
            else:
                batch_embeddings.append(embedding_obj)
        
        all_embeddings.extend(batch_embeddings)
        
        # Small delay to be nice to the API
        time.sleep(0.1)
    
    return all_embeddings

def load_and_merge_data(enrichment_file, lineage_file, selected_captions):
    """
    Load enrichment data and merge with lineage data for WordPress URLs.
    
    Args:
        enrichment_file: Path to multi_prompt_enrichment_output.csv
        lineage_file: Path to complete_image_lineage.csv
        selected_captions: List of caption types to include
    
    Returns:
        Merged DataFrame with selected captions and WordPress URLs
    """
    print(f"Loading enrichment data from: {enrichment_file}")
    enrichment_df = pd.read_csv(enrichment_file)
    
    print(f"Loading lineage data from: {lineage_file}")
    lineage_df = pd.read_csv(lineage_file)
    
    # Filter to selected caption types and successful status
    enrichment_filtered = enrichment_df[
        (enrichment_df['prompt_name'].isin(selected_captions)) &
        (enrichment_df['status'] == 'success')
    ].copy()
    
    print(f"Filtered to {len(enrichment_filtered)} caption records of types: {selected_captions}")
    
    # Merge with lineage data to get WordPress URLs
    # Use original_filename as the merge key
    merged_df = pd.merge(
        enrichment_filtered,
        lineage_df[['original_filename', 'url', 'wordpress_url_thumbnail']],
        on='original_filename',
        how='left',
        suffixes=('', '_lineage')
    )
    
    # Check for missing WordPress URLs
    missing_urls = merged_df['url'].isna().sum()
    if missing_urls > 0:
        print(f"⚠️  Warning: {missing_urls} records missing WordPress URLs")
    
    print(f"Successfully merged data: {len(merged_df)} records ready for upload")
    return merged_df

def prepare_pinecone_records(merged_df, embeddings):
    """
    Prepare records for Pinecone upload with metadata.
    
    Args:
        merged_df: Merged DataFrame with caption and lineage data
        embeddings: List of embedding vectors
    
    Returns:
        List of Pinecone record dictionaries
    """
    pinecone_records = []
    
    print("Preparing Pinecone records with metadata...")
    
    for i, row in merged_df.iterrows():
        # Generate Pinecone ID (handle both 'record_hash' and 'param_hash' column names)
        hash_value = row.get('record_hash', row.get('param_hash', 'unknown'))
        vector_id = generate_pinecone_id(
            row['original_filename'],
            row['prompt_name'],
            hash_value
        )
        
        # Calculate Ada's age at photo time
        ada_age = calculate_ada_age(row['photo_taken_time'])
        
        # Prepare metadata (Pinecone has size limits, so keep essential info)
        metadata = {
            "caption_text": row['prompt_answer'][:1000],  # Truncate if very long
            "prompt_type": row['prompt_name'],
            "original_filename": row['original_filename'],
            "wordpress_url": row['url'] if pd.notna(row['url']) else None,
            "wordpress_thumbnail": row['wordpress_url_thumbnail'] if pd.notna(row['wordpress_url_thumbnail']) else None,
            "photo_date": row['photo_taken_time'] if row['photo_taken_time'] != 'N/A' else None,
            "ada_age": ada_age,
            "model_used": row['model_used'],
            "record_hash": hash_value,
            "source_type": "photo_caption",
            "temporal_context": row['temporal_context'] if (pd.notna(row['temporal_context']) and row['temporal_context'] != 'N/A') else None
        }
        
        # Remove None values and NaN values to keep metadata clean
        metadata = {k: v for k, v in metadata.items() if v is not None and not (isinstance(v, float) and np.isnan(v))}
        
        record = {
            "id": vector_id,
            "values": embeddings[i],
            "metadata": metadata
        }
        
        pinecone_records.append(record)
    
    print(f"Prepared {len(pinecone_records)} Pinecone records")
    return pinecone_records

def upload_to_pinecone(records, pc, index_name, default_namespace, moment_namespace=None, contextual_namespace=None, dry_run=False, batch_size=100):
    """
    Upload records to Pinecone index, routing to specific namespaces if provided.
    
    Args:
        records: List of Pinecone record dictionaries
        pc: Pinecone client instance
        index_name: Name of Pinecone index
        default_namespace: Default namespace for records not matching MOMENT or CONTEXTUAL
        moment_namespace: Namespace for MOMENT captions
        contextual_namespace: Namespace for CONTEXTUAL captions
        dry_run: If True, don't actually upload
        batch_size: Number of records per upload batch
    
    Returns:
        Number of successfully uploaded records
    """
    if not records:
        print("No records to upload.")
        return 0

    # Group records by target namespace
    records_by_namespace = {}
    for record in records:
        prompt_type = record['metadata'].get('prompt_type')
        target_namespace = default_namespace
        if prompt_type == 'MOMENT' and moment_namespace:
            target_namespace = moment_namespace
        elif prompt_type == 'CONTEXTUAL' and contextual_namespace:
            target_namespace = contextual_namespace

        if target_namespace not in records_by_namespace:
            records_by_namespace[target_namespace] = []
        records_by_namespace[target_namespace].append(record)

    total_uploaded_count = 0
    
    if dry_run:
        print(f"🧪 DRY RUN: Preparing to process {len(records)} records for index '{index_name}'.")
        for namespace, ns_records in records_by_namespace.items():
            print(f"  ➡️  Would upload {len(ns_records)} records to namespace '{namespace}'")
            if ns_records:
                sample = ns_records[0].copy()
                sample['values'] = f"[{len(sample['values'])} dimensions]" # Truncate vector
                print(f"    Sample record for namespace '{namespace}':")
                print(json.dumps(sample, indent=2, default=str))
        return 0

    index = pc.Index(index_name)
    
    for namespace, ns_records in records_by_namespace.items():
        if not ns_records:
            continue

        print(f"Uploading {len(ns_records)} records to Pinecone index '{index_name}', namespace '{namespace}'...")

        namespace_uploaded_count = 0
        for i in tqdm(range(0, len(ns_records), batch_size), desc=f"Uploading to {namespace}"):
            batch = ns_records[i:i + batch_size]
            try:
                index.upsert(vectors=batch, namespace=namespace)
                namespace_uploaded_count += len(batch)
            except Exception as e:
                print(f"❌ Error uploading batch to namespace '{namespace}': {e}")
                # Optionally, decide if you want to stop or continue with other namespaces/batches
                continue

        print(f"✅ Successfully uploaded {namespace_uploaded_count} records to namespace '{namespace}'")
        total_uploaded_count += namespace_uploaded_count

    print(f"✅ Total successfully uploaded records: {total_uploaded_count}")
    return total_uploaded_count

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Upload photo captions to Pinecone vector database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--captions',
                        required=True,
                        type=str,
                        help='Comma-separated list of caption types to upload (e.g., EMOTIONAL,CONTEXTUAL)')
    
    parser.add_argument('--input-file',
                        type=str,
                        default='lineage/multi_prompt_enrichment_output.csv',
                        help='Path to enrichment CSV file (default: %(default)s)')
    
    parser.add_argument('--lineage-file',
                        type=str,
                        default='lineage/complete_image_lineage.csv',
                        help='Path to complete lineage CSV file (default: %(default)s)')
    
    parser.add_argument('--index-name',
                        type=str,
                        default='adas-memory-qa-prod', # Updated default index name
                        help='Pinecone index name (default: %(default)s)')
    
    parser.add_argument('--namespace',
                        type=str,
                        default='photo-captions',
                        help='Default Pinecone namespace (default: %(default)s)')

    parser.add_argument('--moment-namespace',
                        type=str,
                        help='Pinecone namespace for MOMENT captions (overrides default)')

    parser.add_argument('--contextual-namespace',
                        type=str,
                        help='Pinecone namespace for CONTEXTUAL captions (overrides default)')
    
    parser.add_argument('--dry-run',
                        action='store_true',
                        help='Show what would be uploaded without actually uploading')
    
    parser.add_argument('--batch-size',
                        type=int,
                        default=90,
                        help='Embedding batch size (default: %(default)s)')
    
    return parser.parse_args()

def main():
    """Main execution function"""
    args = parse_arguments()
    
    # Parse caption types
    selected_captions = [caption.strip().upper() for caption in args.captions.split(',')]
    valid_captions = ['EMOTIONAL', 'MOMENT', 'CONTEXTUAL', 'STORY', 'CHARACTER']
    
    # Validate caption types
    invalid_captions = [c for c in selected_captions if c not in valid_captions]
    if invalid_captions:
        print(f"❌ Error: Invalid caption types: {invalid_captions}")
        print(f"   Valid options: {valid_captions}")
        return
    
    # Resolve file paths
    base_dir = Path(__file__).resolve().parent.parent
    enrichment_file = base_dir / args.input_file
    lineage_file = base_dir / args.lineage_file
    
    # Check file existence
    if not enrichment_file.exists():
        print(f"❌ Error: Enrichment file not found: {enrichment_file}")
        return
    
    if not lineage_file.exists():
        print(f"❌ Error: Lineage file not found: {lineage_file}")
        return
    
    # Initialize Pinecone
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ Error: PINECONE_API_KEY not found in environment variables")
        print("   Please check your .env file")
        return
    
    pc = Pinecone(api_key=api_key)
    
    # Configuration
    model_name = "llama-text-embed-v2"  # Same as Q&A system
    
    print("=" * 80)
    print("🚀 STARTING PHOTO CAPTION UPLOAD TO PINECONE")
    print("=" * 80)
    print(f"📄 Enrichment file: {args.input_file}")
    print(f"📄 Lineage file: {args.lineage_file}")
    print(f"🏷️  Caption types: {selected_captions}")
    print(f"🗂️  Index: {args.index_name}")
    print(f"📁 Default Namespace: {args.namespace}")
    if args.moment_namespace:
        print(f"💅 MOMENT Namespace: {args.moment_namespace}")
    if args.contextual_namespace:
        print(f"🖼️  CONTEXTUAL Namespace: {args.contextual_namespace}")
    print(f"🤖 Embedding model: {model_name}")
    print(f"🧪 Dry run: {'Yes' if args.dry_run else 'No'}")
    print("-" * 80)
    
    try:
        # Step 1: Load and merge data
        merged_df = load_and_merge_data(enrichment_file, lineage_file, selected_captions)
        
        if len(merged_df) == 0:
            print("❌ No records found to upload. Check your caption types and data.")
            return
        
        # Step 2: Generate embeddings
        caption_texts = merged_df['prompt_answer'].tolist()
        embeddings = generate_embeddings_in_batches(caption_texts, pc, model_name, args.batch_size)
        
        # Step 3: Prepare Pinecone records
        pinecone_records = prepare_pinecone_records(merged_df, embeddings)
        
        # Step 4: Upload to Pinecone
        uploaded_count = upload_to_pinecone(
            pinecone_records,
            pc,
            args.index_name,
            args.namespace,  # Default namespace
            args.moment_namespace,
            args.contextual_namespace,
            args.dry_run,
            args.batch_size
        )
        
        print("\n" + "=" * 80)
        print("🎉 UPLOAD COMPLETE!")
        print("=" * 80)
        print(f"📊 Records processed: {len(merged_df)}")
        print(f"✅ Records uploaded: {uploaded_count}")
        if not args.dry_run:
            print(f"🔍 You can now search for photo captions in namespace '{args.namespace}'")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error during upload process: {e}")
        raise

if __name__ == '__main__':
    main()