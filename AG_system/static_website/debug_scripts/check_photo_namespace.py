#!/usr/bin/env python3
"""
Quick test of your photo-captions namespace
"""

import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
index = pc.Index("adas-memory-qa-poc")

# Check namespace stats
stats = index.describe_index_stats()
print("📊 Index stats:")
print(f"Total vectors: {stats.total_vector_count}")

if hasattr(stats, 'namespaces') and stats.namespaces:
    print(f"Namespaces: {list(stats.namespaces.keys())}")
    
    if 'photo-captions' in stats.namespaces:
        photo_count = stats.namespaces['photo-captions'].vector_count
        print(f"✅ photo-captions namespace: {photo_count} vectors")
    else:
        print("❌ photo-captions namespace NOT FOUND")
        print("Available namespaces:", list(stats.namespaces.keys()))
else:
    print("❌ No namespace information available")

# Try a simple query
print("\n🔍 Testing simple query...")
try:
    # Just query anything to see if namespace responds
    test_results = index.query(
        vector=[0.1] * 1024,  # Dummy vector
        top_k=3,
        include_metadata=True,
        namespace="photo-captions"
    )
    
    print(f"Found {len(test_results.matches)} results in photo-captions namespace")
    
    if test_results.matches:
        for i, match in enumerate(test_results.matches):
            print(f"  {i+1}. ID: {match.id}")
            print(f"     Metadata keys: {list(match.metadata.keys())}")
            print(f"     prompt_type: {match.metadata.get('prompt_type', 'MISSING')}")
            
except Exception as e:
    print(f"❌ Error querying photo-captions namespace: {e}")