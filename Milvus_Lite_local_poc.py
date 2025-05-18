#!/usr/bin/env python
# coding: utf-8

# ### Core requirements
# numpy==1.24.3  # Must use NumPy 1.x for compatibility with current PyTorch
# 
# pymilvus>=2.2.0
# 
# sentence-transformers>=2.2.2
# 
# ### Python version: 3.10.x recommended
# Note: Python 3.13 is not compatible with PyTorch required by sentence-transformers
# 
# ### Additional packages
# jupyter

# In[1]:


# Import necessary libraries
import json
import numpy as np
from pymilvus import MilvusClient
from pymilvus import model
from sentence_transformers import SentenceTransformer


# In[2]:


# Load your JSON file
with open('example_QA_output.json', 'r') as f:
    data = json.load(f)


# In[3]:


# Extract question data
print(f"Loaded {len(data)} questions:")
for item in data:
    print(f"{item['question_id']}: {item['question_text']} ({len(item['answers'])} answers)")


# In[4]:


# Create a Milvus Lite instance
client = MilvusClient("questions_db.db")


# In[5]:


# Use a more powerful model through SentenceTransformers directly
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Better for semantic search

# Get the model dimension right away
model_dimension = embedding_model.get_sentence_embedding_dimension()
print(model_dimension)


# In[6]:


# Check if the collection already exists, and delete it if it does
if client.has_collection(collection_name="questions_collection"):
    client.drop_collection(collection_name="questions_collection")


# In[7]:


# Create a new collection with the correct dimension
client.create_collection(
    collection_name="questions_collection",
    dimension=model_dimension,  # Use the dimension from the model
    metric_type="COSINE"  # Change this to select a different metric
)
print(f"Created collection with dimension: {model_dimension}")


# In[8]:


# Generate embeddings for all questions
questions = [item['question_text'] for item in data]
embeddings = embedding_model.encode(questions, normalize_embeddings=True)
print("Note that you may or may not want to normalize embeddings depending on a few factors, just make sure if you normalize here you normalize the query as well")

# Print the actual dimension to verify
print(f"Actual embedding dimension: {len(embeddings[0])}")


# In[9]:


# Prepare data for insertion with answers as JSON
milvus_data = [
    {
        "id": i,
        "vector": embeddings[i],
        "question_id": data[i]['question_id'],
        "question_text": data[i]['question_text'],
        "category": data[i]['category'],
        "answers_json": json.dumps(data[i]['answers'])  # Store answers as JSON string
    }
    for i in range(len(data))
]


# In[10]:


# Insert the data into the collection
result = client.insert(collection_name="questions_collection", data=milvus_data)
print(f"Inserted {result['insert_count']} records with vector dimension {len(embeddings[0])}")


# In[11]:


# Function to search for similar questions
def search_similar_questions(query_text, limit=5, include_answers=True, normalize_embeddings=True):
    """
    Search for questions similar to the query text
    
    Parameters:
    - query_text: The text to search for
    - limit: Maximum number of results to return
    - include_answers: Whether to include answers in the results
    - normalize_embeddings: Whether to normalize the query embeddings (default: True)

    Returns:
    - List of matching questions with their data
    """
    query_embedding = embedding_model.encode([query_text], normalize_embeddings=normalize_embeddings)
    
    output_fields = ["question_id", "question_text", "category"]
    if include_answers:
        output_fields.append("answers_json")
    
    results = client.search(
        collection_name="questions_collection",
        data=query_embedding,
        limit=limit,
        output_fields=output_fields
    )
    
    # Parse the JSON string back to a list if answers are included
    if include_answers and results and results[0]:
        for res in results[0]:
            if "answers_json" in res["entity"]:
                res["entity"]["answers"] = json.loads(res["entity"]["answers_json"])
                del res["entity"]["answers_json"]  # Remove the JSON string field
    
    return results[0]


# In[ ]:





# In[12]:


# Test the search function
#test_query = "What was Ada like as a person?"
test_query = "What was Ada's personality like?"
search_results = search_similar_questions(test_query)

print("\nTest Search Results:")
print(f"Query: '{test_query}'")
print("Top matches:")
for result in search_results:
    print(f"Question ID: {result['entity']['question_id']}")
    print(f"Question: {result['entity']['question_text']}")
    print(f"Category: {result['entity']['category']}")
    print(f"Similarity Score: {1-result['distance']:.4f}")
    
    if "answers" in result["entity"]:
        print(f"Number of answers: {len(result['entity']['answers'])}")
        # Show first answer as example
        if result['entity']['answers']:
            first_answer = result['entity']['answers'][0]
            print(f"First answer: {first_answer['answer_text'][:100]}...")  # Show first 100 chars
    print("---")


# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:





# In[ ]:




