#!/usr/bin/env python3
"""
Complete Pipeline Verification Script
Tests each step of the photo search pipeline independently
"""

import os
import json
import requests
from pinecone import Pinecone
from dotenv import load_dotenv

def test_step_1_api_connectivity():
    """Test Step 1: API is reachable and handles requests"""
    print("🔍 STEP 1: Testing API Connectivity")
    print("-" * 50)
    
    api_url = "https://adas-living-story-qs8gt8lg9-joel-swensons-projects.vercel.app/api/search"
    
    try:
        # Use a real Ada-related query that should match
        response = requests.post(api_url, 
            json={"query": "What was Ada like as a person?", "limit": 1},
            headers={"Content-Type": "application/json", "Origin": "https://adas-spark.org"},
            timeout=15
        )
        
        if response.status_code == 200:
            print("✅ API reachable and responding")
            data = response.json()
            
            # Check for lowScore response
            if data.get('lowScore'):
                print(f"⚠️  Low similarity response: {data.get('message')}")
                return False, None
            
            if 'results' in data:
                print("✅ API returns expected structure")
                if data['results']:
                    result = data['results'][0]
                    print(f"✅ Q&A search working (found: {result['question_text']})")
                    print(f"✅ Similarity score: {result.get('score', 0):.3f}")
                    
                    # Check if answers exist
                    answers = result.get('answers', [])
                    if answers:
                        print(f"✅ Found {len(answers)} answer(s)")
                        answer = answers[0]
                        photos = answer.get('related_photos', [])
                        print(f"📷 Related photos: {len(photos)}")
                        
                        if len(photos) > 0:
                            print("✅ PHOTOS ARE WORKING!")
                            # Show photo details
                            for i, photo in enumerate(photos[:2]):
                                print(f"   Photo {i+1}: {photo.get('caption_type', 'Unknown')} - {photo.get('caption_moment', 'No caption')[:40]}...")
                            return True, result
                        else:
                            print("❌ No photos returned (this is our main issue)")
                            return True, result  # API works, but photos don't
                    else:
                        print("❌ No answers in result")
                        return False, None
                else:
                    print("❌ Empty results array")
                    return False, None
        else:
            print(f"❌ API error: {response.status_code}")
            print(f"Response: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"❌ API connection failed: {e}")
        return False, None

def test_step_2_qa_search():
    """Test Step 2: Q&A search is finding good matches"""
    print("\n🔍 STEP 2: Testing Q&A Search Quality")
    print("-" * 50)
    
    queries = [
        "What was Ada like as a person?",
        "How did Ada show bravery?",
        "What made Ada laugh?"
    ]
    
    api_url = "https://adas-living-story-qs8gt8lg9-joel-swensons-projects.vercel.app/api/search"
    
    for query in queries:
        try:
            response = requests.post(api_url, 
                json={"query": query, "limit": 1},
                headers={"Content-Type": "application/json", "Origin": "https://adas-spark.org"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results'):
                    result = data['results'][0]
                    score = result.get('score', 0)
                    question = result.get('question_text', '')
                    
                    print(f"Query: '{query}'")
                    print(f"  Match: '{question}' (score: {score:.3f})")
                    
                    if score > 0.7:
                        print("  ✅ Good match")
                    elif score > 0.5:
                        print("  ⚠️  Decent match")
                    else:
                        print("  ❌ Poor match")
                        
                    # Check if answer has photos
                    answers = result.get('answers', [])
                    if answers:
                        photos = answers[0].get('related_photos', [])
                        print(f"  📷 Photos: {len(photos)}")
                    else:
                        print("  ❌ No answers found")
                else:
                    print(f"❌ No results for: '{query}'")
        except Exception as e:
            print(f"❌ Error testing '{query}': {e}")

def test_step_3_photo_namespace():
    """Test Step 3: Photo namespace accessibility"""
    print("\n🔍 STEP 3: Testing Photo Namespace")
    print("-" * 50)
    
    load_dotenv()
    
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("adas-memory-qa-poc")
        
        # Check namespace stats
        stats = index.describe_index_stats()
        print(f"Total vectors: {stats.total_vector_count}")
        
        if hasattr(stats, 'namespaces') and stats.namespaces:
            if 'photo-captions' in stats.namespaces:
                photo_count = stats.namespaces['photo-captions'].vector_count
                print(f"✅ photo-captions namespace: {photo_count} vectors")
                
                if photo_count > 0:
                    print("✅ Photos are uploaded")
                    return True
                else:
                    print("❌ No photos in namespace")
                    return False
            else:
                print("❌ photo-captions namespace missing")
                print(f"Available: {list(stats.namespaces.keys())}")
                return False
        else:
            print("❌ No namespace data available")
            return False
            
    except Exception as e:
        print(f"❌ Namespace test failed: {e}")
        return False

def test_step_4_photo_search_direct():
    """Test Step 4: Direct photo search with sample embedding"""
    print("\n🔍 STEP 4: Testing Direct Photo Search")
    print("-" * 50)
    
    load_dotenv()
    
    try:
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("adas-memory-qa-poc")
        
        # Generate test embedding
        test_text = "happy energetic strong-willed child"
        embedding_response = pc.inference.embed(
            model="llama-text-embed-v2",
            inputs=[test_text],
            parameters={"input_type": "query"}
        )
        
        if hasattr(embedding_response[0], 'values'):
            query_vector = embedding_response[0].values
        else:
            query_vector = embedding_response[0]
            
        print(f"✅ Generated embedding (dim: {len(query_vector)})")
        
        # Test basic namespace query
        results = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True,
            namespace="photo-captions"
        )
        
        print(f"📊 Found {len(results.matches)} photos in namespace")
        
        if results.matches:
            print("✅ Namespace query working")
            
            # Test prompt_type filters
            moment_results = index.query(
                vector=query_vector,
                top_k=3,
                include_metadata=True,
                namespace="photo-captions",
                filter={"prompt_type": "MOMENT"}
            )
            
            contextual_results = index.query(
                vector=query_vector,
                top_k=3,
                include_metadata=True,
                namespace="photo-captions",
                filter={"prompt_type": "CONTEXTUAL"}
            )
            
            print(f"📊 MOMENT filter: {len(moment_results.matches)} results")
            print(f"📊 CONTEXTUAL filter: {len(contextual_results.matches)} results")
            
            if len(moment_results.matches) > 0 and len(contextual_results.matches) > 0:
                print("✅ Both filters working")
                
                # Check metadata structure
                sample = results.matches[0].metadata
                required_fields = ['wordpress_thumbnail', 'wordpress_url', 'caption_text', 'prompt_type']
                missing_fields = [field for field in required_fields if field not in sample]
                
                if not missing_fields:
                    print("✅ Photo metadata has required fields")
                    return True
                else:
                    print(f"❌ Missing metadata fields: {missing_fields}")
                    return False
            else:
                print("❌ Filters not working properly")
                return False
        else:
            print("❌ No photos found in namespace")
            return False
            
    except Exception as e:
        print(f"❌ Direct photo search failed: {e}")
        return False

def test_step_5_api_logs_check():
    """Test Step 5: Instructions for checking API logs"""
    print("\n🔍 STEP 5: API Logs Analysis")
    print("-" * 50)
    print("To debug the API photo search:")
    print("1. Go to https://vercel.com")
    print("2. Navigate to your project")
    print("3. Click 'Functions' tab")
    print("4. Find recent function calls")
    print("5. Look for these log messages:")
    print("   - 'Getting photos for answer...'")
    print("   - 'Got embedding, dimension: 1024'")
    print("   - 'Test query results: X matches'")
    print("   - 'Returning X photos'")
    print("")
    print("If you don't see these logs, the photo function isn't being called.")
    print("If you see errors, that's where the issue is.")

def main():
    print("🚀 COMPLETE PIPELINE VERIFICATION")
    print("=" * 60)
    
    # Test each step
    step1_ok, sample_result = test_step_1_api_connectivity()
    
    if step1_ok:
        test_step_2_qa_search()
        
        step3_ok = test_step_3_photo_namespace()
        
        if step3_ok:
            step4_ok = test_step_4_photo_search_direct()
            
            if step4_ok:
                print("\n✅ All local tests passed!")
                print("If photos still don't appear, check API logs (Step 5)")
            else:
                print("\n❌ Photo search failing at Pinecone level")
        else:
            print("\n❌ Photo namespace issues detected")
    
    test_step_5_api_logs_check()
    
    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE")

if __name__ == '__main__':
    main()