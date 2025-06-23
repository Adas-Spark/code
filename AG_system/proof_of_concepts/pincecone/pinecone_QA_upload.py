#!/usr/bin/env python
# coding: utf-8

# Ada's Spark Memory Pinecone Upload Script
# This script implements uploading Q&A pairs to a Pinecone vector database.

# ## Setup Instructions
#
# ### 1. Install Required Packages
#
# Run the following in your terminal:
# ```
# pip install --upgrade pinecone python-dotenv tqdm pandas numpy
# ```
#
# ### 2. Create a .env File
#
# Create a file named `.env` in the same directory as this script with your Pinecone API key:
# ```
# PINECONE_API_KEY=your_api_key_here
# ```
#
# ### 3. Run the Script
#
# Execute the script from your terminal: `python pinecone_QA_upload.py`

import json
import os
import numpy as np
import pandas as pd
from tqdm.auto import tqdm
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import time

def main():
    # Load environment variables from .env file
    load_dotenv()

    # Initialize Pinecone client using API key from environment variables
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        raise ValueError("PINECONE_API_KEY not found in environment variables. Please check your .env file.")

    pc = Pinecone(api_key=api_key)

    # Define the input JSON file
    input_json_file = 'generated_qa_pairs_combined_clean_20250603_214922_enriched.json'
    # Note: The script is in AG_system/proof_of_concepts/pincecone/
    # The data is in AG_system/proof_of_concepts/

    # Load your JSON file
    print(f"Loading data from {input_json_file}...")
    with open(input_json_file, 'r') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} questions.")

    # Define the embedding model to use
    model_name = "llama-text-embed-v2" # Pinecone's new default embedding model
    model_dimension = 1024 # For llama-text-embed-v2
    print(f"Using embedding model: {model_name} with dimension {model_dimension}")

    # Test the embedding API
    try:
        test_embed_response = pc.inference.embed(
            model=model_name,
            inputs=["This is a test sentence."],
            parameters={"input_type": "query"} # or "passage" / "document" depending on use case
        )
        # The response is a list of Embedding objects
        if test_embed_response and hasattr(test_embed_response[0], 'values'):
            actual_dimension = len(test_embed_response[0].values)
            print(f"✅ Embedding API test successful! Produced a vector with dimension: {actual_dimension}")
            if actual_dimension != model_dimension:
                print(f"⚠️ Warning: Actual dimension ({actual_dimension}) doesn't match expected ({model_dimension}). Using actual.")
                model_dimension = actual_dimension
        else:
            print(f"❌ Embedding API test returned unexpected response: {test_embed_response}")
            raise ValueError("Embedding API test failed to return valid embedding structure.")

    except Exception as e:
        print(f"❌ Embedding API test failed: {str(e)}")
        print("  Check your API key and model availability in your Pinecone account.")
        raise

    # Define index name
    index_name = "adas-memory-qa-prod"

    # Check if the index already exists and delete it if needed
    # For production, we might want to update or skip this step.
    # For this script, we'll delete and recreate for a clean upload.
    if index_name in [index.name for index in pc.list_indexes()]:
        print(f"Deleting existing index: {index_name}...")
        pc.delete_index(index_name)
        print(f"Waiting for index '{index_name}' to be deleted...")
        while index_name in [index.name for index in pc.list_indexes()]:
            time.sleep(5)
        print(f"Index '{index_name}' deleted.")


    # Create a new Pinecone serverless index
    print(f"Creating new index: {index_name} with dimension {model_dimension}...")
    pc.create_index(
        name=index_name,
        dimension=model_dimension,
        metric="cosine",
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1" # Choose the region closest to you
        )
    )
    print(f"Index '{index_name}' creation initiated.")

    # Wait for the index to be ready
    print(f"Waiting for index '{index_name}' to be ready...")
    while not pc.describe_index(index_name).status['ready']:
        time.sleep(5)
    print(f"Index '{index_name}' is ready.")

    # Connect to the newly created index
    index = pc.Index(index_name)
    index_stats = index.describe_index_stats()
    print(f"Connected to index. Initial stats: {index_stats}")

    # Prepare data for insertion - We will embed only the question text.
    # Answers and their detailed source information will be stored in metadata.
    pinecone_records_to_insert = []
    texts_to_embed = [] # This will now only contain question texts

    print("Preparing records for Pinecone insertion (embedding questions only)...")
    for question_block in tqdm(data, desc="Processing question blocks"):
        question_id = question_block['question_id']
        question_text = question_block['question_text']
        category = question_block['category']

        # The text to be embedded is just the question
        texts_to_embed.append(question_text)

        # Process answers while preserving array structure for source fields
        processed_answers = []
        for ans in question_block['answers']:
            processed_ans = ans.copy()
            
            # Handle source fields that might be arrays or single values
            for field in ["source_post_id", "source_date", "source_title", "source_url"]:
                value = ans.get(field, "")
                
                if isinstance(value, list):
                    # If it's already a list, keep it as is
                    processed_ans[field] = value
                elif value:
                    # If it's a non-empty string, keep it as is
                    processed_ans[field] = value
                else:
                    # If it's empty or None, set to empty string
                    processed_ans[field] = ""
            
            processed_answers.append(processed_ans)
            
        # Metadata will include the question text, category, and all answers (with their sources) as a JSON string.
        metadata = {
            "question_text": question_text,
            "category": category,
            "answers_json": json.dumps(processed_answers) # Store all answers here
        }

        # The vector ID is the question_id
        pinecone_records_to_insert.append({"id": question_id, "metadata": metadata})

    print(f"Prepared {len(pinecone_records_to_insert)} question records for embedding and insertion.")

    # Generate embeddings in batches for question texts
    def generate_embeddings_in_batches(texts, model, batch_size=90):
        all_embeddings = []

        for i in tqdm(range(0, len(texts), batch_size), desc="Generating embeddings"):
            batch_texts = texts[i:i + batch_size]
            response = pc.inference.embed(
                model=model,
                inputs=batch_texts,
                parameters={"input_type": "query"}
            )
            batch_embeddings = [embedding.values for embedding in response]
            all_embeddings.extend(batch_embeddings)
            time.sleep(0.1) # Be nice to the API
        return all_embeddings

    print(f"Generating embeddings for {len(texts_to_embed)} question texts...")
    embeddings = generate_embeddings_in_batches(texts_to_embed, model_name)
    print(f"Generated {len(embeddings)} embeddings.")

    # Add embeddings to the records
    for i, record in enumerate(pinecone_records_to_insert):
        record["values"] = embeddings[i]

    # Insert the data into Pinecone in batches
    batch_size = 100 # Pinecone's recommended max batch size for upsert
    print(f"Inserting {len(pinecone_records_to_insert)} records into Pinecone index '{index_name}'...")
    for i in tqdm(range(0, len(pinecone_records_to_insert), batch_size), desc="Upserting to Pinecone"):
        batch_records = pinecone_records_to_insert[i:i + batch_size]
        index.upsert(vectors=batch_records) # No namespace for Q&A data, uses default

    print("Insertion process complete.")

    # Wait a moment for indexing to settle
    print("Waiting for indexing to settle (approx 60 seconds)...")
    time.sleep(60)

    # Verify insertion
    final_index_stats = index.describe_index_stats()
    print(f"Index '{index_name}' now contains {final_index_stats.get('total_vector_count', 'N/A')} vectors.")

    expected_vector_count = len(data) # One vector per question block
    if final_index_stats.get('total_vector_count', 0) == expected_vector_count:
        print("✅ Successfully inserted all question records.")
    else:
        print(f"⚠️ Discrepancy in vector count. Expected: {expected_vector_count}, Found: {final_index_stats.get('total_vector_count', 'N/A')}")
        print("   This might be due to indexing delays or other issues. Please verify in Pinecone console.")

    print("Script finished.")

if __name__ == "__main__":
    main()
